from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["system"])


@router.get("/health")
@router.get("/api/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "stock-reminder-backend",
        "environment": settings.app_env,
    }

