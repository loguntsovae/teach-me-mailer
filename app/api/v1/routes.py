from datetime import datetime
from typing import List
import uuid
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.deps import get_db, get_current_api_key, get_settings_dependency
from app.core.config import Settings
from app.models.api_key import APIKey
from app.schemas.mail import MailRequest, MailResponse, HealthResponse
from app.services.mailer import MailerService
from app.services.atomic_rate_limit import AtomicRateLimitService
from app.services.email_queue import EmailQueueService


logger = structlog.get_logger(__name__)
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


@router.post("/send", response_model=MailResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_mail(
    request: MailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key),
    settings: Settings = Depends(get_settings_dependency)
) -> MailResponse:
    """Send email with atomic rate limiting and background processing."""
    
    logger.info("Send mail request", 
               api_key_id=str(api_key.id),
               recipient=str(request.to),
               subject=request.subject[:50])
    
    # Single recipient count for this request
    email_count = 1
    
    # Initialize services
    atomic_rate_limiter = AtomicRateLimitService(db, settings)
    email_queue = EmailQueueService(db, settings)
    
    # Step 1: Atomic rate limit check
    try:
        rate_check_result = await atomic_rate_limiter.check_and_increment_rate_limit(
            api_key_id=api_key.id,
            email_count=email_count
        )
    except Exception as e:
        logger.error("Rate limit check failed", 
                    api_key_id=str(api_key.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rate limit check failed"
        )
    
    if not rate_check_result.allowed:
        # Calculate retry-after header (seconds until tomorrow)
        retry_after_seconds = rate_check_result.retry_after_seconds
        
        logger.warning("Rate limit exceeded",
                      api_key_id=str(api_key.id),
                      current_count=rate_check_result.current_count,
                      daily_limit=api_key.daily_limit,
                      retry_after_seconds=retry_after_seconds)
        
        # Add Retry-After header for 429 response
        response = Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        response.headers["Retry-After"] = str(retry_after_seconds)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily email limit exceeded. Current: {rate_check_result.current_count}, "
                   f"Limit: {api_key.daily_limit}. Try again in {retry_after_seconds} seconds.",
            headers={"Retry-After": str(retry_after_seconds)}
        )
    
    # Step 2: Create SendLog entry immediately with null message_id
    try:
        log_id = await email_queue.create_send_log(
            api_key_id=api_key.id,
            recipient=str(request.to)
        )
        await db.commit()  # Commit the send log creation
        
        logger.info("SendLog created",
                   log_id=log_id,
                   api_key_id=str(api_key.id),
                   recipient=str(request.to))
        
    except Exception as e:
        logger.error("Failed to create send log",
                    api_key_id=str(api_key.id),
                    error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create send log"
        )
    
    # Step 3: Enqueue email sending as background task
    background_tasks.add_task(
        email_queue.send_email_background,
        log_id=log_id,
        to=str(request.to),
        subject=request.subject,
        html=request.html,
        text=request.text,
        headers=request.headers
    )
    
    # Calculate remaining emails for response
    remaining = api_key.daily_limit - (rate_check_result.current_count + email_count)
    
    logger.info("Email queued successfully",
               log_id=log_id,
               api_key_id=str(api_key.id),
               remaining=remaining)
    
    # Step 4: Return 202 Accepted with status and remaining count
    return MailResponse(
        status="queued",
        remaining=remaining
    )


@router.get("/usage", response_model=dict)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key),
    settings: Settings = Depends(get_settings_dependency)
) -> dict:
    """Get current usage statistics for the API key."""
    
    logger.info("Usage request", api_key_id=str(api_key.id))
    
    # Use the atomic rate limiter to get current usage (with 0 increment)
    atomic_rate_limiter = AtomicRateLimitService(db, settings)
    
    try:
        # Check current usage without incrementing (0 email count)
        rate_check_result = await atomic_rate_limiter.check_and_increment_rate_limit(
            api_key_id=api_key.id,
            email_count=0
        )
        
        return {
            "api_key_id": str(api_key.id),
            "daily_limit": api_key.daily_limit,
            "emails_sent_today": rate_check_result.current_count,
            "emails_remaining": max(0, api_key.daily_limit - rate_check_result.current_count),
            "reset_time": rate_check_result.reset_time.isoformat() if rate_check_result.reset_time else None
        }
    
    except Exception as e:
        logger.error("Failed to get usage statistics",
                    api_key_id=str(api_key.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


@router.get("/debug-sentry")
async def debug_sentry():
    """
    Debug endpoint to test Sentry error capture.
    
    This endpoint intentionally raises an exception to verify that Sentry
    is properly configured and can capture errors from the FastAPI application.
    """
    logger.info("Testing Sentry error capture")
    
    # Intentionally raise an exception to test Sentry integration
    raise Exception("Test exception for Sentry error tracking - this is intentional!")