"""
Context Engine — AI Financial Copilot
Xây dựng rich context từ KPI data cho LLM.

Context schema (theo AI_MODEL_FLOW.md):
{
    "period": "2026-06",
    "dashboard": "overview",
    "kpis": { ... enriched KPI data ... },
    "comparison": { ... previous period comparison + highlights ... },
    "trend": { ... multi-month trend data ... },
    "anomalies": [ ... detected anomalies ... ],
    "summary": "natural language summary"
}

Context này được dùng cho:
- Financial Report (báo cáo)
- Financial Exploration (hỏi đáp)
- Suggested Analysis (gợi ý phân tích)
"""
from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from statistics import mean
from src.schemas.kpi_schema import KPIObject

log = logging.getLogger("ai-property-advisor")


# ============================================================================
# TREND ANALYSIS UTILITIES (giữ lại từ ContextEngine cũ + mở rộng)
# ============================================================================

class TrendAnalyzer:
    """Phân tích xu hướng đa kỳ từ dữ liệu monthly"""

    @staticmethod
    def calculate_moving_average(values: List[float], window: int = 3) -> Optional[float]:
        """Tính trung bình động"""
        if len(values) < window:
            return None
        return round(mean(values[-window:]), 2)

    @staticmethod
    def compare_to_benchmark(current: float, benchmark: Optional[float]) -> Optional[float]:
        """Phần trăm chênh lệch so với benchmark"""
        if benchmark is None or benchmark == 0:
            return None
        return round((current - benchmark) / benchmark * 100, 1)

    @staticmethod
    def detect_trend(values: List[float]) -> Dict[str, Any]:
        """
        Phát hiện xu hướng từ chuỗi dữ liệu.
        Returns: {direction, strength, consecutive_months, volatility}
        """
        if len(values) < 2:
            return {"direction": "insufficient", "strength": 0, "consecutive_months": 0, "volatility": "unknown"}

        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        avg_change = mean(diffs) if diffs else 0

        # Đếm số tháng liên tiếp cùng chiều
        directions = ["up" if d > 0 else "down" if d < 0 else "stable" for d in diffs]
        consecutive = 1
        current_dir = directions[-1]
        for d in reversed(directions[:-1]):
            if d == current_dir:
                consecutive += 1
            else:
                break

        # Độ biến động (coefficient of variation)
        mean_val = mean(values)
        volatility = "unknown"
        if mean_val > 0:
            cv = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5 / mean_val
            if cv < 0.05:
                volatility = "low"
            elif cv < 0.15:
                volatility = "medium"
            else:
                volatility = "high"

        # Xác định xu hướng tổng thể
        if consecutive >= 3 and current_dir != "stable":
            direction = current_dir
            strength = min(1.0, consecutive * 0.2)
        elif abs(avg_change) / (abs(mean_val) + 1) < 0.02:
            direction = "stable"
            strength = 0.3
        elif avg_change > 0:
            direction = "slight_up" if avg_change / (abs(mean_val) + 1) < 0.05 else "up"
            strength = min(0.5, abs(avg_change) / (abs(mean_val) + 1) * 5)
        else:
            direction = "slight_down" if abs(avg_change) / (abs(mean_val) + 1) < 0.05 else "down"
            strength = min(0.5, abs(avg_change) / (abs(mean_val) + 1) * 5)

        return {
            "direction": direction,
            "strength": round(strength, 2),
            "consecutive_months": consecutive,
            "volatility": volatility,
            "avg_change_pct": round(avg_change / (abs(mean_val) + 0.001) * 100, 1),
        }


# ============================================================================
# CONTEXT BUILDER
# ============================================================================

class ContextBuilder:
    """
    Xây dựng rich context từ KPI data.

    Input: KPIObject + optional parameters
    Output: {
        "period": str,
        "dashboard": str,
        "kpis": dict,
        "comparison": dict,
        "trend": dict,
        "anomalies": list,
        "summary": str,
        "generated_at": str
    }
    """

    @staticmethod
    def build(
        kpi: KPIObject,
        dashboard: str = "overview",
        monthly_revenue: Optional[List[Dict]] = None,
        monthly_occupancy: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Build the full context from KPI data.
        
        Args:
            kpi: KPIObject with current period data
            dashboard: Name of the dashboard (overview, revenue, expense, debt, occupancy)
            monthly_revenue: Optional list of monthly revenue data
            monthly_occupancy: Optional list of monthly occupancy data
        
        Returns:
            Rich context dict
        """
        kpis_section = ContextBuilder._build_kpis_section(kpi)
        comparison_section = ContextBuilder._build_comparison_section(kpi)
        trend_section = ContextBuilder._build_trend_section(
            kpi, monthly_revenue, monthly_occupancy
        )
        anomalies = ContextBuilder._detect_anomalies(kpi, comparison_section)
        summary = ContextBuilder._build_summary(kpi, comparison_section, anomalies)

        return {
            "period": kpi.period,
            "dashboard": dashboard,
            "kpis": kpis_section,
            "comparison": comparison_section,
            "trend": trend_section,
            "anomalies": anomalies,
            "summary": summary,
            "generated_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _build_kpis_section(kpi: KPIObject) -> Dict[str, Any]:
        """Build enriched KPIs section with breakdowns and percentages"""
        rev = kpi.revenue
        exp = kpi.expense
        prof = kpi.profit
        debt = kpi.debt
        occ = kpi.occupancy

        rev_total = rev.total if rev and rev.total > 0 else 1

        # Revenue breakdown
        revenue_data = {
            "total": rev.total if rev else 0,
            "rent": rev.rent if rev else 0,
            "electricity": rev.electricity if rev else 0,
            "water": rev.water if rev else 0,
            "service": rev.service if rev else 0,
            "other": rev.other if rev else 0,
            "growth_pct": rev.growth_pct if rev else None,
            "breakdown": {
                "rent_pct": round(rev.rent / rev_total * 100, 1) if rev else 0,
                "electricity_pct": round(rev.electricity / rev_total * 100, 1) if rev else 0,
                "water_pct": round(rev.water / rev_total * 100, 1) if rev else 0,
                "service_pct": round(rev.service / rev_total * 100, 1) if rev else 0,
                "other_pct": round(rev.other / rev_total * 100, 1) if rev else 0,
            },
            "formatted": f"{rev.total:,.0f}đ" if rev else "0đ",
            "primary_source": "rent" if rev and rev.rent > 0 else "none",
        }

        # Expense breakdown
        exp_total = exp.total if exp and exp.total > 0 else 1
        expense_data = {
            "total": exp.total if exp else 0,
            "electricity": exp.electricity if exp else 0,
            "water": exp.water if exp else 0,
            "maintenance": exp.maintenance if exp else 0,
            "penalty": exp.penalty if exp else 0,
            "other": exp.other if exp else 0,
            "breakdown": {
                "electricity_pct": round(exp.electricity / exp_total * 100, 1) if exp else 0,
                "water_pct": round(exp.water / exp_total * 100, 1) if exp else 0,
                "maintenance_pct": round(exp.maintenance / exp_total * 100, 1) if exp else 0,
                "penalty_pct": round(exp.penalty / exp_total * 100, 1) if exp else 0,
                "other_pct": round(exp.other / exp_total * 100, 1) if exp else 0,
            },
            "formatted": f"{exp.total:,.0f}đ" if exp else "0đ",
        }

        # Debt with room details
        debt_rooms = []
        if debt and debt.debt_by_room:
            for d in debt.debt_by_room:
                debt_rooms.append({
                    "room": d.room,
                    "total_debt": d.total_debt,
                    "type": d.type,
                    "months": d.months,
                    "formatted": f"Phòng {d.room}: {d.total_debt:,.0f}đ ({d.months} tháng)",
                })

        debt_data = {
            "collection_rate": debt.collection_rate if debt else 100.0,
            "overdue_count": debt.overdue_count if debt else 0,
            "overdue_amount": debt.overdue_amount if debt else 0,
            "debt_by_room": debt_rooms,
            "formatted": f"{debt.overdue_amount:,.0f}đ ({debt.overdue_count} hóa đơn)" if debt else "0đ",
        }

        # Profit
        profit_data = {
            "net": prof.net if prof else 0,
            "growth_pct": prof.growth_pct if prof else None,
            "expense_ratio": prof.expense_ratio if prof else 0,
            "formatted": f"{prof.net:,.0f}đ" if prof else "0đ",
        }

        # Occupancy
        occupancy_data = {
            "total_rooms": occ.total_rooms if occ else 0,
            "occupied_rooms": occ.occupied_rooms if occ else 0,
            "vacant_rooms": occ.vacant_rooms if occ else 0,
            "occupancy_rate": occ.occupancy_rate if occ else 0,
            "occupancy_change": occ.occupancy_change if occ else None,
            "formatted": f"{occ.occupancy_rate}% ({occ.occupied_rooms}/{occ.total_rooms} phòng)" if occ else "0%",
        }

        return {
            "revenue": revenue_data,
            "expense": expense_data,
            "profit": profit_data,
            "debt": debt_data,
            "occupancy": occupancy_data,
            "health_score": kpi.health_score if kpi else None,
            "health_status": kpi.health_status if kpi else "UNKNOWN",
        }

    @staticmethod
    def _build_comparison_section(kpi: KPIObject) -> Dict[str, Any]:
        """Build comparison section: previous period + change analysis + highlights"""
        prev = kpi.previous_period
        change = kpi.change_pct

        if not prev and not change:
            return {
                "available": False,
                "summary": "Không có dữ liệu so sánh với kỳ trước",
                "highlights": [],
            }

        # Revenue comparison
        rev_current = kpi.revenue.total if kpi.revenue else 0
        rev_prev = (prev.revenue.get("total", 0) if prev and prev.revenue else 0) if prev else 0
        rev_change = change.revenue if change else None

        # Expense comparison
        exp_current = kpi.expense.total if kpi.expense else 0
        exp_prev = (prev.expense.get("total", 0) if prev and prev.expense else 0) if prev else 0
        exp_change = change.expense if change else None

        # Profit comparison
        prof_current = kpi.profit.net if kpi.profit else 0
        prof_prev = (prev.profit.get("net", 0) if prev and prev.profit else 0) if prev else 0
        prof_change = change.profit if change else None

        # Occupancy comparison
        occ_current = kpi.occupancy.occupancy_rate if kpi.occupancy else 0
        occ_prev = (prev.occupancy.get("occupancy_rate", 0) if prev and prev.occupancy else 0) if prev else 0
        occ_change = change.occupancy if change else None

        # Build highlights
        highlights = []
        revenue_direction = "up" if rev_change and rev_change > 0 else "down" if rev_change and rev_change < 0 else "stable"
        if revenue_direction != "stable":
            highlights.append({
                "metric": "revenue",
                "direction": revenue_direction,
                "change_pct": abs(rev_change) if rev_change else 0,
                "message": f"Doanh thu {'tăng' if revenue_direction == 'up' else 'giảm'} {abs(rev_change):.1f}%",
                "severity": "high" if (rev_change and abs(rev_change) > 20) else "medium" if (rev_change and abs(rev_change) > 10) else "low",
            })

        expense_direction = "up" if exp_change and exp_change > 0 else "down" if exp_change and exp_change < 0 else "stable"
        if expense_direction != "stable":
            highlights.append({
                "metric": "expense",
                "direction": expense_direction,
                "change_pct": abs(exp_change) if exp_change else 0,
                "message": f"Chi phí {'tăng' if expense_direction == 'up' else 'giảm'} {abs(exp_change):.1f}%",
                "severity": "high" if (exp_change and abs(exp_change) > 20) else "medium" if (exp_change and abs(exp_change) > 10) else "low",
            })

        profit_direction = "up" if prof_change and prof_change > 0 else "down" if prof_change and prof_change < 0 else "stable"
        if profit_direction != "stable":
            highlights.append({
                "metric": "profit",
                "direction": profit_direction,
                "change_pct": abs(prof_change) if prof_change else 0,
                "message": f"Lợi nhuận {'tăng' if profit_direction == 'up' else 'giảm'} {abs(prof_change):.1f}%",
                "severity": "high" if (prof_change and abs(prof_change) > 20) else "medium" if (prof_change and abs(prof_change) > 10) else "low",
            })

        occ_direction = "up" if occ_change and occ_change > 0 else "down" if occ_change and occ_change < 0 else "stable"
        if occ_direction != "stable":
            highlights.append({
                "metric": "occupancy",
                "direction": occ_direction,
                "change_pct": abs(occ_change) if occ_change else 0,
                "message": f"Lấp đầy {'tăng' if occ_direction == 'up' else 'giảm'} {abs(occ_change):.1f}%",
                "severity": "high" if (occ_change and abs(occ_change) > 15) else "medium" if (occ_change and abs(occ_change) > 5) else "low",
            })

        # Natural language summary
        summary_parts = []
        if rev_change is not None:
            summary_parts.append(f"Doanh thu {'tăng' if rev_change > 0 else 'giảm'} {abs(rev_change):.1f}% ({rev_current:,.0f}đ vs {rev_prev:,.0f}đ)")
        if exp_change is not None:
            summary_parts.append(f"Chi phí {'tăng' if exp_change > 0 else 'giảm'} {abs(exp_change):.1f}%")
        if prof_change is not None:
            summary_parts.append(f"Lợi nhuận {'tăng' if prof_change > 0 else 'giảm'} {abs(prof_change):.1f}%")
        if occ_change is not None:
            summary_parts.append(f"Lấp đầy {'tăng' if occ_change > 0 else 'giảm'} {abs(occ_change):.1f}%")

        return {
            "available": True,
            "previous_period": {
                "revenue": rev_prev,
                "expense": exp_prev,
                "profit": prof_prev,
                "occupancy_rate": occ_prev,
            },
            "changes": {
                "revenue": {"pct": rev_change, "abs": rev_current - rev_prev, "direction": revenue_direction},
                "expense": {"pct": exp_change, "abs": exp_current - exp_prev, "direction": expense_direction},
                "profit": {"pct": prof_change, "abs": prof_current - prof_prev, "direction": profit_direction},
                "occupancy": {"pct": occ_change, "abs": occ_current - occ_prev, "direction": occ_direction},
            },
            "highlights": highlights,
            "summary": ". ".join(summary_parts) if summary_parts else "Không có thay đổi đáng kể",
        }

    @staticmethod
    def _build_trend_section(
        kpi: KPIObject,
        monthly_revenue: Optional[List[Dict]] = None,
        monthly_occupancy: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Build trend section from available monthly data"""
        trend_result = {
            "available": False,
            "revenue_trend": {"direction": "unknown", "strength": 0, "consecutive_months": 0, "volatility": "unknown"},
            "occupancy_trend": {"direction": "unknown", "strength": 0, "consecutive_months": 0, "volatility": "unknown"},
            "monthly_data": {},
            "summary": "Không đủ dữ liệu để phân tích xu hướng",
        }

        # Revenue trend từ previous_period + change_pct (nếu không có monthly data)
        rev_trend_data = []
        if kpi.previous_period and kpi.previous_period.revenue:
            prev_total = kpi.previous_period.revenue.get("total", 0)
            if prev_total > 0:
                rev_trend_data.append(prev_total)
        if kpi.revenue and kpi.revenue.total > 0:
            rev_trend_data.append(kpi.revenue.total)

        if len(rev_trend_data) >= 2:
            trend_result["revenue_trend"] = TrendAnalyzer.detect_trend(rev_trend_data)
            trend_result["available"] = True

        # Occupancy trend
        occ_trend_data = []
        if kpi.previous_period and kpi.previous_period.occupancy:
            prev_occ = kpi.previous_period.occupancy.get("occupancy_rate", 0)
            if prev_occ > 0:
                occ_trend_data.append(prev_occ)
        if kpi.occupancy and kpi.occupancy.occupancy_rate > 0:
            occ_trend_data.append(kpi.occupancy.occupancy_rate)

        if len(occ_trend_data) >= 2:
            trend_result["occupancy_trend"] = TrendAnalyzer.detect_trend(occ_trend_data)
            trend_result["available"] = True

        # Nếu có monthly data phong phú hơn, dùng nó
        if monthly_revenue and len(monthly_revenue) >= 2:
            rev_values = [m.get("total", 0) for m in monthly_revenue]
            trend_result["revenue_trend"] = TrendAnalyzer.detect_trend(rev_values)
            trend_result["monthly_data"]["revenue"] = monthly_revenue
            trend_result["available"] = True

        if monthly_occupancy and len(monthly_occupancy) >= 2:
            occ_values = [m.get("occupancy_rate", 0) for m in monthly_occupancy]
            trend_result["occupancy_trend"] = TrendAnalyzer.detect_trend(occ_values)
            trend_result["monthly_data"]["occupancy"] = monthly_occupancy
            trend_result["available"] = True

        # Trend summary
        rt = trend_result["revenue_trend"]
        ot = trend_result["occupancy_trend"]
        summary_parts = []
        if rt["direction"] not in ("unknown", "insufficient"):
            dir_text = {"up": "tăng", "down": "giảm", "stable": "ổn định", "slight_up": "tăng nhẹ", "slight_down": "giảm nhẹ"}
            summary_parts.append(f"Doanh thu có xu hướng {dir_text.get(rt['direction'], rt['direction'])}")
        if ot["direction"] not in ("unknown", "insufficient"):
            dir_text = {"up": "tăng", "down": "giảm", "stable": "ổn định", "slight_up": "tăng nhẹ", "slight_down": "giảm nhẹ"}
            summary_parts.append(f"Lấp đầy có xu hướng {dir_text.get(ot['direction'], ot['direction'])}")

        if summary_parts:
            trend_result["summary"] = ". ".join(summary_parts) + "."

        return trend_result

    @staticmethod
    def _detect_anomalies(
        kpi: KPIObject,
        comparison: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect anomalies and significant changes in KPI data"""
        anomalies = []
        changes = comparison.get("changes", {})

        # Revenue anomaly
        rev_change = changes.get("revenue", {}).get("pct")
        if rev_change is not None and abs(rev_change) > 20:
            anomalies.append({
                "type": "revenue_change",
                "severity": "critical" if abs(rev_change) > 30 else "high",
                "metric": "revenue.total",
                "change_pct": round(rev_change, 1),
                "message": f"Doanh thu {'tăng' if rev_change > 0 else 'giảm'} mạnh {abs(rev_change):.1f}% so với kỳ trước",
            })
        elif rev_change is not None and abs(rev_change) > 10:
            anomalies.append({
                "type": "revenue_change",
                "severity": "medium",
                "metric": "revenue.total",
                "change_pct": round(rev_change, 1),
                "message": f"Doanh thu {'tăng' if rev_change > 0 else 'giảm'} {abs(rev_change):.1f}% so với kỳ trước",
            })

        # Expense anomaly
        exp_change = changes.get("expense", {}).get("pct")
        if exp_change is not None and abs(exp_change) > 30:
            anomalies.append({
                "type": "expense_spike",
                "severity": "critical" if abs(exp_change) > 50 else "high",
                "metric": "expense.total",
                "change_pct": round(exp_change, 1),
                "message": f"Chi phí {'tăng' if exp_change > 0 else 'giảm'} đột biến {abs(exp_change):.1f}% - cần kiểm tra!",
            })
        elif exp_change is not None and abs(exp_change) > 15:
            anomalies.append({
                "type": "expense_change",
                "severity": "medium",
                "metric": "expense.total",
                "change_pct": round(exp_change, 1),
                "message": f"Chi phí {'tăng' if exp_change > 0 else 'giảm'} {abs(exp_change):.1f}%",
            })

        # Debt anomaly
        if kpi.debt and kpi.debt.overdue_count > 0:
            severity = "critical" if kpi.debt.overdue_count >= 5 else "high" if kpi.debt.overdue_count >= 3 else "medium"
            anomalies.append({
                "type": "debt_overdue",
                "severity": severity,
                "metric": "debt.overdue_count",
                "value": kpi.debt.overdue_count,
                "message": f"Có {kpi.debt.overdue_count} hóa đơn quá hạn, tổng {kpi.debt.overdue_amount:,.0f}đ",
            })

        # Collection rate anomaly
        if kpi.debt and kpi.debt.collection_rate < 70:
            anomalies.append({
                "type": "collection_rate_low",
                "severity": "critical" if kpi.debt.collection_rate < 50 else "high",
                "metric": "debt.collection_rate",
                "value": kpi.debt.collection_rate,
                "message": f"Tỷ lệ thu tiền chỉ đạt {kpi.debt.collection_rate}% - rủi ro dòng tiền!",
            })

        # Occupancy anomaly
        if kpi.occupancy and kpi.occupancy.occupancy_rate < 50:
            anomalies.append({
                "type": "low_occupancy",
                "severity": "critical" if kpi.occupancy.occupancy_rate < 30 else "high",
                "metric": "occupancy.occupancy_rate",
                "value": kpi.occupancy.occupancy_rate,
                "message": f"Tỉ lệ lấp đầy chỉ {kpi.occupancy.occupancy_rate}% - {kpi.occupancy.vacant_rooms} phòng trống!",
            })

        occ_change = changes.get("occupancy", {}).get("pct")
        if occ_change is not None and abs(occ_change) > 15:
            anomalies.append({
                "type": "occupancy_drop",
                "severity": "high",
                "metric": "occupancy.occupancy_rate",
                "change_pct": round(occ_change, 1),
                "message": f"Lấp đầy {'tăng' if occ_change > 0 else 'giảm'} {abs(occ_change):.1f}% - biến động lớn!",
            })

        # Health score anomaly
        if kpi.health_score is not None and kpi.health_score < 50:
            anomalies.append({
                "type": "low_health_score",
                "severity": "critical" if kpi.health_score < 30 else "high",
                "metric": "health_score",
                "value": kpi.health_score,
                "message": f"Điểm sức khỏe KPI chỉ {kpi.health_score}/100 - cần can thiệp!",
            })

        return anomalies

    @staticmethod
    def _build_summary(
        kpi: KPIObject,
        comparison: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
    ) -> str:
        """Build natural language summary of the KPI context"""
        rev = kpi.revenue
        exp = kpi.expense
        prof = kpi.profit
        debt = kpi.debt
        occ = kpi.occupancy

        parts = [f"Kỳ {kpi.period}:"]

        # KPI values
        if rev:
            parts.append(f"Doanh thu {rev.total:,.0f}đ")
        if exp and exp.total > 0:
            parts.append(f"Chi phí {exp.total:,.0f}đ")
        if prof:
            parts.append(f"Lợi nhuận {prof.net:,.0f}đ")
        if occ:
            parts.append(f"Lấp đầy {occ.occupancy_rate}% ({occ.occupied_rooms}/{occ.total_rooms} phòng)")
        if debt and debt.overdue_amount > 0:
            parts.append(f"Nợ {debt.overdue_amount:,.0f}đ ({debt.overdue_count} hóa đơn)")

        # Health
        if kpi.health_status:
            parts.append(f"Sức khỏe: {kpi.health_status}")

        # Comparison highlights
        highlights = comparison.get("highlights", [])
        critical_highlights = [h for h in highlights if h.get("severity") == "high"]
        if critical_highlights:
            high_msgs = [h["message"] for h in critical_highlights[:2]]
            parts.append(" | ".join(high_msgs))

        # Anomalies
        critical_anomalies = [a for a in anomalies if a.get("severity") in ("critical", "high")]
        if critical_anomalies:
            parts.append(f"⚠️ {len(critical_anomalies)} vấn đề cần xử lý!")

        return ". ".join(parts) + "."


# ============================================================================
# Giữ lại các method cũ của ContextEngine để không break backward compatibility
# ============================================================================

class ContextEngine:
    """Giữ lại các method cũ cho backward compatibility, wrapper cho ContextBuilder mới"""

    @staticmethod
    def calculate_3m_average(values: List[float], current_index: int) -> Optional[float]:
        return TrendAnalyzer.calculate_moving_average(values[:current_index], window=3)

    @staticmethod
    def calculate_6m_average(values: List[float], current_index: int) -> Optional[float]:
        return TrendAnalyzer.calculate_moving_average(values[:current_index], window=6)

    @staticmethod
    def calculate_12m_average(values: List[float], current_index: int) -> Optional[float]:
        return TrendAnalyzer.calculate_moving_average(values[:current_index], window=12)

    @staticmethod
    def compare_to_benchmark(current: float, benchmark: Optional[float]) -> Optional[float]:
        return TrendAnalyzer.compare_to_benchmark(current, benchmark)

    @staticmethod
    def detect_trend(values: List[float], min_months: int = 3) -> Dict[str, Any]:
        return TrendAnalyzer.detect_trend(values)

    @classmethod
    def analyze_revenue_context(cls, monthly_revenue, current_month_idx, potential_revenue):
        """Wrapper: giữ nguyên interface cũ"""
        return {"note": "Use ContextBuilder.build() for rich context"}

    @classmethod
    def analyze_occupancy_context(cls, monthly_occupancy, current_month_idx):
        return {"note": "Use ContextBuilder.build() for rich context"}

    @classmethod
    def calculate_trend_score(cls, trend):
        if trend.get("direction") == "up":
            return min(1.0, 0.5 + trend.get("consecutive_months", 0) * 0.1)
        elif trend.get("direction") == "down":
            return max(0.0, round(0.5 - trend.get("consecutive_months", 0) * 0.15, 2))
        return 0.5
