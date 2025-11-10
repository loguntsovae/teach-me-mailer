import uuid
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.models.send_log import SendLog

logger = structlog.get_logger(__name__)


class RateLimitResult(NamedTuple):
    """Result of a rate limit check."""

    allowed: bool
    current_count: int
    retry_after_seconds: Optional[int] = None


class AtomicRateLimitService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def check_and_increment_rate_limit(self, api_key_id: uuid.UUID, email_count: int = 1) -> RateLimitResult:
        """
        Atomically check and increment daily usage count.

        Returns:
            RateLimitResult: Result with allowed status, current count, and retry info
        """
        today = date.today()  # UTC date

        try:
            # Get effective daily limit for this API key
            effective_limit = await self._get_effective_daily_limit(api_key_id)

            # Use a transactional SELECT ... FOR UPDATE to atomically read/update the
            # DailyUsage row. If the row does not exist we create it. Handle a possible
            # race where two transactions try to create the row simultaneously by
            # catching IntegrityError and retrying once.
            class _RateLimitExceeded(Exception):
                def __init__(self, old_count: int):
                    self.old_count = old_count

            try:
                stmt = (
                    select(DailyUsage)
                    .where(DailyUsage.api_key_id == api_key_id, DailyUsage.day == today)
                    .with_for_update()
                )
                res = await self.db.execute(stmt)
                usage = res.scalar_one_or_none()

                if usage is None:
                    # create a new row
                    usage = DailyUsage(api_key_id=api_key_id, day=today, count=email_count)
                    self.db.add(usage)
                    # flush to assign DB defaults / persist
                    await self.db.flush()
                    old_count = 0
                    new_count = usage.count
                else:
                    old_count = usage.count
                    usage.count = usage.count + email_count
                    new_count = usage.count

                # If the new count exceeds the limit, raise to rollback the transaction
                if new_count > effective_limit:
                    # raising will rollback the current transaction
                    raise _RateLimitExceeded(old_count)

                # if we reach here the transaction committed successfully
                logger.info(
                    "Rate limit check passed",
                    api_key_id=str(api_key_id),
                    day=today.isoformat(),
                    new_count=new_count,
                    effective_limit=effective_limit,
                    email_count=email_count,
                )
                return RateLimitResult(allowed=True, current_count=new_count, retry_after_seconds=None)

            except _RateLimitExceeded as ex:
                retry_after = self._calculate_retry_after_seconds()
                logger.warning(
                    "Rate limit exceeded",
                    api_key_id=str(api_key_id),
                    day=today.isoformat(),
                    current_count=ex.old_count,
                    effective_limit=effective_limit,
                    requested_count=email_count,
                    retry_after_seconds=retry_after,
                )
                return RateLimitResult(allowed=False, current_count=ex.old_count, retry_after_seconds=retry_after)
            except IntegrityError:
                # Rare race when two transactions inserted the row at the same time.
                # In that case, retry the operation once by selecting the row and
                # applying the increment under a transaction.
                # Rollback the failed transaction before retrying to ensure the
                # session is clean; otherwise attempting to begin a new
                # transaction can raise InvalidRequestError.
                try:
                    await self.db.rollback()
                except Exception:
                    # ignore rollback errors here; we'll surface the original problem
                    pass

                try:
                    stmt = (
                        select(DailyUsage)
                        .where(DailyUsage.api_key_id == api_key_id, DailyUsage.day == today)
                        .with_for_update()
                    )
                    res = await self.db.execute(stmt)
                    usage = res.scalar_one_or_none()

                    if usage is None:
                        raise ValueError("DailyUsage row not found after FOR UPDATE lock")

                    old_count = usage.count
                    usage.count = usage.count + email_count
                    new_count = usage.count

                    if new_count > effective_limit:
                        raise _RateLimitExceeded(old_count)

                    logger.info(
                        "Rate limit check passed (retry)",
                        api_key_id=str(api_key_id),
                        day=today.isoformat(),
                        new_count=new_count,
                        effective_limit=effective_limit,
                        email_count=email_count,
                    )
                    return RateLimitResult(allowed=True, current_count=new_count, retry_after_seconds=None)

                except _RateLimitExceeded as ex:
                    retry_after = self._calculate_retry_after_seconds()
                    logger.warning(
                        "Rate limit exceeded (retry)",
                        api_key_id=str(api_key_id),
                        day=today.isoformat(),
                        current_count=ex.old_count,
                        effective_limit=effective_limit,
                        requested_count=email_count,
                        retry_after_seconds=retry_after,
                    )
                    return RateLimitResult(allowed=False, current_count=ex.old_count, retry_after_seconds=retry_after)

        except Exception as e:
            logger.error(
                "Error in atomic rate limit check",
                api_key_id=str(api_key_id),
                day=today.isoformat(),
                email_count=email_count,
                error=str(e),
            )
            # On error, deny the request for safety
            return RateLimitResult(
                allowed=False,
                current_count=0,
                retry_after_seconds=self._calculate_retry_after_seconds(),
            )

    async def log_successful_sends(
        self,
        api_key_id: uuid.UUID,
        recipients: list[str],
        message_id: Optional[str] = None,
    ) -> None:
        """Log successful email sends in SendLog after emails are queued."""
        sent_at = datetime.now(timezone.utc)

        try:
            # Bulk insert send logs
            send_logs = [
                SendLog(
                    api_key_id=api_key_id,
                    sent_at=sent_at,
                    recipient=recipient,
                    message_id=message_id,
                )
                for recipient in recipients
            ]

            self.db.add_all(send_logs)
            await self.db.flush()

            logger.info(
                "Send logs recorded",
                api_key_id=str(api_key_id),
                recipient_count=len(recipients),
                message_id=message_id,
                sent_at=sent_at.isoformat(),
            )

        except Exception as e:
            logger.error(
                "Error recording send logs",
                api_key_id=str(api_key_id),
                recipient_count=len(recipients),
                error=str(e),
            )
            raise

    async def get_usage_summary(self, api_key_id: uuid.UUID) -> dict:
        """Get current usage summary for an API key."""
        today = date.today()

        try:
            # Get effective daily limit
            effective_limit = await self._get_effective_daily_limit(api_key_id)

            # Get current usage for today
            current_usage = await self._get_current_usage(api_key_id, today)

            # Calculate remaining quota
            remaining = max(0, effective_limit - current_usage)

            # Get total emails sent (all time)
            total_sent_result = await self.db.execute(
                select(func.count()).select_from(SendLog).where(SendLog.api_key_id == api_key_id)
            )
            total_sent = total_sent_result.scalar() or 0

            return {
                "api_key_id": str(api_key_id),
                "daily_limit": effective_limit,
                "today_usage": current_usage,
                "today_remaining": remaining,
                "total_sent": total_sent,
                "date": today.isoformat(),
                "next_reset_utc": self._get_next_midnight_utc().isoformat(),
            }

        except Exception as e:
            logger.error(
                "Error getting usage summary",
                api_key_id=str(api_key_id),
                error=str(e),
            )
            # Return safe defaults on error
            return {
                "api_key_id": str(api_key_id),
                "daily_limit": self.settings.default_daily_limit,
                "today_usage": 0,
                "today_remaining": self.settings.default_daily_limit,
                "total_sent": 0,
                "date": today.isoformat(),
                "next_reset_utc": self._get_next_midnight_utc().isoformat(),
            }

    async def _get_effective_daily_limit(self, api_key_id: uuid.UUID) -> int:
        """Get the effective daily limit for an API key."""
        try:
            result = await self.db.execute(select(APIKey.daily_limit).where(APIKey.id == api_key_id))
            daily_limit = result.scalar_one_or_none()

            # Treat None or non-positive limits as unspecified and fall back to default
            if daily_limit is None or (isinstance(daily_limit, int) and daily_limit <= 0):
                return self.settings.default_daily_limit

            # Use API key specific positive limit
            return daily_limit

        except Exception as e:
            logger.error(
                "Error getting daily limit",
                api_key_id=str(api_key_id),
                error=str(e),
            )
            return self.settings.default_daily_limit

    async def _get_current_usage(self, api_key_id: uuid.UUID, day: date) -> int:
        """Get current usage count for a specific day."""
        try:
            result = await self.db.execute(
                select(DailyUsage.count).where(DailyUsage.api_key_id == api_key_id, DailyUsage.day == day)
            )
            count = result.scalar_one_or_none()
            return count if count is not None else 0

        except Exception as e:
            logger.error(
                "Error getting current usage",
                api_key_id=str(api_key_id),
                day=day.isoformat(),
                error=str(e),
            )
            return 0

    def _calculate_retry_after_seconds(self) -> int:
        """Calculate seconds until next midnight UTC."""
        now_utc = datetime.now(timezone.utc)
        next_midnight = self._get_next_midnight_utc()
        return int((next_midnight - now_utc).total_seconds())

    def _get_next_midnight_utc(self) -> datetime:
        """Get next midnight in UTC."""
        now_utc = datetime.now(timezone.utc)
        next_day = (now_utc + timedelta(days=1)).date()
        return datetime.combine(next_day, datetime.min.time(), timezone.utc)
