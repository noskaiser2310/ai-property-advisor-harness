"""
Suggested Analysis Service — AI Financial Copilot
Khác với Suggested Questions (câu hỏi tĩnh), đây là proactive analysis:
AI tự phát hiện biến động KPI và đề xuất hướng phân tích.

Ví dụ:
- "Chi phí sửa chữa tăng đáng kể trong kỳ này. Bạn có muốn xem chi tiết?"
- "Doanh thu đang giảm. Bạn có muốn xem khoản chi nào tăng mạnh?"

Theo AI_MODEL_FLOW.md:
    Dashboard Render
    ↓
    AI đọc KPI
    ↓
    Phát hiện biến động
    ↓
    Sinh đề xuất
    ↓
    Hiển thị: "Bạn có muốn xem [phân tích]?"
"""
import logging
from typing import List, Dict, Any, Optional
from src.schemas.kpi_schema import KPIObject
from src.engines.kpi_repository import KPIRepository, AnalysisCache

log = logging.getLogger("ai-property-advisor")


class SuggestedAnalysis:
    """
    Một phân tích đề xuất (proactive).
    """
    def __init__(self, title: str, description: str, metric: str,
                 severity: str, prompt: str, change_pct: Optional[float] = None):
        self.title = title
        self.description = description
        self.metric = metric
        self.severity = severity  # critical | high | medium | info
        self.prompt = prompt
        self.change_pct = change_pct

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "metric": self.metric,
            "severity": self.severity,
            "prompt": self.prompt,
            "change_pct": self.change_pct,
        }


class SuggestedAnalysisService:
    """
    Service phát hiện biến động KPI và sinh phân tích đề xuất (proactive).
    
    Không gọi LLM — sử dụng rule-based để nhanh và không tốn token.
    LLM sẽ được dùng cho phần sinh Suggested Questions (suggestion_service.py).
    """

    @staticmethod
    def analyze(kpi: KPIObject) -> List[Dict[str, Any]]:
        """
        Phân tích KPI và trả về danh sách các phân tích đề xuất.
        """
        analyses: List[SuggestedAnalysis] = []
        change = kpi.change_pct

        if kpi is None:
            return []

        # === Revenue analysis ===
        rev_change = change.revenue if change else None
        if rev_change is not None:
            if rev_change < -20:
                analyses.append(SuggestedAnalysis(
                    title="Doanh thu giảm mạnh",
                    description=f"Doanh thu giảm {abs(rev_change):.1f}% so với kỳ trước — cần kiểm tra nguyên nhân.",
                    metric="revenue.total",
                    severity="critical",
                    prompt=f"Vì sao doanh thu giảm {abs(rev_change):.1f}%?",
                    change_pct=rev_change,
                ))
            elif rev_change < -10:
                analyses.append(SuggestedAnalysis(
                    title="Doanh thu giảm",
                    description=f"Doanh thu giảm {abs(rev_change):.1f}% so với kỳ trước.",
                    metric="revenue.total",
                    severity="high",
                    prompt=f"Khoản thu nào giảm nhiều nhất trong kỳ này?",
                    change_pct=rev_change,
                ))
            elif rev_change > 20:
                analyses.append(SuggestedAnalysis(
                    title="Doanh thu tăng mạnh",
                    description=f"Doanh thu tăng {rev_change:.1f}% — yếu tố nào đóng góp chính?",
                    metric="revenue.total",
                    severity="medium",
                    prompt=f"Doanh thu tăng {rev_change:.1f}% — khoản mục nào đóng góp nhiều nhất?",
                    change_pct=rev_change,
                ))

        # === Expense analysis ===
        exp_change = change.expense if change else None
        if exp_change is not None and exp_change > 30:
            analyses.append(SuggestedAnalysis(
                title="Chi phí tăng đột biến",
                description=f"Chi phí tăng {exp_change:.1f}% so với kỳ trước — cần kiểm tra khoản mục!",
                metric="expense.total",
                severity="critical",                    prompt=f"Chi phí tăng {exp_change:.1f}% — khoản mục nào chính?",
                change_pct=exp_change,
            ))
        elif exp_change is not None and exp_change > 15:
            analyses.append(SuggestedAnalysis(
                title="Chi phí tăng",
                description=f"Chi phí tăng {exp_change:.1f}% so với kỳ trước.",
                metric="expense.total",
                severity="high",                    prompt=f"Khoản chi nào tăng nhiều nhất trong tháng?",
                change_pct=exp_change,
            ))

        # === Expense breakdown analysis ===
        if kpi.expense and kpi.revenue and kpi.revenue.total > 0:
            expense_ratio = kpi.expense.total / kpi.revenue.total * 100
            if expense_ratio > 40:
                analyses.append(SuggestedAnalysis(
                    title="Tỷ lệ chi phí cao",
                    description=f"Chi phí chiếm {expense_ratio:.1f}% doanh thu — cần tối ưu!",
                    metric="expense.ratio",
                    severity="high",
                    prompt="Có thể cắt giảm chi phí nào để cải thiện lợi nhuận?",
                ))

        # === Maintenance spike ===
        if kpi.expense and kpi.expense.maintenance > kpi.expense.total * 0.4:
            analyses.append(SuggestedAnalysis(
                title="Chi phí sửa chữa chiếm tỷ trọng lớn",
                description=f"Chi phí sửa chữa {kpi.expense.maintenance:,.0f}đ chiếm tỷ trọng lớn trong tổng chi phí.",
                metric="expense.maintenance",
                severity="high",                    prompt="Chi phí sửa chữa có thể tối ưu được không?",
            ))

        # === Debt analysis ===
        if kpi.debt:
            if kpi.debt.overdue_count >= 5:
                analyses.append(SuggestedAnalysis(
                    title=f"{kpi.debt.overdue_count} hóa đơn quá hạn",
                    description=f"Có {kpi.debt.overdue_count} hóa đơn quá hạn, tổng {kpi.debt.overdue_amount:,.0f}đ.",
                    metric="debt.overdue_count",
                    severity="critical",
                    prompt=f"Phòng nào nợ nhiều nhất? Cần ưu tiên xử lý phòng nào?",
                ))
            elif kpi.debt.overdue_count >= 3:
                analyses.append(SuggestedAnalysis(
                    title=f"{kpi.debt.overdue_count} hóa đơn quá hạn",
                    description=f"Có {kpi.debt.overdue_count} hóa đơn quá hạn.",
                    metric="debt.overdue_count",
                    severity="high",
                    prompt="Phòng nào đang nợ nhiều nhất?",
                ))

            if kpi.debt.collection_rate < 70:
                analyses.append(SuggestedAnalysis(
                    title="Tỷ lệ thu tiền thấp",
                    description=f"Tỷ lệ thu tiền chỉ {kpi.debt.collection_rate}% — rủi ro dòng tiền!",
                    metric="debt.collection_rate",
                    severity="critical",
                    prompt="Phòng nào đang kéo tỷ lệ thu tiền xuống?",
                ))
            elif kpi.debt.collection_rate < 85:
                analyses.append(SuggestedAnalysis(
                    title="Tỷ lệ thu tiền cần cải thiện",
                    description=f"Tỷ lệ thu tiền {kpi.debt.collection_rate}% — dưới mục tiêu 90%.",
                    metric="debt.collection_rate",
                    severity="medium",
                    prompt="Làm thế nào để cải thiện tỷ lệ thu tiền?",
                ))

            if kpi.debt.overdue_amount > 0:
                # Cash flow impact analysis
                analyses.append(SuggestedAnalysis(
                    title="Tác động dòng tiền",
                    description=f"Nếu thu hồi hết {kpi.debt.overdue_amount:,.0f}đ công nợ, dòng tiền cải thiện đáng kể.",
                    metric="debt.overdue_amount",
                    severity="high",
                    prompt=f"Nếu thu hồi hết {kpi.debt.overdue_amount:,.0f}đ công nợ, lợi nhuận thay đổi thế nào?",
                ))

        # === Occupancy analysis ===
        occ_change = change.occupancy if change else None
        if occ_change is not None and occ_change < -5:
            analyses.append(SuggestedAnalysis(
                title="Tỉ lệ lấp đầy giảm mạnh",
                description=f"Tỉ lệ lấp đầy giảm {abs(occ_change):.1f}% — {kpi.occupancy.vacant_rooms} phòng trống!",
                metric="occupancy.occupancy_rate",
                severity="critical",                    prompt=f"Phòng trống tập trung ở khu vực nào? Cần điều chỉnh giá?",
                change_pct=occ_change,
            ))
        elif occ_change is not None and occ_change < -2:
            analyses.append(SuggestedAnalysis(
                title="Tỉ lệ lấp đầy giảm",
                description=f"Tỉ lệ lấp đầy giảm {abs(occ_change):.1f}% so với kỳ trước.",
                metric="occupancy.occupancy_rate",
                severity="high",                    prompt="Vì sao tỉ lệ lấp đầy giảm? Phòng trống do hết hợp đồng hay khách mới không vào?",
                change_pct=occ_change,
            ))

        if kpi.occupancy and kpi.occupancy.occupancy_rate < 60:
            analyses.append(SuggestedAnalysis(
                title="Tỉ lệ lấp đầy thấp",
                description=f"Tỉ lệ lấp đầy chỉ {kpi.occupancy.occupancy_rate}% ({kpi.occupancy.vacant_rooms} phòng trống).",
                metric="occupancy.occupancy_rate",
                severity="critical",                    prompt="Cần điều chỉnh giá hay chính sách để tăng tỉ lệ lấp đầy?",
            ))

        # === Profit analysis ===
        prof_change = change.profit if change else None
        if prof_change is not None and prof_change < 0:
            exp_direction = "tăng" if exp_change is not None and exp_change > 0 else "không đổi"
            analyses.append(SuggestedAnalysis(
                title="Lợi nhuận giảm",
                description=f"Lợi nhuận giảm {abs(prof_change):.1f}% trong khi chi phí {exp_direction}.",
                metric="profit.net",
                severity="high",                    prompt="Yếu tố nào ảnh hưởng nhiều nhất đến lợi nhuận?",
                change_pct=prof_change,
            ))

        # === Revenue breakdown insight ===
        if kpi.revenue and kpi.revenue.total > 0:
            rent_pct = kpi.revenue.rent / kpi.revenue.total * 100 if kpi.revenue.total > 0 else 0
            if rent_pct > 90:
                analyses.append(SuggestedAnalysis(
                    title="Phụ thuộc lớn vào tiền phòng",
                    description=f"Tiền phòng chiếm {rent_pct:.1f}% doanh thu — rủi ro tập trung.",
                    metric="revenue.rent_pct",
                    severity="medium",
                    prompt="Có thể đa dạng hóa nguồn thu (dịch vụ, tiện ích) không?",
                ))

        # === Health score ===
        if kpi.health_score is not None and kpi.health_score < 50:
            analyses.append(SuggestedAnalysis(
                title="Sức khỏe KPI thấp",
                description=f"Điểm sức khỏe KPI chỉ {kpi.health_score}/100.",
                metric="health_score",
                severity="critical",                    prompt="Các chỉ số nào đang kéo điểm sức khỏe xuống thấp nhất?",
            ))

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
        analyses.sort(key=lambda a: severity_order.get(a.severity, 99))

        return [a.to_dict() for a in analyses[:6]]  # Max 6 proactive analyses

    @staticmethod
    async def get_analysis(landlord_id: int, period: str) -> List[Dict[str, Any]]:
        """
        Get proactive analysis for a landlord+period.
        Ưu tiên đọc từ cache, nếu không có thì compute mới.
        """
        # Check cache first
        cached = AnalysisCache.get_analysis(landlord_id, period)
        if cached is not None:
            log.debug("Analysis cache HIT: L%s, %s (%d items)", landlord_id, period, len(cached))
            return cached
        
        # Compute new analysis
        kpi = KPIRepository.get_kpi(landlord_id, period)
        if kpi is None:
            return []
        
        result = SuggestedAnalysisService.analyze(kpi)
        if result:
            AnalysisCache.set_analysis(landlord_id, period, result)
        return result

    @staticmethod
    async def generate_and_cache(landlord_id: int, period: str) -> None:
        """
        Background job: generate analysis and cache it.
        Được gọi từ background trigger khi KPI hash thay đổi.
        Luôn ghi đè cache (kể cả empty) để tránh stale data.
        """
        kpi = KPIRepository.get_kpi(landlord_id, period)
        if kpi is None:
            log.debug("Analysis background: no KPI for L%s, %s", landlord_id, period)
            return
        
        result = SuggestedAnalysisService.analyze(kpi)
        AnalysisCache.set_analysis(landlord_id, period, result)
        log.info("Analysis background: cached %d items for L%s, %s", 
                 len(result), landlord_id, period)


suggested_analysis_service = SuggestedAnalysisService()
