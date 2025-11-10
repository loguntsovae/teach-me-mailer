"""Unit tests for RateLimitService (in-memory rate limiting)."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.services.rate_limit import RateLimitService


class TestRateLimitService:
    """Tests for in-memory rate limiting."""

    async def test_check_daily_limit_within_limit(self, test_settings):
        """Test check passes when within daily limit."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_1"

        # Should be within limit (default is 100)
        result = await rate_limit.check_daily_limit(api_key, email_count=10)

        assert result is True

    async def test_check_daily_limit_at_limit(self, test_settings):
        """Test check fails when at limit."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_2"

        # Record 100 emails (the limit)
        await rate_limit.record_emails(api_key, email_count=100)

        # Should fail for additional email
        result = await rate_limit.check_daily_limit(api_key, email_count=1)

        assert result is False

    async def test_check_daily_limit_exceed_limit(self, test_settings):
        """Test check fails when exceeding limit."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_3"

        # Record 50 emails
        await rate_limit.record_emails(api_key, email_count=50)

        # Try to send 51 more (total 101, exceeds 100 limit)
        result = await rate_limit.check_daily_limit(api_key, email_count=51)

        assert result is False

    async def test_check_daily_limit_just_under_limit(self, test_settings):
        """Test check passes when just under limit."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_4"

        # Record 99 emails
        await rate_limit.record_emails(api_key, email_count=99)

        # Should pass for 1 more (total 100, at limit)
        result = await rate_limit.check_daily_limit(api_key, email_count=1)

        assert result is True

    async def test_record_emails_single(self, test_settings):
        """Test recording single email."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_5"

        await rate_limit.record_emails(api_key, email_count=1)

        assert len(rate_limit.requests[api_key]) == 1

    async def test_record_emails_multiple(self, test_settings):
        """Test recording multiple emails."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_6"

        await rate_limit.record_emails(api_key, email_count=5)

        assert len(rate_limit.requests[api_key]) == 5

    async def test_record_emails_incremental(self, test_settings):
        """Test recording emails incrementally."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_7"

        await rate_limit.record_emails(api_key, email_count=3)
        await rate_limit.record_emails(api_key, email_count=2)
        await rate_limit.record_emails(api_key, email_count=5)

        assert len(rate_limit.requests[api_key]) == 10

    async def test_multiple_api_keys_independent(self, test_settings):
        """Test that different API keys have independent limits."""
        rate_limit = RateLimitService(test_settings)
        key1 = "sk_test_key_8"
        key2 = "sk_test_key_9"

        # Record for key1
        await rate_limit.record_emails(key1, email_count=50)

        # Record for key2
        await rate_limit.record_emails(key2, email_count=30)

        # Check limits are independent
        assert len(rate_limit.requests[key1]) == 50
        assert len(rate_limit.requests[key2]) == 30

        # key1 can still send 50 more
        result1 = await rate_limit.check_daily_limit(key1, email_count=50)
        assert result1 is True

        # key2 can still send 70 more
        result2 = await rate_limit.check_daily_limit(key2, email_count=70)
        assert result2 is True

    async def test_cleanup_old_requests(self, test_settings):
        """Test cleanup of old requests outside rate window."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_10"

        now = datetime.utcnow()

        # Add old request (2 days ago, outside 1-day window)
        old_time = now - timedelta(days=2)
        rate_limit.requests[api_key].append(old_time)

        # Add recent request
        rate_limit.requests[api_key].append(now)

        # Trigger cleanup
        await rate_limit._cleanup_old_requests(api_key, now)

        # Should only have the recent request
        assert len(rate_limit.requests[api_key]) == 1
        assert rate_limit.requests[api_key][0] == now

    async def test_check_daily_limit_triggers_cleanup(self, test_settings):
        """Test that check_daily_limit automatically cleans up old requests."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_11"

        now = datetime.utcnow()

        # Add 100 old requests (2 days ago)
        old_time = now - timedelta(days=2)
        for _ in range(100):
            rate_limit.requests[api_key].append(old_time)

        # Should pass because old requests are cleaned up
        result = await rate_limit.check_daily_limit(api_key, email_count=10)

        assert result is True
        # Old requests should be cleaned
        assert len(rate_limit.requests[api_key]) == 0

    async def test_rate_window_days_setting(self, test_settings):
        """Test that rate window respects settings."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_12"

        now = datetime.utcnow()

        # Add request exactly at window edge (1 day ago)
        window_edge = now - timedelta(days=test_settings.rate_window_days)
        rate_limit.requests[api_key].append(window_edge)

        # Add request just inside window
        inside_window = now - timedelta(hours=23)
        rate_limit.requests[api_key].append(inside_window)

        await rate_limit._cleanup_old_requests(api_key, now)

        # Request at window edge should be removed, inside should remain
        assert len(rate_limit.requests[api_key]) == 1

    async def test_empty_requests_for_new_key(self, test_settings):
        """Test that new API key has empty request list."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_new"

        result = await rate_limit.check_daily_limit(api_key, email_count=1)

        assert result is True
        assert len(rate_limit.requests[api_key]) == 0

    async def test_record_zero_emails(self, test_settings):
        """Test recording zero emails."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_13"

        await rate_limit.record_emails(api_key, email_count=0)

        assert len(rate_limit.requests[api_key]) == 0

    async def test_check_daily_limit_zero_count(self, test_settings):
        """Test checking limit with zero email count."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_14"

        result = await rate_limit.check_daily_limit(api_key, email_count=0)

        assert result is True


class TestRateLimitTimestamps:
    """Tests for timestamp handling in rate limiting."""

    async def test_timestamps_are_datetime(self, test_settings):
        """Test that all stored timestamps are datetime objects."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_15"

        await rate_limit.record_emails(api_key, email_count=5)

        for timestamp in rate_limit.requests[api_key]:
            assert isinstance(timestamp, datetime)

    async def test_timestamps_recent(self, test_settings):
        """Test that recorded timestamps are recent."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_16"

        before = datetime.utcnow()
        await rate_limit.record_emails(api_key, email_count=1)
        after = datetime.utcnow()

        timestamp = rate_limit.requests[api_key][0]
        assert before <= timestamp <= after

    async def test_multiple_timestamps_ordered(self, test_settings):
        """Test that multiple timestamps maintain order."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_17"

        await rate_limit.record_emails(api_key, email_count=3)

        timestamps = rate_limit.requests[api_key]
        # All timestamps should be very close (same utcnow() call)
        assert len(timestamps) == 3
        # They should all be equal or very close
        time_diff = (timestamps[-1] - timestamps[0]).total_seconds()
        assert time_diff < 1  # Less than 1 second apart


class TestRateLimitEdgeCases:
    """Tests for edge cases in rate limiting."""

    async def test_large_email_count(self, test_settings):
        """Test handling large email count."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_18"

        # Try to send 1000 emails at once (exceeds limit)
        result = await rate_limit.check_daily_limit(api_key, email_count=1000)

        assert result is False

    async def test_exactly_at_limit(self, test_settings):
        """Test behavior when exactly at limit."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_19"
        limit = test_settings.default_daily_limit

        # Record exactly at limit
        await rate_limit.record_emails(api_key, email_count=limit)

        # Check should fail for any additional
        result = await rate_limit.check_daily_limit(api_key, email_count=1)
        assert result is False

        # But should pass for 0
        result_zero = await rate_limit.check_daily_limit(api_key, email_count=0)
        assert result_zero is True

    async def test_concurrent_api_keys(self, test_settings):
        """Test handling multiple API keys concurrently."""
        rate_limit = RateLimitService(test_settings)

        # Simulate multiple keys being used
        keys = [f"sk_test_key_{i}" for i in range(10)]

        for key in keys:
            await rate_limit.record_emails(key, email_count=10)

        # All keys should have independent counts
        for key in keys:
            assert len(rate_limit.requests[key]) == 10
            result = await rate_limit.check_daily_limit(key, email_count=90)
            assert result is True

    async def test_cleanup_with_empty_requests(self, test_settings):
        """Test cleanup when there are no requests."""
        rate_limit = RateLimitService(test_settings)
        api_key = "sk_test_key_20"

        now = datetime.utcnow()

        # Should not raise error
        await rate_limit._cleanup_old_requests(api_key, now)

        assert len(rate_limit.requests[api_key]) == 0

    async def test_requests_dict_structure(self, test_settings):
        """Test that requests dictionary has correct structure."""
        rate_limit = RateLimitService(test_settings)

        assert isinstance(rate_limit.requests, dict)

        # Add some data
        await rate_limit.record_emails("key1", 5)

        # Check structure
        assert "key1" in rate_limit.requests
        assert isinstance(rate_limit.requests["key1"], list)
        assert all(isinstance(ts, datetime) for ts in rate_limit.requests["key1"])
