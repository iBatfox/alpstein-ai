from fastapi import APIRouter

from app.core.config import settings

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
