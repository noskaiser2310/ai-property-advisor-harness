"""
Harness Tools — Core Tools for AI Property Advisor
SOTA Toolset with Code Interpreter Agent (Self-Coding Execution) capability.
"""
import json
import logging
import re
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional
from database.connection import get_db
from src.engines.kpi_repository import KPIRepository

log = logging.getLogger("ai-property-advisor.harness.tools")

# ── Core Tool Definitions (Includes Code Interpreter REPL Tool) ───────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_kpi_overview",
        "description": "Lấy tổng quan tất cả chỉ số KPI (doanh thu tổng, chi phí tổng, lợi nhuận, công nợ tổng, tỉ lệ lấp đầy) trong kỳ báo cáo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "landlord_id": {"type": "integer", "description": "ID người quản lý (user_id)"},
                "period": {"type": "string", "description": "Kỳ báo cáo (định dạng YYYY-MM, ví dụ '2026-06')"}
            },
            "required": ["landlord_id", "period"]
        }
    },
    {
        "name": "execute_sql_query",
        "description": "Truy vấn CSDL MySQL trực tiếp để trả lời TẤT CẢ các câu hỏi chi tiết về ma trận trạng thái phòng, danh sách phòng nợ, chỉ số điện nước, phiếu bảo trì, tỉ suất lợi nhuận và lịch sử các tháng.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string", "description": "Câu lệnh SELECT/WITH MySQL thuần túy (dùng CURDATE(), DATE_FORMAT, JOIN hợp lệ, WHERE property_id = $1)"},
                "landlord_id": {"type": "integer", "description": "ID người quản lý để lọc dữ liệu theo property"}
            },
            "required": ["sql_query", "landlord_id"]
        }
    },
    {
        "name": "execute_dynamic_python_script",
        "description": "Code Interpreter: Cho phép AI tự viết đoạn mã Python để xử lý các phép toán phức tạp, phân tích dữ liệu đa chiều, hoặc chạy mô hình dự báo ngẫu nhiên mà không bị ảo giác.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Đoạn mã Python thuần túy cần thực thi để tính toán kết quả"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "generate_marketing_post",
        "description": "Tạo bài đăng Facebook/Zalo tìm khách thuê phòng trọ chuẩn AIDA dựa trên thông tin phòng.",
        "input_schema": {
            "type": "object",
            "properties": {
                "room_number": {"type": "string", "description": "Mã/Số phòng"},
                "base_price": {"type": "number", "description": "Giá thuê hàng tháng (VNĐ)"},
                "area_sqm": {"type": "number", "description": "Diện tích (m²)"},
                "amenities": {"type": "string", "description": "Các tiện ích sẵn có (điều hòa, nóng lạnh, ban công...)"},
                "property_address": {"type": "string", "description": "Địa chỉ khu trọ"}
            },
            "required": ["room_number", "base_price"]
        }
    }
]


# ── Tool Implementations ──────────────────────────────────────────────────────

async def tool_get_kpi_overview(landlord_id: int, period: str) -> str:
    try:
        kpi = KPIRepository.get_kpi(landlord_id, period)
        if kpi is None:
            from src.api.v1.kpi import _calculate_full_kpi
            kpi = await _calculate_full_kpi(landlord_id, period)
        
        if not kpi:
            return json.dumps({"error": f"Không tìm thấy dữ liệu KPI cho kỳ {period}"}, ensure_ascii=False)

        data = {
            "period": kpi.period,
            "revenue": kpi.revenue.model_dump() if kpi.revenue else {},
            "expense": kpi.expense.model_dump() if kpi.expense else {},
            "profit": kpi.profit.model_dump() if kpi.profit else {},
            "debt": kpi.debt.model_dump() if kpi.debt else {},
            "occupancy": kpi.occupancy.model_dump() if kpi.occupancy else {},
            "health_score": kpi.health_score,
            "health_status": kpi.health_status,
        }
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        log.error("Tool get_kpi_overview failed: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def tool_execute_sql_query(sql_query: str, landlord_id: int) -> str:
    try:
        db = await get_db()
        if db._pool is None:
            return json.dumps({"warning": "Database connection offline (Mock Mode). Cannot run SQL."}, ensure_ascii=False)

        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        sql_upper = clean_sql.upper()

        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return json.dumps({"error": "Chỉ cho phép thực thi truy vấn SELECT hoặc CTE (WITH)."}, ensure_ascii=False)

        row = await db.fetchrow(
            "SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE' LIMIT 1",
            landlord_id
        )
        property_id = row.get("property_id") if row else 1

        rows = await db.fetch(clean_sql, property_id)
        if not rows:
            return json.dumps({"status": "SUCCESS", "row_count": 0, "data": []}, ensure_ascii=False)

        return json.dumps({
            "status": "SUCCESS",
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "data": rows[:30]
        }, ensure_ascii=False)
    except Exception as e:
        log.warning("Tool execute_sql_query failed: %s", e)
        return json.dumps({"error": str(e), "sql_attempted": sql_query}, ensure_ascii=False)


async def tool_execute_dynamic_python_script(code: str) -> str:
    """Code Interpreter Execution — Agent writes Python code dynamically to calculate facts"""
    try:
        clean_code = code.replace("```python", "").replace("```", "").strip()
        
        # Block dangerous system OS commands
        forbidden = ["import os.system", "shutil.rmtree", "subprocess.call", "os.remove"]
        if any(f in clean_code for f in forbidden):
            return json.dumps({"error": "Mã Python chứa lệnh không an toàn và đã bị chặn."}, ensure_ascii=False)

        # Run script in isolated python process
        proc = subprocess.run(
            [sys.executable, "-c", clean_code],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = (proc.stdout + proc.stderr).strip()
        return json.dumps({"execution_status": "SUCCESS", "output": output[:5000]}, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Thời gian thực thi mã Python quá 10 giây (Timeout)."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi thực thi mã Python: {str(e)}"}, ensure_ascii=False)


async def tool_generate_marketing_post(
    room_number: str,
    base_price: float,
    area_sqm: float = 25.0,
    amenities: str = "Điều hòa, Nóng lạnh, Giường tủ, Ban công",
    property_address: str = "Khu vực trung tâm"
) -> str:
    post = f"""🔥 CHO THUÊ PHÒNG TRỌ KHỎI CHÊ — PHÒNG {room_number} SẴN SÀNG Ở NGAY 🔥

📍 Địa chỉ: {property_address}
💰 Giá thuê hấp dẫn: {base_price:,.0f} VNĐ/tháng
📐 Diện tích rộng rãi: {area_sqm} m²

✨ TIỆN ÍCH TRANG BỊ ĐẦY ĐỦ:
- {amenities}

🔒 AN NINH & ĐỜI SỐNG VĂN MINH:
- Khóa cửa vân tay thông minh, camera an ninh 24/7.
- Giờ giấc hoàn toàn tự do, không chung chủ.
- Wifi cáp quang tốc độ cao, chỗ để xe máy rộng rãi.

📞 LIÊN HỆ XEM PHÒNG TRỰC TIẾP (MIỄN PHÍ):
- Hotline/Zalo Quản lý: 09xx.xxx.xxx (Ưu tiên khách thiện chí xem phòng sớm!)"""
    return json.dumps({"marketing_post": post}, ensure_ascii=False)


# ── Tool Dispatcher ───────────────────────────────────────────────────────────

async def dispatch_tool(tool_name: str, args: dict, landlord_id: int = 1) -> str:
    log.info("Dispatching tool: %s with args %s", tool_name, args)
    l_id = args.get("landlord_id", landlord_id)
    period = args.get("period", "2026-06")

    if tool_name == "get_kpi_overview":
        return await tool_get_kpi_overview(l_id, period)
    elif tool_name == "execute_sql_query":
        sql = args.get("sql_query", "")
        return await tool_execute_sql_query(sql, l_id)
    elif tool_name == "execute_dynamic_python_script":
        code = args.get("code", "")
        return await tool_execute_dynamic_python_script(code)
    elif tool_name == "generate_marketing_post":
        return await tool_generate_marketing_post(
            room_number=str(args.get("room_number", "101")),
            base_price=float(args.get("base_price", 3000000)),
            area_sqm=float(args.get("area_sqm", 25.0)),
            amenities=str(args.get("amenities", "Điều hòa, Nóng lạnh")),
            property_address=str(args.get("property_address", "Địa chỉ khu trọ"))
        )

    return json.dumps({"error": f"Tool '{tool_name}' không tồn tại."}, ensure_ascii=False)
