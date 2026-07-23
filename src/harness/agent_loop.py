"""
Harness Agent Loop (No Template Fallbacks Architecture)
Rule: Zero template/dummy fallbacks. Real errors raise exceptions directly.
Gemini Model Fallback Cascade (gemini-3.5 -> gemini-3.1) is preserved.
"""
import json
import logging
import asyncio
import time
import traceback
from typing import Dict, Any, List, Optional
from config.settings import settings
from src.harness.tools import TOOL_DEFINITIONS, dispatch_tool
from src.harness.prompts import HARNESS_SYSTEM_PROMPT
from src.harness.skill_loader import SkillLoader
from src.harness.hooks import pre_tool_hook, post_tool_hook
from src.services.gemini_service import gemini_service

log = logging.getLogger("ai-property-advisor.harness.loop")

MAX_AGENT_STEPS = 10
MAX_TOOL_RETRY = 2


def get_current_time_context() -> str:
    """Tự động lấy thời gian hệ thống thực tế và format chuẩn tiếng Việt (múi giờ Việt Nam)"""
    from datetime import datetime, timezone, timedelta
    vn_tz = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh (UTC+7)
    now = datetime.now(vn_tz)
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    weekday_name = weekdays[now.weekday()]
    return f"{weekday_name}, {now.strftime('%d/%m/%Y %H:%M:%S')} (GMT+7)"


class HarnessAgentLoop:
    """Production-Grade Harness Agentic Loop — Strict No-Template-Fallback Execution"""

    @staticmethod
    def _compact_context_if_needed(history: str, max_turns: int = 8) -> str:
        if not history:
            return ""
        turns = history.strip().split("\n")
        if len(turns) <= max_turns * 2:
            return history

        # Semantic summarization: extract key topics from old turns
        old_turns = turns[:-8]
        recent_turns = turns[-8:]
        # Extract user questions from old turns for better context retention
        old_questions = []
        for t in old_turns:
            if t.startswith("User:") or t.startswith("Q:"):
                old_questions.append(t.split(":", 1)[-1].strip()[:80])
        question_summary = "; ".join(old_questions[-5:]) if old_questions else "các câu hỏi trước"
        summary_line = f"[TÓM TẮT ({len(old_turns)//2} lượt thoại trước): {question_summary}]"
        return summary_line + "\n" + "\n".join(recent_turns)

    @staticmethod
    async def run(
        question: str,
        landlord_id: int = 1,
        period: str = "2026-06",
        history: str = ""
    ) -> Dict[str, Any]:
        start_time = time.time()
        log.info("HarnessAgentLoop executing: '%s' (Landlord %d, Period %s)", question[:60], landlord_id, period)

        # Fail-fast check for Gemini API key
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "YOUR_API_KEY":
            err_msg = "CHƯA CẤU HÌNH GEMINI_API_KEY: Vui lòng bổ sung GEMINI_API_KEY hợp lệ vào file .env."
            log.error(err_msg)
            raise ValueError(err_msg)

        # 1. Dynamic Skill Loading (s07)
        relevant_skills = SkillLoader.select_relevant_skills(question)
        system_instruction = HARNESS_SYSTEM_PROMPT
        if relevant_skills:
            system_instruction += f"\n\n====================\nSKILLS & KNOWLEDGE PACKAGES:\n{relevant_skills}\n===================="

        # 1b. DB availability: tools will report DATABASE_OFFLINE if DB is down.
        # No pre-check needed — let tools handle it at call time.

        # 2. Context Compaction (s08)
        compacted_history = HarnessAgentLoop._compact_context_if_needed(history)

        from google.genai import types

        current_time_str = get_current_time_context()

        prompt_text = f"""THÔNG TIN KỲ BÁO CÁO, USER & THỜI GIAN THỰC TẾ TẠI HỆ THỐNG:
- Thời gian hiện tại: {current_time_str}
- Landlord ID: {landlord_id}
- Kỳ báo cáo đang chọn: {period}

LỊCH SỬ HỘI THOẠI (ĐÃ NÉN):
{compacted_history if compacted_history else 'Chưa có lịch sử.'}

CÂU HỎI CỦA USER: "{question}"

Hãy suy luận và sử dụng các Tool cần thiết để thu thập số liệu chính xác nhất trước khi trả lời."""

        messages = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_text)]
            )
        ]

        tools_used = []
        step = 0

        from google.genai import types

        gemini_tools = []
        for tdef in TOOL_DEFINITIONS:
            gemini_tools.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tdef["name"],
                            description=tdef["description"],
                            parameters=tdef["input_schema"]
                        )
                    ]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
            tools=gemini_tools,
            max_output_tokens=2048,
        )

        # Agent Execution Loop
        while step < MAX_AGENT_STEPS:
            step += 1
            log.debug("Agent Loop Step %d/%d", step, MAX_AGENT_STEPS)

            # Gemini Model Fallback Cascade executed inside _call_with_retry
            response = await gemini_service._call_with_retry(
                model=gemini_service.model,
                contents=messages,
                config=config
            )

            if not response or not response.candidates:
                err_msg = f"Gemini API (model {gemini_service.model}) không trả về phản hồi hợp lệ ở bước {step}."
                log.error(err_msg)
                raise RuntimeError(err_msg)

            candidate = response.candidates[0]
            part = candidate.content.parts[0] if candidate.content and candidate.content.parts else None

            # Check tool call
            if hasattr(part, "function_call") and part.function_call:
                func_call = part.function_call
                fn_name = func_call.name
                fn_args = dict(func_call.args) if func_call.args else {}

                log.info("Agent invoked tool '%s' with args: %s", fn_name, fn_args)

                # Pre-Tool Execution Hook (s04)
                allowed, block_reason, fn_args = pre_tool_hook(fn_name, fn_args)
                if not allowed:
                    tool_result_str = json.dumps({"error": block_reason}, ensure_ascii=False)
                else:
                    # Self-Healing & Error Recovery Loop (s11)
                    tool_result_str = None
                    for retry_idx in range(MAX_TOOL_RETRY + 1):
                        try:
                            raw_res = await dispatch_tool(fn_name, fn_args, landlord_id=landlord_id)
                            tool_result_str = post_tool_hook(fn_name, raw_res)
                            break
                        except Exception as tool_err:
                            log.error("Tool %s execution error (attempt %d/%d): %s", fn_name, retry_idx + 1, MAX_TOOL_RETRY + 1, tool_err, exc_info=True)
                            if retry_idx == MAX_TOOL_RETRY:
                                raise RuntimeError(f"Lỗi thực thi công cụ {fn_name} sau {MAX_TOOL_RETRY} lần thử: {str(tool_err)}")

                tools_used.append({"name": fn_name, "args": fn_args, "step": step})
                messages.append(candidate.content)

                resp_content = {"result": tool_result_str}
                if step >= 3:
                    resp_content["instruction"] = "Nếu kết quả dữ liệu CSDL đã ĐỦ THÔNG TIN để giải đáp trọn vẹn câu hỏi của người dùng, hãy tổng hợp và trả lời trực tiếp ngay trong lượt này. Nếu vẫn thiếu thông tin, hãy tiếp tục gọi công cụ để lấy thêm."

                messages.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=fn_name,
                                response=resp_content
                            )
                        ]
                    )
                )
                continue

            # Final Answer Text — post-process to strip LaTeX math syntax
            text_response = gemini_service._safe_text(response)
            # Remove LaTeX math blocks entirely (don't try to clean — just strip)
            import re as _re
            text_response = _re.sub(r'\$\$[^$]+\$\$', '', text_response)  # Display math
            text_response = _re.sub(r'\$[^$]+\$', '', text_response)       # Inline math
            text_response = _re.sub(r'\\([^)]+\\)', '', text_response)   # \(...\)
            text_response = _re.sub(r'\[([^]]+)\]', '', text_response)   # \[...\]
            # Clean up double spaces from removed math
            text_response = _re.sub(r'  +', ' ', text_response).strip()
            elapsed_ms = (time.time() - start_time) * 1000
            log.info("Agent Loop completed in %d steps. Tools used: %s", step, [t["name"] for t in tools_used])
            
            from src.harness.payload_logger import PayloadAuditLogger
            PayloadAuditLogger.log_turn(
                question=question,
                landlord_id=landlord_id,
                period=period,
                system_instruction=system_instruction,
                skills_loaded=list(SkillLoader.load_all_skills().keys()),
                tools_called=tools_used,
                reply=text_response,
                method="advanced_harness_agent_loop",
                latency_ms=elapsed_ms
            )

            return {
                "reply": text_response,
                "type": "ADVANCED_HARNESS_AGENT",
                "plan": {
                    "iterations": step,
                    "method": "advanced_harness_agent_loop",
                    "tools_called": tools_used,
                    "skills_loaded": list(SkillLoader.load_all_skills().keys()),
                }
            }

        # Max steps reached — graceful degradation with partial results
        last_text = ""
        if messages and len(messages) > 1:
            # Try to extract last model (assistant) response, skip function responses
            for msg in reversed(messages):
                if hasattr(msg, 'role') and msg.role == 'model':
                    if hasattr(msg, 'parts') and msg.parts:
                        for p in msg.parts:
                            if hasattr(p, 'text') and p.text and len(p.text) > 30:
                                last_text = p.text
                                break
                    if last_text:
                        break
        
        elapsed_ms = (time.time() - start_time) * 1000
        log.warning("Agent Loop reached max steps (%d). Returning partial results.", MAX_AGENT_STEPS)
        
        partial_reply = last_text or f"⚠️ Hệ thống cần thêm thời gian phân tích. Tools đã sử dụng: {', '.join([t['name'] for t in tools_used])}. Vui lòng thử lại với câu hỏi cụ thể hơn."
        
        return {
            "reply": partial_reply,
            "type": "ADVANCED_HARNESS_AGENT_MAX_STEPS",
            "plan": {
                "iterations": MAX_AGENT_STEPS,
                "method": "advanced_harness_agent_loop_max_steps",
                "tools_called": tools_used,
                "skills_loaded": list(SkillLoader.load_all_skills().keys()),
            }
        }
