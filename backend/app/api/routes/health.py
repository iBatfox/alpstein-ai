from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {
        "success": True,
        "data": {
            "status": "ok",
            "service": settings.service_name,
            "environment": settings.environment,
        },
    }


@router.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_db_session)) -> dict:
    """
    Readiness check for orchestrated startup.

    Must verify PostgreSQL connectivity with a simple `SELECT 1` query only.
    Must not have any side effects.
    """
    try:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar_one_or_none()
        if value != 1:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "DATABASE_ERROR",
                        "message": "PostgreSQL readiness check failed",
                    },
                },
            )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "PostgreSQL is not reachable",
                },
            },
        )

    return {
        "success": True,
        "data": {
            "status": "ready",
            "service": settings.service_name,
            "environment": settings.environment,
            "db": "reachable",
        },
    }
