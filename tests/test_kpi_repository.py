"""Tests for KPI Repository — Cache layer + Version Tracker + Session Store"""
import pytest
from src.engines.kpi_repository import KPIRepository, AIReportCache, SessionStore
from src.schemas.kpi_schema import KPIObject, Revenue, Expense, Debt, Profit, Occupancy


def _make_sample_kpi(period="2026-07", landlord_id=1):
    return KPIObject(
        period=period,
        landlord_id=landlord_id,
        revenue=Revenue(total=420000000, rent=340000000, electricity=35000000,
                        water=15000000, service=25000000, other=5000000,
                        growth_pct=6.1),
        expense=Expense(total=95000000, electricity=15000000, water=5000000,
                        maintenance=45000000, penalty=5000000, other=25000000),
        debt=Debt(collection_rate=85.5, overdue_count=6, overdue_amount=18000000),
        profit=Profit(net=325000000, growth_pct=5.3, expense_ratio=22.6),
        occupancy=Occupancy(total_rooms=35, occupied_rooms=30, vacant_rooms=5,
                           occupancy_rate=85.7, occupancy_change=-1.3),
    )


class TestKPIRepository:
    def setup_method(self):
        KPIRepository.invalidate_kpi(1, "2026-07")

    def test_set_and_get_kpi(self):
        kpi = _make_sample_kpi()
        KPIRepository.set_kpi(1, "2026-07", kpi)
        cached = KPIRepository.get_kpi(1, "2026-07")
        assert cached is not None
        assert cached.period == "2026-07"
        assert cached.revenue.total == 420000000
        assert cached.debt.overdue_count == 6

    def test_get_kpi_not_found(self):
        result = KPIRepository.get_kpi(999, "2099-01")
        assert result is None

    def test_invalidate_kpi(self):
        kpi = _make_sample_kpi()
        KPIRepository.set_kpi(1, "2026-07", kpi)
        KPIRepository.invalidate_kpi(1, "2026-07")
        assert KPIRepository.get_kpi(1, "2026-07") is None

    def test_version_tracker(self):
        KPIRepository.set_kpi(1, "2026-07", _make_sample_kpi())
        version = KPIRepository.get_kpi_version(1, "2026-07")
        assert version is not None
        assert version > 0

    def test_is_kpi_stale(self):
        KPIRepository.set_kpi(1, "2026-07", _make_sample_kpi())
        old_version = KPIRepository.get_kpi_version(1, "2026-07")
        # Same version -> not stale
        assert not KPIRepository.is_kpi_stale(1, "2026-07", old_version)
        # Newer version than cached -> stale (data changed)
        assert KPIRepository.is_kpi_stale(1, "2026-07", old_version + 1)
        # Older version than cached -> not stale
        assert not KPIRepository.is_kpi_stale(1, "2026-07", old_version - 1)

    def test_tenant_isolation(self):
        kpi1 = _make_sample_kpi(landlord_id=1)
        kpi2 = _make_sample_kpi(landlord_id=2)
        KPIRepository.set_kpi(1, "2026-07", kpi1)
        KPIRepository.set_kpi(2, "2026-07", kpi2)
        assert KPIRepository.get_kpi(1, "2026-07").landlord_id == 1
        assert KPIRepository.get_kpi(2, "2026-07").landlord_id == 2

    def test_different_periods(self):
        july = _make_sample_kpi(period="2026-07")
        june = _make_sample_kpi(period="2026-06")
        KPIRepository.set_kpi(1, "2026-07", july)
        KPIRepository.set_kpi(1, "2026-06", june)
        assert KPIRepository.get_kpi(1, "2026-07").revenue.total == 420000000
        assert KPIRepository.get_kpi(1, "2026-07").period == "2026-07"
        assert KPIRepository.get_kpi(1, "2026-06").period == "2026-06"


class TestAIReportCache:
    def setup_method(self):
        AIReportCache.invalidate_report(1, "2026-07")

    def test_set_and_get_report(self):
        AIReportCache.set_report(1, "2026-07", "Bao cao kiem tra")
        report = AIReportCache.get_report(1, "2026-07")
        assert report == "Bao cao kiem tra"

    def test_has_report(self):
        assert not AIReportCache.has_report(1, "2026-07")
        AIReportCache.set_report(1, "2026-07", "test")
        assert AIReportCache.has_report(1, "2026-07")

    def test_invalidate(self):
        AIReportCache.set_report(1, "2026-07", "test")
        AIReportCache.invalidate_report(1, "2026-07")
        assert not AIReportCache.has_report(1, "2026-07")


class TestSessionStore:
    def test_create_session(self):
        sid = SessionStore.create_session(1)
        assert sid is not None
        assert str(sid).startswith("1:")

    def test_session_history_empty(self):
        sid = SessionStore.create_session(1)
        history = SessionStore.get_history(sid)
        assert history == []

    def test_add_and_get_turns(self):
        sid = SessionStore.create_session(1)
        SessionStore.add_turn(sid, "Doanh thu bao nhieu?", "Doanh thu 420tr")
        history = SessionStore.get_history(sid)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_multiple_turns(self):
        sid = SessionStore.create_session(1)
        SessionStore.add_turn(sid, "Q1", "A1")
        SessionStore.add_turn(sid, "Q2", "A2")
        SessionStore.add_turn(sid, "Q3", "A3")
        history = SessionStore.get_history(sid)
        assert len(history) == 6

    def test_session_max_pairs(self):
        sid = SessionStore.create_session(1)
        for i in range(10):
            SessionStore.add_turn(sid, "Q" + str(i), "A" + str(i))
        history = SessionStore.get_history(sid)
        assert len(history) <= 10

    def test_format_history_context(self):
        sid = SessionStore.create_session(1)
        SessionStore.add_turn(sid, "Doanh thu?", "420tr")
        context = SessionStore.format_history_for_context(sid)
        # Use the actual Vietnamese characters from session format
        assert "Doanh thu?" in context
        assert "420tr" in context

    def test_unknown_session(self):
        history = SessionStore.get_history("nonexistent")
        assert history == []

    def test_different_landlords(self):
        sid1 = SessionStore.create_session(1)
        sid2 = SessionStore.create_session(2)
        assert sid1 != sid2
        SessionStore.add_turn(sid1, "Q1", "A1")
        assert len(SessionStore.get_history(sid2)) == 0
