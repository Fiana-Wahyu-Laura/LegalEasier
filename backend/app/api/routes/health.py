from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.common import StandardResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=StandardResponse)
async def health_check() -> StandardResponse:
    settings = get_settings()
    return StandardResponse(
        success=True,
        data={
            "status": "ok",
            "app_name": settings.app_name,
            "environment": settings.environment,
        },
        message="Service is healthy.",
    )


@router.get("/health/db", response_model=StandardResponse)
async def health_db_check(db: AsyncSession = Depends(get_db)) -> StandardResponse:
    try:
        await db.execute(text("SELECT 1"))
        return StandardResponse(
            success=True,
            data={"status": "ok", "database": "connected"},
            message="Database is reachable.",
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable",
        ) from error
