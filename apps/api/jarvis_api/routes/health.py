from fastapi import APIRouter

from apps.api.jarvis_api.schemas.health import HealthResponse
from core.runtime.settings import load_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = load_settings()
    return HealthResponse(
        ok=True,
        app=settings.app_name,
        environment=settings.environment,
    )
