import json
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from config.settings import settings

log = logging.getLogger("ai-property-advisor")


class ModelRegistry:
    """
    Model Registry — Track RPM/RPD cho mỗi model.
    
    Theo design doc:
    - Primary: gemini-3.1-flash-lite (RPM: 15, TPM: 250K, RPD: 500)
    - Fallback: gemma-4-26b-a4b-it (RPM: 15, TPM: Unlimited, RPD: 1,500)
    
    Decision matrix:
    1. Check primary RPM/RPD → available? → call primary
    2. Primary fail → check fallback RPM/RPD → available? → call fallback
    3. Both unavailable → return None (caller uses template)
    """

    MODELS = {
        "gemini-2.0-flash": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 1},
        "gemini-2.0-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 2},
        "gemini-3.6-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 3},
        "gemini-3.5-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 4},
    }

    def __init__(self):
        self._rpm_tracker: Dict[str, List[float]] = {}  # model_id -> [timestamps for RPM]
        self._rpd_tracker: Dict[str, List[float]] = {}  # model_id -> [timestamps for RPD]
        self._total_calls: Dict[str, int] = {}
        self._total_tokens: Dict[str, int] = {}
        self._fallback_count: Dict[str, int] = {}

    def check_available(self, model_id: str) -> bool:
        """Check if model is available (under RPM and RPD limits)"""
        if model_id not in self.MODELS:
            return False

        now = time.time()
        model_spec = self.MODELS[model_id]
        rpm_limit = model_spec["rpm"]
        rpd_limit = model_spec["rpd"]

        # Clean old RPM entries (last 60s)
        rpm_ts = self._rpm_tracker.get(model_id, [])
        rpm_ts = [ts for ts in rpm_ts if ts > now - 60]
        self._rpm_tracker[model_id] = rpm_ts

        # Clean old RPD entries (last 24h)
        rpd_ts = self._rpd_tracker.get(model_id, [])
        rpd_ts = [ts for ts in rpd_ts if ts > now - 86400]
        self._rpd_tracker[model_id] = rpd_ts

        if len(rpm_ts) >= rpm_limit:
            log.warning("Model %s: RPM limit reached (%d/%d)", model_id, len(rpm_ts), rpm_limit)
            return False
        if len(rpd_ts) >= rpd_limit:
            log.warning("Model %s: RPD limit reached (%d/%d)", model_id, len(rpd_ts), rpd_limit)
            return False

        return True

    def record_call(self, model_id: str, token_count: int = 0, is_fallback: bool = False) -> None:
        """Record a successful call to a model"""
        now = time.time()

        if model_id not in self._rpm_tracker:
            self._rpm_tracker[model_id] = []
        self._rpm_tracker[model_id].append(now)

        if model_id not in self._rpd_tracker:
            self._rpd_tracker[model_id] = []
        self._rpd_tracker[model_id].append(now)

        self._total_calls[model_id] = self._total_calls.get(model_id, 0) + 1
        self._total_tokens[model_id] = self._total_tokens.get(model_id, 0) + token_count

        if is_fallback:
            self._fallback_count[model_id] = self._fallback_count.get(model_id, 0) + 1

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for monitoring"""
        stats = {}
        for model_id in self.MODELS:
            now = time.time()
            rpm_ts = [ts for ts in self._rpm_tracker.get(model_id, []) if ts > now - 60]
            rpd_ts = [ts for ts in self._rpd_tracker.get(model_id, []) if ts > now - 86400]
            stats[model_id] = {
                "current_rpm": len(rpm_ts),
                "current_rpd": len(rpd_ts),
                "total_calls": self._total_calls.get(model_id, 0),
                "total_tokens": self._total_tokens.get(model_id, 0),
                "fallback_calls": self._fallback_count.get(model_id, 0),
                "rpm_limit": self.MODELS[model_id]["rpm"],
                "rpd_limit": self.MODELS[model_id]["rpd"],
                "available": self.check_available(model_id),
            }
        return stats

    def select_model(self) -> Optional[str]:
        """
        Select the best available model based on priority.
        Returns model_id or None if no model available.
        """
        sorted_models = sorted(self.MODELS.items(), key=lambda x: x[1]["priority"])
        for model_id, _ in sorted_models:
            if self.check_available(model_id):
                return model_id
        return None


class GeminiService:
    @property
    def model(self) -> str:
        return settings.GEMINI_MODEL

    @property
    def fallback_model(self) -> str:
        return settings.GEMINI_FALLBACK_MODEL

    def __init__(self):
        self._client = None
        self.temperature = settings.GEMINI_TEMPERATURE
        self._timeout = settings.GEMINI_TIMEOUT
        self._max_retries = 2
        self.registry = ModelRegistry()

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _safe_text(self, response) -> str:
        if response.text:
            return response.text.strip()
        if response.candidates:
            c = response.candidates[0]
            if c.content and c.content.parts:
                return ''.join(p.text for p in c.content.parts if p.text).strip()
        return ''

    async def _call_with_retry(self, model: str, contents: str, config) -> Any:
        """
        Call LLM with retry + fallback chain:
        1. Try primary model (retry 2x with exponential backoff)
        2. If primary fail → try fallback model
        3. If both fail → raise exception
        """
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini client not initialized")

        last_exc = None
        primary_used = model
        is_fallback = False

        # Step 1: Try primary with retries
        for attempt in range(self._max_retries):
            if not self.registry.check_available(model):
                log.debug("Model %s: rate limited, trying fallback", model)
                break
            try:
                result = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model, contents=contents, config=config
                    ),
                    timeout=self._timeout,
                )
                # Only record call AFTER successful response
                self.registry.record_call(model)
                return result
            except Exception as e:
                last_exc = e
                if attempt < self._max_retries - 1:
                    wait = (2 ** attempt) + 1
                    log.debug("Retrying model %s (attempt %d/%d) after %ds: %s",
                              model, attempt + 1, self._max_retries, wait, str(e)[:60])
                    await asyncio.sleep(wait)

        # Step 2: Try fallback model cascade
        fallback_candidates = [self.fallback_model, "gemini-2.0-flash-lite", "gemini-2.0-flash-lite-001", "gemini-2.5-pro"]
        for fb_model in fallback_candidates:
            if not fb_model or fb_model == model:
                continue
            is_fallback = True
            log.info("Primary model %s failed, trying fallback %s", model, fb_model)
            try:
                await asyncio.sleep(1.0)
                result = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=fb_model, contents=contents, config=config
                    ),
                    timeout=self._timeout,
                )
                self.registry.record_call(fb_model, is_fallback=True)
                return result
            except Exception as fb_err:
                log.warning("Fallback model %s failed: %s", fb_model, fb_err)

        raise last_exc or RuntimeError(f"All models failed after retries (primary={primary_used}, fallback={is_fallback})")

    async def generate_action_descriptions(self, actions_data: Dict[str, Any]) -> Dict[str, Any]:
        from src.services.prompt_templates import ACTION_WRITER_PROMPT
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=2048,
            system_instruction=ACTION_WRITER_PROMPT,
        )
        user_content = f"DỮ LIỆU:\n{json.dumps(actions_data, ensure_ascii=False, default=str)}\n\nHÃY VIẾT MÔ TẢ CHO CÁC HÀNH ĐỘNG TRÊN (trả về JSON):"
        response = await self._call_with_retry(
            model=self.model,
            contents=user_content,
            config=config,
        )
        content = self._safe_text(response)
        try:
            cleaned = content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"priority_action": {"description": "", "quick_action_label": ""}, "other_recommendations": []}

    async def generate_text_to_sql(self, question: str, context_summary: str = "",
                                     few_shot_examples: str = "", schema_subset: str = "") -> str:
        from src.services.prompt_templates import TEXT_TO_SQL_SYSTEM_PROMPT
        from google.genai import types

        schema_block = f"\n\nSCHEMA LIÊN QUAN:\n{schema_subset}" if schema_subset else ""
        sys_inst = f"{TEXT_TO_SQL_SYSTEM_PROMPT}{schema_block}{few_shot_examples}"
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1280,
            system_instruction=sys_inst,
        )

        history_block = f"\n\nLỊCH SỬ HỘI THOẠI:\n{context_summary}\n" if context_summary else ""

        user_content = f"""{history_block}
YÊU CẦU:
Dịch câu hỏi sau thành câu lệnh SQL (MySQL). Chỉ trả về SQL, không giải thích.

Câu hỏi: "{question}"

SQL:"""
        try:
            response = await asyncio.wait_for(
                self._call_with_retry(model=self.model, contents=user_content, config=config),
                timeout=30.0,
            )
            return self._safe_text(response)
        except asyncio.TimeoutError:
            return "SELECT 1 AS result WHERE 1=0 -- timeout"

    @staticmethod
    def _parse_mysql_error(error_str: str) -> Dict[str, Any]:
        """
        Parse MySQL error message thành structured data để Gemini dễ sửa hơn.
        
        Input: "(pymysql.err.OperationalError) (1054, \"Unknown column 'x' in 'field list'\")"
        Output: {
            "type": "COLUMN_NOT_FOUND",
            "mysql_code": 1054,
            "element": "x",
            "context": "field list",
            "description": "Cột 'x' không tồn tại",
            "suggestion": "Kiểm tra tên cột trong bảng, dùng SHOW COLUMNS hoặc xem DDL"
        }
        """
        import re
        error_lower = error_str.lower()
        result = {
            "raw": error_str[:300],
            "type": "UNKNOWN",
            "mysql_code": None,
            "element": None,
            "context": None,
            "description": error_str[:200],
            "suggestion": "Kiểm tra cú pháp SQL và tên bảng/cột",
        }

        # Extract MySQL error code
        code_match = re.search(r'\((\d+)\)', error_str)
        if code_match:
            result["mysql_code"] = int(code_match.group(1))

        # Error type classification + extraction
        # 1. Column not found (MySQL 1054)
        if "unknown column" in error_lower:
            result["type"] = "COLUMN_NOT_FOUND"
            col_match = re.search(r"unknown column '([^']+)'", error_lower)
            if col_match:
                result["element"] = col_match.group(1)
                result["description"] = f"Cột '{result['element']}' không tồn tại"
            context_match = re.search(r"in '([^']+)'", error_lower)
            if context_match:
                result["context"] = context_match.group(1)
            result["suggestion"] = (
                f"Cột '{result.get('element', '?')}' không tồn tại trong {result.get('context', 'bảng')}. "
                "Kiểm tra tên cột trong DDL (invoice_lines.line_type, invoices.status, rooms.current_status...). "
                "Dùng COALESCE để tránh NULL. Kiểm tra alias đã được định nghĩa chưa."
            )

        # 2. Table not found (MySQL 1146)
        elif "table" in error_lower and "doesn't exist" in error_lower:
            result["type"] = "TABLE_NOT_FOUND"
            tbl_match = re.search(r"table '([^']+)' doesn't exist", error_lower)
            if tbl_match:
                result["element"] = tbl_match.group(1)
                result["description"] = f"Bảng '{result['element']}' không tồn tại"
            result["suggestion"] = (
                f"Bảng '{result.get('element', '?')}' không tồn tại. "
                "Kiểm tra tên bảng trong DDL. Các bảng có sẵn: properties, rooms, users, person_profiles, "
                "tenants, lease_contracts, invoices, invoice_lines, payment_transactions, "
                "payment_allocations, maintenance_tickets, maintenance_costs, property_staff_assignments, "
                "meters, meter_readings, vacancy_logs, debt_snapshots, ai_chat_history. "
                "Dùng alias đúng: r=rooms, i=invoices, il=invoice_lines, pt=payment_transactions..."
            )

        # 3. Syntax error (MySQL 1064)
        elif "syntax" in error_lower or "error 1064" in error_lower:
            result["type"] = "SYNTAX_ERROR"
            pos_match = re.search(r"at line (\d+)", error_lower)
            if pos_match:
                result["element"] = f"line {pos_match.group(1)}"
                result["description"] = f"Lỗi cú pháp SQL tại {result['element']}"
            result["suggestion"] = (
                "Kiểm tra cú pháp MySQL:"
                "1. Dùng DATE_FORMAT(col, '%%Y-%%m') thay vì '%Y-%m' (%% để escape)"
                "2. Dùng COALESCE(col, 0) thay vì IFNULL(col, 0)"
                "3. Kiểm tra dấu nháy: dùng ' chuỗi, ` tên cột/bảng (hoặc không cần `)"
                "4. Kiểm tra JOIN: ON condition phải đúng cú pháp"
                "5. GROUP BY phải có tất cả cột không aggregate"
                "6. Giá trị chuỗi phải trong 'nháy đơn'"
            )

        # 4. Function not found (MySQL 1305 or 1630)
        elif "function" in error_lower and "does not exist" in error_lower:
            result["type"] = "FUNCTION_NOT_FOUND"
            fn_match = re.search(r"function ([^ ]+)", error_lower)
            if fn_match:
                result["element"] = fn_match.group(1)
                result["description"] = f"Hàm '{result['element']}' không tồn tại"
            result["suggestion"] = (
                "Kiểm tra tên hàm MySQL. Hàm thường dùng: "
                "DATE_FORMAT(), DATE_SUB(), DATE_ADD(), DATEDIFF(), CURDATE(), "
                "COALESCE(), ROUND(), SUM(), COUNT(), GROUP_CONCAT(). "
                "Không dùng hàm STRING_AGG (PostgreSQL) hay GROUP_CONCAT với ORDER BY sai cú pháp."
            )

        # 5. GROUP BY error (MySQL 1055)
        elif "group by" in error_lower or "1055" in error_lower:
            result["type"] = "GROUP_BY_ERROR"
            result["description"] = "Lỗi GROUP BY: cột không aggregate thiếu trong GROUP BY"
            result["suggestion"] = (
                "Thêm tất cả cột SELECT không aggregate vào GROUP BY. "
                "Hoặc dùng ANY_VALUE() cho các cột không cần group. "
                "VD: SELECT r.room_code, SUM(i.total_amount) FROM ... GROUP BY r.room_code"
            )

        # 6. Duplicate column (MySQL 1060)
        elif "duplicate column" in error_lower or "1060" in error_lower:
            result["type"] = "DUPLICATE_COLUMN"
            col_match = re.search(r"duplicate column name '([^']+)'", error_lower)
            if col_match:
                result["element"] = col_match.group(1)
                result["description"] = f"Cột '{result['element']}' bị trùng tên"
            result["suggestion"] = (
                "Đặt alias cho các cột trùng tên. VD: SELECT i.total_amount AS invoice_total, "
                "il.amount AS line_amount. Dùng alias khác nhau cho mỗi cột."
            )

        # 7. WHERE clause ambiguous (MySQL 1052)
        elif "ambiguous" in error_lower or "1052" in error_lower:
            result["type"] = "AMBIGUOUS_COLUMN"
            col_match = re.search(r"column '([^']+)' in (.*)", error_lower)
            if col_match:
                result["element"] = col_match.group(1)
                result["context"] = col_match.group(2)
                element_val = result.get('element', '?')
                result["description"] = "Cot '" + element_val + "' khong ro rang (co trong nhieu bang)"
            result["suggestion"] = (
                "Them alias bang vao ten cot. VD: thay vi 'status' dung 'i.status' hoac 'r.current_status'. "
                "Kiem tra cac bang trong JOIN de biet cot nao thuoc bang nao."
            )

        # 8. Data too long (MySQL 1406)
        elif "data too long" in error_lower or "1406" in error_lower:
            result["type"] = "DATA_TOO_LONG"
            result["description"] = "Dữ liệu quá dài cho cột"
            result["suggestion"] = "Dùng LEFT(column, n) hoặc CAST(column AS VARCHAR(n)) để cắt bớt dữ liệu."

        log.debug("Parsed MySQL error: type=%s code=%s element=%s",
                  result["type"], result["mysql_code"], result.get("element"))
        return result

    @staticmethod
    def _build_correction_guidance(parsed_error: Dict[str, Any], previous_sql: str) -> str:
        """
        Xây dựng hướng dẫn sửa lỗi chi tiết dựa trên error type.
        """
        error_type = parsed_error.get("type", "UNKNOWN")
        description = parsed_error.get("description", "Lỗi không xác định")
        suggestion = parsed_error.get("suggestion", "")
        element = parsed_error.get("element", "")

        guidance = f"▪ LỖI: {description}\n"
        guidance += f"▪ LOẠI: {error_type}\n"

        if element:
            guidance += f"▪ NGUYÊN NHÂN: {element}\n"

        guidance += f"▪ CÁCH SỬA: {suggestion}\n"

        # Thêm phân tích cụ thể dựa vào error type
        if error_type == "COLUMN_NOT_FOUND" and element:
            # Suggest common column names based on the context
            common_cols = {"status": "i.status, r.current_status, u.status, lc.status",
                          "total": "i.total_amount, pa.amount, pt.amount, mc.amount",
                          "amount": "pa.amount, i.total_amount, i.remaining_amount, pt.amount",
                          "name": "p.name, r.room_code, u.full_name, pp.full_name",
                          "date": "pt.transaction_time, i.due_date, i.issue_date, lc.start_date",
                          "period": "i.billing_period, mr.reading_period",
                          "room": "r.room_code, r.room_id",
                          "rent": "lc.monthly_rent, i.total_amount",
                          "debt": "i.remaining_amount, ds.rent_debt_amount",
                          }
            for keyword, cols in common_cols.items():
                if keyword in element.lower():
                    guidance += f"▪ CÓ THỂ BẠN MUỐN: {cols}\n"
                    break

        if error_type == "TABLE_NOT_FOUND" and element:
            # The element might have the wrong schema prefix
            if "." in element:
                parts = element.split(".")
                if len(parts) == 2:
                    guidance += f"▪ MẸO: Bỏ schema prefix '{parts[0]}.', chỉ dùng tên bảng '{parts[1]}'.\n"

        return guidance

    async def correct_sql(self, question: str, last_error: str, previous_sql: str,
                           context_summary: str = "", few_shot_examples: str = "",
                           schema_subset: str = "") -> str:
        """
        Self-correction: phân tích lỗi MySQL chi tiết + gửi cho Gemini để sửa.
        
        So với phiên bản cũ:
        - Parse error message → error type + element + suggestion
        - Thêm correction guidance dựa trên error type
        - Thêm DDL context cho bảng/cột liên quan đến lỗi
        """
        from src.services.prompt_templates import TEXT_TO_SQL_SYSTEM_PROMPT
        from google.genai import types

        # === Step 1: Parse error ===
        parsed = self._parse_mysql_error(last_error)
        guidance = self._build_correction_guidance(parsed, previous_sql)

        # === Step 2: Include relevant DDL context ===
        schema_block = ""
        if schema_subset:
            schema_block = f"\n\nSCHEMA LIÊN QUAN:\n{schema_subset}"

        sys_inst = f"{TEXT_TO_SQL_SYSTEM_PROMPT}{schema_block}"

        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1280,
            system_instruction=sys_inst,
        )

        user_content = f"""LẦN TRƯỚC bạn đã tạo SQL nhưng bị lỗi khi chạy trên MySQL. Hãy SỬA LẠI.

---
CÂU HỎI GỐC: {question}

---
SQL BỊ LỖI:
{previous_sql}

---
CHI TIẾT LỖI:
{guidance}

---
LỖI GỐC TỪ MYSQL:
{last_error[:500]}

---
YÊU CẦU:
1. Phân tích lỗi {parsed.get('type', 'UNKNOWN')} ở trên
2. Sửa SQL để khắc phục lỗi
3. Chỉ trả về SQL đã sửa, không giải thích, không markdown
4. Giữ nguyên cấu trúc SELECT và property_id = $1

SQL ĐÃ SỬA:"""
        try:
            response = await asyncio.wait_for(
                self._call_with_retry(model=self.model, contents=user_content, config=config),
                timeout=30.0,
            )
            return self._safe_text(response)
        except asyncio.TimeoutError:
            return "SELECT 1 AS result WHERE 1=0 -- timeout"

    async def generate_response(self, question: str, sql_result: List[Dict[str, Any]], chart_type: Optional[str] = None) -> str:
        from src.services.prompt_templates import RESPONSE_GENERATOR_PROMPT
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=1024,
            system_instruction=RESPONSE_GENERATOR_PROMPT,
        )
        user_content = f"""DỮ LIỆU:
{json.dumps({
            'question': question,
            'result': sql_result,
            'chart_type': chart_type,
        }, ensure_ascii=False, default=str)}

HÃY TRẢ LỜI NGAY (tiếng Việt, tự nhiên):"""
        response = await self._call_with_retry(
            model=self.model,
            contents=user_content,
            config=config,
        )
        return self._safe_text(response)

    async def select_visualization(self, sql_result: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
        from src.services.prompt_templates import VISUALIZATION_SELECTOR_PROMPT
        from google.genai import types

        if not sql_result:
            return {"type": "BIG_NUMBER", "title": "Không có dữ liệu", "data": []}

        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024,
            system_instruction=VISUALIZATION_SELECTOR_PROMPT,
        )
        sample = sql_result[:5]
        user_content = f"""DỮ LIỆU:
{json.dumps({
            'columns': columns,
            'sample_data': sample,
            'row_count': len(sql_result),
        }, ensure_ascii=False, default=str)}

HÃY CHỌN LOẠI BIỂU ĐỒ (trả về JSON):"""
        try:
            response = await self._call_with_retry(
                model=self.model,
                contents=user_content,
                config=config,
            )
            content = self._safe_text(response)
            cleaned = content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            return self._fallback_visualization(sql_result, columns)

    def _fallback_visualization(self, data: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
        if not data:
            return {"type": "BIG_NUMBER", "title": "Không có dữ liệu", "data": []}

        date_cols = [c for c in columns if any(kw in c.lower() for kw in ["date", "time", "month", "year", "period"])]
        numeric_cols = [c for c in columns if any(kw in c.lower() for kw in ["amount", "price", "revenue", "count", "rate", "score", "days", "loss", "total", "sum", "avg"])]
        categorical_cols = [c for c in columns if c not in date_cols and c not in numeric_cols]

        if date_cols and numeric_cols:
            chart_type = "LINE_CHART"
            x_axis = date_cols[0]
            y_axis = numeric_cols[0]
        elif categorical_cols and numeric_cols:
            chart_type = "BAR_CHART"
            x_axis = categorical_cols[0]
            y_axis = numeric_cols[0]
        elif len(numeric_cols) == 1 and len(data) == 1:
            chart_type = "BIG_NUMBER"
            x_axis = None
            y_axis = numeric_cols[0]
        else:
            chart_type = "TABLE"
            x_axis = columns[0] if columns else None
            y_axis = columns[1] if len(columns) > 1 else None

        return {
            "type": chart_type,
            "title": f"Kết quả truy vấn ({len(data)} dòng)",
            "x_axis": x_axis,
            "y_axis": y_axis,
            "data": data[:50],
        }

    async def generate_deep_analysis(
        self,
        question: str,
        kpi_context: Dict[str, Any],
        comparison_context: Dict[str, Any],
        trend_context: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
        history: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate deep analysis with Chain-of-Thought reasoning for complex questions.

        Args:
            question: User's complex analytical question
            kpi_context: Full KPI context (revenue, expense, profit, debt, occupancy)
            comparison_context: Previous period comparison data
            trend_context: Multi-month trend data
            anomalies: Detected anomalies
            history: Conversation history

        Returns:
            Dict with analysis fields or None if failed
        """
        from src.services.prompt_templates import DEEP_ANALYSIS_SYSTEM_PROMPT
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=4096,
            system_instruction=DEEP_ANALYSIS_SYSTEM_PROMPT,
        )

        history_block = f"\nLỊCH SỬ HỘI THOẠI:\n{history}\n" if history else ""

        user_content = f"""{history_block}
## DỮ LIỆU KPI HIỆN TẠI
```json
{json.dumps(kpi_context, ensure_ascii=False, indent=2)}
```

## SO SÁNH KỲ TRƯỚC
```json
{json.dumps(comparison_context, ensure_ascii=False, indent=2)}
```

## XU HƯỚNG ĐA KỲ
```json
{json.dumps(trend_context, ensure_ascii=False, indent=2)}
```

## CẢNH BÁO / BẤT THƯỜNG
```json
{json.dumps(anomalies, ensure_ascii=False, indent=2)}
```

## CÂU HỎI CẦN PHÂN TÍCH SÂU
"{question}"

HÃY THỰC HIỆN PHÂN TÍCH THEO QUY TRÌNH (B1→B2→B3→B4) VÀ TRẢ VỀ JSON:"""
        try:
            response = await self._call_with_retry(
                model=self.model,
                contents=user_content,
                config=config,
            )
            text = self._safe_text(response)
            if not text:
                return None
            cleaned = text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            log.warning("Deep analysis JSON parse failed: %s", str(e)[:60])
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{[^{}]*"analysis"[^{}]*\{[^{}]*"summary"[^{}]*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return None
        except Exception as e:
            log.warning("Deep analysis generation failed: %s", str(e)[:60])
            return None

    async def generate_marketing_content(self, room_data: Dict[str, Any]) -> str:
        from src.services.prompt_templates import MARKETING_CONTENT_PROMPT
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=1024,
            system_instruction=MARKETING_CONTENT_PROMPT,
        )
        user_content = f"""THÔNG TIN PHÒNG:
{json.dumps(room_data, ensure_ascii=False, default=str)}

HÃY VIẾT BÀI ĐĂNG CHO THUÊ NGAY BÂY GIỜ:"""
        response = await self._call_with_retry(
            model=self.model,
            contents=user_content,
            config=config,
        )
        return self._safe_text(response)

    async def run_sql_agent(self, prompt: str, tool_declarations: List[Any], tool_handlers: Dict[str, Any], max_turns: int = 7, system_instruction: Optional[str] = None) -> str:
        """
        Runs a ReAct agent loop using Google GenAI manual function calling.
        """
        from google.genai import types
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            tools=[types.Tool(function_declarations=tool_declarations)],
            system_instruction=system_instruction,
        )
        
        client = self._get_client()
        chat = client.aio.chats.create(model=self.model, config=config)
        
        try:
            response = await asyncio.wait_for(chat.send_message(prompt), timeout=30.0)
        except asyncio.TimeoutError:
            return "SELECT 1 AS result WHERE 1=0 -- initial prompt timeout"
            
        for turn in range(max_turns):
            if response.function_calls:
                parts = []
                for fc in response.function_calls:
                    name = fc.name
                    args = fc.args
                    if name in tool_handlers:
                        try:
                            # Handle both async and sync tool handlers
                            handler = tool_handlers[name]
                            if asyncio.iscoroutinefunction(handler):
                                result = await handler(**args)
                            else:
                                result = handler(**args)
                            
                            # Ensure result is a dictionary or convertable to JSON
                            if not isinstance(result, dict):
                                result = {"result": str(result)}
                                
                        except Exception as e:
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"Unknown function: {name}"}
                    
                    parts.append(types.Part.from_function_response(
                        name=name,
                        response=result
                    ))
                
                try:
                    response = await asyncio.wait_for(chat.send_message(parts), timeout=30.0)
                except asyncio.TimeoutError:
                    return "SELECT 1 AS result WHERE 1=0 -- function response timeout"
            else:
                # No function calls, model returned final text
                return self._safe_text(response)
                
        return "SELECT 1 AS result WHERE 1=0 -- max turns reached"

gemini_service = GeminiService()