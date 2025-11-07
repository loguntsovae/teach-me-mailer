import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict

import structlog

from app.core.config import Settings


logger = structlog.get_logger(__name__)


class RateLimitService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.requests: Dict[str, list] = defaultdict(list)

    async def check_daily_limit(self, api_key: str, email_count: int = 1) -> bool:
        """Check if API key is within daily email limits."""
        now = datetime.utcnow()
        
        # Clean old requests
        await self._cleanup_old_requests(api_key, now)
        
        # Get recent requests within the rate window
        window_start = now - timedelta(days=self.settings.rate_window_days)
        recent_requests = [req for req in self.requests[api_key] if req > window_start]
        
        # Check if adding new emails would exceed daily limit
        if len(recent_requests) + email_count > self.settings.default_daily_limit:
            logger.warning(
                "Daily rate limit exceeded",
                api_key=api_key[:8] + "...",
                current_count=len(recent_requests),
                requested_count=email_count,
                limit=self.settings.default_daily_limit,
                window_days=self.settings.rate_window_days,
            )
            return False
        
        return True

    async def record_emails(self, api_key: str, email_count: int) -> None:
        """Record email sends for rate limiting."""
        now = datetime.utcnow()
        
        # Add one entry per email sent
        for _ in range(email_count):
            self.requests[api_key].append(now)
        
        logger.debug(
            "Emails recorded for rate limiting",
            api_key=api_key[:8] + "...",
            count=email_count,
            timestamp=now.isoformat(),
        )

    async def _cleanup_old_requests(self, api_key: str, now: datetime) -> None:
        """Remove requests older than the rate window."""
        window_start = now - timedelta(days=self.settings.rate_window_days)
        self.requests[api_key] = [
            req for req in self.requests[api_key] if req > window_start
        ]

    async def get_remaining_quota(self, api_key: str) -> Dict[str, int]:
        """Get remaining email quota for an API key."""
        now = datetime.utcnow()
        await self._cleanup_old_requests(api_key, now)
        
        # Count emails in current window
        window_start = now - timedelta(days=self.settings.rate_window_days)
        used_emails = len([req for req in self.requests[api_key] if req > window_start])
        
        remaining = max(0, self.settings.default_daily_limit - used_emails)
        
        return {
            "remaining": remaining,
            "used": used_emails,
            "limit": self.settings.default_daily_limit,
            "window_days": self.settings.rate_window_days,
            "resets_at": (window_start + timedelta(days=self.settings.rate_window_days)).isoformat(),
        }