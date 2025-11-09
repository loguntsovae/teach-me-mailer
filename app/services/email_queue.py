import uuid
from typing import Optional

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.send_log import SendLog
from app.services.mailer import MailerService

logger = structlog.get_logger(__name__)


class EmailQueueService:
    """Service for handling background email sending and logging."""

    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.mailer = MailerService(settings)

    async def create_send_log(self, api_key_id: uuid.UUID, recipient: str) -> int:
        """Create a SendLog entry with null message_id."""
        send_log = SendLog(
            api_key_id=api_key_id,
            recipient=recipient,
            message_id=None,  # Will be updated after sending
        )

        self.db.add(send_log)
        await self.db.flush()  # Get the ID without committing

        logger.info(
            "Created send log entry",
            log_id=send_log.id,
            api_key_id=str(api_key_id),
            recipient=recipient,
        )

        return send_log.id

    async def update_send_log_message_id(self, log_id: int, message_id: Optional[str]) -> None:
        """Update the message_id in an existing SendLog entry using a new session."""
        from app.db.session import AsyncSessionLocal

        try:
            # Create a new session for the background update
            async with AsyncSessionLocal() as db_session:
                await db_session.execute(update(SendLog).where(SendLog.id == log_id).values(message_id=message_id))
                await db_session.commit()

                logger.info(
                    "Updated send log with message ID",
                    log_id=log_id,
                    message_id=message_id,
                )

        except Exception as e:
            logger.error("Failed to update send log message ID", log_id=log_id, error=str(e))

    async def send_email_background(
        self,
        log_id: int,
        to: str,
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> None:
        """Send email in background and update send log with message ID."""
        try:
            message_id = await self.mailer.send_email(to=[to], subject=subject, html=html, text=text, headers=headers)

            # Update the send log with the message ID (or None if failed)
            await self.update_send_log_message_id(log_id, message_id)

            if message_id:
                logger.info(
                    "Background email sent successfully",
                    log_id=log_id,
                    recipient=to,
                    message_id=message_id,
                )
            else:
                logger.error("Background email send failed", log_id=log_id, recipient=to)

        except Exception as e:
            logger.error("Background email send error", log_id=log_id, recipient=to, error=str(e))
            # Update with None to indicate failure
            await self.update_send_log_message_id(log_id, None)
