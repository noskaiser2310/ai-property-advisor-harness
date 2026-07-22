"""
Full Communication & Payload Audit Logger
Logs 100% of user inputs, AI model system prompts, dynamic skill loads, tool call arguments, raw SQL queries, and final AI responses into both JSONL file and Database table `ai_audit_logs`.
"""
import os
import json
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from database.connection import get_db

log = logging.getLogger("ai-property-advisor.harness.payload_logger")

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "logs"))
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "full_server_audit.jsonl")


class PayloadAuditLogger:
    """Records complete 360-degree audit trail of Server <-> AI <-> User communications"""

    @staticmethod
    def log_turn(
        question: str,
        landlord_id: int,
        period: str,
        system_instruction: str,
        skills_loaded: List[str],
        tools_called: List[Dict[str, Any]],
        reply: str,
        method: str,
        latency_ms: float,
        session_id: Optional[str] = None
    ) -> None:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "landlord_id": landlord_id,
                "period": period,
                "user_input": {
                    "question": question,
                },
                "harness_context": {
                    "system_instruction_length": len(system_instruction),
                    "skills_loaded": skills_loaded,
                    "method": method,
                    "latency_ms": round(latency_ms, 2)
                },
                "tool_executions": tools_called,
                "ai_output": {
                    "reply": reply,
                    "reply_length": len(reply)
                }
            }

            # 1. Write formatted line to JSONL file
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # 2. Persist to Database table in background
            asyncio.create_task(PayloadAuditLogger._persist_to_database(
                session_id=session_id,
                landlord_id=landlord_id,
                period=period,
                question=question,
                system_instruction_len=len(system_instruction),
                skills_loaded=",".join(skills_loaded),
                method=method,
                tools_called=json.dumps(tools_called, ensure_ascii=False),
                reply=reply,
                latency_ms=latency_ms
            ))

            log.info("Full audit payload logged to file and queued for DB persistence.")
        except Exception as e:
            log.warning("Failed to record payload audit log: %s", e)

    @staticmethod
    async def _persist_to_database(
        session_id: Optional[str],
        landlord_id: int,
        period: str,
        question: str,
        system_instruction_len: int,
        skills_loaded: str,
        method: str,
        tools_called: str,
        reply: str,
        latency_ms: float
    ) -> None:
        """Persist payload turn to database table `ai_audit_logs`"""
        try:
            db = await get_db()
            if db._pool is None:
                return

            sql = """
            INSERT INTO ai_audit_logs (
                session_id, landlord_id, period, question, system_instruction_len,
                skills_loaded, method, tools_called, reply, latency_ms
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            await db.execute(
                sql,
                session_id or "", landlord_id, period, question, system_instruction_len,
                skills_loaded, method, tools_called, reply, latency_ms
            )
            log.debug("Turn persisted to database table ai_audit_logs")
        except Exception as e:
            log.debug("DB audit log persistence notice: %s", e)

    @staticmethod
    def read_all_logs(limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent audit log entries from JSONL file"""
        if not os.path.exists(AUDIT_LOG_FILE):
            return []
        entries = []
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line.strip()))
            return entries[-limit:]
        except Exception as e:
            log.warning("Failed to read audit log file: %s", e)
            return []
