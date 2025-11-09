import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_current_api_key, get_db, get_settings_dependency
from app.models.api_key import APIKey
from app.services.atomic_rate_limit import AtomicRateLimitService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/usage", response_model=dict)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key),
    settings: Settings = Depends(get_settings_dependency),
) -> dict:
    """Get current usage statistics for the API key."""

    logger.info("Usage request", api_key_id=str(api_key.id))

    # Use the atomic rate limiter to get current usage (with 0 increment)
    atomic_rate_limiter = AtomicRateLimitService(db, settings)

    try:
        # Check current usage without incrementing (0 email count)
        rate_check_result = await atomic_rate_limiter.check_and_increment_rate_limit(
            api_key_id=api_key.id, email_count=0
        )

        # Use effective limit for arithmetic since API key daily_limit can be None
        effective_limit: int = (
            api_key.daily_limit
            if api_key.daily_limit is not None
            else settings.default_daily_limit
        )

        return {
            "api_key_id": str(api_key.id),
            "daily_limit": api_key.daily_limit,
            "emails_sent_today": rate_check_result.current_count,
            "emails_remaining": max(
                0, effective_limit - rate_check_result.current_count
            ),
            # Compute next reset using the service helper
            "reset_time": atomic_rate_limiter._get_next_midnight_utc().isoformat(),
        }

    except Exception as e:
        logger.error(
            "Failed to get usage statistics", api_key_id=str(api_key.id), error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics",
        )
