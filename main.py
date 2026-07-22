import time
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from config.settings import settings
from database.connection import init_db, close_db
from src.api.router import router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-property-advisor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Property Advisor v3.0 (MySQL)...")
    await init_db()
    logger.info("Database initialized (MySQL)")
    yield
    await close_db()
    logger.info("Database closed. Shutdown complete.")


app = FastAPI(
    title="AI Property Advisor - Financial Copilot (MySQL)",
    description="Hệ thống báo cáo tài chính nhà trọ trên MySQL — KPI Dashboard + AI Copilot",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    logger.info("%s %s -> %d (%.3fs)", request.method, request.url.path, response.status_code, duration)
    return response


# Rate limit middleware (cho AI endpoints — copilot/*)
from src.engines.rate_limiter import rate_limit_middleware
app.middleware("http")(rate_limit_middleware)

app.include_router(router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/ui", response_class=HTMLResponse)
@app.get("/test", response_class=HTMLResponse)
async def test_ui():
    html_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(html_path):
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-property-advisor", "version": "3.0.0", "db": "mysql"}


@app.get("/")
async def root():
    return {
        "service": "AI Property Advisor - Financial Copilot",
        "version": "3.0.0",
        "database": "MySQL (SE Group Schema)",
        "docs": "/docs",
        "dashboard": "/ui",
        "endpoints": {
            "kpi_overview": "GET /api/v1/advisor/kpi/overview",
            "kpi_revenue": "GET /api/v1/advisor/kpi/revenue",
            "kpi_expense": "GET /api/v1/advisor/kpi/expense",
            "kpi_debt": "GET /api/v1/advisor/kpi/debt",
            "kpi_occupancy": "GET /api/v1/advisor/kpi/occupancy",
            "kpi_export": "GET /api/v1/advisor/kpi/export",
            "copilot_report": "POST /api/v1/advisor/copilot/report",
            "copilot_ask": "POST /api/v1/advisor/copilot/ask",
            "copilot_suggestions": "GET /api/v1/advisor/copilot/suggestions",
            "copilot_session": "POST /api/v1/advisor/copilot/session",
        },
    }
