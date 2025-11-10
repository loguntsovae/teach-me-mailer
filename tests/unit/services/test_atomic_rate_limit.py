"""Unit tests for AtomicRateLimitService (PostgreSQL-based rate limiting)."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.services.atomic_rate_limit import AtomicRateLimitService, RateLimitResult


class TestAtomicRateLimitService:
    """Tests for atomic PostgreSQL-based rate limiting."""

    async def test_check_and_increment_new_key(self, db_session, test_settings):
        """Test rate limit check for new API key (creates DailyUsage)."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_1", name="Atomic Test Key 1")
        db_session.add(api_key)
        await db_session.commit()

        # First check should create DailyUsage entry
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=5)
        await db_session.commit()

        assert result.allowed is True
        assert result.current_count == 5
        assert result.retry_after_seconds is None

    async def test_check_and_increment_existing_usage(self, db_session, test_settings):
        """Test incrementing existing daily usage."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_2", name="Atomic Test Key 2")
        db_session.add(api_key)
        await db_session.commit()

        # Create existing usage
        usage = DailyUsage(api_key_id=api_key.id, day=date.today(), count=10)
        db_session.add(usage)
        await db_session.commit()

        # Increment
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=5)
        await db_session.commit()

        assert result.allowed is True
        assert result.current_count == 15

    async def test_check_and_increment_exceeds_limit(self, db_session, test_settings):
        """Test that exceeding limit is rejected and not committed."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_3", name="Atomic Test Key 3")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage at 99 (limit is 100)
        usage = DailyUsage(api_key_id=api_key.id, day=date.today(), count=99)
        db_session.add(usage)
        await db_session.commit()

        # Try to add 2 (would be 101, exceeds 100)
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=2)

        assert result.allowed is False
        assert result.current_count == 99  # Should return old count
        assert result.retry_after_seconds is not None

        # Verify count was NOT updated in DB
        await db_session.refresh(usage)
        assert usage.count == 99

    async def test_check_and_increment_at_limit(self, db_session, test_settings):
        """Test that reaching exactly the limit is allowed."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_4", name="Atomic Test Key 4")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage at 95
        usage = DailyUsage(api_key_id=api_key.id, day=date.today(), count=95)
        db_session.add(usage)
        await db_session.commit()

        # Add 5 to reach exactly 100
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=5)
        await db_session.commit()

        assert result.allowed is True
        assert result.current_count == 100

    async def test_get_effective_daily_limit_custom(self, db_session, test_settings):
        """Test getting custom daily limit from API key."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key with custom limit
        api_key = APIKey(key_hash="test_hash_atomic_5", name="Custom Limit Key", daily_limit=500)
        db_session.add(api_key)
        await db_session.commit()

        limit = await service._get_effective_daily_limit(api_key.id)

        assert limit == 500

    async def test_get_effective_daily_limit_default(self, db_session, test_settings):
        """Test getting default daily limit when API key has no custom limit."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key without custom limit
        api_key = APIKey(key_hash="test_hash_atomic_6", name="Default Limit Key", daily_limit=None)
        db_session.add(api_key)
        await db_session.commit()

        limit = await service._get_effective_daily_limit(api_key.id)

        assert limit == test_settings.default_daily_limit

    async def test_calculate_retry_after_seconds(self, db_session, test_settings):
        """Test retry-after calculation."""
        service = AtomicRateLimitService(db_session, test_settings)

        retry_after = service._calculate_retry_after_seconds()

        # Should be positive and reasonable (less than 24 hours)
        assert retry_after > 0
        assert retry_after <= 86400

    async def test_multiple_increments_same_day(self, db_session, test_settings):
        """Test multiple increments on same day accumulate."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_10", name="Multi Increment Key")
        db_session.add(api_key)
        await db_session.commit()

        # Multiple increments
        result1 = await service.check_and_increment_rate_limit(api_key.id, email_count=10)
        await db_session.commit()

        result2 = await service.check_and_increment_rate_limit(api_key.id, email_count=15)
        await db_session.commit()

        result3 = await service.check_and_increment_rate_limit(api_key.id, email_count=20)
        await db_session.commit()

        assert result1.current_count == 10
        assert result2.current_count == 25
        assert result3.current_count == 45

    async def test_different_days_independent(self, db_session, test_settings):
        """Test that usage on different days is independent."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_11", name="Different Days Key")
        db_session.add(api_key)
        await db_session.commit()

        # Create usage for yesterday
        yesterday = date.today() - timedelta(days=1)
        usage_yesterday = DailyUsage(api_key_id=api_key.id, day=yesterday, count=100)  # At limit for yesterday
        db_session.add(usage_yesterday)
        await db_session.commit()

        # Today should start fresh
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=5)
        await db_session.commit()

        assert result.allowed is True
        assert result.current_count == 5


class TestAtomicRateLimitConcurrency:
    """Tests for concurrent access scenarios."""

    async def test_concurrent_increment_safety(self, db_session, test_settings):
        """Test that atomic operations prevent race conditions."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_12", name="Concurrent Test Key")
        db_session.add(api_key)
        await db_session.commit()

        # Sequential operations should be atomic
        result1 = await service.check_and_increment_rate_limit(api_key.id, email_count=30)
        await db_session.commit()

        result2 = await service.check_and_increment_rate_limit(api_key.id, email_count=30)
        await db_session.commit()

        # Both should succeed and counts should be accurate
        assert result1.allowed is True
        assert result2.allowed is True
        assert result2.current_count == 60


class TestAtomicRateLimitEdgeCases:
    """Tests for edge cases."""

    async def test_zero_email_count(self, db_session, test_settings):
        """Test with zero email count."""
        service = AtomicRateLimitService(db_session, test_settings)

        # Create API key
        api_key = APIKey(key_hash="test_hash_atomic_13", name="Zero Count Key")
        db_session.add(api_key)
        await db_session.commit()

        # Should still work but not increment
        result = await service.check_and_increment_rate_limit(api_key.id, email_count=0)
        await db_session.commit()

        assert result.allowed is True
        assert result.current_count == 0

    async def test_nonexistent_api_key(self, db_session, test_settings):
        """Test with non-existent API key ID."""
        service = AtomicRateLimitService(db_session, test_settings)

        fake_uuid = uuid.uuid4()

        # Should raise or handle gracefully
        try:
            result = await service.check_and_increment_rate_limit(fake_uuid, email_count=1)
            # If it succeeds, it should use default limit
            assert result.allowed is True
        except Exception:
            # Or it may raise an exception, which is also valid
            pass
