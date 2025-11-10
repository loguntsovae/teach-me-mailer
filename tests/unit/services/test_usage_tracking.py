"""Unit tests for UsageTrackingService."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.models.send_log import SendLog
from app.services.usage_tracking import UsageTrackingService


class TestUsageTrackingService:
    """Tests for usage tracking service."""

    async def test_get_daily_limit_custom(self, db_session, test_settings):
        """Test getting custom daily limit from API key."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key with custom limit
        api_key = APIKey(key_hash="test_usage_1", name="Custom Limit Key", daily_limit=250)
        db_session.add(api_key)
        await db_session.commit()

        limit = await service.get_daily_limit(api_key.id)

        assert limit == 250

    async def test_get_daily_limit_default(self, db_session, test_settings):
        """Test getting default daily limit."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key without custom limit
        api_key = APIKey(key_hash="test_usage_2", name="Default Limit Key", daily_limit=None)
        db_session.add(api_key)
        await db_session.commit()

        limit = await service.get_daily_limit(api_key.id)

        assert limit == test_settings.default_daily_limit

    async def test_get_usage_for_day(self, db_session, test_settings):
        """Test getting usage for specific day."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_usage_3", name="Usage Day Key")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage for today
        today = date.today()
        usage = DailyUsage(api_key_id=api_key.id, day=today, count=42)
        db_session.add(usage)
        await db_session.commit()

        count = await service.get_usage_for_day(api_key.id, today)

        assert count == 42

    async def test_get_usage_for_day_no_data(self, db_session, test_settings):
        """Test getting usage when no data exists."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_usage_4", name="No Usage Key")
        db_session.add(api_key)
        await db_session.commit()

        today = date.today()
        count = await service.get_usage_for_day(api_key.id, today)

        assert count == 0

    async def test_check_daily_limit_within(self, db_session, test_settings):
        """Test check passes when within limit."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_usage_5", name="Within Limit Key")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage at 50
        today = date.today()
        usage = DailyUsage(api_key_id=api_key.id, day=today, count=50)
        db_session.add(usage)
        await db_session.commit()

        # Check if can send 10 more (50 + 10 = 60 < 100)
        allowed = await service.check_daily_limit(api_key.id, email_count=10)

        assert allowed is True

    async def test_check_daily_limit_exceeds(self, db_session, test_settings):
        """Test check fails when would exceed limit."""
        service = UsageTrackingService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_usage_6", name="Exceed Limit Key")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage at 95
        today = date.today()
        usage = DailyUsage(api_key_id=api_key.id, day=today, count=95)
        db_session.add(usage)
        await db_session.commit()

        # Check if can send 10 more (95 + 10 = 105 > 100)
        allowed = await service.check_daily_limit(api_key.id, email_count=10)

        assert allowed is False

    async def test_nonexistent_api_key(self, db_session, test_settings):
        """Test handling non-existent API key gracefully."""
        service = UsageTrackingService(db_session, test_settings)

        fake_uuid = uuid.uuid4()

        # Should return default limit
        limit = await service.get_daily_limit(fake_uuid)
        assert limit == test_settings.default_daily_limit

        # Should return 0 usage
        usage = await service.get_usage_for_day(fake_uuid, date.today())
        assert usage == 0
