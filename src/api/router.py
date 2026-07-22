from fastapi import APIRouter
from src.api.v1 import kpi, copilot


router = APIRouter(prefix="/api/v1/advisor")

router.include_router(kpi.router, tags=["KPI Analytics"])
router.include_router(copilot.router, tags=["AI Copilot"])
