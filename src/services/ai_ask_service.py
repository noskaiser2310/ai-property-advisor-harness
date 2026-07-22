"""
AI Ask Dashboard Service — Kế toán đặt câu hỏi bằng ngôn ngữ tự nhiên
- Question classifier (rule-based)
- Session store (TTL 30 phút)
- KPI context provider
- Multi-turn conversation
- Text-to-SQL agent (hỏi đáp bằng database query)
- Fallback template answers
"""
import json
import logging
import re
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from src.schemas.kpi_schema import KPIObject
from src.engines.kpi_repository import KPIRepository, AIReportCache, SessionStore
from src.services.evaluation_logger import eval_logger
from database.connection import get_db

log = logging.getLogger("ai-property-advisor")

# Question types — 8 base types + 8 extended types + 1 text-to-sql
Q_REVENUE = "REVENUE"
Q_REVENUE_BREAKDOWN = "REVENUE_BREAKDOWN"
Q_EXPENSE = "EXPENSE"
Q_EXPENSE_ANALYSIS = "EXPENSE_ANALYSIS"
Q_PROFIT = "PROFIT"
Q_PROFIT_DRIVERS = "PROFIT_DRIVERS"
Q_DEBT = "DEBT"
Q_DEBT_DETAIL = "DEBT_DETAIL"
Q_OCCUPANCY = "OCCUPANCY"
Q_OCCUPANCY_TREND = "OCCUPANCY_TREND"
Q_COMPARISON = "COMPARISON"
Q_ANALYSIS = "ANALYSIS"
Q_CASH_FLOW = "CASH_FLOW"
Q_FORECAST = "FORECAST"
Q_RISK_ASSESSMENT = "RISK_ASSESSMENT"
Q_TEXT_TO_SQL = "TEXT_TO_SQL"
Q_DEEP_ANALYSIS = "DEEP_ANALYSIS"
Q_GENERAL = "GENERAL"

# Question classification rules
QUESTION_PATTERNS = [
    # REVENUE (co ban)
    (Q_REVENUE, [r"doanh\s*thu", r"thu\s*nhập", r"thu\s*được", r"tiền\s*phòng", r"khoản.*thu"]),
    # REVENUE_BREAKDOWN (phan tich chi tiet doanh thu)
    (Q_REVENUE_BREAKDOWN, [r"cơ.*cấu.*thu", r"khoản.*mục.*thu", r"tiền\s*điện.*tăng", r"tiền\s*nước.*tăng", r"breakdown.*thu", r"chi.*tiết.*thu", r"phân.*tích.*doanh.*thu"]),
    # EXPENSE
    (Q_EXPENSE, [r"chi\s*phí", r"tiêu\s*tiền"]),
    # EXPENSE_ANALYSIS (phan tich chi phi)
    (Q_EXPENSE_ANALYSIS, [r"cao.*nhất.*phí", r"nhiều.*nhất.*chi", r"phân.*tích.*chi", r"cơ.*cấu.*chi", r"sửa\s*chữa", r"bảo\s*trì", r"phí\s*dịch\s*vụ"]),
    # PROFIT
    (Q_PROFIT, [r"lợi\s*nhuận", r"lãi", r"lỗ", r"lời\s*rong"]),
    # PROFIT_DRIVERS (yeu to anh huong)
    (Q_PROFIT_DRIVERS, [r"ảnh.*hưởng.*lợi", r"yếu.*tố.*lợi", r"tác.*động.*lợi", r"nguyên.*nhân.*lợi"]),
    # DEBT
    (Q_DEBT, [r"nợ", r"công\s*nợ", r"quá\s*hạn", r"chưa\s*trả", r"còn\s*thiếu", r"hóa\s*đơn.*nợ"]),
    # DEBT_DETAIL (chi tiet cong no)
    (Q_DEBT_DETAIL, [r"chi.*tiết.*nợ", r"phòng.*nào.*nợ", r"nợ.*lâu", r"aging", r"tuổi.*nợ"]),
    # OCCUPANCY
    (Q_OCCUPANCY, [r"lấp\s*đầy", r"phòng\s*trống", r"phòng\s*có\s*khách", r"tỉ\s*lệ", r"occupancy"]),
    # OCCUPANCY_TREND (xu huong)
    (Q_OCCUPANCY_TREND, [r"xu.*hướng.*phòng", r"6.*tháng.*phòng", r"theo.*thời.*gian.*phòng", r"biến.*động.*lấp"]),
    # COMPARISON
    (Q_COMPARISON, [r"so\s*sánh", r"thay\s*đổi", r"tăng.*giảm", r"hơn.*trước", r"nay.*trước", r"quý.*trước", r"so.*voi"]),
    # CASH_FLOW (dong tien)
    (Q_CASH_FLOW, [r"dòng\s*tiền", r"dòng\s*ngân", r"cash\s*flow", r"thu.*chi"]),
    # FORECAST (du bao)
    (Q_FORECAST, [r"dự\s*báo", r"dự\s*đoán", r"ước\s*tính", r"kỳ\s*vọng"]),
    # RISK_ASSESSMENT (rui ro)
    (Q_RISK_ASSESSMENT, [r"rủi\s*ro", r"nguy\s*cơ", r"cảnh\s*báo", r"vấn\s*đề\s*cần"]),
    # ANALYSIS
    (Q_ANALYSIS, [r"vì\s*sao", r"tại\s*sao", r"nguyên\s*nhân", r"lý\s*do", r"phân\s*tích", r"xu\s*hướng"]),
    # DEEP_ANALYSIS — câu hỏi phân tích phức tạp cần chain-of-thought
    (Q_DEEP_ANALYSIS, [
        r"tại.*sao.*doanh.*thu",           # "tại sao doanh thu giảm?"
        r"vì.*sao.*lợi.*nhuận",            # "vì sao lợi nhuận giảm?"
        r"nguyên.*nhân.*sâu.*xa",          # "nguyên nhân sâu xa"
        r"phân.*tích.*toàn.*diện",         # "phân tích toàn diện"
        r"đánh.*giá.*tổng.*quan.*rủi",     # "đánh giá tổng quan rủi ro"
        r"tương.*quan.*giữa",              # "tương quan giữa doanh thu và lấp đầy"
        r"mối.*liên.*hệ.*giữa",           # "mối liên hệ giữa"
        r"ảnh.*hưởng.*đến.*nhau",          # "ảnh hưởng đến nhau"
        r"root.*cause",                    # "root cause"
        r"dự.*báo.*rủi.*ro",              # "dự báo rủi ro"
        r"tình.*hình.*kinh.*doanh.*tổng",  # "tình hình kinh doanh tổng thể"
        r"tổng.*quan.*tài.*chính",        # "tổng quan tài chính"
        r"chẩn.*đoán.*tài.*chính",        # "chẩn đoán tài chính"
        r"tư.*vấn.*chiến.*lược",          # "tư vấn chiến lược"
        r"có.*nên.*tăng.*giá",            # "có nên tăng giá phòng không?"
        r"giải.*pháp.*cải.*thiện",         # "giải pháp cải thiện"
        r"khắc.*phục.*tình.*trạng",       # "khắc phục tình trạng"
        r"đề.*xuất.*chiến.*lược",         # "đề xuất chiến lược"
        # Extra patterns for comprehensive financial analysis questions
        r"t\u1ea1i.*sao.*doanh.*thu",           # "t\u1ea1i sao doanh thu"
        r"v\u00ec.*sao.*doanh.*thu",             # "v\u00ec sao doanh thu"
        r"doanh.*thu.*th\u1ea5p",                # "doanh thu th\u1ea5p"
        r"doanh.*thu.*gi\u1ea3m",               # "doanh thu gi\u1ea3m"
        r"ph\u00e2n.*t\u00edch.*t\u00e0i.*ch\u00ednh", # "ph\u00e2n t\u00edch t\u00e0i ch\u00ednh"
        r"t\u00ecnh.*h\u00ecnh.*t\u00e0i.*ch\u00ednh", # "t\u00ecnh h\u00ecnh t\u00e0i ch\u00ednh"
        r"t\u1ed5ng.*quan.*t\u00e0i.*ch\u00ednh",      # "t\u1ed5ng quan t\u00e0i ch\u00ednh"
        r"t\u00ecnh.*h\u00ecnh.*kinh.*doanh",    # "t\u00ecnh h\u00ecnh kinh doanh"
        r"doanh.*thu.*th\u1ea5p",                # doanh thu thap
        r"doanh.*thu.*gi\u1ea3m",               # doanh thu giam
        r"ph\u00e2n.*t\u00edch.*t\u00e0i.*ch\u00ednh", # phan tich tai chinh
        r"t\u00ecnh.*h\u00ecnh.*t\u00e0i.*ch\u00ednh", # tinh hinh tai chinh
        r"t\u00ecnh.*h\u00ecnh.*kinh.*doanh",    # tinh hinh kinh doanh
        r"l\u1ee3i.*nhu\u1eadn.*gi\u1ea3m",            # loi nhuan giam
        r"nguy\u00ean.*nh\u00e2n.*g\u1ed1c.*r\u1ec5",         # nguyen nhan goc re
        r"nguy\u00ean.*nh\u00e2n.*doanh.*thu",           # nguyen nhan doanh thu




        r"doanh.*thu.*thấp",                # doanh thu thap
        r"doanh.*thu.*giảm",               # doanh thu giam
        r"phân.*tích.*tài.*chính", # phan tich tai chinh
        r"tình.*hình.*tài.*chính", # tinh hinh tai chinh
        r"tình.*hình.*kinh.*doanh",    # tinh hinh kinh doanh

        r"lợi.*nhuận.*giảm",            # loi nhuan giam
        r"nguyên.*nhân.*gốc.*rễ",         # nguyen nhan goc re
        r"nguyên.*nhân.*doanh.*thu",           # nguyen nhan doanh thu
    ]),
    # TEXT_TO_SQL — câu hỏi cần truy vấn database trực tiếp
    (Q_TEXT_TO_SQL, [
        # Complex aggregation patterns (so sanh, xep hang, phan tich phong)
        r"tỉ\s*suất.*lợi.*nhuận",       # profit margin
        r"lợi.*nhuận.*cao.*nhất",        # highest profit
        r"doanh.*thu.*giữa.*phòng",      # compare revenue per room
        r"phòng.*nào.*cao.*nhất.*thu",   # highest revenue room
        r"phòng.*nào.*mang.*lại.*nhiều", # which room brings most
        r"so.*sánh.*lợi.*nhuận.*phòng", # compare profit by room
        r"xếp.*hạng.*phòng",             # rank rooms
        r"xếp.*hạng.*doanh.*thu",      # rank revenue
        r"top.*phòng.*doanh.*thu",        # top revenue room
        r"phòng.*tốt.*nhất.*doanh",     # best revenue room
        r"hiệu.*quả.*phòng",            # efficiency
        r"tổng.*doanh.*thu.*phòng",        # total revenue
        # Tiebreaker: general room questions (higher score than PROFIT/REVENUE)
        r"phòng.*nào",                    # general room questions
        r"so.*sánh.*doanh.*thu",          # compare revenue
        r"nào.*mang.*lại",                # which brings
        r"nào.*hiệu.*quả",               # which efficient
        r"doanh.*thu.*theo.*phòng",      # revenue per room
        r"lợi.*nhuận.*theo.*phòng",      # profit per room
        # Câu hỏi cơ bản về phòng cụ thể
        r"phòng\s*\d{3}",              # "phòng 501"
        r"p\d{3}",                      # "p501"
        r"tháng.*\d{4}",               # "tháng 6/2026"
        r"hợp\s*\u0111ồng.*\d{4}",          # "hợp đồng 001"
        r"hóa\s*\u0111ơn.*\d{4}",           # "hóa đơn HD001"
        r"chỉ\s*số\s*điện",            # "chỉ số điện"
        r"chỉ\s*số\s*nước",            # "chỉ số nước"
        r"sự\s*cố.*bảo\s*trì",          # "sự cố bảo trì"
        r"phiếu.*sửa",                  # "phiếu sửa chữa"
        r"thanh\s*toán.*phòng",         # "thanh toán phòng 501"
        r"lịch\s*sử.*thanh.*toán",      # "lịch sử thanh toán"
        r"đóng\s*tiền",                 # "đóng tiền"
        r"chuyển.*phòng",               # "chuyển phòng"
        r"đặt\s*cọc",                   # "đặt cọc"
        r"gia\s*hạn",                   # "gia hạn"
        r"cọc.*phòng",                  # "cọc phòng"
        r"bàn\s*giao",                  # "bàn giao"
        r"thanh\s*lý",                  # "thanh lý"

    ]),

]

# KPI mapping: mỗi loại câu hỏi cần những KPI nào?
QUESTION_KPI_NEEDS = {
    Q_REVENUE: ["revenue.total", "revenue.rent", "revenue.electricity", "revenue.water", "revenue.service", "revenue.growth_pct"],
    Q_REVENUE_BREAKDOWN: ["revenue.rent", "revenue.electricity", "revenue.water", "revenue.service", "revenue.other", "occupancy.occupied_rooms", "occupancy.total_rooms"],
    Q_EXPENSE: ["expense.total", "expense.electricity", "expense.water", "expense.maintenance"],
    Q_EXPENSE_ANALYSIS: ["expense.electricity", "expense.water", "expense.maintenance", "expense.penalty", "expense.other", "profit.expense_ratio"],
    Q_PROFIT: ["profit.net", "profit.growth_pct", "profit.expense_ratio", "revenue.total", "expense.total"],
    Q_PROFIT_DRIVERS: ["profit.net", "revenue.total", "expense.total", "occupancy.occupied_rooms", "occupancy.occupancy_rate", "debt.overdue_amount"],
    Q_DEBT: ["debt.collection_rate", "debt.overdue_count", "debt.overdue_amount"],
    Q_DEBT_DETAIL: ["debt.debt_by_room", "debt.overdue_amount", "debt.overdue_count", "debt.collection_rate"],
    Q_OCCUPANCY: ["occupancy.occupancy_rate", "occupancy.occupied_rooms", "occupancy.total_rooms", "occupancy.vacant_rooms", "occupancy.occupancy_change"],
    Q_OCCUPANCY_TREND: ["occupancy.occupancy_rate", "occupancy.occupancy_change", "occupancy.occupied_rooms", "occupancy.total_rooms"],
    Q_COMPARISON: ["revenue.total", "expense.total", "profit.net", "change_pct.revenue", "change_pct.expense", "occupancy.occupancy_rate"],
    Q_ANALYSIS: ["revenue.total", "expense.total", "profit.net", "occupancy.occupancy_rate", "debt.overdue_amount", "health_score"],
    Q_CASH_FLOW: ["revenue.total", "debt.collection_rate", "debt.overdue_amount", "profit.net", "occupancy.occupancy_rate"],
    Q_FORECAST: ["revenue.total", "revenue.growth_pct", "occupancy.occupancy_rate", "occupancy.occupancy_change"],
    Q_RISK_ASSESSMENT: ["debt.overdue_amount", "debt.overdue_count", "occupancy.occupancy_rate", "health_score", "health_status", "debt.collection_rate"],
    Q_DEEP_ANALYSIS: [  # Deep analysis cần TẤT CẢ KPI
        "revenue.total", "revenue.rent", "revenue.electricity", "revenue.water", "revenue.service", "revenue.growth_pct",
        "expense.total", "expense.electricity", "expense.water", "expense.maintenance",
        "profit.net", "profit.growth_pct", "profit.expense_ratio",
        "debt.collection_rate", "debt.overdue_count", "debt.overdue_amount", "debt.debt_by_room",
        "occupancy.occupancy_rate", "occupancy.occupied_rooms", "occupancy.total_rooms", "occupancy.occupancy_change",
        "health_score", "health_status",
        "change_pct.revenue", "change_pct.expense", "change_pct.profit",
    ],
    Q_TEXT_TO_SQL: [],  # Text-to-SQL không cần KPI — tự query database
    Q_GENERAL: ["revenue.total", "expense.total", "profit.net", "occupancy.occupancy_rate", "health_score"],
}


# Prompt cho LLM Question Router (Planner Agent)
CLASSIFIER_PROMPT = """Bạn là chuyên gia phân loại câu hỏi tài chính cho hệ thống AI Financial Copilot.

NGỮ CẢNH KPI hiện tại:
- Doanh thu: {revenue}đ (rent: {rent}đ, service: {service}đ)
- Chi phí: {expense}đ
- Lợi nhuận ròng: {profit}đ
- Công nợ: {debt}đ ({overdue_count} hóa đơn quá hạn, tỷ lệ thu: {collection_rate}%)
- Tỉ lệ lấp đầy: {occupancy_rate}% ({occupied_rooms}/{total_rooms} phòng)

CÂU HỎI: "{question}"

Hãy phân loại câu hỏi trên vào MỘT trong các loại sau:
- REVENUE: Hỏi về doanh thu tổng, tiền phòng
- REVENUE_BREAKDOWN: Hỏi về cơ cấu doanh thu, chi tiết từng khoản (tiền điện, tiền nước...) vì sao tăng/giảm
- EXPENSE: Hỏi về tổng chi phí
- EXPENSE_ANALYSIS: Hỏi về phân tích chi phí, khoản nào cao, cơ cấu chi phí
- PROFIT: Hỏi về lợi nhuận, lãi lỗ
- PROFIT_DRIVERS: Hỏi về yếu tố ảnh hưởng đến lợi nhuận
- DEBT: Hỏi về công nợ, tổng nợ quá hạn
- DEBT_DETAIL: Hỏi về chi tiết công nợ, phòng nào nợ, tuổi nợ
- OCCUPANCY: Hỏi về tỉ lệ lấp đầy, phòng trống
- OCCUPANCY_TREND: Hỏi về xu hướng lấp đầy qua thời gian
- COMPARISON: Hỏi về so sánh, thay đổi so với kỳ trước
- ANALYSIS: Hỏi về phân tích tổng quan, xu hướng
- CASH_FLOW: Hỏi về dòng tiền, khả năng thu hồi công nợ
- FORECAST: Hỏi về dự báo, dự đoán tương lai
- RISK_ASSESSMENT: Hỏi về rủi ro, nguy cơ, cảnh báo
- TEXT_TO_SQL: Hỏi về dữ liệu cụ thể của một phòng (VD: "phòng 501 đóng tiền chưa?"), lịch sử thanh toán, chỉ số điện/nước, hợp đồng, sự cố bảo trì, bàn giao, thanh lý — cần truy vấn database
- DEEP_ANALYSIS: Câu hỏi phân tích SÂU, phức tạp cần chain-of-thought reasoning (VD: "tại sao doanh thu giảm?", "nguyên nhân gốc rễ của vấn đề", "phân tích toàn diện tình hình tài chính", "có nên tăng giá phòng?", "tương quan giữa doanh thu và lấp đầy") — cần tổng hợp nhiều KPI và phân tích nguyên nhân - kết quả
- GENERAL: Câu hỏi chung, không thuộc loại nào

Trả về JSON DUY NHẤT:
{{"type": "LOẠI_CÂU_HỎI", "confidence": 0.95, "reason": "lý do ngắn"}}
"""

class QuestionClassifier:
    """Rule-based Question Classifier — fallback khi LLM không khả dụng"""

    @staticmethod
    def classify(question: str) -> Tuple[str, float]:
        """Phân loại câu hỏi bằng regex, trả về (type, confidence)"""
        lower_q = question.lower()
        normalized_q = _normalize_vietnamese(lower_q)
        scores = {}
        for qtype, patterns in QUESTION_PATTERNS:
            score = 0
            for pat in patterns:
                if re.search(pat, lower_q) or re.search(_normalize_vietnamese(pat), normalized_q):
                    score += 1
            if score > 0:
                scores[qtype] = score

        if not scores:
            return Q_GENERAL, 0.3

        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]
        total_score = sum(scores.values())
        confidence = round(max_score / total_score, 2) if total_score > 0 else 0.3
        return best_type, confidence


class PlannerAgent:
    """
    Agent 1: PLANNER — Phân loại câu hỏi + xác định KPI cần thiết
    
    Input: question, kpi context
    Output: {
        "type": "REVENUE_BREAKDOWN",
        "required_kpis": ["revenue.electricity", "revenue.water", ...],
        "confidence": 0.95,
        "reason": "Hỏi về biến động tiền điện",
        "missing_kpis": []  # được set nếu là lần loop lại
    }
    """

    @staticmethod
    async def plan(
        question: str,
        kpi: Optional[KPIObject] = None,
        previous_missing: Optional[List[str]] = None,
    ) -> dict:
        """
        Lập kế hoạch: phân loại câu hỏi + xác định KPI cần.
        Trả về dict với type, required_kpis, confidence, reason.
        Fallback: dùng regex classifier + QUESTION_KPI_NEEDS.
        """
        qtype, confidence = QuestionClassifier.classify(question)
        
        # Luôn lấy KPI cần từ mapping (dù dùng regex hay LLM)
        required = list(QUESTION_KPI_NEEDS.get(qtype, QUESTION_KPI_NEEDS[Q_GENERAL]))
        if previous_missing:
            # Neu dang loop lai, them nhung KPI thieu vao required
            for k in previous_missing:
                if k not in required:
                    required.append(k)

        result = {
            "type": qtype,
            "required_kpis": required,
            "confidence": confidence,
            "reason": "regex match" if qtype != Q_GENERAL else "fallback",
        }

        # Neu regex khong phan loai duoc va co API key -> thu LLM
        if qtype == Q_GENERAL:
            from config.settings import settings
            if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "YOUR_API_KEY":
                try:
                    llm_result = await PlannerAgent._call_llm_planner(question, kpi, previous_missing)
                    if llm_result:
                        result = llm_result
                except Exception:
                    pass  # keep regex fallback

        log.debug("Planner: type=%s req=%s conf=%.2f", result["type"], result["required_kpis"], result["confidence"])
        return result

    @staticmethod
    async def _call_llm_planner(
        question: str,
        kpi: Optional[KPIObject] = None,
        previous_missing: Optional[List[str]] = None,
    ) -> Optional[dict]:
        """Gọi LLM để phân loại câu hỏi nâng cao (có required_kpis)"""
        try:
            from src.services.gemini_service import gemini_service
            from google.genai import types

            rev = kpi.revenue if kpi else None
            exp = kpi.expense if kpi else None
            debt = kpi.debt if kpi else None
            occ = kpi.occupancy if kpi else None
            prof = kpi.profit if kpi else None

            missing_context = ""
            if previous_missing:
                missing_context = f"\nLẦN TRƯỚC THIẾU KPI: {', '.join(previous_missing)} — hãy ưu tiên lấy các KPI này."

            prompt = CLASSIFIER_PROMPT.format(
                question=question,
                revenue=f"{rev.total:,.0f}" if rev else "N/A",
                rent=f"{rev.rent:,.0f}" if rev else "N/A",
                service=f"{rev.service:,.0f}" if rev else "N/A",
                expense=f"{exp.total:,.0f}" if exp else "N/A",
                profit=f"{prof.net:,.0f}" if prof else "N/A",
                debt=f"{debt.overdue_amount:,.0f}" if debt else "N/A",
                overdue_count=debt.overdue_count if debt else 0,
                collection_rate=debt.collection_rate if debt else 100.0,
                occupancy_rate=occ.occupancy_rate if occ else 0,
                occupied_rooms=occ.occupied_rooms if occ else 0,
                total_rooms=occ.total_rooms if occ else 0,
            ) + missing_context

            config = types.GenerateContentConfig(temperature=0.0, max_output_tokens=512)
            response = await asyncio.wait_for(
                gemini_service._get_client().aio.models.generate_content(
                    model=gemini_service.model,
                    contents=prompt,
                    config=config,
                ),
                timeout=30.0,
            )
            text = gemini_service._safe_text(response)
            if not text:
                return None

            cleaned = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            qtype = result.get("type", "").upper()

            ALL_TYPES = {
                Q_REVENUE, Q_REVENUE_BREAKDOWN, Q_EXPENSE, Q_EXPENSE_ANALYSIS,
                Q_PROFIT, Q_PROFIT_DRIVERS, Q_DEBT, Q_DEBT_DETAIL,
                Q_OCCUPANCY, Q_OCCUPANCY_TREND, Q_COMPARISON, Q_ANALYSIS,
                Q_CASH_FLOW, Q_FORECAST, Q_RISK_ASSESSMENT, Q_TEXT_TO_SQL,
                Q_DEEP_ANALYSIS, Q_GENERAL,
            }
            if qtype not in ALL_TYPES:
                return None

            required = list(QUESTION_KPI_NEEDS.get(qtype, QUESTION_KPI_NEEDS[Q_GENERAL]))
            if previous_missing:
                for k in previous_missing:
                    if k not in required:
                        required.append(k)

            return {
                "type": qtype,
                "required_kpis": required,
                "confidence": result.get("confidence", 0.8),
                "reason": result.get("reason", ""),
            }
        except Exception as e:
            log.debug("LLM planner error: %s", str(e))
            return None


class RetrieverAgent:
    """
    Agent 2: RETRIEVER — Lấy KPI data, phát hiện thiếu, request thêm
    
    Input: required_kpis list, KPIObject
    Output: {
        "available": {"revenue.total": 54600000, ...},
        "missing": ["revenue.monthly_history"],
        "has_gaps": True/False,
        "summary": "Doanh thu 54.6tr, ..."
    }
    """

    @staticmethod
    def retrieve(required_kpis: List[str], kpi: KPIObject) -> dict:
        """
        Lấy KPI data từ KPIObject dựa trên required_kpis.
        Phát hiện KPI nào không có sẵn để request thêm.
        """
        available = {}
        missing = []

        # Map field paths to extraction functions
        field_map = RetrieverAgent._build_field_map(kpi)

        for kpi_path in required_kpis:
            # Hỗ trợ path dạng "revenue.total" hoặc "revenue"
            parts = kpi_path.split(".")
            if len(parts) == 1:
                # Lấy cả object
                if parts[0] in field_map:
                    val = field_map[parts[0]]
                    if val is not None:
                        available[kpi_path] = val
                    else:
                        missing.append(kpi_path)
            else:
                # Lấy field cụ thể
                obj_key = parts[0]
                field_key = parts[1]
                if obj_key in field_map and field_map[obj_key] is not None:
                    obj = field_map[obj_key]
                    if hasattr(obj, field_key):
                        val = getattr(obj, field_key)
                        available[kpi_path] = val
                    elif isinstance(obj, dict) and field_key in obj:
                        available[kpi_path] = obj[field_key]
                    else:
                        missing.append(kpi_path)
                else:
                    missing.append(kpi_path)

        # Summary text
        summary_parts = []
        rev_data = available.get("revenue.total") or (field_map.get("revenue") and getattr(field_map["revenue"], "total", None))
        exp_data = available.get("expense.total") or (field_map.get("expense") and getattr(field_map["expense"], "total", None))
        occ_data = available.get("occupancy.occupancy_rate") or (field_map.get("occupancy") and getattr(field_map["occupancy"], "occupancy_rate", None))
        debt_data = available.get("debt.overdue_amount") or (field_map.get("debt") and getattr(field_map["debt"], "overdue_amount", None))
        prof_data = available.get("profit.net") or (field_map.get("profit") and getattr(field_map["profit"], "net", None))

        if rev_data is not None:
            summary_parts.append(f"Doanh thu {rev_data:,.0f}đ")
        if exp_data is not None:
            summary_parts.append(f"Chi phí {exp_data:,.0f}đ")
        if prof_data is not None:
            summary_parts.append(f"Lợi nhuận {prof_data:,.0f}đ")
        if occ_data is not None:
            summary_parts.append(f"Lấp đầy {occ_data}%")
        if debt_data is not None and debt_data > 0:
            summary_parts.append(f"Nợ {debt_data:,.0f}đ")

        has_gaps = len(missing) > 0
        if has_gaps:
            log.debug("Retriever: missing %d KPIs: %s", len(missing), missing)

        return {
            "available": available,
            "missing": missing,
            "has_gaps": has_gaps,
            "summary": "; ".join(summary_parts) if summary_parts else "Không có dữ liệu",
        }

    @staticmethod
    def _build_field_map(kpi: KPIObject) -> dict:
        """Xây dựng map field paths từ KPIObject"""
        return {
            "revenue": kpi.revenue if kpi else None,
            "expense": kpi.expense if kpi else None,
            "profit": kpi.profit if kpi else None,
            "debt": kpi.debt if kpi else None,
            "occupancy": kpi.occupancy if kpi else None,
            "previous_period": kpi.previous_period if kpi else None,
            "change_pct": kpi.change_pct if kpi else None,
            "health_score": kpi.health_score if kpi else None,
            "health_status": kpi.health_status if kpi else None,
        }


class AnswerAgent:
    """
    Agent 3: ANSWER — Tạo câu trả lời từ KPI đã thu thập
    
    Input: question, collected data (available KPI), qtype
    Output: reply string
    """

    @staticmethod
    async def answer(
        question: str,
        qtype: str,
        kpi: KPIObject,
        collected: dict,
        history: str = "",
        sql_data: Optional[list] = None,
    ) -> str:
        """
        Sinh câu trả lời. Ưu tiên:
          1. KPI cache (luôn được truyền vào collected)
          2. sql_data — dữ liệu bổ sung từ SQL nếu KPI có gap
          3. Fallback template nếu Gemini không available
        """
        from config.settings import settings
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "YOUR_API_KEY":
            try:
                from src.services.gemini_service import gemini_service
                from google.genai import types
                kpi_context = AIAskService._build_kpi_context(kpi)

                # Phần dữ liệu bổ sung từ SQL (nếu có)
                sql_section = ""
                if sql_data:
                    sql_section = f"""

DỮ LIỆU BỔ SUNG TỪ DATABASE (SQL):
{json.dumps(sql_data[:20], ensure_ascii=False, indent=2)}
Lưu ý: Dùng dữ liệu SQL này để bổ sung cho các KPI còn thiếu ở trên."""

                prompt = f"""Bạn là AI Financial Copilot - trợ lý tài chính cho kế toán nhà trọ.

NGỮ CẢNH HIỆN TẠI:
KPI Data: {json.dumps(kpi_context, ensure_ascii=False, indent=2)}

DỮ LIỆU KPI THU THẬP:
{json.dumps(collected.get('available', {}), ensure_ascii=False, indent=2)}{sql_section}

LỊCH SỬ HỘI THOẠI:
{history if history else "Chưa có lịch sử"}

CÂU HỎI: "{question}"
LOẠI: {qtype}

YÊU CẦU:
1. Ưu tiên dùng DỮ LIỆU KPI THU THẬP, ngắn gọn và chính xác
2. Nếu KPI thiếu → dùng DỮ LIỆU BỔ SUNG TỪ DATABASE (SQL) để bổ sung
3. Chỉ dùng số liệu có trong dữ liệu được cung cấp, KHÔNG bịa đặt
4. Nếu phân tích (REVENUE_BREAKDOWN, EXPENSE_ANALYSIS...), giải thích chi tiết
5. Trả về JSON duy nhất:
{{"reply": "Câu trả lời tiếng Việt"}}
"""
                config = types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
                response = await gemini_service._call_with_retry(model=gemini_service.model, contents=prompt, config=config)
                text = gemini_service._safe_text(response)
                try:
                    cleaned = text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(cleaned)
                    return result.get("reply", text)
                except (json.JSONDecodeError, ValueError):
                    return text
            except Exception as e:
                log.warning("Gemini answer failed, using template: %s", str(e))

        # Fallback: template-based answer
        return AIAskService._build_fallback_answer(qtype, kpi)


class DeepAnalysisAgent:
    """
    Agent 4 (Enhanced): DEEP ANALYSIS — Phân tích sâu với Chain-of-Thought
    Dành cho câu hỏi phức tạp: tại sao, root cause, tương quan, chiến lược

    Pipeline:
    1. Xây dựng rich context từ KPI data + comparison + trend + anomalies
    2. Gọi Gemini generate_deep_analysis với CoT reasoning
    3. Fallback: rule-based analysis nếu Gemini không available

    Input: question, KPIObject, collected data, history
    Output: {
        "reply": "...phân tích chi tiết...",
        "type": Q_DEEP_ANALYSIS,
        "analysis_result": {
            "summary": "...",
            "key_findings": [...],
            "correlations": [...],
            "root_causes": [...],
            "recommendations": [...],
            "forecast": "..."
        },
        "plan": {
            "method": "deep_analysis",
            "iterations": 1
        }
    }
    """

    @staticmethod
    async def analyze(
        question: str,
        kpi: KPIObject,
        collected: dict,
        history: str = "",
    ) -> dict:
        """
        Perform deep analysis using Chain-of-Thought reasoning.
        """
        from src.services.gemini_service import gemini_service
        from src.engines.context_engine import ContextBuilder, TrendAnalyzer

        # === STEP 1: Build rich context ===
        kpi_context = AIAskService._build_kpi_context(kpi)

        # Comparison context
        comparison = ContextBuilder._build_comparison_section(kpi)

        # Trend context
        trend = ContextBuilder._build_trend_section(kpi)

        # Anomalies
        anomalies = ContextBuilder._detect_anomalies(kpi, comparison)

        # === STEP 2: Try Gemini deep analysis ===
        from config.settings import settings
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "YOUR_API_KEY":
            try:
                result = await gemini_service.generate_deep_analysis(
                    question=question,
                    kpi_context=kpi_context,
                    comparison_context=comparison,
                    trend_context=trend,
                    anomalies=anomalies,
                    history=history,
                )
                if result and "analysis" in result:
                    analysis = result["analysis"]
                    reply = DeepAnalysisAgent._format_analysis_reply(analysis)
                    return {
                        "reply": reply,
                        "type": Q_DEEP_ANALYSIS,
                        "analysis_result": analysis,
                        "plan": {
                            "method": "deep_analysis_gemini",
                            "iterations": 1,
                        },
                    }
                else:
                    log.debug("DeepAnalysis: Gemini returned empty/invalid result")
            except Exception as e:
                log.warning("DeepAnalysis: Gemini failed: %s", str(e)[:60])

        # === STEP 3: Fallback — rule-based deep analysis ===
        return DeepAnalysisAgent._rule_based_analysis(question, kpi, collected, comparison, anomalies)

    @staticmethod
    def _rule_based_analysis(
        question: str,
        kpi: KPIObject,
        collected: dict,
        comparison: dict,
        anomalies: list,
    ) -> dict:
        """Rule-based fallback analysis when Gemini is unavailable"""
        rev = kpi.revenue
        exp = kpi.expense
        prof = kpi.profit
        debt = kpi.debt
        occ = kpi.occupancy

        findings = []
        correlations = []
        root_causes = []
        recommendations = []

        # === FINDING 1: Revenue analysis ===
        if rev:
            if rev.growth_pct is not None:
                if rev.growth_pct < 0:
                    findings.append(f"Doanh thu giảm {abs(rev.growth_pct):.1f}% so với kỳ trước — cần xác định nguyên nhân")
                    # Root cause: check components
                    if occ and occ.occupancy_change and occ.occupancy_change < 0:
                        root_causes.append({
                            "problem": "Doanh thu giảm",
                            "why": f"Lấp đầy giảm {abs(occ.occupancy_change):.1f}% dẫn đến ít phòng có khách hơn",
                            "evidence": f"Tỉ lệ lấp đầy {occ.occupancy_rate}% ({occ.occupied_rooms}/{occ.total_rooms} phòng)",
                            "severity": "high",
                        })
                    elif debt and debt.overdue_amount > 0:
                        root_causes.append({
                            "problem": "Doanh thu thực tế thấp",
                            "why": f"Công nợ {debt.overdue_amount:,.0f}đ chưa thu hồi được, ảnh hưởng đến doanh thu thực",
                            "evidence": f"Tỷ lệ thu chỉ {debt.collection_rate}%",
                            "severity": "high",
                        })
                    else:
                        root_causes.append({
                            "problem": "Doanh thu giảm",
                            "why": "Cần phân tích thêm dữ liệu chi tiết theo từng khoản mục",
                            "evidence": f"Mức giảm {abs(rev.growth_pct):.1f}%",
                            "severity": "medium",
                        })
                elif rev.growth_pct > 10:
                    findings.append(f"Doanh thu tăng trưởng tốt (+{rev.growth_pct:.1f}%) — nên duy trì đà tăng trưởng")

        # === FINDING 2: Expense ratio analysis ===
        if prof and prof.expense_ratio is not None:
            if prof.expense_ratio > 80:
                findings.append(f"Tỷ lệ chi phí/doanh thu {prof.expense_ratio}% — rất cao, cần tối ưu chi phí")
                if exp and exp.maintenance > 0:
                    root_causes.append({
                        "problem": "Chi phí cao",
                        "why": f"Chi phí bảo trì {exp.maintenance:,.0f}đ đang chiếm tỷ trọng lớn",
                        "evidence": f"Tỷ lệ CP/DT {prof.expense_ratio}%",
                        "severity": "high",
                    })
            elif prof.expense_ratio > 60:
                findings.append(f"Tỷ lệ chi phí/doanh thu {prof.expense_ratio}% — ở mức trung bình, có thể tối ưu thêm")

        # === FINDING 3: Correlation: revenue vs occupancy ===
        if rev and occ:
            rel = "cùng chiều"
            # Determine if there's a divergence
            rev_growth = rev.growth_pct if rev.growth_pct is not None else 0
            occ_change = occ.occupancy_change if occ.occupancy_change is not None else 0
            if (rev_growth > 0 and occ_change < 0) or (rev_growth < 0 and occ_change > 0):
                rel = "nghịch chiều (phi tương quan)"
                findings.append(
                    f"Phát hiện bất thường: Doanh thu và lấp đầy biến động {rel} — "
                    f"doanh thu {'tăng' if rev_growth > 0 else 'giảm'} {abs(rev_growth):.1f}% "
                    f"nhưng lấp đầy {'tăng' if occ_change > 0 else 'giảm'} {abs(occ_change):.1f}%"
                )
                correlations.append({
                    "metric_a": "doanh thu",
                    "metric_b": "tỉ lệ lấp đầy",
                    "relationship": rel,
                    "impact": "Có thể do thay đổi giá phòng hoặc cơ cấu khách thuê",
                })
            else:
                correlations.append({
                    "metric_a": "doanh thu",
                    "metric_b": "tỉ lệ lấp đầy",
                    "relationship": rel,
                    "impact": "Biến động cùng chiều — bình thường",
                })

        # === FINDING 4: Debt & Cash flow ===
        if debt and debt.overdue_count > 0:
            findings.append(f"Có {debt.overdue_count} hóa đơn quá hạn ({debt.overdue_amount:,.0f}đ) — ảnh hưởng đến dòng tiền")
            if debt.collection_rate < 80:
                findings.append(f"Tỷ lệ thu hồi công nợ chỉ {debt.collection_rate}% — rủi ro dòng tiền cao")
                root_causes.append({
                    "problem": "Công nợ cao, thu hồi kém",
                    "why": "Tỷ lệ thu hồi thấp có thể do chính sách thu nợ chưa hiệu quả hoặc khách thuê gặp khó khăn",
                    "evidence": f"{debt.overdue_count} hóa đơn quá hạn, collection rate {debt.collection_rate}%",
                    "severity": "critical" if debt.collection_rate < 50 else "high",
                })

        # === FINDING 5: Occupancy risk ===
        if occ and occ.occupancy_rate < 60:
            findings.append(f"Tỉ lệ lấp đầy chỉ {occ.occupancy_rate}% — {occ.vacant_rooms} phòng trống, cần đẩy mạnh marketing")
            recommendations.append({
                "action": "Đẩy mạnh marketing cho các phòng trống",
                "expected_impact": f"Lấp đầy {occ.vacant_rooms} phòng có thể tăng doanh thu đáng kể, cần xem xét chính sách giá để tối ưu hóa",
                "priority": 1,
            })

        # === FINDING 6: Health score ===
        if kpi.health_score is not None:
            if kpi.health_score < 40:
                findings.append(f"Điểm sức khỏe KPI {kpi.health_score}/100 — tình trạng yếu kém, cần can thiệp khẩn cấp")
            elif kpi.health_score < 60:
                findings.append(f"Điểm sức khỏe KPI {kpi.health_score}/100 — ở mức trung bình, cần cải thiện")
            elif kpi.health_score >= 80:
                findings.append(f"Điểm sức khỏe KPI {kpi.health_score}/100 — tốt, tiếp tục duy trì")

        # === RECOMMENDATIONS ===
        if not recommendations:
            if rev and rev.growth_pct is not None and rev.growth_pct < 0:
                recommendations.append({
                    "action": "Phân tích chi tiết từng khoản mục doanh thu để tìm nguyên nhân giảm",
                    "expected_impact": "Xác định chính xác vấn đề để có giải pháp phù hợp",
                    "priority": 1,
                })
            if debt and debt.overdue_count > 0:
                recommendations.append({
                    "action": "Tăng cường thu hồi công nợ: gọi điện, gửi thông báo, áp dụng phạt quá hạn",
                    "expected_impact": f"Thu hồi {debt.overdue_amount:,.0f}đ công nợ",
                    "priority": 2,
                })
            if occ and occ.occupancy_rate < 70:
                recommendations.append({
                    "action": "Xem xét điều chỉnh giá hoặc chính sách ưu đãi để thu hút khách thuê mới",
                    "expected_impact": "Cải thiện tỉ lệ lấp đầy và doanh thu",
                    "priority": 3,
                })
            recommendations.append({
                "action": "Theo dõi sát các chỉ số KPI hàng tháng để phát hiện sớm biến động bất thường",
                "expected_impact": "Chủ động ứng phó với rủi ro tài chính",
                "priority": 4,
            })

        # === FORECAST ===
        forecast = ""
        if rev and rev.growth_pct is not None and rev.growth_pct < 0 and occ and occ.occupancy_rate < 60:
            forecast = "Nếu không có biện pháp can thiệp, doanh thu và lấp đầy có thể tiếp tục giảm trong tháng tới. "
            forecast += "Cần ưu tiên tìm khách thuê mới và thu hồi công nợ để cải thiện dòng tiền."
        elif debt and debt.overdue_count > 3:
            forecast = "Công nợ đang ở mức báo động. Nếu không thu hồi kịp, rủi ro mất trắng và ảnh hưởng đến thanh khoản."
        elif rev and rev.growth_pct is not None and rev.growth_pct > 10:
            forecast = "Đà tăng trưởng tích cực. Duy trì chính sách hiện tại và theo dõi biến động thị trường."
        else:
            forecast = "Tình hình ổn định. Tiếp tục theo dõi các chỉ số hàng tháng."

        # === BUILD ANALYSIS ===
        analysis = {
            "summary": f"Phân tích kỳ {kpi.period}: {' + '.join(findings[:2]) if findings else 'Tình hình bình thường.'}",
            "key_findings": findings[:5],
            "correlations": correlations[:3],
            "root_causes": root_causes[:3],
            "recommendations": recommendations[:5],
            "forecast": forecast,
        }

        reply = DeepAnalysisAgent._format_analysis_reply(analysis)

        return {
            "reply": reply,
            "type": Q_DEEP_ANALYSIS,
            "analysis_result": analysis,
            "plan": {
                "method": "deep_analysis_rule",
                "iterations": 1,
            },
        }

    @staticmethod
    def _format_analysis_reply(analysis: dict) -> str:
        """Format analysis result thành plain text (thead không render markdown)"""
        parts = [f"📊 PHÂN TÍCH & ĐÁNH GIÁ\n{analysis.get('summary', '')}"]

        # Key findings
        findings = analysis.get("key_findings", [])
        if findings:
            parts.append("\n🔍 PHÁT HIỆN CHÍNH")
            for i, f in enumerate(findings, 1):
                parts.append(f"\n{i}. {f}")

        # Root causes
        causes = analysis.get("root_causes", [])
        if causes:
            parts.append("\n\n🎯 NGUYÊN NHÂN GỐC RỄ")
            for c in causes:
                sev_text = {"critical": "🔴 CẤP BÁCH", "high": "🟠 CAO", "medium": "🟡 TRUNG BÌNH", "low": "🟢 THẤP"}
                icon = sev_text.get(c.get("severity", "medium"), "⚪")
                parts.append(f"\n{icon}")
                parts.append(f"\n- Vấn đề: {c['problem']}")
                parts.append(f"\n- Nguyên nhân: {c['why']}")
                parts.append(f"\n- Bằng chứng: {c['evidence']}")

        # Correlations
        corrs = analysis.get("correlations", [])
        if corrs:
            parts.append("\n\n🔗 TƯƠNG QUAN GIỮA CÁC CHỈ SỐ")
            for c in corrs:
                parts.append(f"\n- {c['metric_a']} với {c['metric_b']}: {c['relationship']}")
                parts.append(f"\n  Tác động: {c['impact']}")

        # Recommendations
        recs = analysis.get("recommendations", [])
        if recs:
            parts.append("\n\n💡 KHUYẾN NGHỊ HÀNH ĐỘNG")
            for i, r in enumerate(recs, 1):
                parts.append(f"\n{i}. {r['action']}")
                parts.append(f"\n   - Dự kiến: {r['expected_impact']}")

        # Forecast
        forecast = analysis.get("forecast", "")
        if forecast:
            parts.append(f"\n\n🔮 DỰ BÁO\n{forecast}")

        return "".join(parts)


class SelfCheckAgent:
    """
    Agent 5: SELF-CHECK — Kiểm tra chất lượng câu trả lời (nâng cấp)
    
    Input: question, reply, qtype, collected data
    Output: {"passed": True/False, "reason": "...", "missing_kpis": [...], "quality_scores": {...}}
    """

    @staticmethod
    def check(
        question: str,
        reply: str,
        qtype: str,
        collected: dict,
    ) -> dict:
        """
        Kiểm tra câu trả lời với nhiều tiêu chí hơn.
        
        Checks:
        1. Reply không rỗng
        2. Có số liệu cụ thể (số tiền, phần trăm)
        3. KPI đã được dùng trong reply
        4. (Chỉ cho DEEP_ANALYSIS) Cấu trúc phân tích đầy đủ
        """
        checks = []
        check_details = {}

        # 1. Reply không rỗng
        check1 = bool(reply and len(reply.strip()) > 0)
        checks.append(check1)
        check_details["non_empty"] = check1

        # 2. Có số liệu cụ thể
        has_numbers = bool(re.search(r'\d[\d,.]*', reply)) if reply else False
        checks.append(has_numbers)
        check_details["has_numbers"] = has_numbers

        # 3. KPI có sẵn (có dữ liệu, kể cả giá trị 0 — ví dụ phòng mới chưa có doanh thu)
        # Không yêu cầu v > 0 để tránh false-positive khi dữ liệu hợp lệ nhưng bằng 0
        available = collected.get("available", {})
        used_kpis = sum(1 for v in available.values() if v is not None)
        check3 = used_kpis > 0
        checks.append(check3)
        check_details["kpi_used"] = check3

        # 4. Độ dài reply hợp lý (không quá ngắn cho phân tích)
        if qtype == Q_DEEP_ANALYSIS:
            check4 = len(reply) > 200 if reply else False
            checks.append(check4)
            check_details["adequate_length"] = check4
        else:
            check_details["adequate_length"] = True  # Skip for non-analysis

        # 5. (Optional) Reply có cấu trúc: bullet points, section headers
        has_structure = False
        if reply:
            has_structure = bool(re.search(r'[\*\-]\s|\d+\.\s|##|\n\n', reply))
        check_details["has_structure"] = has_structure

        passed = all(checks)
        if not passed:
            reasons = []
            if not check1:
                reasons.append("Reply trống")
            if not has_numbers:
                reasons.append("Thiếu số liệu cụ thể")
            if not check3:
                reasons.append("Không sử dụng KPI có sẵn")
            if not check_details.get("adequate_length", True):
                reasons.append("Phân tích quá ngắn")
            reason = "; ".join(reasons) if reasons else "Unknown check failure"
        else:
            reason = "OK"

        # Xác định missing KPIs
        missing_kpis = []
        if not has_numbers:
            missing_kpis = QUESTION_KPI_NEEDS.get(qtype, [])[:3]

        return {
            "passed": passed,
            "reason": reason,
            "missing_kpis": missing_kpis,
            "quality_scores": check_details,
        }


class TextToSQLAgent:
    """
    Agent 5: TEXT-TO-SQL — Dịch câu hỏi thành SQL và thực thi
    
    Pipeline:
    1. Generate SQL từ Gemini (dùng TEXT_TO_SQL_SYSTEM_PROMPT đã cập nhật)
    2. Escape % → %% trong DATE_FORMAT (tránh xung đột pymysql)
    3. Execute SQL với property_id = $1
    4. Nếu lỗi → self-correction (gọi Gemini correct_sql) → retry (tối đa 2 lần)
    5. Generate response từ SQL result
    6. Select visualization type
    
    Input: question, property_id, db, history
    Output: {
        "reply": "...",
        "sql": "SELECT ...",
        "data": [...],
        "columns": [...],
        "visualization": {...},
        "row_count": N,
    } hoặc None nếu thất bại
    """
    MAX_SQL_CORRECTIONS = 2

    @staticmethod
    def _escape_date_format(sql: str) -> str:
        """
        Escape % trong string literals của SQL để pymysql không interpret
        %Y/%m/%d... như Python format specifiers.
        Dùng regex để bắt tất cả quoted strings có chứa %, bao gồm:
          DATE_FORMAT(col, '%Y-%m-%d'), DATE_FORMAT(col, '%Y-%m'), '%Y', v.v.
        """
        def _double_percent(m):
            # Nhân đôi tất cả % bên trong cặp nháy đơn
            return "'" + m.group(1).replace("%", "%%") + "'"
        return re.sub(r"'([^']*%[^']*)'" , _double_percent, sql)

    @staticmethod
    async def process(
        question: str,
        property_id: int,
        db,
        history: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Full Text-to-SQL pipeline với SQL query history cache.
        
        Cache flow:
        1. Normalize question → check cache
        2. Cache hit → dùng SQL đã cached (skip Gemini)
        3. Cache miss → gọi Gemini → lưu cache
        
        Returns dict with reply, sql, data, columns, visualization, row_count
        hoặc None nếu không thể generate SQL.
        """
        from src.services.gemini_service import gemini_service
        from src.engines.kpi_repository import sql_query_cache

        # === STEP 1: Check SQL Query Cache (skip Gemini nếu có) ===
        cached_sql = sql_query_cache.get(question)
        if cached_sql:
            sql = cached_sql
            log.debug("TextToSQL: Cache HIT for '%s'", question[:50])
        else:
            log.debug("TextToSQL: Cache MISS for '%s' -> calling Gemini", question[:50])
            sql = await gemini_service.generate_text_to_sql(
                question=question,
                context_summary=history,
            )
            if not sql or "SELECT" not in sql.upper():
                log.debug("TextToSQL: No valid SQL generated")
                return None
            # Lưu vào cache (cả khi có self-correction)
            sql_query_cache.set(question, sql)

        # Clean SQL: remove markdown, strip whitespace
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        # Safety check: only allow SELECT and WITH (CTE) statements
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            log.debug("TextToSQL: Rejected non-SELECT SQL: %s", sql[:100])
            return None
        
        sql = TextToSQLAgent._escape_date_format(sql)

        log.debug("TextToSQL: Generated SQL (first 200 chars): %s", sql[:200])

        # === STEP 2: Execute with self-correction loop ===
        rows = []
        last_error = None

        for attempt in range(TextToSQLAgent.MAX_SQL_CORRECTIONS + 1):
            try:
                rows = await db.fetch(sql, property_id)
                log.debug("TextToSQL: Execute OK, %d rows returned", len(rows))
                # Update cache with corrected SQL if self-correction was used
                if attempt > 0:
                    sql_query_cache.set(question, sql)
                    log.debug("TextToSQL: Updated cache with corrected SQL")
                break
            except Exception as e:
                last_error = str(e)
                log.warning("TextToSQL: Execute failed (attempt %d/%d): %s",
                            attempt + 1, TextToSQLAgent.MAX_SQL_CORRECTIONS + 1, last_error[:100])
                if attempt < TextToSQLAgent.MAX_SQL_CORRECTIONS:
                    corrected_sql = await gemini_service.correct_sql(
                        question=question,
                        last_error=last_error,
                        previous_sql=sql,
                    )
                    if corrected_sql and "SELECT" in corrected_sql.upper():
                        sql = corrected_sql.replace("```sql", "").replace("```", "").strip()
                        sql = TextToSQLAgent._escape_date_format(sql)
                    else:
                        log.debug("TextToSQL: Self-correction returned invalid SQL")
                        return None
                else:
                    log.debug("TextToSQL: All correction attempts failed: %s", last_error[:100])
                    sql_query_cache.invalidate(question)
                    return None

        if not rows:
            rows = []

        # === STEP 3: Get columns ===
        columns = list(rows[0].keys()) if rows else []

        # === STEP 4: Generate response ===
        reply = await gemini_service.generate_response(
            question=question,
            sql_result=rows,
        )
        if not reply:
            reply = f"Tìm thấy {len(rows)} kết quả."

        # === STEP 5: Select visualization ===
        viz = await gemini_service.select_visualization(
            sql_result=rows,
            columns=columns,
        )

        return {
            "reply": reply,
            "sql": sql,
            "data": rows[:50],
            "columns": columns,
            "visualization": viz,
            "row_count": len(rows),
            "error": None,
        }


class MultiAgentOrchestrator:
    """
    Orchestrator — Điều phối 5 agents với self-correction loop + Text-to-SQL fallback
    
    Main flow:
    1. PLANNER → [DEEP_ANALYSIS?] → RETRIEVER (loop) → ANSWER/DeepAnalysis → SELF-CHECK
    2. DEEP_ANALYSIS route: bỏ qua KPI pipeline, dùng DeepAnalysisAgent trực tiếp
    3. TEXT_TO_SQL route: chuyển sang TextToSQLAgent
    4. Standard route: ANSWER → SELF-CHECK → Text-to-SQL fallback nếu cần
    
    Enhanced flow:
    [1] PLANNER → [2a] DEEP_ANALYSIS → DeepAnalysisAgent → DONE
                   [2b] TEXT_TO_SQL   → TextToSQLAgent     → DONE
                   [2c] Standard       → RETRIEVER loop → ANSWER → SELF-CHECK → (fallback) → DONE
    """

    MAX_ITERATIONS = 2

    @staticmethod
    async def process(
        question: str,
        kpi: KPIObject,
        history: str = "",
        db=None,
        property_id: Optional[int] = None,
    ) -> dict:
        """
        Run the multi-agent pipeline with self-correction loop + Text-to-SQL fallback.
        """
        missing_kpis = None
        collected = None
        current_type = None
        used_text_to_sql = False
        t2s_result = None

        # === Detect direct routes: DEEP_ANALYSIS or TEXT_TO_SQL ===
        qtype_direct, _ = QuestionClassifier.classify(question)

        # Direct DEEP_ANALYSIS route — KPI-first, SQL supplement nếu có gap
        if qtype_direct == Q_DEEP_ANALYSIS:
            log.debug("Orchestrator: DEEP_ANALYSIS route for '%s'", question[:50])

            # Bước 1: Ưu tiên KPI cache — lấy toàn bộ KPI có sẵn
            collected = RetrieverAgent.retrieve(
                QUESTION_KPI_NEEDS[Q_DEEP_ANALYSIS], kpi
            )

            # Bước 2: Nếu KPI có gap VÀ có database → dùng SQL bổ sung dữ liệu còn thiếu
            sql_supplement_context = ""
            if collected["has_gaps"] and db is not None and property_id is not None:
                log.debug("DEEP_ANALYSIS: KPI gaps=%s → trying SQL supplement", collected["missing"][:3])
                try:
                    t2s_result = await TextToSQLAgent.process(question, property_id, db, history)
                    if t2s_result and t2s_result.get("data"):
                        supplement_rows = t2s_result["data"][:20]  # giới hạn 20 rows
                        sql_supplement_context = (
                            f"\n\nDỮ LIỆU BỔ SUNG TỪ DATABASE (SQL):\n"
                            + json.dumps(supplement_rows, ensure_ascii=False, indent=2)
                        )
                        log.debug("DEEP_ANALYSIS: SQL supplement OK, %d rows", len(supplement_rows))
                except Exception as e:
                    log.debug("DEEP_ANALYSIS: SQL supplement failed: %s", str(e)[:60])

            # Bước 3: Phân tích sâu với KPI + SQL supplement (nếu có)
            enriched_history = history + sql_supplement_context
            analysis_result = await DeepAnalysisAgent.analyze(
                question=question,
                kpi=kpi,
                collected=collected,
                history=enriched_history,
            )

            suggestions = _get_suggestions_for_type(Q_DEEP_ANALYSIS, kpi)
            analysis_result["suggestions"] = suggestions
            analysis_result["plan"] = analysis_result.get("plan", {})
            analysis_result["plan"]["required_kpis"] = list(collected.get("available", {}).keys())
            analysis_result["plan"]["kpi_gaps"] = collected.get("missing", [])
            analysis_result["plan"]["sql_supplement"] = bool(sql_supplement_context)
            return analysis_result

        # Direct TEXT_TO_SQL route
        if qtype_direct == Q_TEXT_TO_SQL and db is not None and property_id is not None:
            log.debug("Orchestrator: direct TEXT_TO_SQL route for '%s'", question[:50])
            t2s_result = await TextToSQLAgent.process(question, property_id, db, history)
            used_text_to_sql = True
            if t2s_result and t2s_result.get("error") is None:
                return {
                    "reply": t2s_result["reply"],
                    "suggestions": [],
                    "type": Q_TEXT_TO_SQL,
                    "plan": {
                        "iterations": 1,
                        "method": "text_to_sql_direct",
                        "sql": t2s_result.get("sql", ""),
                        "row_count": t2s_result.get("row_count", 0),
                        "visualization": t2s_result.get("visualization"),
                    },
                }

        # === Standard KPI pipeline ===
        for iteration in range(MultiAgentOrchestrator.MAX_ITERATIONS):
            log.debug("Orchestrator iteration %d/%d", iteration + 1, MultiAgentOrchestrator.MAX_ITERATIONS)

            # === STEP 1: PLANNER ===
            plan = await PlannerAgent.plan(question, kpi, previous_missing=missing_kpis)
            qtype = plan["type"]
            required_kpis = plan["required_kpis"]
            current_type = qtype

            # Nếu planner phân loại là DEEP_ANALYSIS — KPI-first + SQL supplement
            if qtype == Q_DEEP_ANALYSIS:
                log.debug("Orchestrator: Planner routed to DEEP_ANALYSIS for '%s'", question[:50])

                # Bước 1: Ưu tiên KPI
                collected = RetrieverAgent.retrieve(
                    QUESTION_KPI_NEEDS[Q_DEEP_ANALYSIS], kpi
                )

                # Bước 2: SQL supplement nếu KPI có gap (và chưa dùng SQL)
                sql_supplement_context = ""
                if collected["has_gaps"] and db is not None and property_id is not None and not used_text_to_sql:
                    log.debug("DEEP_ANALYSIS (planner): KPI gaps → SQL supplement")
                    try:
                        t2s_result = await TextToSQLAgent.process(question, property_id, db, history)
                        used_text_to_sql = True
                        if t2s_result and t2s_result.get("data"):
                            supplement_rows = t2s_result["data"][:20]
                            sql_supplement_context = (
                                f"\n\nDỮ LIỆU BỔ SUNG TỪ DATABASE (SQL):\n"
                                + json.dumps(supplement_rows, ensure_ascii=False, indent=2)
                            )
                    except Exception as e:
                        log.debug("DEEP_ANALYSIS (planner): SQL supplement failed: %s", str(e)[:60])

                # Bước 3: Phân tích sâu
                enriched_history = history + sql_supplement_context
                analysis_result = await DeepAnalysisAgent.analyze(
                    question=question,
                    kpi=kpi,
                    collected=collected,
                    history=enriched_history,
                )
                suggestions = _get_suggestions_for_type(Q_DEEP_ANALYSIS, kpi)
                analysis_result["suggestions"] = suggestions
                analysis_result["plan"] = analysis_result.get("plan", {})
                analysis_result["plan"]["kpi_gaps"] = collected.get("missing", [])
                analysis_result["plan"]["sql_supplement"] = bool(sql_supplement_context)
                return analysis_result

            # Nếu planner phân loại là TEXT_TO_SQL, chuyển sang TextToSQL
            if qtype == Q_TEXT_TO_SQL and db is not None and property_id is not None and not used_text_to_sql:
                log.debug("Orchestrator: Planner routed to TEXT_TO_SQL for '%s'", question[:50])
                t2s_result = await TextToSQLAgent.process(question, property_id, db, history)
                used_text_to_sql = True
                if t2s_result and t2s_result.get("error") is None:
                    return {
                        "reply": t2s_result["reply"],
                        "suggestions": [],
                        "type": Q_TEXT_TO_SQL,
                        "plan": {
                            "iterations": 1,
                            "method": "text_to_sql_planned",
                            "sql": t2s_result.get("sql", ""),
                            "row_count": t2s_result.get("row_count", 0),
                            "visualization": t2s_result.get("visualization"),
                        },
                    }

            # === STEP 2: RETRIEVER — Lấy KPI có sẵn ===
            collected = RetrieverAgent.retrieve(required_kpis, kpi)

            # === Check: can gap? ===
            if collected["has_gaps"] and iteration < MultiAgentOrchestrator.MAX_ITERATIONS - 1:
                missing_kpis = collected["missing"]
                log.debug("Gap detected: %d missing KPIs -> re-planning", len(missing_kpis))
                continue  # Loop lai tu Planner
            else:
                break  # Du KPI hoac het luot loop

        # === STEP 2b: SQL supplement nếu KPI vẫn còn gap sau loop ===
        sql_data_for_answer = None
        if collected and collected["has_gaps"] and db is not None and property_id is not None and not used_text_to_sql:
            log.debug("Standard pipeline: KPI gaps=%s → SQL supplement before Answer", collected.get("missing", [])[:3])
            try:
                supplement = await TextToSQLAgent.process(question, property_id, db, history)
                if supplement and supplement.get("data"):
                    sql_data_for_answer = supplement["data"][:20]
                    used_text_to_sql = True
                    log.debug("Standard: SQL supplement OK, %d rows → passing to AnswerAgent", len(sql_data_for_answer))
            except Exception as e:
                log.debug("Standard: SQL supplement failed: %s", str(e)[:60])

        # === STEP 3: ANSWER — KPI + SQL supplement (nếu có) ===
        reply = await AnswerAgent.answer(
            question, current_type, kpi, collected, history,
            sql_data=sql_data_for_answer,
        )

        # === STEP 4: SELF-CHECK ===
        check_result = SelfCheckAgent.check(question, reply, current_type, collected)

        # === STEP 5: Text-to-SQL fallback nếu self-check fail ===
        if not check_result["passed"] and db is not None and property_id is not None and not used_text_to_sql:
            log.debug("Self-check failed: %s -> trying Text-to-SQL fallback", check_result["reason"])
            t2s_result = await TextToSQLAgent.process(question, property_id, db, history)
            if t2s_result and t2s_result.get("error") is None:
                # Text-to-SQL thành công, dùng kết quả này
                suggestions = _get_suggestions_for_type(current_type, kpi)
                return {
                    "reply": t2s_result["reply"],
                    "suggestions": suggestions,
                    "type": f"{current_type}_WITH_SQL",
                    "plan": {
                        "iterations": (1 if missing_kpis is None else 2),
                        "method": "kpi_with_text_to_sql_fallback",
                        "sql": t2s_result.get("sql", ""),
                        "row_count": t2s_result.get("row_count", 0),
                        "visualization": t2s_result.get("visualization"),
                    },
                }
            else:
                # Text-to-SQL cũng fail, dùng template fallback
                log.debug("Text-to-SQL fallback also failed, using template")
                reply = AIAskService._build_fallback_answer(current_type, kpi)
        elif not check_result["passed"]:
            log.debug("Self-check failed, using template fallback (no db): %s", check_result["reason"])
            reply = AIAskService._build_fallback_answer(current_type, kpi)

        # Generate suggestions
        suggestions = _get_suggestions_for_type(current_type, kpi)

        plan_result = {
            "iterations": (1 if missing_kpis is None else 2),
            "required_kpis": list(collected.get("available", {}).keys()) if collected else [],
            "gaps_filled": missing_kpis is None or len(missing_kpis) == 0,
        }

        # Thêm thông tin Text-to-SQL nếu đã dùng
        if t2s_result:
            plan_result["sql"] = t2s_result.get("sql", "")
            plan_result["row_count"] = t2s_result.get("row_count", 0)

        return {
            "reply": reply,
            "suggestions": suggestions,
            "type": current_type,
            "plan": plan_result,
        }


async def _resolve_property_id(landlord_id: int, db) -> Optional[int]:
    """
    Map landlord_id (user_id) sang property_id.
    Dùng property_staff_assignments để tìm property của user.
    """
    try:
        row = await db.fetchrow(
            """SELECT property_id FROM property_staff_assignments 
               WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE' 
               LIMIT 1""",
            landlord_id
        )
        if row:
            return row.get("property_id")
        # Fallback: lấy property đầu tiên
        row = await db.fetchrow(
            "SELECT property_id FROM properties WHERE deleted_at IS NULL LIMIT 1"
        )
        return row.get("property_id") if row else None
    except Exception as e:
        log.warning("Failed to resolve property_id: %s", e)
        return None


class AIAskService:
    """Service xử lý câu hỏi của kế toán"""

    # Fallback templates theo loại câu hỏi (16 types)
    # Lưu ý: revenue keys dùng {electricity}/{water}, expense keys dùng {exp_electricity}/{exp_water}
    FALLBACK_TEMPLATES = {
        Q_REVENUE: "Doanh thu kỳ {period}: {rev_total}đ (Tiền phòng: {rent}đ, Điện: {electricity}đ, Nước: {water}đ, DV: {service}đ). Tăng trưởng: {growth}.",
        Q_REVENUE_BREAKDOWN: "Cơ cấu doanh thu kỳ {period}: Tiền phòng {rent}đ ({rent_pct}%), Điện {electricity}đ ({elec_pct}%), Nước {water}đ ({water_pct}%), DV {service}đ ({svc_pct}%), Khác {rev_other}đ ({other_pct}%). Phòng có khách: {occupied}/{occ_total}.",
        Q_EXPENSE: "Tổng chi phí kỳ {period}: {exp_total}đ (Điện: {exp_electricity}đ, Nước: {exp_water}đ, Sửa chữa: {maintenance}đ).",
        Q_EXPENSE_ANALYSIS: "Phân tích chi phí kỳ {period}: Tổng {exp_total}đ. Chi tiết: Điện {exp_electricity}đ, Nước {exp_water}đ, Sửa chữa {maintenance}đ, Phạt {penalty}đ, Khác {exp_other}đ. Tỷ lệ CP/DT: {ratio}%.",
        Q_PROFIT: "Lợi nhuận ròng: {rev_total} - {exp_total} = {profit}đ. Tỷ lệ chi phí/doanh thu: {ratio}%.",
        Q_PROFIT_DRIVERS: "Lợi nhuận {profit}đ từ Doanh thu {rev_total}đ - Chi phí {exp_total}đ. Yếu tố chính: {occupied}/{occ_total} phòng có khách ({occ_rate}%), công nợ {debt_total}đ.",
        Q_DEBT: "Tổng công nợ: {debt_total}đ ({count} hóa đơn quá hạn). Tỷ lệ thu tiền: {rate}%.",
        Q_DEBT_DETAIL: "Chi tiết công nợ: {count} hóa đơn quá hạn, tổng {debt_total}đ. Tỷ lệ thu: {rate}%. Phòng có nợ: {debt_rooms}. Cần ưu tiên xử lý phòng nợ lâu ngày.",
        Q_OCCUPANCY: "Tỉ lệ lấp đầy kỳ {period}: {occ_rate}% ({occupied}/{occ_total} phòng, {vacant} phòng trống). Thay đổi: {change}% so với kỳ trước.",
        Q_OCCUPANCY_TREND: "Xu hướng lấp đầy: {occ_rate}% ({occupied}/{occ_total} phòng). Thay đổi so với kỳ trước: {change}%. Đang có {vacant} phòng trống cần tìm khách.",
        Q_COMPARISON: "Doanh thu: {current_rev}đ. Kỳ trước: {prev_rev}đ. {change_pct}%. Chi phí: {current_exp}đ (kỳ trước: {prev_exp}đ).",
        Q_CASH_FLOW: "Dòng tiền kỳ {period}: Doanh thu {rev_total}đ, tỷ lệ thu {rate}%. Nợ quá hạn {debt_total}đ ({count} hóa đơn). Lợi nhuận {profit}đ.",
        Q_FORECAST: "Dự báo dựa trên dữ liệu kỳ {period}: Doanh thu {rev_total}đ, lấp đầy {occ_rate}% ({occupied}/{occ_total} phòng). Tăng trưởng: {growth}. Cần theo dõi biến động phòng trống.",
        Q_RISK_ASSESSMENT: "Đánh giá rủi ro kỳ {period}: Sức khỏe {health_status} ({health_score}/100). Nợ {debt_total}đ ({count} hóa đơn), lấp đầy {occ_rate}%. Cần theo dõi chặt công nợ và tỉ lệ phòng trống.",
        Q_ANALYSIS: "Kỳ {period}: Doanh thu {rev}đ, Chi phí {exp}đ, Lợi nhuận {profit}đ, Lấp đầy {occ}%. Sức khỏe: {health_status}.",
        Q_DEEP_ANALYSIS: "Phân tích kỳ {period}: Doanh thu {rev}đ, Chi phí {exp}đ, Lợi nhuận {profit}đ, Lấp đầy {occ}%. Sức khỏe: {health_status}. Chi tiết: Doanh thu {rent}đ (tiền phòng), {electricity}đ (điện), {water}đ (nước), {service}đ (dịch vụ). Chi phí: {exp_electricity}đ (điện), {exp_water}đ (nước), bảo trì {maintenance}đ. Công nợ {debt_total}đ ({count} hóa đơn, tỷ lệ thu {rate}%). {debt_rooms}.",
        Q_TEXT_TO_SQL: "Rất tiếc, tôi không thể truy vấn database ngay lúc này. Vui lòng thử lại sau.",
        Q_GENERAL: "Kỳ {period}: Doanh thu {rev}đ, Chi phí {exp}đ, Lợi nhuận {profit}đ, Lấp đầy {occ}%. Sức khỏe: {health_status}.",
    }

    @staticmethod
    def _build_kpi_context(kpi: KPIObject) -> dict:
        """Build KPI context cho LLM"""
        return {
            "period": kpi.period,
            "revenue": kpi.revenue.model_dump(),
            "expense": kpi.expense.model_dump(),
            "profit": kpi.profit.model_dump(),
            "debt": kpi.debt.model_dump(),
            "occupancy": kpi.occupancy.model_dump(),
            "previous_period": kpi.previous_period.model_dump() if kpi.previous_period else None,
            "change_pct": kpi.change_pct.model_dump() if kpi.change_pct else None,
            "health_score": kpi.health_score,
            "health_status": kpi.health_status,
        }

    @staticmethod
    def _build_fallback_answer(qtype: str, kpi: KPIObject) -> str:
        """Tạo fallback answer từ template (16 types)"""
        template = AIAskService.FALLBACK_TEMPLATES.get(qtype, AIAskService.FALLBACK_TEMPLATES[Q_GENERAL])

        rev = kpi.revenue
        exp = kpi.expense
        prof = kpi.profit
        debt = kpi.debt
        occ = kpi.occupancy
        prev = kpi.previous_period

        # Tinh ty trong doanh thu
        rev_total = rev.total if rev and rev.total > 0 else 1
        rent_pct = round(rev.rent / rev_total * 100, 1) if rev else 0
        elec_pct = round(rev.electricity / rev_total * 100, 1) if rev else 0
        water_pct = round(rev.water / rev_total * 100, 1) if rev else 0
        svc_pct = round(rev.service / rev_total * 100, 1) if rev else 0
        other_pct = round(rev.other / rev_total * 100, 1) if rev else 0

        # Debt rooms string
        debt_rooms_str = "không có"
        if debt and debt.debt_by_room:
            room_names = [d.room for d in debt.debt_by_room[:5]]
            debt_rooms_str = ", ".join(room_names)

        kwargs = {
            "period": kpi.period,
            "rev_total": f"{rev.total:,.0f}" if rev else "0",
            "rent": f"{rev.rent:,.0f}" if rev else "0",
            "electricity": f"{rev.electricity:,.0f}" if rev else "0",
            "water": f"{rev.water:,.0f}" if rev else "0",
            "service": f"{rev.service:,.0f}" if rev else "0",
            "rev_other": f"{rev.other:,.0f}" if rev else "0",
            "growth": f"{rev.growth_pct}%" if rev and rev.growth_pct else "không có dữ liệu",
            "rent_pct": rent_pct,
            "elec_pct": elec_pct,
            "water_pct": water_pct,
            "svc_pct": svc_pct,
            "other_pct": other_pct,
            "exp_total": f"{exp.total:,.0f}" if exp else "0",
            "exp_electricity": f"{exp.electricity:,.0f}" if exp else "0",
            "exp_water": f"{exp.water:,.0f}" if exp else "0",
            "maintenance": f"{exp.maintenance:,.0f}" if exp else "0",
            "penalty": f"{exp.penalty:,.0f}" if exp else "0",
            "exp_other": f"{exp.other:,.0f}" if exp else "0",
            "revenue": f"{rev.total:,.0f}" if rev else "0",
            "expense": f"{exp.total:,.0f}" if exp else "0",
            "profit": f"{prof.net:,.0f}" if prof else "0",
            "ratio": prof.expense_ratio if prof else 0,
            "debt_total": f"{debt.overdue_amount:,.0f}" if debt else "0",
            "count": debt.overdue_count if debt else 0,
            "rate": debt.collection_rate if debt else 100.0,
            "debt_rooms": debt_rooms_str,
            "occ_rate": occ.occupancy_rate if occ else 0,
            "occupied": occ.occupied_rooms if occ else 0,
            "occ_total": occ.total_rooms if occ else 0,
            "vacant": (occ.total_rooms - occ.occupied_rooms) if occ else 0,
            "change": occ.occupancy_change if occ and occ.occupancy_change else 0,
            "current_rev": f"{rev.total:,.0f}" if rev else "0",
            "prev_rev": f"{prev.revenue.get('total', 0):,.0f}" if prev and prev.revenue else "N/A",
            "change_pct": f"Tăng {kpi.change_pct.revenue}%" if kpi.change_pct and kpi.change_pct.revenue and kpi.change_pct.revenue > 0
                          else f"Giảm {abs(kpi.change_pct.revenue)}%" if kpi.change_pct and kpi.change_pct.revenue and kpi.change_pct.revenue < 0
                          else "Không thay đổi",
            "current_exp": f"{exp.total:,.0f}" if exp else "0",
            "prev_exp": f"{prev.expense.get('total', 0):,.0f}" if prev and prev.expense else "N/A",
            "rev": f"{rev.total:,.0f}" if rev else "0",
            "exp": f"{exp.total:,.0f}" if exp else "0",
            "profit": f"{prof.net:,.0f}" if prof else "0",
            "occ": occ.occupancy_rate if occ else 0,
            "health_status": kpi.health_status if kpi and kpi.health_status else "Bình thường",
            "health_score": kpi.health_score if kpi and kpi.health_score else 0,
        }
        return template.format(**kwargs)

    @staticmethod
    async def process_question(
        question: str,
        landlord_id: int,
        period: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Xử lý câu hỏi của kế toán — Multi-Agent Pipeline + Text-to-SQL
        
        Pipeline:
        1. Lấy KPI context + database connection
        2. Session management
        3. Multi-Agent Orchestrator (PLANNER → RETRIEVER loop → ANSWER → SELF-CHECK)
        4. Text-to-SQL fallback khi cần (direct hoặc self-check fail)
        5. Evaluation logging
        6. Save to session
        """
        # Start evaluation logging
        with eval_logger.start(
            question=question,
            intent="GENERAL",
            landlord_id=landlord_id,
            period=period,
            session_id=session_id,
        ) as eval_ctx:
            # === STEP 0: Get KPI context + database connection ===
            kpi = KPIRepository.get_kpi(landlord_id, period)
            if kpi is None:
                from src.api.v1.kpi import _calculate_full_kpi
                kpi = await _calculate_full_kpi(landlord_id, period)

            # Get database connection for Text-to-SQL
            db = None
            property_id = None
            try:
                db = await get_db()
                property_id = await _resolve_property_id(landlord_id, db)
            except Exception as e:
                log.warning("Failed to get database for Text-to-SQL: %s", e)

            # === STEP 0b: Session management ===
            if not session_id:
                session_id = SessionStore.create_session(landlord_id)
            history = SessionStore.format_history_for_context(session_id)

            # === STEP 1-5: Harness Agentic Reasoning Loop ===
            log.debug("process_question: starting Harness Agent Loop for '%s' (L%s, %s)", question[:50], landlord_id, period)
            from src.harness.agent_loop import HarnessAgentLoop
            result = await HarnessAgentLoop.run(
                question=question,
                landlord_id=landlord_id,
                period=period,
                history=history,
            )

            # Update evaluation context
            qtype = result["type"]
            eval_ctx.set_intent(qtype)
            use_model = "text_to_sql" if "SQL" in qtype or qtype == Q_TEXT_TO_SQL else "multi-agent-template"
            eval_ctx.set_reply(
                reply=result["reply"],
                model_used=use_model,
                token_count=0,
                from_cache=False,
                fallback_used=(qtype == "GENERAL" and len(result.get("reply", "")) < 20),
            )

            # === STEP 6: Save to session (in-memory + database) ===
            SessionStore.add_turn(session_id, question, result["reply"])
            # Persist to database in background (fire-and-forget)
            sql_q = None
            plan = result.get("plan")
            if isinstance(plan, dict):
                sql_q = plan.get("sql")
            asyncio.create_task(SessionStore.persist_turn(
                session_id=session_id,
                landlord_id=landlord_id,
                question=question,
                reply=result["reply"],
                db=db,
                sql_query=sql_q,
                is_successful=True,
            ))

            from src.services.suggestion_service import suggestion_service
            dynamic_suggestions = await suggestion_service.get_suggestions(landlord_id, period, kpi=kpi)

            return {
                "reply": result["reply"],
                "session_id": session_id,
                "suggestions": dynamic_suggestions[:4],
                "type": qtype,
                "plan": result.get("plan", {}),
            }


def _normalize_vietnamese(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để regex match cả input có dấu và không dấu"""
    replacements = {
        'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ạ': 'a',
        'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text


def _get_suggestions_for_type(qtype: str, kpi: KPIObject) -> List[str]:
    """Sinh gợi ý câu hỏi đào sâu theo ngữ cảnh KPI"""
    # Luôn thêm câu hỏi đào sâu dựa trên KPI context
    deep_questions = []

    rev = kpi.revenue
    exp = kpi.expense
    debt = kpi.debt
    occ = kpi.occupancy
    prof = kpi.profit
    # Cau hoi phan tuong quan
    if rev and rev.total > 0:
        if exp and exp.total > 0:
            deep_questions.append(
                f"Vi sao doanh thu {rev.total:,.0f}d nhung chi phi {exp.total:,.0f}d — co the toi uu duoc khong?"
            )
        if occ and occ.occupancy_rate < 100:
            deep_questions.append(
                f"Neu lap day {occ.vacant_rooms} phong trong, doanh thu tang them bao nhieu?"
            )
        if debt and debt.overdue_amount > 0:
            deep_questions.append(
                f"Neu thu hoi {debt.overdue_amount:,.0f}d cong no, dong tien cai thien the nao?"
            )

        # Phan tich bien dong
        if kpi.change_pct:
            if kpi.change_pct.revenue and kpi.change_pct.expense:
                c_rev = kpi.change_pct.revenue
                c_exp = kpi.change_pct.expense
                if c_rev > 0 and c_exp > c_rev:
                    deep_questions.append(
                        f"Doanh thu tang {c_rev}% nhung chi phi tang {c_exp}% — vi sao chi phi tang nhanh hon?"
                    )
            if kpi.change_pct.revenue and kpi.change_pct.revenue < 0:
                deep_questions.append(
                    f"Doanh thu giam {abs(kpi.change_pct.revenue)}% — nguyen nhan chinh tu khoan muc nao?"
                )

        # Cau hoi ve hieu suat
        if rev.rent > 0 and rev.service > 0:
            service_ratio = round(rev.service / rev.rent * 100, 1)
            deep_questions.append(
                f"Ti le dich vu/tien phong la {service_ratio}% — co phu hop voi mat bang thi truong khong?"
            )

        # Cau hoi du bao
        if occ and occ.occupancy_change and occ.occupancy_change < -2:
            deep_questions.append(
                f"Ti le lap day giam {abs(occ.occupancy_change)}% trong thang — can co chien luoc gi de cai thien?"
            )

    # Neu co no qua han -> uu tien
    if debt and debt.overdue_count > 0:
        if debt.debt_by_room:
            warning_rooms = [d.room for d in debt.debt_by_room[:3]]
            deep_questions.append(
                f"Phong {', '.join(warning_rooms)} dang co no canh bao — co nen gia han hay yeu cau tra ngay?"
            )
        else:
            deep_questions.append(
                f"Co {debt.overdue_count} hoa don qua han tong {debt.overdue_amount:,.0f}d — chien luoc xu ly the nao?"
            )

    # Suggestions theo loai (16 types)
    suggestions_map = {
        Q_REVENUE: [
            "Phan tich co cau doanh thu: khoan nao dang tang, khoan nao dang giam?",
            "Ty trong doanh thu giua cac nguon co thay doi bat thuong khong?",
            "Doanh thu thuc te so voi ky vong chenh lech bao nhieu?",
        ],
        Q_REVENUE_BREAKDOWN: [
            "Khoan muc nao trong doanh thu bien dong nhieu nhat?",
            "Vi sao tien dien/tien nuoc lai thay doi so voi thang truoc?",
            "Co nen dieu chinh co cau dich vu de toi uu doanh thu?",
        ],
        Q_EXPENSE: [
            "Dinh muc chi phi moi phong la bao nhieu — co cao hon trung binh nganh khong?",
            "Chi phi nao co the cat giam ma khong anh huong den chat luong dich vu?",
            "Ty le chi phi/doanh thu qua cac thang dang tang hay giam?",
        ],
        Q_EXPENSE_ANALYSIS: [
            "Khoan chi phi nao chiem ty trong lon nhat va tai sao?",
            "Chi phi bao tri co tang bat thuong trong ky khong?",
            "Co co hoi nao de toi uu chi phi dien/nuoc khong?",
        ],
        Q_PROFIT: [
            "Bien loi nhuan gop qua 6 thang co xu huong gi?",
            "Diem hoa von o muc lap day bao nhieu %?",
            "Neu dieu chinh gia phong, loi nhuan thay doi the nao?",
        ],
        Q_PROFIT_DRIVERS: [
            "Yeu to nao anh huong nhieu nhat den loi nhuan?",
            "Neu lap day phong trong, loi nhuan tang bao nhieu?",
            "Co nen tang gia hoac giam chi phi de cai thien loi nhuan?",
        ],
        Q_DEBT: [
            "Phan tich cu the tung phong no: ly do, thoi gian, kha nang thu hoi?",
            "Co nen ap dung chinh sach phat phat qua han hay uu dai cho tra som?",
            "Rui ro tong the tu cong no hien tai la gi?",
        ],
        Q_DEBT_DETAIL: [
            "Phong nao co tuoi no cao nhat va can xu ly gap?",
            "Xep hang uu tien cac phong can thu hoi no?",
            "Co the ap dung bien phap phap ly cho phong no lau khong?",
        ],
        Q_OCCUPANCY: [
            "Phong trong lau nhat la phong nao — co van de ve gia hay chat luong?",
            "Mua vu co anh huong den ti le lap day khong?",
            "Chien luoc marketing nao co the ap dung de lap day phong trong?",
        ],
        Q_OCCUPANCY_TREND: [
            "Xu huong lap day 6 thang dang tang hay giam?",
            "Thang nao trong nam co ti le bo phong cao nhat?",
            "Co quy luat theo mua trong viec lap day phong khong?",
        ],
        Q_COMPARISON: [
            "Phan tich xu huong tang truong 6 thang gan day?",
            "So voi cung ky nam ngoai, hieu qua kinh doanh cai thien hay suy giam?",
            "Mua nao trong nam la mua cao diem va thap diem?",
        ],
        Q_CASH_FLOW: [
            "Kha nang thu hoi cong no co anh huong the nao den dong tien?",
            "Co du tien mat de chi tra cac khoan phi trong thang toi khong?",
            "De xuat cai thien dong tien cho thang toi?",
        ],
        Q_FORECAST: [
            "Du bao doanh thu thang toi dua tren xu huong hien tai?",
            "Kha nang lap day trong thang toi the nao?",
            "Can chuan bi gi cho bien dong theo mua sap toi?",
        ],
        Q_RISK_ASSESSMENT: [
            "Rui ro lon nhat hien tai la gi va can xu ly ra sao?",
            "Chi so suc khoe KPI co dang suy giam khong?",
            "Ke hoach giam thieu rui ro uu tien trong thang toi?",
        ],
        Q_ANALYSIS: [
            "Phan tich SWAT diem manh, diem yeu cua ky nay?",
            "Buc tranh tong the tai chinh cua ky nay the nao?",
            "Chi so nao co dau hieu can theo doi dac biet?",
        ],
        Q_DEEP_ANALYSIS: [
            "Phân tích chi tiết từng yếu tố ảnh hưởng đến lợi nhuận?",
            "So sánh hiệu quả kinh doanh giữa các tháng?",
            "Chiến lược cải thiện doanh thu trong 3 tháng tới?",
            "Rủi ro lớn nhất hiện tại và cách giảm thiểu?",
            "Đề xuất kế hoạch hành động ưu tiên?",
        ],
        Q_GENERAL: [
            "Chi so KPI nao can quan tam nhat trong thang nay?",
            "Buc tranh tong the tai chinh cua ky nay the nao?",
            "Khuyn nghi uu tien hanh dong trong thang toi la gi?",
            "Chi so nao co dau hieu can theo doi dac biet?",
        ],
    }

    # Ket hop: questions theo loai + deep questions + mac dinh
    type_questions = suggestions_map.get(qtype, suggestions_map[Q_GENERAL])
    result = type_questions[:3] + deep_questions + [
        "Phan tich tong quan tinh hinh kinh doanh thang nay?",
        "De xuat hanh dong uu tien cho thang toi?",
    ]
    return result[:8]


ai_ask_service = AIAskService()
