"""
Rate Limiter — In-memory sliding window for Gemini API abuse protection

Modules:
- InMemoryRateLimiter: per-key sliding window counter
- get_rate_limiter(): singleton accessor
- rate_limit_dependency(): FastAPI dependency for route-level rate limiting

Config from settings:
- RATE_LIMIT_ENABLED: toggle on/off
- RATE_LIMIT_REQUESTS: max requests per window
- RATE_LIMIT_WINDOW: window size in seconds

Usage (middleware):
    from src.engines.rate_limiter import rate_limiter, record_request
    if not record_request(landlord_id):
        raise HTTPException(429, "Rate limit exceeded")

Usage (dependency):
    @router.post("/copilot/ask")
    async def ask_ai(..., _: None = Depends(rate_limit_dependency)):
        ...
"""
import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from config.settings import settings

log = logging.getLogger("ai-property-advisor")


class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter.
    
    Tracks request timestamps per key (landlord_id or IP).
    Uses a sliding window: removes timestamps older than WINDOW seconds,
    then checks if remaining count exceeds the limit.
    
    Thread-safe for sync access; async endpoints should use the singleton.
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, List[float]] = defaultdict(list)
        self._total_blocked: int = 0
        self._total_checked: int = 0

    def _clean_expired(self, key: str, now: float) -> None:
        """Remove timestamps older than the window"""
        cutoff = now - self.window_seconds
        bucket = self._buckets.get(key, [])
        self._buckets[key] = [ts for ts in bucket if ts > cutoff]

    def check(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed, remaining): 
            - allowed=True means within limit
            - remaining = requests left in window
        """
        now = time.time()
        self._clean_expired(key, now)
        self._total_checked += 1

        bucket = self._buckets[key]
        current_count = len(bucket)

        if current_count >= self.max_requests:
            self._total_blocked += 1
            return False, 0

        return True, self.max_requests - current_count

    def record(self, key: str) -> None:
        """Record a request for the given key"""
        now = time.time()
        self._buckets[key].append(now)

    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window"""
        now = time.time()
        self._clean_expired(key, now)
        current_count = len(self._buckets.get(key, []))
        return max(0, self.max_requests - current_count)

    def get_retry_after(self, key: str) -> float:
        """
        Get seconds until the window resets (oldest timestamp expires).
        Returns 0 if no requests recorded.
        """
        bucket = self._buckets.get(key, [])
        if not bucket:
            return 0
        oldest = min(bucket)
        elapsed = time.time() - oldest
        return max(0, self.window_seconds - elapsed)

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limit for a specific key, or all keys"""
        if key:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()
            self._total_blocked = 0
            self._total_checked = 0

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "total_checked": self._total_checked,
            "total_blocked": self._total_blocked,
            "block_rate": round(100.0 * self._total_blocked / max(self._total_checked, 1), 1),
            "active_keys": len(self._buckets),
        }


# Global singleton
_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get or create the rate limiter singleton"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter(
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW,
        )
    return _rate_limiter


# ============================================================
# FastAPI Middleware Integration
# ============================================================

AI_PATHS = [
    "/api/v1/advisor/copilot/report",
    "/api/v1/advisor/copilot/ask",
    "/api/v1/advisor/copilot/suggestions",
]


def is_ai_path(path: str) -> bool:
    """Check if the request path is an AI endpoint that needs rate limiting"""
    for ai_path in AI_PATHS:
        if path.startswith(ai_path):
            return True
    return False


def extract_key(request: Request) -> str:
    """
    Extract the rate limit key from the request.
    Priority: landlord_id query param > client IP > 'anonymous'
    """
    # Try landlord_id from query params
    landlord_id = request.query_params.get("landlord_id")
    if landlord_id:
        return f"user:{landlord_id}"

    # Fallback: client IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting AI endpoints.
    Add to main.py:
        app.middleware("http")(rate_limit_middleware)
    """
    # Only rate-limit AI paths
    if not is_ai_path(request.url.path):
        return await call_next(request)

    # Check if rate limiting is enabled
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    limiter = get_rate_limiter()
    key = extract_key(request)

    allowed, remaining = limiter.check(key)

    if not allowed:
        retry_after = limiter.get_retry_after(key)
        log.warning("Rate limit exceeded for %s (path=%s, retry=%ds)", key, request.url.path, retry_after)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please wait {int(retry_after)} seconds before trying again.",
                "retry_after_seconds": int(retry_after),
                "limit": limiter.max_requests,
                "window_seconds": limiter.window_seconds,
            },
            headers={
                "Retry-After": str(int(retry_after)),
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": "0",
            },
        )

    # Record the request
    limiter.record(key)

    # Call the next handler
    response = await call_next(request)

    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining - 1 if remaining > 0 else 0)
    return response


# ============================================================
# FastAPI Dependency (alternative to middleware)
# ============================================================

async def rate_limit_dependency(request: Request) -> None:
    """
    FastAPI dependency for per-route rate limiting.
    
    Usage:
        @router.post("/copilot/ask")
        async def ask_ai(..., _: None = Depends(rate_limit_dependency)):
            ...
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    limiter = get_rate_limiter()
    key = extract_key(request)

    allowed, _ = limiter.check(key)
    if not allowed:
        retry_after = limiter.get_retry_after(key)
        log.warning("Rate limit exceeded (dep) for %s", key)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Wait {int(retry_after)}s.",
                "retry_after_seconds": int(retry_after),
            },
            headers={"Retry-After": str(int(retry_after))},
        )

    limiter.record(key)
