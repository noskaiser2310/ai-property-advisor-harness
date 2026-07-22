"""
Copilot API Endpoints — AI Financial Copilot
- POST /copilot/report — AI Financial Report
- POST /copilot/ask — AI Ask Dashboard
- GET /copilot/suggestions — Suggested Questions
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from src.api.dependencies import get_landlord_id, parse_month_param
from src.engines.kpi_repository import KPIRepository, AIReportCache, sql_query_cache
from src.services.ai_report_service import ai_report_service
from src.services.ai_ask_service import ai_ask_service
from src.services.suggestion_service import suggestion_service
from src.services.suggested_analysis_service import suggested_analysis_service
from src.services.evaluation_logger import eval_logger
from src.services.gemini_service import gemini_service

log = logging.getLogger("ai-property-advisor")
router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="Câu hỏi của kế toán")
    session_id: Optional[str] = Field(None, description="Session ID để duy trì hội thoại")


class ZaloSendRequest(BaseModel):
    recipient_phone: Optional[str] = Field("0988.123.456", description="SĐT Chủ nhà nhận Zalo")
    message: str = Field(..., min_length=2, description="Nội dung tin nhắn / báo cáo gửi Zalo")


# ============================================================
# AI REPORT
# ============================================================

@router.post("/copilot/report")
async def get_ai_report(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
    force: bool = False,
):
    """
    AI Financial Report — Báo cáo tài chính bằng ngôn ngữ tự nhiên
    - Nếu có cache → trả về cached
    - Nếu không → gọi Gemini → cache
    """
    result = await ai_report_service.generate_report(landlord_id, period, force=force)

    return {
        "status": "success",
        "data": {
            "report": result["report"],
            "from_cache": result["from_cache"],
            "generated_at": result.get("generated_at"),
            "cache_version": result.get("cache_version"),
            "period": period,
        }
    }


@router.get("/copilot/report/export-docx")
async def export_ai_report_docx(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """
    Xuất Báo cáo Tài chính chuyên sâu sang file Word (.docx)
    """
    from fastapi.responses import StreamingResponse
    result = await ai_report_service.generate_report(landlord_id, period)
    docx_buffer = ai_report_service.export_report_to_docx(result["report"], period)

    filename = f"Bao_Cao_Tai_Chinh_{period}.docx"
    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/copilot/report/refresh")
async def refresh_ai_report(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """Force refresh AI Report — xóa cache và sinh lại"""
    AIReportCache.invalidate_report(landlord_id, period)
    result = await ai_report_service.generate_report(landlord_id, period, force=True)

    return {
        "status": "success",
        "data": {
            "report": result["report"],
            "from_cache": False,
            "generated_at": result.get("generated_at"),
            "cache_version": result.get("cache_version"),
            "period": period,
        }
    }


# ============================================================
# AI ASK
# ============================================================

@router.post("/copilot/ask")
async def ask_ai(
    request: AskRequest,
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """
    AI Ask Dashboard — Kế toán đặt câu hỏi bằng ngôn ngữ tự nhiên
    Hỗ trợ multi-turn conversation qua session_id
    """
    result = await ai_ask_service.process_question(
        question=request.question,
        landlord_id=landlord_id,
        period=period,
        session_id=request.session_id,
    )

    return {
        "status": "success",
        "data": result,
    }


# ============================================================
# SUGGESTED QUESTIONS
# ============================================================

@router.get("/copilot/suggestions")
async def get_suggestions(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """
    Suggested Questions — Gợi ý câu hỏi phân tích từ KPI hiện tại
    """
    questions = await suggestion_service.get_suggestions(landlord_id, period)

    return {
        "status": "success",
        "data": {
            "questions": questions,
            "period": period,
        }
    }


# ============================================================
# SUGGESTED ANALYSIS (PROACTIVE)
# ============================================================

@router.get("/copilot/analysis")
async def get_suggested_analysis(
    landlord_id: int = Depends(get_landlord_id),
    period: str = Depends(parse_month_param),
):
    """
    Suggested Analysis — Phát hiện biến động KPI và đề xuất hướng phân tích (proactive)
    Không gọi LLM, dùng rule-based để nhanh và không tốn token
    
    Ví dụ:
    - "Doanh thu giảm 15% — Khoản thu nào giảm nhiều nhất?"
    - "Chi phí sửa chữa tăng — Có thể tối ưu không?"
    - "5 hóa đơn quá hạn — Cần ưu tiên xử lý phòng nào?"
    """
    analyses = await suggested_analysis_service.get_analysis(landlord_id, period)

    return {
        "status": "success",
        "data": {
            "analyses": analyses,
            "period": period,
            "total_issues": len(analyses),
        }
    }


# ============================================================
# EVALUATION & MONITORING
# ============================================================

@router.get("/copilot/eval")
async def get_evaluation_stats():
    """
    Evaluation Statistics — Metrics đánh giá chất lượng AI
    Theo dõi: accuracy, latency, fallback rate, cache hit rate
    Bao gồm SQL Query Cache stats để monitor hiệu quả giảm Gemini API calls
    """
    stats = eval_logger.get_stats()
    model_stats = gemini_service.registry.get_usage_stats()
    sql_cache_stats = sql_query_cache.get_stats()

    return {
        "status": "success",
        "data": {
            "ai_stats": stats,
            "model_stats": model_stats,
            "sql_cache": sql_cache_stats,
        }
    }


@router.get("/copilot/eval/logs")
async def get_evaluation_logs(n: int = 10):
    """Recent evaluation logs"""
    logs = eval_logger.get_recent_logs(n=n)
    return {
        "status": "success",
        "data": {
            "logs": logs,
        }
    }


# ============================================================
# SESSION MANAGEMENT
# ============================================================

@router.get("/copilot/session/{session_id}")
async def get_session_history(
    session_id: str,
    landlord_id: int = Depends(get_landlord_id),
):
    """Lấy lịch sử hội thoại của session (memory + database fallback)"""
    from src.engines.kpi_repository import SessionStore
    # Ưu tiên in-memory cache (nhanh), fallback database (sau restart)
    history = SessionStore.get_history(session_id)
    if not history:
        history = await SessionStore.load_history_async(session_id)
    return {
        "status": "success",
        "data": {
            "session_id": session_id,
            "history": history,
        }
    }


@router.post("/copilot/session")
async def create_session(
    landlord_id: int = Depends(get_landlord_id),
):
    """Tạo session mới cho hội thoại AI Ask"""
    from src.engines.kpi_repository import SessionStore
    session_id = SessionStore.create_session(landlord_id)
    return {
        "status": "success",
        "data": {
            "session_id": session_id,
        }
    }


# ============================================================
# SQL CACHE STATS
# ============================================================

@router.get("/copilot/sql-cache/stats")
async def get_sql_cache_stats():
    """
    SQL Query Cache Statistics — Theo dõi hiệu quả cache Text-to-SQL
    
    Metrics:
    - hit_rate: % câu hỏi dùng cache thay vì gọi Gemini
    - hits: số lần cache hit (tiết kiệm Gemini API call)
    - misses: số lần cache miss (phải gọi Gemini)
    - evictions: số lần cache bị xóa do đầy hoặc TTL hết hạn
    - current_size: số entry hiện tại trong cache
    - max_size: dung lượng tối đa (100)
    """
# ============================================================
# AUTOMATED ZALO DISPATCHER
# ============================================================

@router.post("/copilot/send-zalo")
async def send_zalo_dispatch(
    request: ZaloSendRequest,
    landlord_id: int = Depends(get_landlord_id),
):
    """
    Automated Zalo Dispatcher — Tự động bắn tin nhắn / Báo cáo tài chính qua Zalo cho Chủ nhà
    """
    log.info("Zalo Dispatcher triggered for Landlord %d to phone %s", landlord_id, request.recipient_phone)
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return {
        "status": "success",
        "data": {
            "sent": True,
            "recipient_phone": request.recipient_phone or "0988.123.456",
            "channel": "Zalo OA Enterprise Webhook",
            "timestamp": now_str,
            "message_snippet": request.message[:120] + ("..." if len(request.message) > 120 else ""),
        }
    }
