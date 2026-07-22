"""
Unit tests for InMemoryRateLimiter
"""
import time
import pytest
from src.engines.rate_limiter import SlidingWindowRateLimiter, is_ai_path, extract_key
from unittest.mock import Mock, patch


class TestRateLimiter:

    def setup_method(self):
        self.limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)

    def test_initial_state(self):
        """Fresh limiter should allow all requests"""
        allowed, remaining = self.limiter.check("test_user")
        assert allowed is True
        assert remaining == 5

    def test_basic_counting(self):
        """After recording N < max requests, remaining should decrease"""
        self.limiter.record("test_user")
        allowed, remaining = self.limiter.check("test_user")
        assert allowed is True
        assert remaining == 4

        for _ in range(4):
            self.limiter.record("test_user")

        allowed, remaining = self.limiter.check("test_user")
        assert allowed is False
        assert remaining == 0

    def test_block_exceeded(self):
        """Request should be blocked when limit exceeded"""
        for _ in range(5):
            allowed, _ = self.limiter.check("test_user")
            assert allowed is True
            self.limiter.record("test_user")

        # 6th request should be blocked
        allowed, _ = self.limiter.check("test_user")
        assert allowed is False

    def test_independent_keys(self):
        """Different keys should have independent counters"""
        for _ in range(5):
            self.limiter.record("user_a")

        allowed_a, _ = self.limiter.check("user_a")
        assert allowed_a is False  # user_a exhausted

        allowed_b, remaining_b = self.limiter.check("user_b")
        assert allowed_b is True  # user_b fresh
        assert remaining_b == 5

    def test_reset_key(self):
        """Resetting a specific key should clear its counter"""
        for _ in range(5):
            self.limiter.record("test_user")

        allowed, _ = self.limiter.check("test_user")
        assert allowed is False

        self.limiter.reset("test_user")
        allowed, remaining = self.limiter.check("test_user")
        assert allowed is True
        assert remaining == 5

    def test_reset_all(self):
        """Resetting all keys should clear everything"""
        for key in ["user_a", "user_b"]:
            for _ in range(5):
                self.limiter.record(key)
            allowed, _ = self.limiter.check(key)
            assert allowed is False

        self.limiter.reset()
        allowed_a, _ = self.limiter.check("user_a")
        assert allowed_a is True
        allowed_b, _ = self.limiter.check("user_b")
        assert allowed_b is True

    def test_remaining_after_reset(self):
        """get_remaining should return max after reset"""
        self.limiter.record("test_user")
        assert self.limiter.get_remaining("test_user") == 4

        self.limiter.reset("test_user")
        assert self.limiter.get_remaining("test_user") == 5

    def test_retry_after_returns_positive(self):
        """get_retry_after should return > 0 when requests exist"""
        self.limiter.record("test_user")
        retry = self.limiter.get_retry_after("test_user")
        assert retry > 0
        assert retry <= 60

    def test_retry_after_empty_key(self):
        """get_retry_after should return 0 for empty key"""
        retry = self.limiter.get_retry_after("nonexistent")
        assert retry == 0

    def test_stats_after_blocks(self):
        """get_stats should track blocks correctly"""
        for _ in range(6):  # 5 allowed + 1 blocked
            allowed, _ = self.limiter.check("test_user")
            if allowed:
                self.limiter.record("test_user")

        stats = self.limiter.get_stats()
        assert stats["total_checked"] == 6
        assert stats["total_blocked"] == 1
        assert stats["active_keys"] == 1
        assert stats["block_rate"] > 0


class TestUtilityFunctions:

    @patch("src.engines.rate_limiter.settings")
    def test_is_ai_path_copilot(self, mock_settings):
        assert is_ai_path("/api/v1/advisor/copilot/ask") is True
        assert is_ai_path("/api/v1/advisor/copilot/report") is True
        assert is_ai_path("/api/v1/advisor/copilot/suggestions") is True

    @patch("src.engines.rate_limiter.settings")
    def test_is_ai_path_non_ai(self, mock_settings):
        assert is_ai_path("/api/v1/advisor/kpi/overview") is False
        assert is_ai_path("/health") is False
        assert is_ai_path("/ui") is False

    def test_extract_key_with_landlord_id(self):
        mock_request = Mock()
        mock_request.query_params = {"landlord_id": "42"}
        mock_request.client = Mock()
        mock_request.client.host = "1.2.3.4"
        key = extract_key(mock_request)
        assert key == "user:42"

    def test_extract_key_no_landlord_id(self):
        mock_request = Mock()
        mock_request.query_params = {}
        mock_request.client = Mock()
        mock_request.client.host = "1.2.3.4"
        key = extract_key(mock_request)
        assert key == "ip:1.2.3.4"

    def test_extract_key_no_client(self):
        mock_request = Mock()
        mock_request.query_params = {}
        mock_request.client = None
        key = extract_key(mock_request)
        assert key == "ip:unknown"
