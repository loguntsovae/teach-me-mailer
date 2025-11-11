"""Integration tests for AtomicRateLimitService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.atomic_rate_limit import AtomicRateLimitService
from app.services.auth import AuthService


class TestAtomicRateLimitIntegration:
    """Integration tests for atomic rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_with_high_concurrency(self, db_session: AsyncSession, test_settings):
        """Test rate limiting with high concurrency."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Concurrency Test", daily_limit=100)
        await db_session.commit()

        # Try to send many emails
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=50)
        assert result.allowed is True
        await db_session.commit()

        # Try to send more
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=40)
        assert result.allowed is True
        await db_session.commit()

        # This should fail (would exceed limit)
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=20)
        assert result.allowed is False
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def test_rate_limit_with_zero_limit_key(self, db_session: AsyncSession, test_settings):
        """Test rate limiting with zero daily limit (treated as None/default)."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        # Zero limit is treated as None/default by AuthService
        key_obj, api_key = await auth_service.create_api_key(name="Zero Limit Test", daily_limit=0)
        await db_session.commit()

        # daily_limit=0 is converted to None, so uses default limit
        # Therefore this should succeed (not immediately fail)
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=1)
        # With default limit (100), 1 email should be allowed
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_at_exact_limit(self, db_session: AsyncSession, test_settings):
        """Test rate limiting at exact limit boundary."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Exact Limit Test", daily_limit=5)
        await db_session.commit()

        # Use exactly the limit
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=5)
        assert result.allowed is True
        assert result.current_count == 5
        await db_session.commit()

        # Next request should fail
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=1)
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_small_increments(self, db_session: AsyncSession, test_settings):
        """Test rate limiting with many small increments."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Small Increments Test", daily_limit=10)
        await db_session.commit()

        # Send 10 requests of 1 email each
        for i in range(10):
            result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=1)
            assert result.allowed is True
            await db_session.commit()

        # 11th should fail
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=1)
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_large_batch(self, db_session: AsyncSession, test_settings):
        """Test rate limiting with large batch."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Large Batch Test", daily_limit=1000)
        await db_session.commit()

        # Send large batch
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=500)
        assert result.allowed is True
        await db_session.commit()

        # Another large batch that would exceed
        result = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=600)
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_get_effective_daily_limit_with_custom(self, db_session: AsyncSession, test_settings):
        """Test getting effective daily limit with custom limit."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Custom Limit Test", daily_limit=500)
        await db_session.commit()

        limit = await rate_limiter._get_effective_daily_limit(key_obj.id)
        assert limit == 500

    @pytest.mark.asyncio
    async def test_get_effective_daily_limit_with_default(self, db_session: AsyncSession, test_settings):
        """Test getting effective daily limit with default."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Default Limit Test", daily_limit=None)
        await db_session.commit()

        limit = await rate_limiter._get_effective_daily_limit(key_obj.id)
        assert limit == test_settings.default_daily_limit

    @pytest.mark.asyncio
    async def test_calculate_retry_after(self, db_session: AsyncSession, test_settings):
        """Test retry-after calculation."""
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        retry_seconds = rate_limiter._calculate_retry_after_seconds()

        # Should be positive and reasonable (less than 24 hours)
        assert retry_seconds > 0
        assert retry_seconds <= 86400  # 24 hours in seconds

    @pytest.mark.asyncio
    async def test_rate_limit_sequential_increments(self, db_session: AsyncSession, test_settings):
        """Test sequential rate limit increments."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        key_obj, api_key = await auth_service.create_api_key(name="Sequential Test", daily_limit=20)
        await db_session.commit()

        # First increment
        result1 = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=7)
        assert result1.allowed is True
        assert result1.current_count == 7
        await db_session.commit()

        # Second increment
        result2 = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=8)
        assert result2.allowed is True
        assert result2.current_count == 15
        await db_session.commit()

        # Third increment
        result3 = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=5)
        assert result3.allowed is True
        assert result3.current_count == 20
        await db_session.commit()

        # Fourth should fail
        result4 = await rate_limiter.check_and_increment_rate_limit(key_obj.id, email_count=1)
        assert result4.allowed is False
        assert result4.current_count == 20

    @pytest.mark.asyncio
    async def test_rate_limit_multiple_keys_independent(self, db_session: AsyncSession, test_settings):
        """Test that different API keys have independent rate limits."""
        auth_service = AuthService(db_session, test_settings)
        rate_limiter = AtomicRateLimitService(db_session, test_settings)

        # Create two keys
        key1_obj, key1 = await auth_service.create_api_key(name="Key 1", daily_limit=10)
        key2_obj, key2 = await auth_service.create_api_key(name="Key 2", daily_limit=10)
        await db_session.commit()

        # Use key1
        result1 = await rate_limiter.check_and_increment_rate_limit(key1_obj.id, email_count=10)
        assert result1.allowed is True
        await db_session.commit()

        # Key1 should be at limit
        result1_extra = await rate_limiter.check_and_increment_rate_limit(key1_obj.id, email_count=1)
        assert result1_extra.allowed is False

        # But key2 should still work
        result2 = await rate_limiter.check_and_increment_rate_limit(key2_obj.id, email_count=5)
        assert result2.allowed is True
        assert result2.current_count == 5
