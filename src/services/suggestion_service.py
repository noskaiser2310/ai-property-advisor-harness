"""
Suggested Questions Service — Gợi ý câu hỏi phân tích từ KPI context
- LLM (Gemini) sinh câu hỏi đa dạng, theo ngữ cảnh
- Template fallback khi Gemini không khả dụng
"""
import json
import logging
from typing import List, Optional
from src.schemas.kpi_schema import KPIObject
from src.engines.kpi_repository import KPIRepository

log = logging.getLogger("ai-property-advisor")

# Template fallback questions
FALLBACK_QUESTIONS = {
    "revenue": [
        "Doanh thu thay đổi thế nào so với kỳ trước?",
        "Khoản thu nào chiếm tỷ trọng lớn nhất?",
        "Doanh thu tháng này cao hơn hay thấp hơn trung bình 6 tháng?",
        "Tỷ trọng doanh thu các nguồn có thay đổi so với quý trước?",
    ],
    "expense": [
        "Khoản chi nào tăng nhiều nhất trong tháng?",
        "Tỷ lệ chi phí/doanh thu đang ở mức nào?",
        "Chi phí sửa chữa có bất thường không?",
        "So với tháng trước, chi phí thay đổi thế nào?",
    ],
    "debt": [
        "Bao nhiêu hóa đơn quá hạn?",
        "Phòng nào công nợ nhiều nhất?",
        "Tỷ lệ thu tiền hiện tại là bao nhiêu?",
        "Phòng nào nợ tiền lâu nhất?",
    ],
    "occupancy": [
        "Tỉ lệ lấp đầy hiện tại ra sao?",
        "Phòng trống nhiều nhất ở khu vực nào?",
        "Phòng nào trống lâu nhất?",
        "Xu hướng 6 tháng gần đây về tỉ lệ lấp đầy?",
    ],
    "mixed": [
        "Vì sao doanh thu tăng nhưng lợi nhuận không tăng tương ứng?",
        "Nếu lấp đầy hết phòng trống, doanh thu tăng thêm bao nhiêu?",
        "Nếu thu hồi hết công nợ, dòng tiền cải thiện thế nào?",
        "Chi phí tăng/giảm có tương xứng với doanh thu không?",
    ],
}


SUGGESTION_PROMPT = """Bạn là AI Financial Copilot. Dựa vào KPI dưới đây, hãy đề xuất 5-8 câu hỏi phân tích mà kế toán nhà trọ nên đặt ra.

KPI hiện tại:
- Doanh thu: {revenue} ({revenue_growth})
- Chi phí: {expense} ({expense_growth})
- Lợi nhuận ròng: {profit}
- Công nợ: {debt} ({overdue_count} hóa đơn quá hạn)
- Tỷ lệ thu tiền: {collection_rate}%
- Tỉ lệ lấp đầy: {occupancy_rate}% ({occupied_rooms}/{total_rooms} phòng)

Yêu cầu:
1. Câu hỏi phải đi sâu vào biến động
2. Đa dạng: so sánh, nguyên nhân, dự báo
3. Ưu tiên các chỉ số bất thường
4. Trả về JSON array: ["câu hỏi 1", "câu hỏi 2", ...]

Output:
"""


class SuggestionService:
    """Service sinh câu hỏi gợi ý"""

    @staticmethod
    def _select_fallback(kpi: KPIObject) -> List[str]:
        """Chọn fallback questions dựa trên KPI"""
        questions = []
        rev = kpi.revenue
        exp = kpi.expense
        debt = kpi.debt
        occ = kpi.occupancy

        # Dựa vào biến động để chọn câu hỏi phù hợp
        if kpi.change_pct and kpi.change_pct.revenue and abs(kpi.change_pct.revenue) > 5:
            questions.append(f"Vì sao doanh thu {'tăng' if kpi.change_pct.revenue > 0 else 'giảm'} {abs(kpi.change_pct.revenue)}%?")
        if kpi.change_pct and kpi.change_pct.expense and abs(kpi.change_pct.expense) > 5:
            questions.append(f"Chi phí {'tăng' if kpi.change_pct.expense > 0 else 'giảm'} {abs(kpi.change_pct.expense)}% — khoản mục nào chính?")
        if debt.overdue_count > 0:
            questions.append(f"Nếu thu hồi hết {debt.overdue_amount:,.0f}đ công nợ, lợi nhuận thay đổi thế nào?")
        if occ.occupancy_change and occ.occupancy_change < -1:
            questions.append(f"Tỉ lệ lấp đầy giảm {abs(occ.occupancy_change)}% — phòng trống tập trung ở khu vực nào?")
        if exp.maintenance > exp.total * 0.3:
            questions.append("Chi phí sửa chữa chiếm tỷ trọng lớn — có thể tối ưu được không?")
        if debt.collection_rate < 80:
            questions.append(f"Tỷ lệ thu tiền {debt.collection_rate}% đang thấp — phòng nào kéo xuống?")

        # Thêm các câu hỏi mặc định
        default_questions = [
            "Khoản thu nào chiếm tỷ trọng lớn nhất?",
            "Tỉ lệ lấp đầy hiện tại ra sao?",
            "Bao nhiêu hóa đơn quá hạn?",
            "Xu hướng 6 tháng gần đây ra sao?",
        ]
        questions.extend(default_questions)
        return questions[:8]

    @staticmethod
    async def get_suggestions(landlord_id: int, period: str, kpi: Optional[KPIObject] = None) -> List[str]:
        """Lấy danh sách câu hỏi gợi ý"""
        if kpi is None:
            kpi = KPIRepository.get_kpi(landlord_id, period)

        if kpi is None:
            return FALLBACK_QUESTIONS["mixed"]

        # Thử dùng LLM
        try:
            from src.services.gemini_service import gemini_service
            from google.genai import types

            prompt = SUGGESTION_PROMPT.format(
                revenue=f"{kpi.revenue.total:,.0f}đ",
                revenue_growth=f"{kpi.change_pct.revenue}%" if kpi.change_pct and kpi.change_pct.revenue else "N/A",
                expense=f"{kpi.expense.total:,.0f}đ",
                expense_growth=f"{kpi.change_pct.expense}%" if kpi.change_pct and kpi.change_pct.expense else "N/A",
                profit=f"{kpi.profit.net:,.0f}đ",
                debt=f"{kpi.debt.overdue_amount:,.0f}đ",
                overdue_count=kpi.debt.overdue_count,
                collection_rate=kpi.debt.collection_rate,
                occupancy_rate=kpi.occupancy.occupancy_rate,
                occupied_rooms=kpi.occupancy.occupied_rooms,
                total_rooms=kpi.occupancy.total_rooms,
            )

            config = types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1024,
            )
            content_payload = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            ]
            response = await gemini_service._call_with_retry(
                model=gemini_service.model,
                contents=content_payload,
                config=config,
            )
            text = gemini_service._safe_text(response)

            if text:
                try:
                    cleaned = text.replace("```json", "").replace("```", "").strip()
                    questions = json.loads(cleaned)
                    if isinstance(questions, list) and len(questions) >= 3:
                        return questions[:8]
                except (json.JSONDecodeError, ValueError):
                    pass

        except Exception as e:
            log.warning("Gemini suggestion failed, using fallback: %s", str(e))

        return SuggestionService._select_fallback(kpi)


suggestion_service = SuggestionService()
