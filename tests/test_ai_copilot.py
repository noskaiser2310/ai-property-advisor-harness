"""Tests for AI Financial Copilot — KPI endpoints + Copilot Services"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class MockGeminiService:
    model = "gemini-3.6-flash-lite"
    fallback_model = "gemini-3.5-flash-lite"

    async def _call_with_retry(self, model, contents, config):
        part = MagicMock()
        part.text = "Câu trả lời mẫu từ AI Copilot."
        part.function_call = None
        cand = MagicMock()
        cand.content.parts = [part]
        resp = MagicMock()
        resp.text = "Câu trả lời mẫu từ AI Copilot."
        resp.candidates = [cand]
        return resp

    def _safe_text(self, response):
        return response.text if hasattr(response, 'text') else ""

    async def generate_narrative(self, data):
        return "Báo cáo tài chính: Doanh thu 420tr."

    async def generate_action_descriptions(self, data):
        return {"priority_action": {"description": "Hành động ưu tiên."}}

    async def generate_text_to_sql(self, question, schema_snippet=None, examples_snippet=None, user_prompt=None, property_id=None):
        """Generate SQL from natural language question"""
        return f"SELECT * FROM rooms WHERE property_id = {property_id or 1} LIMIT 5"

    async def correct_sql(self, question, sql, error_msg, schema_snippet=None):
        """Correct SQL based on error message"""
        return "SELECT * FROM rooms LIMIT 5"

    async def generate_response(self, question, rows, columns=None):
        """Generate natural language response from SQL result"""
        if rows:
            return f"Ket qua: {len(rows)} dong du lieu."
        return "Khong co du lieu."

    async def select_visualization(self, rows, columns=None):
        """Select visualization type for data"""
        return {"type": "TABLE", "title": "Ket qua truy van"}


@pytest.fixture(autouse=True)
def mock_gemini():
    mock = MockGeminiService()
    patcher = patch("src.services.gemini_service.gemini_service", mock)
    patcher.start()
    yield
    patcher.stop()


class TestKPIEndpoints:
    def test_kpi_overview(self):
        resp = client.get("/api/v1/advisor/kpi/overview",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "success"
        assert "revenue" in data["data"]
        assert "expense" in data["data"]
        assert "debt" in data["data"]
        assert "profit" in data["data"]
        assert "occupancy" in data["data"]

    def test_kpi_revenue(self):
        resp = client.get("/api/v1/advisor/kpi/revenue",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "current" in data["data"]
        assert "monthly_history" in data["data"]
        assert "breakdown" in data["data"]

    def test_kpi_expense(self):
        resp = client.get("/api/v1/advisor/kpi/expense",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "current" in data["data"]

    def test_kpi_debt(self):
        resp = client.get("/api/v1/advisor/kpi/debt",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "collection_rate" in data["data"]
        assert "debt_by_room" in data["data"]
        assert "aging_report" in data["data"]
        assert "warnings" in data["data"]

    def test_kpi_occupancy(self):
        resp = client.get("/api/v1/advisor/kpi/occupancy",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "current" in data["data"]
        assert "monthly_history" in data["data"]

    def test_kpi_missing_params(self):
        resp = client.get("/api/v1/advisor/kpi/overview")
        assert resp.status_code == 422

    def test_kpi_invalid_month(self):
        resp = client.get("/api/v1/advisor/kpi/overview",
                         params={"landlord_id": 1, "period": "invalid"})
        assert resp.status_code == 422


class TestCopilotEndpoints:
    def test_ai_report(self):
        resp = client.post("/api/v1/advisor/copilot/report?",
                          params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "report" in data["data"]

    def test_ai_ask(self):
        resp = client.post("/api/v1/advisor/copilot/ask?",
                          params={"landlord_id": 1, "period": "2026-06"},
                          json={"question": "Doanh thu thang nay?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "reply" in data["data"]
        assert "session_id" in data["data"]
        assert "suggestions" in data["data"]

    def test_ai_suggestions(self):
        resp = client.get("/api/v1/advisor/copilot/suggestions",
                         params={"landlord_id": 1, "period": "2026-06"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]["questions"]) > 0

    def test_create_session(self):
        resp = client.post("/api/v1/advisor/copilot/session",
                          params={"landlord_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["session_id"] is not None


class TestHealthCheck:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "AI Property Advisor" in resp.json()["service"]
