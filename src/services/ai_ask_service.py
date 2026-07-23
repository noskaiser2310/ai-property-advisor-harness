"""
AI Ask Dashboard Service — Kế toán đặt câu hỏi bằng ngôn ngữ tự nhiên
Xử lý câu hỏi qua Harness Agentic Reasoning Loop (CSDL 61 bảng MySQL Live)
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List

from src.schemas.kpi_schema import KPIObject
from src.engines.kpi_repository import KPIRepository, SessionStore
from src.services.evaluation_logger import eval_logger
from database.connection import get_db

log = logging.getLogger("ai-property-advisor")


async def _resolve_property_id(landlord_id: int, db) -> Optional[int]:
    """Map landlord_id (user_id) sang property_id."""
    try:
        row = await db.fetchrow(
            """SELECT property_id FROM property_staff_assignments 
               WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE' 
               LIMIT 1""",
            landlord_id
        )
        if row:
            return row.get("property_id")
        row = await db.fetchrow(
            "SELECT property_id FROM properties WHERE deleted_at IS NULL LIMIT 1"
        )
        return row.get("property_id") if row else None
    except Exception as e:
        log.warning("Failed to resolve property_id for landlord %d: %s", landlord_id, e)
        return None


class AIAskService:
    """Service xử lý hỏi đáp cho Kế toán/Chủ nhà thông qua Harness Agent Loop"""

    # Out-of-domain rejection patterns (câu hỏi không liên quan đến nhà trọ/tài chính)
    # Patterns use unaccented Vietnamese for robust matching
    OUT_OF_DOMAIN_PATTERNS = [
        r'\b(chinh tri|bau cu|dang|cong san|ton giao|phat|chua|kito)\b',
        r'\b(hack|crack|exploit|inject|bypass|vuot tuong lua|ma doc|virus)\b',
        r'\b(boi toan|tu vi|phong thuy|xem tay|xem chi tay|cung|bua|ngai)\b',
        r'\b(chat|tan gau|buon chuyen|hen ho|yeu duong|ban gai|ban trai|troi dep|hom nay|thoi tiet|hello|hi\b|xin chao|chao buoi)\b',
        r'\b(code|viet code|lap trinh app|game|website) ((?!sql|bao cao).)*$',
    ]
    DOMAIN_KEYWORDS = [
        'doanh thu', 'chi phi', 'loi nhuan', 'no', 'phong', 'hoa don',
        'bao cao', 'kpi', 'lap day', 'khach thue', 'cho thue', 'bao tri',
        'dien', 'nuoc', 'tien', 'hop dong', 'dong tien', 'tai chinh',
        'suc khoe', 'thang', 'ky', 'tro', 'nha tro', 'chu nha',
    ]

    @staticmethod
    def _strip_vietnamese_accents(text: str) -> str:
        """Strip Vietnamese diacritics for robust accent-insensitive matching"""
        replacements = {
            'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
            'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
            'đ': 'd', 'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
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
        return text

    @classmethod
    def is_out_of_domain(cls, question: str) -> bool:
        """Check if question is outside the property management domain"""
        import re
        # Strip accents for robust matching (users may type unaccented Vietnamese)
        q_normalized = cls._strip_vietnamese_accents(question.lower())
        # Use word-boundary matching to avoid false positives (e.g. "no" matching inside "nao")
        _domain_re = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in cls.DOMAIN_KEYWORDS) + r')\b'
        )
        if _domain_re.search(q_normalized):
            return False
        # If matches out-of-domain pattern → reject
        for pattern in cls.OUT_OF_DOMAIN_PATTERNS:
            if re.search(pattern, q_normalized):
                return True
        # If too short and no domain keywords → likely out of domain
        if len(question.strip()) < 2:
            return True
        return False

    @staticmethod
    async def process_question(
        question: str,
        landlord_id: int,
        period: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Xử lý câu hỏi của kế toán — Harness Agentic Reasoning Loop
        """
        with eval_logger.start(
            question=question,
            intent="ADVANCED_HARNESS_AGENT",
            landlord_id=landlord_id,
            period=period,
            session_id=session_id,
        ) as eval_ctx:
            # === STEP 0: Get KPI context + database connection ===
            kpi = KPIRepository.get_kpi(landlord_id, period)
            if kpi is None:
                from src.api.v1.kpi import _calculate_full_kpi
                kpi = await _calculate_full_kpi(landlord_id, period)

            db = None
            try:
                db = await get_db()
                await _resolve_property_id(landlord_id, db)
            except Exception as e:
                log.warning("Failed to get database connection: %s", e)

            # === STEP 0b: Session management ===
            if not session_id:
                session_id = SessionStore.create_session(landlord_id)
            history = SessionStore.format_history_for_context(session_id)

            # === STEP 1: Harness Agentic Reasoning Loop (with intent check) ===
            log.debug("process_question: starting Harness Agent Loop for '%s' (L%s, %s)", question[:50], landlord_id, period)
            
            # Intent check: reject out-of-domain questions
            if AIAskService.is_out_of_domain(question):
                eval_ctx.set_intent("OUT_OF_DOMAIN_REJECTED")
                eval_ctx.set_reply(
                    reply="Xin lỗi, tôi là AI Trợ lý Tài chính & Vận hành Nhà trọ. Tôi chỉ có thể trả lời các câu hỏi về doanh thu, chi phí, công nợ, tỉ lệ lấp đầy, bảo trì phòng trọ và các vấn đề vận hành nhà trọ. Vui lòng đặt câu hỏi liên quan.",
                    model_used="intent_filter", token_count=0, from_cache=True, fallback_used=False,
                )
                return {
                    "reply": "Xin lỗi, tôi là AI Trợ lý Tài chính & Vận hành Nhà trọ. Tôi chỉ có thể trả lời các câu hỏi về doanh thu, chi phí, công nợ, tỉ lệ lấp đầy, bảo trì phòng trọ và các vấn đề vận hành nhà trọ. Vui lòng đặt câu hỏi liên quan.",
                    "session_id": session_id or SessionStore.create_session(landlord_id),
                    "suggestions": [],
                    "type": "OUT_OF_DOMAIN",
                    "plan": {"method": "intent_filter_rejected"},
                }
            
            from src.harness.agent_loop import HarnessAgentLoop
            result = await HarnessAgentLoop.run(
                question=question,
                landlord_id=landlord_id,
                period=period,
                history=history,
            )

            qtype = result.get("type", "ADVANCED_HARNESS_AGENT")
            eval_ctx.set_intent(qtype)
            eval_ctx.set_reply(
                reply=result["reply"],
                model_used="multi-agent-template",
                token_count=0,
                from_cache=False,
                fallback_used=False,
            )

            # === STEP 2: Save to session (in-memory + database) ===
            SessionStore.add_turn(session_id, question, result["reply"])
            sql_q = None
            plan = result.get("plan")
            if isinstance(plan, dict):
                sql_q = plan.get("sql")

            asyncio.create_task(SessionStore.persist_turn(
                session_id=session_id,
                landlord_id=landlord_id,
                question=question,
                reply=result["reply"],
                db=db,
                sql_query=sql_q,
                is_successful=True,
            ))

            from src.services.suggestion_service import suggestion_service
            dynamic_suggestions = await suggestion_service.get_suggestions(landlord_id, period, kpi=kpi)

            return {
                "reply": result["reply"],
                "session_id": session_id,
                "suggestions": dynamic_suggestions[:4],
                "type": qtype,
                "plan": result.get("plan", {}),
            }


ai_ask_service = AIAskService()
