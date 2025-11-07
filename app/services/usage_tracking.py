from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

import structlog

from app.core.config import Settings
from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.models.send_log import SendLog


logger = structlog.get_logger(__name__)


class UsageTrackingService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def get_daily_limit(self, api_key_id: uuid.UUID) -> int:
        """Get the daily limit for an API key."""
        try:
            stmt = select(APIKey.daily_limit).where(APIKey.id == api_key_id)
            result = await self.db.execute(stmt)
            daily_limit = result.scalar_one_or_none()
            
            # Use API key specific limit or default from settings
            return daily_limit if daily_limit is not None else self.settings.default_daily_limit
            
        except Exception as e:
            logger.error("Error getting daily limit", api_key_id=str(api_key_id), error=str(e))
            return self.settings.default_daily_limit

    async def get_usage_for_day(self, api_key_id: uuid.UUID, day: date) -> int:
        """Get email count for a specific day."""
        try:
            stmt = select(DailyUsage.count).where(
                DailyUsage.api_key_id == api_key_id,
                DailyUsage.day == day
            )
            result = await self.db.execute(stmt)
            count = result.scalar_one_or_none()
            return count if count is not None else 0
            
        except Exception as e:
            logger.error("Error getting daily usage", api_key_id=str(api_key_id), day=day, error=str(e))
            return 0

    async def check_daily_limit(self, api_key_id: uuid.UUID, email_count: int = 1) -> bool:
        """Check if sending emails would exceed daily limit."""
        today = date.today()
        current_usage = await self.get_usage_for_day(api_key_id, today)
        daily_limit = await self.get_daily_limit(api_key_id)
        
        would_exceed = (current_usage + email_count) > daily_limit
        
        if would_exceed:
            logger.warning(
                "Daily limit would be exceeded",
                api_key_id=str(api_key_id),
                current_usage=current_usage,
                requested=email_count,
                daily_limit=daily_limit,
            )
        
        return not would_exceed

    async def record_email_sends(self, api_key_id: uuid.UUID, recipients: list[str], message_id: Optional[str] = None) -> None:
        """Record email sends in both send log and daily usage."""
        sent_at = datetime.utcnow()
        today = date.today()
        email_count = len(recipients)
        
        try:
            # Record individual send logs
            for recipient in recipients:
                send_log = SendLog(
                    api_key_id=api_key_id,
                    sent_at=sent_at,
                    recipient=recipient,
                    message_id=message_id,
                )
                self.db.add(send_log)
            
            # Update daily usage using upsert
            stmt = insert(DailyUsage).values(
                api_key_id=api_key_id,
                day=today,
                count=email_count
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uq_daily_usage_api_key_day',
                set_=dict(count=DailyUsage.count + stmt.excluded.count)
            )
            
            await self.db.execute(stmt)
            await self.db.flush()
            
            logger.info(
                "Email sends recorded",
                api_key_id=str(api_key_id),
                email_count=email_count,
                day=today,
            )
            
        except Exception as e:
            logger.error(
                "Error recording email sends",
                api_key_id=str(api_key_id),
                email_count=email_count,
                error=str(e),
            )
            raise

    async def get_usage_summary(self, api_key_id: uuid.UUID) -> dict:
        """Get usage summary for an API key."""
        today = date.today()
        
        try:
            # Get today's usage
            current_usage = await self.get_usage_for_day(api_key_id, today)
            daily_limit = await self.get_daily_limit(api_key_id)
            
            # Get total emails sent
            stmt = select(func.count(SendLog.id)).where(SendLog.api_key_id == api_key_id)
            result = await self.db.execute(stmt)
            total_sent = result.scalar() or 0
            
            return {
                "api_key_id": str(api_key_id),
                "daily_limit": daily_limit,
                "today_usage": current_usage,
                "today_remaining": max(0, daily_limit - current_usage),
                "total_sent": total_sent,
                "date": today.isoformat(),
            }
            
        except Exception as e:
            logger.error("Error getting usage summary", api_key_id=str(api_key_id), error=str(e))
            return {
                "api_key_id": str(api_key_id),
                "daily_limit": self.settings.default_daily_limit,
                "today_usage": 0,
                "today_remaining": self.settings.default_daily_limit,
                "total_sent": 0,
                "date": today.isoformat(),
            }