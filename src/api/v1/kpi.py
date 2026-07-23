"""
KPI API Endpoints — AI Financial Copilot
Cung cấp 5 endpoints KPI: overview, revenue, expense, debt, occupancy + export
"""
import json
import logging
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from database.connection import get_db
from database.queries.kpi_queries import (
    REVENUE_KPI_QUERY, EXPENSE_KPI_QUERY, DEBT_KPI_QUERY,
    DEBT_BY_ROOM_QUERY, OCCUPANCY_KPI_QUERY, DEBT_AGING_QUERY,
    MONTHLY_REVENUE_QUERY, MONTHLY_EXPENSE_QUERY, MONTHLY_OCCUPANCY_QUERY
)
from src.engines.metrics_engine import MetricsEngine
from src.engines.kpi_repository import KPIRepository, AIReportCache
from src.schemas.kpi_schema import (
    KPIObject, Revenue, Expense, Debt, DebtByRoom,
    Profit, Occupancy, PreviousPeriod, ChangePct
)
from src.api.dependencies import get_landlord_id, parse_month_param


log = logging.getLogger("ai-property-advisor")
router = APIRouter()


def _get_period_range(period: str):
    """Chuyển period YYYY-MM thành (start_date, end_date, prev_start_date)"""
    year, month_num = map(int, period.split("-"))
    period_start = date(year, month_num, 1)
    if month_num == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month_num + 1, 1)
    # Previous period
    if month_num == 1:
        prev_start = date(year - 1, 12, 1)
    else:
        prev_start = date(year, month_num - 1, 1)
    return period_start, period_end, prev_start


async def _calculate_full_kpi(landlord_id: int, period: str) -> KPIObject:
    """Tính toán toàn bộ KPI từ database + previous_period + YoY"""
    db = await get_db()

    period_start, period_end, prev_start = _get_period_range(period)

    # YoY comparison: cùng tháng năm ngoái
    year, month_num = map(int, period.split("-"))
    yoy_start = date(year - 1, month_num, 1)
    if month_num == 12:
        yoy_end = date(year, 12, 31)
    else:
        yoy_end = date(year - 1, month_num + 1, 1)

    # 1. Revenue KPI
    rev_rows = await db.fetch(REVENUE_KPI_QUERY, landlord_id, period_start, period_end, prev_start, yoy_start, yoy_end)
    rev = rev_rows[0] if rev_rows else {}
    previous_revenue_total = rev.get("previous_total", 0)
    growth_pct = None
    if previous_revenue_total and previous_revenue_total > 0:
        growth_pct = round((rev.get("total", 0) - previous_revenue_total) / previous_revenue_total * 100, 1)

    revenue = Revenue(
        total=round(rev.get("total", 0)),
        rent=round(rev.get("rent", 0)),
        electricity=round(rev.get("electricity", 0)),
        water=round(rev.get("water", 0)),
        service=round(rev.get("service", 0)),
        other=round(rev.get("other", 0)),
        growth_pct=growth_pct,
    )

    # Store YoY data for response
    yoy_revenue_total = rev_rows[0].get("year_ago_total", 0) if rev_rows else 0
    yoy_growth_pct = None
    if yoy_revenue_total and yoy_revenue_total > 0:
        yoy_growth_pct = round((rev_rows[0].get("total", 0) - yoy_revenue_total) / yoy_revenue_total * 100, 1)

    # 2. Expense KPI
    exp_rows = await db.fetch(EXPENSE_KPI_QUERY, landlord_id, period_start, period_end, prev_start)
    exp = exp_rows[0] if exp_rows else {}
    expense_previous_total = exp.get("previous_total", 0)

    expense = Expense(
        total=round(exp.get("total", 0)),
        electricity=round(exp.get("electricity", 0)),
        water=round(exp.get("water", 0)),
        maintenance=round(exp.get("maintenance", 0)),
        penalty=round(exp.get("penalty", 0)),
        other=round(exp.get("other", 0)),
    )

    # 3. Debt KPI
    debt_rows = await db.fetch(DEBT_KPI_QUERY, landlord_id)
    debt = debt_rows[0] if debt_rows else {}

    # Debt by room
    debt_room_rows = await db.fetch(DEBT_BY_ROOM_QUERY, landlord_id)
    debt_by_rooms = []
    for row in debt_room_rows:
        debt_by_rooms.append(DebtByRoom(
            room=row.get("room", ""),
            total_debt=round(row.get("total_debt", 0)),
            type=row.get("type", "RENT"),
            months=row.get("months", 0),
        ))

    debt_obj = Debt(
        collection_rate=round(debt.get("collection_rate", 100.0), 1),
        overdue_count=debt.get("overdue_count", 0),
        overdue_amount=round(debt.get("overdue_amount", 0)),
        debt_by_room=debt_by_rooms,
    )

    # 4. Occupancy KPI
    occ_rows = await db.fetch(OCCUPANCY_KPI_QUERY, landlord_id)
    occ = occ_rows[0] if occ_rows else {}
    total_rooms_val = occ.get("total_rooms", 0)
    occupied_rooms_val = occ.get("occupied_rooms", 0)
    vacant_rooms_val = occ.get("vacant_rooms", 0)
    occupancy_rate = occ.get("occupancy_rate", 0)

    # Occupancy change - compare with previous period estimate
    # Since occupancy is point-in-time, use historical monthly data
    monthly_occ_rows = await db.fetch(MONTHLY_OCCUPANCY_QUERY, landlord_id)
    prev_occ_rate = 0.0
    if len(monthly_occ_rows) >= 2:
        prev_occ_rate = monthly_occ_rows[-2].get("occupancy_rate", 0)
    elif len(monthly_occ_rows) == 1:
        prev_occ_rate = monthly_occ_rows[-1].get("occupancy_rate", 0)
    occ_change = round(occupancy_rate - prev_occ_rate, 1) if prev_occ_rate else None

    occupancy = Occupancy(
        total_rooms=total_rooms_val,
        occupied_rooms=occupied_rooms_val,
        vacant_rooms=vacant_rooms_val,
        occupancy_rate=occupancy_rate,
        occupancy_change=occ_change,
    )

    # 5. Profit
    net_profit = revenue.total - expense.total
    profit_growth_pct = None
    if previous_revenue_total and expense_previous_total:
        prev_profit = previous_revenue_total - expense_previous_total
        if prev_profit and prev_profit > 0:
            profit_growth_pct = round((net_profit - prev_profit) / prev_profit * 100, 1)

    expense_ratio = round(expense.total / revenue.total * 100, 1) if revenue.total > 0 else 0

    profit = Profit(
        net=net_profit,
        growth_pct=profit_growth_pct,
        expense_ratio=expense_ratio,
    )

    # 6. Previous period
    previous_period = PreviousPeriod(
        revenue={"total": round(previous_revenue_total)},
        expense={"total": round(expense_previous_total)},
        profit={"net": round(previous_revenue_total - expense_previous_total)},
        occupancy={"occupancy_rate": prev_occ_rate},
    )

    # 7. Change percentages
    rev_change = growth_pct
    exp_change = None
    if expense_previous_total and expense_previous_total > 0:
        exp_change = round((expense.total - expense_previous_total) / expense_previous_total * 100, 1)
    profit_change = profit_growth_pct

    change_pct = ChangePct(
        revenue=rev_change,
        expense=exp_change,
        profit=profit_change,
        occupancy=occ_change,
    )

    # 8. Health score
    # Calculate using existing MetricsEngine for consistency
    revenue_util = revenue.total / (revenue.total + debt_obj.overdue_amount) if (revenue.total + debt_obj.overdue_amount) > 0 else 1
    occ_rate_decimal = occupancy_rate / 100.0
    debt_health_val = 1 - (debt_obj.overdue_amount / (revenue.total + expense.total + 1)) if (revenue.total + expense.total) > 0 else 1
    debt_health_val = max(0, min(1, debt_health_val))

    trend_score = 0.5
    health_score = MetricsEngine.calculate_health_score(
        actual=revenue.total,
        potential=revenue.total + debt_obj.overdue_amount,
        occupancy_rate=occ_rate_decimal,
        debt_health=debt_health_val,
        trend_score=trend_score,
    )
    health_status, _ = MetricsEngine.get_health_status(health_score)

    kpi = KPIObject(
        period=period,
        landlord_id=landlord_id,
        revenue=revenue,
        expense=expense,
        debt=debt_obj,
        profit=profit,
        occupancy=occupancy,
        previous_period=previous_period,
        change_pct=change_pct,
        health_score=health_score,
        health_status=health_status,
    )

    # Cache
    KPIRepository.set_kpi(landlord_id, period, kpi)
    return kpi


async def _get_or_calculate_kpi(landlord_id: int, period: str) -> KPIObject:
    """Lấy KPI từ cache hoặc tính toán mới"""
    cached = KPIRepository.get_kpi(landlord_id, period)
    if cached is not None:
        return cached
    return await _calculate_full_kpi(landlord_id, period)


# ============================================================
# KPI ENDPOINTS
# ============================================================

@router.get("/kpi/overview")
async def get_kpi_overview(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """KPI tổng quan — revenue + expense + debt + profit + occupancy"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)
    # Lấy AI report nếu có
    report = AIReportCache.get_report(landlord_id, period)
    return {
        "status": "success",
        "data": kpi.model_dump(),
        "ai_report": report,
    }


@router.get("/kpi/revenue")
async def get_kpi_revenue(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """KPI doanh thu chi tiết + lịch sử 12 tháng"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)
    db = await get_db()
    period_start, period_end, _ = _get_period_range(period)

    monthly_rows = await db.fetch(MONTHLY_REVENUE_QUERY, landlord_id)
    monthly_data = []
    for row in monthly_rows:
        monthly_data.append({
            "month": row.get("month", ""),
            "total": round(row.get("total", 0)),
        })

    return {
        "status": "success",
        "data": {
            "current": kpi.revenue.model_dump(),
            "growth_pct": kpi.change_pct.revenue if kpi.change_pct else None,
            "monthly_history": monthly_data,
            "breakdown": {
                "rent_pct": round(kpi.revenue.rent / kpi.revenue.total * 100, 1) if kpi.revenue.total > 0 else 0,
                "electricity_pct": round(kpi.revenue.electricity / kpi.revenue.total * 100, 1) if kpi.revenue.total > 0 else 0,
                "water_pct": round(kpi.revenue.water / kpi.revenue.total * 100, 1) if kpi.revenue.total > 0 else 0,
                "service_pct": round(kpi.revenue.service / kpi.revenue.total * 100, 1) if kpi.revenue.total > 0 else 0,
                "other_pct": round(kpi.revenue.other / kpi.revenue.total * 100, 1) if kpi.revenue.total > 0 else 0,
            }
        }
    }


@router.get("/kpi/expense")
async def get_kpi_expense(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """KPI chi phí chi tiết + lịch sử 12 tháng"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)

    db = await get_db()
    monthly_rows = await db.fetch(MONTHLY_EXPENSE_QUERY, landlord_id)
    monthly_data = []
    for row in monthly_rows:
        monthly_data.append({
            "month": row.get("month", ""),
            "total": round(row.get("total", 0)),
        })

    return {
        "status": "success",
        "data": {
            "current": kpi.expense.model_dump(),
            "growth_pct": kpi.change_pct.expense if kpi.change_pct else None,
            "monthly_history": monthly_data,
            "breakdown": {
                "electricity_pct": round(kpi.expense.electricity / kpi.expense.total * 100, 1) if kpi.expense.total > 0 else 0,
                "water_pct": round(kpi.expense.water / kpi.expense.total * 100, 1) if kpi.expense.total > 0 else 0,
                "maintenance_pct": round(kpi.expense.maintenance / kpi.expense.total * 100, 1) if kpi.expense.total > 0 else 0,
                "penalty_pct": round(kpi.expense.penalty / kpi.expense.total * 100, 1) if kpi.expense.total > 0 else 0,
                "other_pct": round(kpi.expense.other / kpi.expense.total * 100, 1) if kpi.expense.total > 0 else 0,
            }
        }
    }


@router.get("/kpi/debt")
async def get_kpi_debt(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """KPI công nợ chi tiết + aging + cảnh báo"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)

    # Debt aging (phân loại nợ theo thời gian)
    db = await get_db()
    aging_rows = await db.fetch(DEBT_AGING_QUERY, landlord_id)
    aging = aging_rows[0] if aging_rows else {}

    # Warning thresholds
    warnings = []
    for deb in kpi.debt.debt_by_room:
        if deb.type == "ELECTRICITY" and deb.months >= 3:
            warnings.append({
                "room": deb.room,
                "type": deb.type,
                "months": deb.months,
                "amount": deb.total_debt,
                "severity": "CRITICAL",
                "message": f"Phòng {deb.room}: Nợ điện {deb.months} tháng — cần xử lý gấp!",
            })
        elif deb.type == "RENT" and deb.months >= 3:
            warnings.append({
                "room": deb.room,
                "type": deb.type,
                "months": deb.months,
                "amount": deb.total_debt,
                "severity": "CRITICAL",
                "message": f"Phòng {deb.room}: Nợ tiền phòng {deb.months} tháng — nguy cơ mất khách!",
            })
        elif deb.months >= 2:
            warnings.append({
                "room": deb.room,
                "type": deb.type,
                "months": deb.months,
                "amount": deb.total_debt,
                "severity": "WARNING",
                "message": f"Phòng {deb.room}: Nợ {deb.type} {deb.months} tháng — cần nhắc nhở!",
            })

    return {
        "status": "success",
        "data": {
            "collection_rate": kpi.debt.collection_rate,
            "overdue_count": kpi.debt.overdue_count,
            "overdue_amount": kpi.debt.overdue_amount,
            "debt_by_room": [d.model_dump() for d in kpi.debt.debt_by_room],
            "aging_report": {
                "0_7_days": round(aging.get("age_0_7", 0)),
                "8_30_days": round(aging.get("age_8_30", 0)),
                "31_60_days": round(aging.get("age_31_60", 0)),
                "60_plus_days": round(aging.get("age_60_plus", 0)),
            },
            "warnings": warnings,
        }
    }


@router.get("/kpi/occupancy")
async def get_kpi_occupancy(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """KPI tỉ lệ lấp đầy chi tiết + lịch sử"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)

    db = await get_db()
    monthly_rows = await db.fetch(MONTHLY_OCCUPANCY_QUERY, landlord_id)
    monthly_data = []
    for row in monthly_rows:
        monthly_data.append({
            "month": row.get("month", ""),
            "total_rooms": row.get("total_rooms", 0),
            "occupied_rooms": row.get("occupied_rooms", 0),
            "occupancy_rate": row.get("occupancy_rate", 0),
        })

    return {
        "status": "success",
        "data": {
            "current": kpi.occupancy.model_dump(),
            "change_pct": kpi.change_pct.occupancy if kpi.change_pct else None,
            "monthly_history": monthly_data,
        }
    }


@router.get("/kpi/export")
async def export_kpi_report(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
    format: str = Query("json", description="json | excel"),
):
    """Xuất báo cáo KPI (JSON / Excel)"""
    kpi = await _get_or_calculate_kpi(landlord_id, period)

    if format == "excel":
        try:
            import openpyxl
            from io import BytesIO
            from fastapi.responses import StreamingResponse

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Bao cao {period}"

            # Header
            ws.append(["BÁO CÁO TÀI CHÍNH", f"Kỳ: {period}", f"Chủ trọ ID: {landlord_id}"])
            ws.append([])

            # Doanh thu
            ws.append(["DOANH THU"])
            ws.append(["Khoản mục", "Giá trị", "Tỷ trọng"])
            total_rev = kpi.revenue.total or 1
            ws.append(["Tổng doanh thu", kpi.revenue.total, "100%"])
            ws.append(["Tiền phòng", kpi.revenue.rent, f"{round(kpi.revenue.rent/total_rev*100,1)}%"])
            ws.append(["Tiền điện", kpi.revenue.electricity, f"{round(kpi.revenue.electricity/total_rev*100,1)}%"])
            ws.append(["Tiền nước", kpi.revenue.water, f"{round(kpi.revenue.water/total_rev*100,1)}%"])
            ws.append(["Dịch vụ", kpi.revenue.service, f"{round(kpi.revenue.service/total_rev*100,1)}%"])
            ws.append(["Phát sinh", kpi.revenue.other, f"{round(kpi.revenue.other/total_rev*100,1)}%"])
            if kpi.change_pct and kpi.change_pct.revenue is not None:
                ws.append(["Tăng trưởng", f"{kpi.change_pct.revenue}%", ""])
            ws.append([])

            # Chi phí
            ws.append(["CHI PHÍ"])
            ws.append(["Khoản mục", "Giá trị", "Tỷ trọng"])
            total_exp = kpi.expense.total or 1
            ws.append(["Tổng chi phí", kpi.expense.total, "100%"])
            ws.append(["Điện", kpi.expense.electricity, f"{round(kpi.expense.electricity/total_exp*100,1)}%"])
            ws.append(["Nước", kpi.expense.water, f"{round(kpi.expense.water/total_exp*100,1)}%"])
            ws.append(["Sửa chữa", kpi.expense.maintenance, f"{round(kpi.expense.maintenance/total_exp*100,1)}%"])
            ws.append(["Phạt", kpi.expense.penalty, f"{round(kpi.expense.penalty/total_exp*100,1)}%"])
            ws.append(["Khác", kpi.expense.other, f"{round(kpi.expense.other/total_exp*100,1)}%"])
            ws.append([])

            # Lợi nhuận
            ws.append(["LỢI NHUẬN"])
            ws.append(["Lợi nhuận ròng", kpi.profit.net])
            ws.append(["Tỷ lệ chi phí", f"{kpi.profit.expense_ratio}%"])
            ws.append([])

            # Công nợ
            ws.append(["CÔNG NỢ"])
            ws.append(["Tổng công nợ", kpi.debt.overdue_amount])
            ws.append(["Số hóa đơn quá hạn", kpi.debt.overdue_count])
            ws.append(["Tỷ lệ thu tiền", f"{kpi.debt.collection_rate}%"])
            ws.append([])

            # Lấp đầy
            ws.append(["TỈ LỆ LẤP ĐẦY"])
            ws.append(["Tổng phòng", kpi.occupancy.total_rooms])
            ws.append(["Phòng có khách", kpi.occupancy.occupied_rooms])
            ws.append(["Phòng trống", kpi.occupancy.vacant_rooms])
            ws.append(["Tỉ lệ lấp đầy", f"{kpi.occupancy.occupancy_rate}%"])

            output = BytesIO()
            wb.save(output)
            output.seek(0)

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=bao_cao_tai_chinh_{period}.xlsx"
                }
            )
        except ImportError:
            return {"error": "openpyxl not installed", "format": "json", "data": kpi.model_dump()}

    return {
        "status": "success",
        "data": kpi.model_dump(),
    }
