from datetime import date, timedelta
from typing import Dict, List, Any
from collections import defaultdict


class MetricsEngine:
    @staticmethod
    def calculate_potential_revenue(rooms: List[Dict[str, Any]], days_in_month: int = 30) -> float:
        """
        Doanh thu tiềm năng tối đa = Tổng giá niêm yết của tất cả các phòng
        """
        return sum(room["base_price"] for room in rooms)

    @staticmethod
    def calculate_vacancy_loss(
        vacancy_logs: List[Dict[str, Any]],
        rooms_map: Dict[int, float],
        start_date: date,
        end_date: date
    ) -> float:
        """
        Thất thoát do phòng trống = Tổng số ngày trống của từng phòng x Giá thuê mỗi ngày
        """
        loss = 0.0
        for log in vacancy_logs:
            v_start = max(log["vacant_from"], start_date)
            v_end = min(log["occupied_at"] or end_date, end_date)

            if v_start <= v_end:
                days_vacant = (v_end - v_start).days + 1
                daily_rate = rooms_map.get(log["room_id"], 0.0) / 30.0
                loss += days_vacant * daily_rate
        return round(loss, 2)

    @staticmethod
    def calculate_debt_loss(overdue_bills: List[Dict[str, Any]], payments: List[Dict[str, Any]] = None) -> float:
        paid_map = {}
        if payments:
            for p in payments:
                paid_map.setdefault(p["bill_id"], 0)
                paid_map[p["bill_id"]] += p["paid_amount"]
        return sum(
            bill["total_amount"] - min(paid_map.get(bill["id"], 0), bill["total_amount"])
            for bill in overdue_bills
        )

    @staticmethod
    def calculate_discount_loss(
        contracts: List[Dict[str, Any]],
        rooms_map: Dict[int, float]
    ) -> float:
        """
        Thất thoát do giảm giá = Tổng chênh lệch giữa Giá niêm yết và Giá thuê hợp đồng thực tế
        """
        loss = 0.0
        for contract in contracts:
            base_price = rooms_map.get(contract["room_id"], 0.0)
            rent_price = contract["rent_price"]
            if rent_price < base_price:
                loss += (base_price - rent_price)
        return round(loss, 2)

    @classmethod
    def calculate_health_score(
        cls,
        actual: float,
        potential: float,
        occupancy_rate: float,
        debt_health: float,
        trend_score: float
    ) -> int:
        """
        Tính điểm sức khỏe từ 4 thành phần có trọng số
        """
        if potential == 0:
            return 0
        revenue_util = actual / potential

        score = (
            (revenue_util * 100 * 0.40) +
            (occupancy_rate * 100 * 0.30) +
            (debt_health * 100 * 0.20) +
            (trend_score * 0.10)
        )
        return int(min(max(score, 0), 100))

    @classmethod
    def calculate_metrics(
        cls,
        rooms: List[Dict[str, Any]],
        contracts: List[Dict[str, Any]],
        bills: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        vacancy_logs: List[Dict[str, Any]],
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """
        Tính toán tất cả metrics cho kỳ báo cáo
        """
        rooms_map = {r["id"]: r["base_price"] for r in rooms}

        potential = cls.calculate_potential_revenue(rooms)

        vacancy_loss = cls.calculate_vacancy_loss(vacancy_logs, rooms_map, period_start, period_end)

        overdue_bills = [b for b in bills if b["status"] in ("OVERDUE", "UNPAID", "PARTIALLY_PAID") and b["due_date"] < period_end]
        debt_loss = cls.calculate_debt_loss(overdue_bills, payments)

        discount_loss = cls.calculate_discount_loss(contracts, rooms_map)

        revenue_leakage = vacancy_loss + debt_loss + discount_loss
        actual = max(potential - revenue_leakage, 0)

        total_rooms = len(rooms)
        rented_rooms = len([c for c in contracts if c["is_active"]])
        occupancy_rate = min(rented_rooms / total_rooms, 1.0) if total_rooms > 0 else 0

        total_potential = potential
        paid_map = {}
        for p in payments:
            paid_map.setdefault(p["bill_id"], 0)
            paid_map[p["bill_id"]] += p["paid_amount"]
        total_debt = sum(
            b["total_amount"] - min(paid_map.get(b["id"], 0), b["total_amount"])
            for b in overdue_bills
        )
        debt_health = 1 - (total_debt / total_potential) if total_potential > 0 else 1

        return {
            "potential_revenue": potential,
            "actual_revenue": round(actual, 2),
            "revenue_leakage": round(revenue_leakage, 2),
            "vacancy_loss": vacancy_loss,
            "debt_loss": debt_loss,
            "discount_loss": discount_loss,
            "occupancy_rate": round(occupancy_rate, 4),
            "debt_health": round(debt_health, 4),
            "revenue_utilization": round(max(actual / potential, 0), 4) if potential > 0 else 0,
            "total_rooms": total_rooms,
            "rented_rooms": rented_rooms,
        }

    @staticmethod
    def get_health_status(score: int) -> tuple[str, str]:
        if score >= 85:
            return "HEALTHY", "green"
        elif score >= 70:
            return "ATTENTION", "yellow"
        elif score >= 50:
            return "WARNING", "orange"
        else:
            return "CRITICAL", "red"