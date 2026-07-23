"""
KPI Repository — Cache layer cho AI Financial Copilot
- KPI Cache: lưu KPI Object theo landlord_id:period
- AI Report Cache: lưu AI-generated report
- Version Tracker: SHA256 hash KPI data — chỉ regenerate khi data thay đổi
- Hỗ trợ cả in-memory (mặc định) và Redis (khi có CACHE_TYPE=redis)
"""
import json
import logging
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from datetime import datetime
from src.schemas.kpi_schema import KPIObject
from config.settings import settings

log = logging.getLogger("ai-property-advisor")

KPI_CACHE_PREFIX = "kpi"
AI_REPORT_PREFIX = "ai:report"
AI_ANALYSIS_PREFIX = "ai:analysis"
AI_SESSION_PREFIX = "ai:session"
SESSION_TTL_MINUTES = 30


def _compute_kpi_hash(kpi: KPIObject) -> str:
    """
    Compute SHA256 hash of KPI data for version tracking.
    Returns first 12 chars of hex digest — đủ để phát hiện thay đổi.
    
    Format: v{hash_prefix} (e.g. "va1b2c3d4e5f6")
    Dùng cho cache key: {dashboard}:{period}:{version}
    """
    raw = json.dumps(kpi.model_dump(), ensure_ascii=False, sort_keys=True, default=str)
    full_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"v{full_hash[:12]}"


# ============================================================
# Abstract Cache Interface — cho phép swap in-memory ↔ Redis
# ============================================================
class CacheBackend(ABC):
    """Abstract cache interface — implement cho mỗi backend"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend (dùng dict)"""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._ttl and time.time() > self._ttl[key]:
            self.delete(key)
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._store[key] = value
        if ttl:
            self._ttl[key] = time.time() + ttl
        elif key in self._ttl:
            del self._ttl[key]

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._ttl.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._store


class RedisCache(CacheBackend):
    """Redis cache backend — dùng khi CACHE_TYPE=redis"""

    def __init__(self):
        self._client = None
        self._available = False
        self._warned_get = False
        self._warned_set = False
        self._warned_del = False

    def _get_client(self):
        if self._client is None:
            try:
                import redis as redis_lib
                self._client = redis_lib.from_url(
                    settings.REDIS_URL or "redis://localhost:6379/0",
                    decode_responses=True,
                )
                self._client.ping()
                self._available = True
                log.info("Redis cache connected: %s", settings.REDIS_URL)
            except Exception as e:
                log.warning("Redis unavailable, falling back to memory: %s", e)
                self._available = False
                return None
        return self._client

    def get(self, key: str) -> Optional[Any]:
        client = self._get_client()
        if not client or not self._available:
            return None
        try:
            val = client.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            if not self._warned_get:
                log.warning("RedisCache get failed for key '%s': %s (suppressing further warnings)", key[:50], str(e)[:100])
                self._warned_get = True
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = self._get_client()
        if not client or not self._available:
            return
        try:
            val = json.dumps(value, default=str)
            if ttl:
                client.setex(key, ttl, val)
            else:
                client.set(key, val)
        except Exception as e:
            if not self._warned_set:
                log.warning("RedisCache set failed for key '%s': %s (suppressing further warnings)", key[:50], str(e)[:100])
                self._warned_set = True

    def delete(self, key: str) -> None:
        client = self._get_client()
        if not client or not self._available:
            return
        try:
            client.delete(key)
        except Exception as e:
            if not self._warned_del:
                log.warning("RedisCache delete failed for key '%s': %s (suppressing further warnings)", key[:50], str(e)[:100])
                self._warned_del = True

    def exists(self, key: str) -> bool:
        client = self._get_client()
        if not client or not self._available:
            return False
        try:
            return bool(client.exists(key))
        except Exception as e:
            log.warning("RedisCache exists failed for key '%s': %s", key[:50], str(e)[:100])
            return False


# Khởi tạo cache backend dựa trên config
def _get_cache_backend() -> CacheBackend:
    if settings.CACHE_TYPE == "redis":
        redis_cache = RedisCache()
        # Test connection, fallback to memory if fails
        if redis_cache._get_client():
            return redis_cache
        log.warning("Redis connection failed, using memory cache")
    return MemoryCache()


_cache = _get_cache_backend()


def _make_kpi_key(landlord_id: int, period: str) -> str:
    return f"{KPI_CACHE_PREFIX}:{landlord_id}:{period}"

def _make_report_key(landlord_id: int, period: str) -> str:
    return f"{AI_REPORT_PREFIX}:{landlord_id}:{period}"

def _make_analysis_key(landlord_id: int, period: str) -> str:
    return f"{AI_ANALYSIS_PREFIX}:{landlord_id}:{period}"

def _make_version_key(landlord_id: int, period: str) -> str:
    """Version key format: kpi:ver:{landlord_id}:{period}"""
    return f"kpi:ver:{landlord_id}:{period}"


class KPIRepository:
    """KPI Cache + Version Tracker (SHA256 hash + integer version counter)"""
    _version_cache = MemoryCache()
    _int_version: Dict[tuple, int] = {}  # (landlord_id, period) -> incremental int

    @staticmethod
    def get_kpi(landlord_id: int, period: str) -> Optional[KPIObject]:
        key = _make_kpi_key(landlord_id, period)
        return _cache.get(key)

    @staticmethod
    def set_kpi(landlord_id: int, period: str, kpi: KPIObject) -> None:
        key = _make_kpi_key(landlord_id, period)
        _cache.set(key, kpi)
        # Lưu SHA256 hash làm version
        kpi_hash = _compute_kpi_hash(kpi)
        ver_key = _make_version_key(landlord_id, period)
        old_hash = KPIRepository._version_cache.get(ver_key)
        KPIRepository._version_cache.set(ver_key, kpi_hash)
        
        # Increment integer version counter (cho is_kpi_stale + get_kpi_version)
        key_tuple = (landlord_id, period)
        current_ver = KPIRepository._int_version.get(key_tuple, 0)
        KPIRepository._int_version[key_tuple] = current_ver + 1
        
        log.debug("KPI cached: %s | version=%s (int=%d)", key, kpi_hash, current_ver + 1)
        
        # Trigger background AI Report + Analysis generation when KPI hash changes
        if old_hash is None or old_hash != kpi_hash:
            log.info("KPI version changed: %s -> %s — triggering background AI jobs",
                     old_hash[:8] if old_hash else "none", kpi_hash[:8])
            try:
                import asyncio
                # Trigger AI Report background generation
                from src.services.ai_report_service import ai_report_service
                asyncio.create_task(ai_report_service.generate_report(landlord_id, period))
                # Trigger Suggested Analysis background generation
                from src.services.suggested_analysis_service import suggested_analysis_service
                asyncio.create_task(suggested_analysis_service.generate_and_cache(landlord_id, period))
                log.debug("Background jobs triggered: report + analysis")
            except Exception as e:
                log.debug("Background trigger: %s", str(e))

    @staticmethod
    def invalidate_kpi(landlord_id: int, period: str) -> None:
        key = _make_kpi_key(landlord_id, period)
        _cache.delete(key)
        AIReportCache.invalidate_report(landlord_id, period)
        ver_key = _make_version_key(landlord_id, period)
        KPIRepository._version_cache.delete(ver_key)
        KPIRepository._int_version.pop((landlord_id, period), None)
        log.debug("KPI cache invalidated: %s", key)

    @staticmethod
    def get_kpi_hash(landlord_id: int, period: str) -> Optional[str]:
        """Lấy SHA256 hash của KPI (dùng để check thay đổi)"""
        ver_key = _make_version_key(landlord_id, period)
        return KPIRepository._version_cache.get(ver_key)

    @staticmethod
    def has_kpi_changed(landlord_id: int, period: str, kpi: KPIObject) -> bool:
        """Check nếu KPI đã thay đổi so với phiên cache trước"""
        current_hash = _compute_kpi_hash(kpi)
        cached_hash = KPIRepository.get_kpi_hash(landlord_id, period)
        if cached_hash is None:
            return True  # Chưa có cache → coi như changed
        return current_hash != cached_hash

    @staticmethod
    def get_kpi_version(landlord_id: int, period: str) -> int:
        """Lấy version integer (tăng dần mỗi lần set_kpi)"""
        return KPIRepository._int_version.get((landlord_id, period), 0)

    @staticmethod
    def is_kpi_stale(landlord_id: int, period: str, current_version: int) -> bool:
        """
        Check nếu version hiện tại (current_version) khác với version đã cache.
        Nếu current_version > cached_version → data đã thay đổi → stale.
        """
        cached_ver = KPIRepository.get_kpi_version(landlord_id, period)
        if cached_ver == 0:
            return True  # Chưa có cache
        return current_version > cached_ver


class AIReportCache:
    """AI Report Cache — lưu báo cáo đã sinh bởi Gemini
    
    Cache key format: ai:report:{landlord_id}:{period}:{version}
    Với version = SHA256 hash (e.g. "va1b2c3d4e5f6")
    
    Nếu version thay đổi → cache miss → regenerate report
    """

    @staticmethod
    def _make_versioned_key(landlord_id: int, period: str, version: str, dashboard: str = "overview") -> str:
        """Cache key format (theo design): {dashboard}:{period}:{version}"""
        return f"{AI_REPORT_PREFIX}:{dashboard}:{period}:{version}"

    @staticmethod
    def get_report(landlord_id: int, period: str, version: Optional[str] = None, dashboard: str = "overview") -> Optional[str]:
        """
        Lấy report từ cache với version check.
        Nếu không truyền version → dùng key cũ (backward compat).
        """
        if version:
            key = AIReportCache._make_versioned_key(landlord_id, period, version, dashboard)
            cached = _cache.get(key)
            if cached is not None:
                return cached
            # Fallback: thử key cũ (không version)
        key = _make_report_key(landlord_id, period)
        return _cache.get(key)

    @staticmethod
    def set_report(landlord_id: int, period: str, report: str, version: Optional[str] = None, dashboard: str = "overview") -> None:
        """
        Lưu report với version.
        Cache key: {dashboard}:{period}:{version}
        Luôn lưu cả key cũ (backward compat) và key mới (có version).
        """
        # Key cũ (luôn lưu để backward compat)
        old_key = _make_report_key(landlord_id, period)
        _cache.set(old_key, report)
        # Key mới có version, format: {dashboard}:{period}:{version}
        if version:
            new_key = AIReportCache._make_versioned_key(landlord_id, period, version, dashboard)
            _cache.set(new_key, report)
            log.debug("AI Report cached: %s | legacy: %s", new_key, old_key)
        else:
            log.debug("AI Report cached (legacy): %s", old_key)

    @staticmethod
    def invalidate_report(landlord_id: int, period: str) -> None:
        old_key = _make_report_key(landlord_id, period)
        _cache.delete(old_key)
        log.debug("AI Report cache invalidated: %s", old_key)

    @staticmethod
    def has_report(landlord_id: int, period: str, version: Optional[str] = None, dashboard: str = "overview") -> bool:
        """Check cache tồn tại với version"""
        if version:
            key = AIReportCache._make_versioned_key(landlord_id, period, version, dashboard)
            if _cache.exists(key):
                return True
        # Fallback: check key cũ
        key = _make_report_key(landlord_id, period)
        return _cache.exists(key)

    @staticmethod
    def is_valid(landlord_id: int, period: str, version: Optional[str] = None, dashboard: str = "overview") -> bool:
        """
        Check cache hợp lệ:
        - Nếu có version → check đúng version
        - Nếu không → check KPI hash có tồn tại không
        """
        if version:
            key = AIReportCache._make_versioned_key(landlord_id, period, version, dashboard)
            return _cache.exists(key)
        # Backward compat
        key = _make_report_key(landlord_id, period)
        if not _cache.exists(key):
            return False
        kpi_hash = KPIRepository.get_kpi_hash(landlord_id, period)
        return kpi_hash is not None


class AnalysisCache:
    """
    Analysis Cache — lưu Suggested Analysis results.
    TTL 1 giờ — tự động refresh khi hết hạn hoặc KPI thay đổi.
    
    Note: Analysis là rule-based (không LLM) nên compute lại rất rẻ.
    Cache chủ yếu để tránh recompute khi nhiều request đồng thời.
    """
    ANALYSIS_TTL = 3600  # 1 hour

    @staticmethod
    def get_analysis(landlord_id: int, period: str) -> Optional[list]:
        key = _make_analysis_key(landlord_id, period)
        return _cache.get(key)

    @staticmethod
    def set_analysis(landlord_id: int, period: str, analysis: list) -> None:
        key = _make_analysis_key(landlord_id, period)
        _cache.set(key, analysis, ttl=AnalysisCache.ANALYSIS_TTL)
        log.debug("Analysis cached: %s (%d items, TTL=%ds)", key, len(analysis), AnalysisCache.ANALYSIS_TTL)

    @staticmethod
    def invalidate_analysis(landlord_id: int, period: str) -> None:
        key = _make_analysis_key(landlord_id, period)
        _cache.delete(key)

    @staticmethod
    def has_analysis(landlord_id: int, period: str) -> bool:
        key = _make_analysis_key(landlord_id, period)
        return _cache.exists(key)


class SQLQueryCache:
    """
    LRU Cache cho Text-to-SQL: question → SQL
    
    - Giảm Gemini API calls: nếu câu hỏi tương tự đã được hỏi → dùng SQL cũ
    - Exact match + fuzzy match (Jaccard similarity trên word sets)
    - TTL: 30 phút
    - Max entries: 100
    - Track hit/miss/eviction stats
    
    Usage:
        cache = SQLQueryCache()
        sql = cache.get(question)      # None nếu miss
        cache.set(question, sql)        # Lưu vào cache
        cache.get_stats()               # Hit/miss/eviction stats
    """

    MAX_SIZE = 100
    TTL_SECONDS = 1800  # 30 phút
    _instance = None
    _SIMILARITY_THRESHOLD = 0.8  # Jaccard similarity threshold for fuzzy match

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        from collections import OrderedDict
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def normalize_question(question: str) -> str:
        """
        Normalize câu hỏi để làm key cache:
        - Lowercase
        - Loại bỏ dấu tiếng Việt
        - Loại bỏ khoảng trắng thừa, dấu câu
        """
        text = question.lower().strip()
        # Vietnamese diacritics map
        replacements = {
            'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a',
            'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'đ': 'd',
            'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
            'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
            'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
            'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
            'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        }
        for accented, plain in replacements.items():
            text = text.replace(accented, plain)
        import re
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _jaccard_similarity(words1: set, words2: set) -> float:
        """Tính Jaccard similarity giữa 2 sets of words"""
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    def get(self, question: str) -> Optional[str]:
        """
        Lấy cached SQL cho câu hỏi.
        - Exact match trước (O(1))
        - Fuzzy match sau (Jaccard similarity > threshold)
        Returns SQL string hoặc None nếu miss.
        """
        normalized = self.normalize_question(question)
        now = time.time()

        # === Step 1: Exact match ===
        if normalized in self._cache:
            entry = self._cache[normalized]
            if now - entry["created_at"] < self.TTL_SECONDS:
                self._cache.move_to_end(normalized)
                entry["hit_count"] += 1
                self._hits += 1
                log.debug("SQLQueryCache: EXACT hit for '%s' (hits=%d)", normalized[:30], entry["hit_count"])
                return entry["sql"]
            else:
                del self._cache[normalized]
                self._evictions += 1

        # === Step 2: Fuzzy match ===
        q_words = set(normalized.split())
        if len(q_words) >= 2:
            best_match = None
            best_score = 0.0
            for key, entry in list(self._cache.items()):
                if now - entry["created_at"] >= self.TTL_SECONDS:
                    del self._cache[key]
                    self._evictions += 1
                    continue
                key_words = set(key.split())
                score = self._jaccard_similarity(q_words, key_words)
                if score > best_score:
                    best_score = score
                    best_match = key

            if best_match and best_score >= self._SIMILARITY_THRESHOLD:
                entry = self._cache[best_match]
                self._cache.move_to_end(best_match)
                entry["hit_count"] += 1
                self._hits += 1
                log.debug("SQLQueryCache: FUZZY hit for '%s' (matched '%s', score=%.2f)",
                          normalized[:30], best_match[:30], best_score)
                return entry["sql"]

        self._misses += 1
        return None

    def set(self, question: str, sql: str):
        """Lưu cặp question → SQL vào cache"""
        normalized = self.normalize_question(question)
        now = time.time()

        if normalized in self._cache:
            entry = self._cache[normalized]
            entry["sql"] = sql
            entry["created_at"] = now
            entry["hit_count"] += 1
            self._cache.move_to_end(normalized)
            return

        # Evict LRU nếu cache đầy
        while len(self._cache) >= self.MAX_SIZE:
            self._cache.popitem(last=False)
            self._evictions += 1

        self._cache[normalized] = {
            "sql": sql,
            "created_at": now,
            "hit_count": 0,
        }
        log.debug("SQLQueryCache: Cached '%s' (size=%d)", normalized[:30], len(self._cache))

    def invalidate(self, question: Optional[str] = None):
        """Xóa cache: theo câu hỏi cụ thể hoặc toàn bộ"""
        if question:
            normalized = self.normalize_question(question)
            if normalized in self._cache:
                del self._cache[normalized]
                log.debug("SQLQueryCache: Invalidated '%s'", normalized[:30])
        else:
            self._cache.clear()
            log.debug("SQLQueryCache: Full invalidation")

    def get_stats(self) -> dict:
        """Trả về thống kê sử dụng cache"""
        total = self._hits + self._misses
        hit_rate = round(100.0 * self._hits / total, 1) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": hit_rate,
            "total_queries": total,
            "current_size": len(self._cache),
            "max_size": self.MAX_SIZE,
            "ttl_seconds": self.TTL_SECONDS,
        }


# Global singleton
sql_query_cache = SQLQueryCache()


class SessionStore:
    """Session Store cho AI Ask — TTL 30 phút + database persistence"""
    _session_cache = MemoryCache()

    @staticmethod
    def create_session(landlord_id: int) -> str:
        import uuid
        session_id = f"{landlord_id}:{uuid.uuid4().hex[:12]}"
        SessionStore._session_cache.set(session_id, [], SESSION_TTL_MINUTES * 60)
        return session_id

    @staticmethod
    def get_history(session_id: str) -> list:
        """
        Lấy lịch sử hội thoại từ in-memory cache.
        Sau restart server, history sẽ trống (client cần tạo session mới).
        Để load từ database, gọi SessionStore.load_history_async().
        """
        history = SessionStore._session_cache.get(session_id)
        if history is not None:
            # Refresh TTL
            SessionStore._session_cache.set(session_id, history, SESSION_TTL_MINUTES * 60)
            return history
        return []

    @staticmethod
    async def load_history_async(session_id: str) -> list:
        """
        Load lịch sử từ database (ai_chat_history table).
        Dùng khi in-memory không có (sau restart) — gọi từ async context.
        Kết quả được cache vào memory để lần sau nhanh hơn.
        """
        try:
            from database.connection import get_db
            db = await get_db()
            if not db or not db._pool:
                return []

            rows = await db.fetch(
                """SELECT question, ai_response, created_at
                   FROM ai_chat_history
                   WHERE session_id = $1
                   ORDER BY created_at ASC
                   LIMIT 10""",
                session_id
            )

            history = []
            for row in rows:
                question = row.get("question", "")
                reply = row.get("ai_response", "")
                ts = row.get("created_at", "")
                if question:
                    history.append({"role": "user", "content": question, "timestamp": ts})
                if reply:
                    history.append({"role": "assistant", "content": reply, "timestamp": ts})

            # Cache vào memory
            if history:
                SessionStore._session_cache.set(session_id, history, SESSION_TTL_MINUTES * 60)

            return history
        except Exception as e:
            log.warning("Failed to load session history from DB: %s", str(e)[:100])
            return []

    @staticmethod
    def add_turn(session_id: str, user_q: str, ai_reply: str) -> None:
        history = SessionStore._session_cache.get(session_id)
        if history is not None:
            now = datetime.now().isoformat()
            history.append({"role": "user", "content": user_q, "timestamp": now})
            history.append({"role": "assistant", "content": ai_reply, "timestamp": now})
            # Giữ tối đa 5 cặp Q&A (10 entries)
            if len(history) > 10:
                history[:] = history[-10:]
            SessionStore._session_cache.set(session_id, history, SESSION_TTL_MINUTES * 60)

    @staticmethod
    async def persist_turn(
        session_id: str,
        landlord_id: int,
        question: str,
        reply: str,
        db=None,
        sql_query: Optional[str] = None,
        sql_result: Optional[Any] = None,
        visualization: Optional[Any] = None,
        is_successful: bool = True,
        execution_time_ms: int = 0,
    ) -> None:
        """
        Persist một turn Q&A (user + AI) vào database table ai_chat_history.
        Fire-and-forget: log warning nếu fail, không raise exception.
        """
        try:
            if db is None:
                from database.connection import get_db
                db = await get_db()

            if not db or not db._pool:
                return

            # Serialize JSON fields — dùng CAST(%s AS JSON) để MySQL nhận string
            sql_result_str = None
            if sql_result:
                sql_result_str = json.dumps(sql_result, ensure_ascii=False, default=str)

            viz_str = None
            if visualization:
                viz_str = json.dumps(visualization, ensure_ascii=False, default=str)

            await db.execute(
                """INSERT INTO ai_chat_history
                   (landlord_id, session_id, question, sql_query, sql_result, ai_response, visualization, is_successful, execution_time_ms)
                   VALUES ($1, $2, $3, $4, CAST($5 AS JSON), $6, CAST($7 AS JSON), $8, $9)""",
                landlord_id,
                session_id,
                question[:5000],
                sql_query[:5000] if sql_query else None,
                sql_result_str,
                reply[:10000] if reply else None,
                viz_str,
                1 if is_successful else 0,
                execution_time_ms,
            )
        except Exception as e:
            log.warning("Failed to persist chat turn: %s", str(e)[:100])

    @staticmethod
    def format_history_for_context(session_id: str) -> str:
        history = SessionStore.get_history(session_id)
        if not history:
            return ""
        parts = []
        for entry in history[-6:]:  # Last 6 entries (3 turns)
            role = "Người dùng" if entry["role"] == "user" else "Trợ lý"
            parts.append(f"{role}: {entry['content']}")
        return "\n".join(parts)
