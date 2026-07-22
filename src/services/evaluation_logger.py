"""
Evaluation Logger — AI Financial Copilot
Theo dõi metrics: accuracy, latency, fallback rate, cache hit rate

Log schema (theo AI_MODEL_FLOW_AND_RATE_LIMITS.md):
- question: str — Câu hỏi người dùng
- intent: str — Loại câu hỏi (REVENUE, EXPENSE, ...)
- model_used: str — Model sử dụng (primary / fallback)
- latency_ms: int — Thời gian xử lý
- token_count: int — Số token tiêu thụ
- response: str — Câu trả lời (preview)
- error: str | None — Lỗi nếu có
- from_cache: bool — Cache hit hay miss
- fallback_used: bool — Có dùng fallback không
"""
import json
import time
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime
from collections import defaultdict

log = logging.getLogger("ai-property-advisor")


class EvaluationLogger:
    """
    Logger đánh giá chất lượng AI.

    Usage:
        logger = EvaluationLogger()
        ctx = logger.start(question="Doanh thu tháng này?", intent="REVENUE")
        # ... process ...
        ctx.end(reply="Doanh thu 420tr", model_used="gemini-3.1-flash-lite",
                token_count=150, from_cache=False)
    """

    def __init__(self):
        self._logs: List[Dict[str, Any]] = []
        self._active_logs: Dict[str, Dict] = {}  # key -> context
        self._stats: Dict[str, Any] = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_count": 0,
            "errors": 0,
            "total_latency_ms": 0,
            "total_tokens": 0,
            "by_intent": defaultdict(lambda: {"count": 0, "errors": 0, "fallbacks": 0}),
        }

    def start(self, question: str, intent: str = "GENERAL",
              session_id: Optional[str] = None,
              landlord_id: Optional[int] = None,
              period: Optional[str] = None) -> 'EvalContext':
        """Start a new evaluation context for a request"""
        self._stats["total_requests"] += 1
        return EvalContext(
            logger=self,
            question=question,
            intent=intent,
            session_id=session_id,
            landlord_id=landlord_id,
            period=period,
        )

    def _record(self, entry: Dict[str, Any]) -> None:
        """Record a completed evaluation entry"""
        self._logs.append(entry)

        # Update stats
        self._stats["total_latency_ms"] += entry.get("latency_ms", 0)
        self._stats["total_tokens"] += entry.get("token_count", 0)

        if entry.get("from_cache"):
            self._stats["cache_hits"] += 1
        else:
            self._stats["cache_misses"] += 1

        if entry.get("fallback_used"):
            self._stats["fallback_count"] += 1
            intent = entry.get("intent", "GENERAL")
            self._stats["by_intent"][intent]["fallbacks"] += 1

        if entry.get("error"):
            self._stats["errors"] += 1
            intent = entry.get("intent", "GENERAL")
            self._stats["by_intent"][intent]["errors"] += 1

        # Log summary
        log.info(
            "AI Eval | intent=%s model=%s latency=%dms tokens=%d cache=%s fallback=%s error=%s",
            entry.get("intent", "?"),
            entry.get("model_used", "?"),
            entry.get("latency_ms", 0),
            entry.get("token_count", 0),
            "HIT" if entry.get("from_cache") else "MISS",
            "YES" if entry.get("fallback_used") else "NO",
            "YES" if entry.get("error") else "NO",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        s = self._stats
        total = s["total_requests"]
        return {
            "total_requests": total,
            "cache_hit_rate": round(s["cache_hits"] / total * 100, 1) if total > 0 else 0,
            "fallback_rate": round(s["fallback_count"] / total * 100, 1) if total > 0 else 0,
            "error_rate": round(s["errors"] / total * 100, 1) if total > 0 else 0,
            "avg_latency_ms": round(s["total_latency_ms"] / total, 1) if total > 0 else 0,
            "avg_tokens": round(s["total_tokens"] / total, 1) if total > 0 else 0,
            "cache_hits": s["cache_hits"],
            "cache_misses": s["cache_misses"],
            "fallback_count": s["fallback_count"],
            "errors": s["errors"],
            "by_intent": dict(s["by_intent"]),
        }

    def get_recent_logs(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent N log entries"""
        return self._logs[-n:]


class EvalContext:
    """
    Context for a single evaluation — dùng với 'with' statement.

    Usage:
        with eval_logger.start(question="...", intent="REVENUE") as ctx:
            # processing
            ctx.set_reply(reply, model_used="...", token_count=150)
            # Nếu có lỗi:
            ctx.set_error("timeout")
    """

    def __init__(self, logger: EvaluationLogger, **kwargs):
        self._logger = logger
        self._data = kwargs
        self._data["started_at"] = time.monotonic()
        self._data["timestamp"] = datetime.now().isoformat()
        self._data["from_cache"] = False
        self._data["fallback_used"] = False
        self._data["error"] = None
        self._data["model_used"] = "unknown"
        self._data["token_count"] = 0
        self._data["latency_ms"] = 0

    def set_reply(self, reply: str, model_used: str = "unknown",
                  token_count: int = 0, from_cache: bool = False,
                  fallback_used: bool = False) -> None:
        """Set the reply and metrics for this evaluation"""
        self._data["response"] = reply[:200]  # preview only
        self._data["model_used"] = model_used
        self._data["token_count"] = token_count
        self._data["from_cache"] = from_cache
        self._data["fallback_used"] = fallback_used

    def set_error(self, error: str) -> None:
        """Set error for this evaluation"""
        self._data["error"] = error[:200]

    def set_intent(self, intent: str) -> None:
        """Update intent (nếu LLM classifier thay đổi)"""
        self._data["intent"] = intent

    def end(self) -> None:
        """Complete the evaluation and log"""
        self._data["latency_ms"] = round((time.monotonic() - self._data["started_at"]) * 1000)
        self._logger._record(self._data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.set_error(str(exc_val))
        self.end()
        return False  # Don't suppress exceptions


# Singleton
eval_logger = EvaluationLogger()
