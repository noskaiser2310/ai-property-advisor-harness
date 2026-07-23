import json
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from config.settings import settings

log = logging.getLogger("ai-property-advisor")


class ModelRegistry:
    """
    Model Registry — Track RPM/RPD cho mỗi model.
    
    ⚠️ LƯU Ý MULTI-WORKER: Khi deploy với nhiều Uvicorn workers (API_WORKERS > 1),
    mỗi worker có bộ đếm RPM/RPD riêng → tổng RPM thực tế = workers × limit.
    Để tránh 429 từ Google API, nên: (1) dùng API_WORKERS=1, hoặc (2) dùng Redis shared counter.
    """

    MODELS = {
        "gemini-2.0-flash": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 1},
        "gemini-2.0-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 2},
        "gemini-3.5-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 3},
        "gemini-3.1-flash-lite": {"rpm": 30, "tpm": 500000, "rpd": 1500, "priority": 4},
    }

    def __init__(self):
        self._rpm_tracker: Dict[str, List[float]] = {}
        self._rpd_tracker: Dict[str, List[float]] = {}
        self._total_calls: Dict[str, int] = {}
        self._total_tokens: Dict[str, int] = {}
        self._fallback_count: Dict[str, int] = {}

    def check_available(self, model_id: str) -> bool:
        """Check if model is available under RPM and RPD limits"""
        if model_id not in self.MODELS:
            return True

        now = time.time()
        model_spec = self.MODELS[model_id]
        rpm_limit = model_spec["rpm"]
        rpd_limit = model_spec["rpd"]

        rpm_ts = [ts for ts in self._rpm_tracker.get(model_id, []) if ts > now - 60]
        self._rpm_tracker[model_id] = rpm_ts

        rpd_ts = [ts for ts in self._rpd_tracker.get(model_id, []) if ts > now - 86400]
        self._rpd_tracker[model_id] = rpd_ts

        if len(rpm_ts) >= rpm_limit:
            log.warning("Model %s: RPM limit reached (%d/%d)", model_id, len(rpm_ts), rpm_limit)
            return False
        if len(rpd_ts) >= rpd_limit:
            log.warning("Model %s: RPD limit reached (%d/%d)", model_id, len(rpd_ts), rpd_limit)
            return False

        return True

    def record_call(self, model_id: str, token_count: int = 0, is_fallback: bool = False) -> None:
        """Record a successful call to a model"""
        now = time.time()
        if model_id not in self._rpm_tracker:
            self._rpm_tracker[model_id] = []
        self._rpm_tracker[model_id].append(now)

        if model_id not in self._rpd_tracker:
            self._rpd_tracker[model_id] = []
        self._rpd_tracker[model_id].append(now)

        self._total_calls[model_id] = self._total_calls.get(model_id, 0) + 1
        self._total_tokens[model_id] = self._total_tokens.get(model_id, 0) + token_count

        if is_fallback:
            self._fallback_count[model_id] = self._fallback_count.get(model_id, 0) + 1

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for monitoring"""
        stats = {}
        for model_id in self.MODELS:
            now = time.time()
            rpm_ts = [ts for ts in self._rpm_tracker.get(model_id, []) if ts > now - 60]
            rpd_ts = [ts for ts in self._rpd_tracker.get(model_id, []) if ts > now - 86400]
            stats[model_id] = {
                "current_rpm": len(rpm_ts),
                "current_rpd": len(rpd_ts),
                "total_calls": self._total_calls.get(model_id, 0),
                "total_tokens": self._total_tokens.get(model_id, 0),
                "fallback_calls": self._fallback_count.get(model_id, 0),
                "rpm_limit": self.MODELS[model_id]["rpm"],
                "rpd_limit": self.MODELS[model_id]["rpd"],
                "available": self.check_available(model_id),
            }
        return stats


class GeminiService:
    @property
    def model(self) -> str:
        return settings.GEMINI_MODEL

    @property
    def fallback_model(self) -> str:
        return settings.GEMINI_FALLBACK_MODEL

    def __init__(self):
        self._client = None
        self.temperature = settings.GEMINI_TEMPERATURE
        self._timeout = settings.GEMINI_TIMEOUT
        self._max_retries = 2
        self.registry = ModelRegistry()

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _safe_text(self, response) -> str:
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        if hasattr(response, "candidates") and response.candidates:
            c = response.candidates[0]
            if hasattr(c, "content") and c.content and hasattr(c.content, "parts") and c.content.parts:
                return ''.join(p.text for p in c.content.parts if hasattr(p, "text") and p.text).strip()
        return ''

    def _extract_function_calls(self, response) -> List[Any]:
        """Extract tool function calls from Gemini API response"""
        calls = []
        if not hasattr(response, "candidates") or not response.candidates:
            return calls
        candidate = response.candidates[0]
        if not hasattr(candidate, "content") or not candidate.content or not hasattr(candidate.content, "parts"):
            return calls
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                calls.append(part.function_call)
        return calls

    async def _call_with_retry(self, model: str, contents: Any, config: Any) -> Any:
        """
        Call LLM with retry + fallback chain:
        1. Try primary model (retry 2x with exponential backoff)
        2. If primary fail → try fallback model cascade
        """
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini client not initialized")

        last_exc = None
        primary_used = model
        is_fallback = False

        for attempt in range(self._max_retries):
            if not self.registry.check_available(model):
                log.debug("Model %s: rate limited, trying fallback", model)
                break
            try:
                result = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model, contents=contents, config=config
                    ),
                    timeout=self._timeout,
                )
                self.registry.record_call(model)
                return result
            except Exception as e:
                last_exc = e
                if attempt < self._max_retries - 1:
                    wait = (2 ** attempt) + 1
                    log.debug("Retrying model %s (attempt %d/%d) after %ds: %s",
                              model, attempt + 1, self._max_retries, wait, str(e)[:60])
                    await asyncio.sleep(wait)

        # Fallback candidates (Gemini 3.1 Flash-Lite làm fallback chuẩn)
        fallback_candidates = [self.fallback_model]
        for fb_model in fallback_candidates:
            if not fb_model or fb_model == model:
                continue
            is_fallback = True
            log.info("Primary model %s failed, trying fallback %s", model, fb_model)
            try:
                await asyncio.sleep(1.0)
                result = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=fb_model, contents=contents, config=config
                    ),
                    timeout=self._timeout,
                )
                self.registry.record_call(fb_model, is_fallback=True)
                return result
            except Exception as fb_err:
                log.warning("Fallback model %s failed: %s", fb_model, fb_err)

        raise last_exc or RuntimeError(f"All models failed after retries (primary={primary_used}, fallback={is_fallback})")


gemini_service = GeminiService()