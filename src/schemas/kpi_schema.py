"""
KPI Object Schema — AI Financial Copilot
Định nghĩa các KPI Object theo design doc: revenue, expense, debt, profit, occupancy, previous_period, change_pct
"""
from __future__ import annotations
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from datetime import datetime


class DebtByRoom(BaseModel):
    room: str = Field(..., description="Số phòng")
    total_debt: float = Field(..., ge=0, description="Tổng nợ")
    type: str = Field(..., description="Loại nợ: RENT, ELECTRICITY, WATER, SERVICE, OTHER")
    months: int = Field(..., ge=0, description="Số tháng nợ")


class Revenue(BaseModel):
    total: float = Field(..., ge=0, description="Tổng doanh thu")
    rent: float = Field(..., ge=0, description="Doanh thu tiền phòng")
    electricity: float = Field(..., ge=0, description="Doanh thu tiền điện")
    water: float = Field(..., ge=0, description="Doanh thu tiền nước")
    service: float = Field(..., ge=0, description="Doanh thu dịch vụ")
    other: float = Field(..., ge=0, description="Doanh thu phát sinh")
    growth_pct: Optional[float] = Field(None, description="Tốc độ tăng trưởng (%)")


class Expense(BaseModel):
    total: float = Field(..., ge=0, description="Tổng chi phí")
    electricity: float = Field(..., ge=0, description="Chi phí điện")
    water: float = Field(..., ge=0, description="Chi phí nước")
    maintenance: float = Field(..., ge=0, description="Chi phí sửa chữa")
    penalty: float = Field(..., ge=0, description="Phạt vi phạm")
    other: float = Field(..., ge=0, description="Chi phí khác")


class Debt(BaseModel):
    collection_rate: float = Field(..., ge=0, le=100, description="Tỷ lệ thu tiền (%)")
    overdue_count: int = Field(..., ge=0, description="Số hóa đơn quá hạn")
    overdue_amount: float = Field(..., ge=0, description="Tổng tiền quá hạn")
    debt_by_room: List[DebtByRoom] = Field(default_factory=list, description="Công nợ chi tiết từng phòng")


class Profit(BaseModel):
    net: float = Field(..., description="Lợi nhuận ròng")
    growth_pct: Optional[float] = Field(None, description="Tăng trưởng lợi nhuận (%)")
    expense_ratio: float = Field(..., ge=0, description="Tỷ lệ chi phí/doanh thu (%)")


class Occupancy(BaseModel):
    total_rooms: int = Field(..., ge=0, description="Tổng số phòng khả dụng")
    occupied_rooms: int = Field(..., ge=0, description="Số phòng đang có khách thuê")
    vacant_rooms: int = Field(..., ge=0, description="Số phòng trống")
    occupancy_rate: float = Field(..., ge=0, le=100, description="Tỉ lệ lấp đầy (%)")
    occupancy_change: Optional[float] = Field(None, description="Thay đổi tỉ lệ lấp đầy so với kỳ trước")


class PreviousPeriod(BaseModel):
    revenue: Optional[dict] = Field(None, description="Doanh thu kỳ trước")
    expense: Optional[dict] = Field(None, description="Chi phí kỳ trước")
    profit: Optional[dict] = Field(None, description="Lợi nhuận kỳ trước")
    occupancy: Optional[dict] = Field(None, description="Lấp đầy kỳ trước")


class ChangePct(BaseModel):
    revenue: Optional[float] = Field(None, description="Thay đổi doanh thu (%)")
    expense: Optional[float] = Field(None, description="Thay đổi chi phí (%)")
    profit: Optional[float] = Field(None, description="Thay đổi lợi nhuận (%)")
    occupancy: Optional[float] = Field(None, description="Thay đổi lấp đầy (%)")


class KPIObject(BaseModel):
    """KPI Object chuẩn hóa — nguồn dữ liệu duy nhất cho cả Dashboard và AI"""
    period: str = Field(..., description="Kỳ báo cáo (YYYY-MM)")
    landlord_id: int = Field(..., description="ID chủ trọ")
    revenue: Revenue
    expense: Expense
    debt: Debt
    profit: Profit
    occupancy: Occupancy
    previous_period: Optional[PreviousPeriod] = Field(None, description="Kỳ trước")
    change_pct: Optional[ChangePct] = Field(None, description="Thay đổi %")
    health_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm sức khỏe")
    health_status: Optional[str] = Field(None, description="HEALTHY | ATTENTION | WARNING | CRITICAL")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Thời gian tạo")
