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

            # === STEP 1: Harness Agentic Reasoning Loop ===
            log.debug("process_question: starting Harness Agent Loop for '%s' (L%s, %s)", question[:50], landlord_id, period)
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
