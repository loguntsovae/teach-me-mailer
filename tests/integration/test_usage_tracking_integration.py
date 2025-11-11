"""Integration tests for UsageTrackingService."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import AuthService
from app.services.usage_tracking import UsageTrackingService


class TestUsageTrackingIntegration:
    """Integration tests for usage tracking service."""

    @pytest.mark.asyncio
    async def test_record_email_sends_multiple_recipients(self, db_session: AsyncSession, test_settings):
        """Test recording email sends for multiple recipients."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Multi Recipient Test")
        await db_session.commit()

        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=recipients, message_id="test-msg-123")
        await db_session.commit()

        # Check usage was recorded
        usage = await usage_service.get_usage_for_day(key_obj.id, date.today())
        assert usage == 3

    @pytest.mark.asyncio
    async def test_record_email_sends_with_message_id(self, db_session: AsyncSession, test_settings):
        """Test recording email send with message ID."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Message ID Test")
        await db_session.commit()

        await usage_service.record_email_sends(
            api_key_id=key_obj.id, recipients=["test@example.com"], message_id="msg-abc-123"
        )
        await db_session.commit()

        # Verify send log was created with message ID
        from sqlalchemy import select

        from app.models.send_log import SendLog

        stmt = select(SendLog).where(SendLog.api_key_id == key_obj.id)
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].message_id == "msg-abc-123"

    @pytest.mark.asyncio
    async def test_record_email_sends_without_message_id(self, db_session: AsyncSession, test_settings):
        """Test recording email send without message ID."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="No Message ID Test")
        await db_session.commit()

        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["test@example.com"], message_id=None)
        await db_session.commit()

        # Verify send log was created
        from sqlalchemy import select

        from app.models.send_log import SendLog

        stmt = select(SendLog).where(SendLog.api_key_id == key_obj.id)
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].message_id is None

    @pytest.mark.asyncio
    async def test_get_usage_summary_comprehensive(self, db_session: AsyncSession, test_settings):
        """Test getting comprehensive usage summary."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Summary Test", daily_limit=50)
        await db_session.commit()

        # Record some sends
        await usage_service.record_email_sends(
            api_key_id=key_obj.id,
            recipients=["user1@example.com", "user2@example.com"],
        )
        await db_session.commit()

        # Get summary
        summary = await usage_service.get_usage_summary(key_obj.id)

        assert summary["api_key_id"] == str(key_obj.id)
        assert summary["daily_limit"] == 50
        assert summary["today_usage"] == 2
        assert summary["today_remaining"] == 48
        assert summary["total_sent"] == 2
        assert "date" in summary

    @pytest.mark.asyncio
    async def test_get_usage_summary_no_usage(self, db_session: AsyncSession, test_settings):
        """Test getting usage summary for key with no usage."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="No Usage Test")
        await db_session.commit()

        summary = await usage_service.get_usage_summary(key_obj.id)

        assert summary["today_usage"] == 0
        assert summary["today_remaining"] == test_settings.default_daily_limit
        assert summary["total_sent"] == 0

    @pytest.mark.asyncio
    async def test_check_daily_limit_within_limit(self, db_session: AsyncSession, test_settings):
        """Test checking daily limit when within limit."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Within Limit Test", daily_limit=10)
        await db_session.commit()

        # Record 5 emails
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["test@example.com"] * 5)
        await db_session.commit()

        # Check if we can send 3 more
        allowed = await usage_service.check_daily_limit(key_obj.id, email_count=3)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_check_daily_limit_at_limit(self, db_session: AsyncSession, test_settings):
        """Test checking daily limit when at limit."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="At Limit Test", daily_limit=5)
        await db_session.commit()

        # Record 5 emails (at limit)
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["test@example.com"] * 5)
        await db_session.commit()

        # Check if we can send 1 more
        allowed = await usage_service.check_daily_limit(key_obj.id, email_count=1)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_check_daily_limit_exceeds(self, db_session: AsyncSession, test_settings):
        """Test checking daily limit when would exceed."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Exceeds Test", daily_limit=10)
        await db_session.commit()

        # Record 8 emails
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["test@example.com"] * 8)
        await db_session.commit()

        # Check if we can send 5 more (would exceed)
        allowed = await usage_service.check_daily_limit(key_obj.id, email_count=5)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_get_daily_limit_custom(self, db_session: AsyncSession, test_settings):
        """Test getting daily limit for key with custom limit."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Custom Limit Test", daily_limit=250)
        await db_session.commit()

        limit = await usage_service.get_daily_limit(key_obj.id)
        assert limit == 250

    @pytest.mark.asyncio
    async def test_get_daily_limit_default(self, db_session: AsyncSession, test_settings):
        """Test getting daily limit for key with no custom limit."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Default Limit Test", daily_limit=None)
        await db_session.commit()

        limit = await usage_service.get_daily_limit(key_obj.id)
        assert limit == test_settings.default_daily_limit

    @pytest.mark.asyncio
    async def test_get_daily_limit_nonexistent_key(self, db_session: AsyncSession, test_settings):
        """Test getting daily limit for non-existent key."""
        usage_service = UsageTrackingService(db_session, test_settings)

        fake_uuid = uuid.uuid4()
        limit = await usage_service.get_daily_limit(fake_uuid)

        # Should return default limit for non-existent key
        assert limit == test_settings.default_daily_limit

    @pytest.mark.asyncio
    async def test_get_usage_for_day_nonexistent_key(self, db_session: AsyncSession, test_settings):
        """Test getting usage for non-existent key."""
        usage_service = UsageTrackingService(db_session, test_settings)

        fake_uuid = uuid.uuid4()
        usage = await usage_service.get_usage_for_day(fake_uuid, date.today())

        # Should return 0 for non-existent key
        assert usage == 0

    @pytest.mark.asyncio
    async def test_record_email_sends_incremental(self, db_session: AsyncSession, test_settings):
        """Test that multiple record calls increment count correctly."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Incremental Test")
        await db_session.commit()

        # Record first batch
        await usage_service.record_email_sends(
            api_key_id=key_obj.id, recipients=["user1@example.com", "user2@example.com"]
        )
        await db_session.commit()

        # Record second batch
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["user3@example.com"])
        await db_session.commit()

        # Check total usage
        usage = await usage_service.get_usage_for_day(key_obj.id, date.today())
        assert usage == 3

    @pytest.mark.asyncio
    async def test_get_usage_summary_with_high_usage(self, db_session: AsyncSession, test_settings):
        """Test usage summary when usage is high."""
        auth_service = AuthService(db_session, test_settings)
        usage_service = UsageTrackingService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="High Usage Test", daily_limit=10)
        await db_session.commit()

        # Record 15 emails (exceeds limit)
        await usage_service.record_email_sends(api_key_id=key_obj.id, recipients=["test@example.com"] * 15)
        await db_session.commit()

        summary = await usage_service.get_usage_summary(key_obj.id)

        assert summary["today_usage"] == 15
        assert summary["today_remaining"] == 0  # max(0, 10 - 15) = 0
        assert summary["total_sent"] == 15
