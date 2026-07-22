from typing import Optional
from fastapi import Depends, HTTPException, Query, Header
from config.settings import settings


async def get_landlord_id(
    landlord_id: int = Query(..., description="ID của chủ trọ", ge=1),
) -> int:
    return landlord_id


async def verify_landlord_access(
    landlord_id: int = Depends(get_landlord_id),
    x_landlord_id: Optional[str] = Header(None, alias="X-Landlord-ID"),
) -> int:
    if x_landlord_id and int(x_landlord_id) != landlord_id:
        raise HTTPException(
            status_code=403,
            detail="Landlord ID in header does not match query parameter"
        )
    return landlord_id


async def get_current_month() -> str:
    from datetime import date
    return date.today().strftime("%Y-%m")


async def parse_month_param(
    period: Optional[str] = Query(None, alias="period", pattern=r"^\d{4}-(?:0[1-9]|1[0-2])$", description="Tháng báo cáo (YYYY-MM)")
) -> str:
    if period:
        return period
    from datetime import date
    return date.today().strftime("%Y-%m")