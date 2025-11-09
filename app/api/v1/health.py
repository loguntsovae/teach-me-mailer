from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.core.deps import get_settings_dependency
from app.schemas.mail import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings_dependency),
) -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
    )
