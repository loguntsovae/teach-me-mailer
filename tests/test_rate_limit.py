from sqlalchemy import select

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.services.atomic_rate_limit import AtomicRateLimitService


class TestRateLimit:
    """Test atomic rate limiting functionality."""

    async def test_rate_limit_within_bounds(self, test_session, test_settings):
        """Test rate limiting when within daily limit."""
        # Create API key with limit of 10
        api_key = APIKey(
            name="Test Key",
            key_hash="within-bounds-test-hash",
            daily_limit=10,
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.flush()

        rate_limiter = AtomicRateLimitService(test_session, test_settings)

        # Test sending 5 emails (within limit)
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=5)

        assert result.allowed is True
        assert result.current_count == 5

        # Test sending 3 more emails (still within limit)
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=3)

        assert result.allowed is True
        assert result.current_count == 8

    async def test_rate_limit_at_boundary(self, test_session, test_settings):
        """Test rate limiting exactly at the daily limit boundary."""
        # Create API key with limit of 5
        api_key = APIKey(
            name="Boundary Test Key",
            key_hash="boundary-test-hash",
            daily_limit=5,
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.flush()

        rate_limiter = AtomicRateLimitService(test_session, test_settings)

        # Send exactly at limit
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=5)

        assert result.allowed is True
        assert result.current_count == 5

        # Try to send 1 more (should fail)
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=1)

        assert result.allowed is False
        assert result.current_count == 5  # Should not increment
        assert result.retry_after_seconds > 0

    async def test_rate_limit_exceeds_boundary(self, test_session, test_settings):
        """Test rate limiting when request exceeds daily limit."""
        # Create API key with limit of 3
        api_key = APIKey(
            name="Exceed Test Key",
            key_hash="exceeds-boundary-test-hash",
            daily_limit=3,
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.flush()

        rate_limiter = AtomicRateLimitService(test_session, test_settings)

        # Try to send 5 emails (exceeds limit of 3)
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=5)

        assert result.allowed is False
        assert result.current_count == 0  # Should not increment
        assert result.retry_after_seconds > 0

    async def test_concurrent_rate_limit_upserts(self, test_session, test_settings):
        """Test atomic upsert behavior sequentially to avoid session conflicts."""
        # Create API key with limit of 20
        api_key = APIKey(
            name="Concurrency Test Key",
            key_hash="concurrency-test-hash",
            daily_limit=20,
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.commit()

        rate_limiter = AtomicRateLimitService(test_session, test_settings)

        # Send emails in multiple batches to test atomic behavior
        results = []
        for i in range(10):
            result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=2)
            results.append(result)

        # All should succeed (10 * 2 = 20 emails, at limit)
        successful_results = [r for r in results if r.allowed]
        failed_results = [r for r in results if not r.allowed]

        assert len(successful_results) == 10
        assert len(failed_results) == 0
        assert successful_results[-1].current_count == 20  # Final count should be 20

        # Verify final count in database
        stmt = select(DailyUsage).where(DailyUsage.api_key_id == api_key.id)
        result = await test_session.execute(stmt)
        usage = result.scalar_one_or_none()

        # If no record found, try to get all records and find manually
        if usage is None:
            all_usage = await test_session.execute(select(DailyUsage))
            all_records = all_usage.scalars().all()
            for record in all_records:
                if record.api_key_id == api_key.id:
                    usage = record
                    break

        assert usage is not None, "Could not find DailyUsage record"
        assert usage.count == 20

        # One more attempt should fail
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=1)
        assert result.allowed is False

    async def test_zero_increment_usage_check(self, test_session, test_settings):
        """Test getting current usage without incrementing."""
        # Create API key with some existing usage
        api_key = APIKey(
            name="Usage Check Key",
            key_hash="usage-check-test-hash",
            daily_limit=100,
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.flush()

        rate_limiter = AtomicRateLimitService(test_session, test_settings)

        # Send some emails first
        await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=15)

        # Check usage with 0 increment
        result = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=0)

        assert result.allowed is True
        assert result.current_count == 15

        # Verify count didn't change
        result2 = await rate_limiter.check_and_increment_rate_limit(api_key_id=api_key.id, email_count=0)
        assert result2.current_count == 15
