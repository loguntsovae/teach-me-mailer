"""Unit tests for DailyUsage model."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage


class TestDailyUsageModel:
    """Tests for DailyUsage model creation and validation."""

    async def test_create_daily_usage_minimal(self, db_session, test_api_key):
        """Test creating a daily usage record with minimal fields."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=0)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.id is not None
        assert usage.api_key_id == test_api_key.id
        assert usage.day == today
        assert usage.count == 0

    async def test_create_daily_usage_with_count(self, db_session, test_api_key):
        """Test creating a daily usage record with initial count."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=42)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == 42

    async def test_daily_usage_default_count(self, db_session, test_api_key):
        """Test that count defaults to 0."""
        today = date.today()
        usage = DailyUsage(
            api_key_id=test_api_key.id,
            day=today,
            # count not specified
        )
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == 0

    async def test_daily_usage_unique_constraint(self, db_session, test_api_key):
        """Test unique constraint on (api_key_id, day)."""
        today = date.today()

        # Create first usage record
        usage1 = DailyUsage(api_key_id=test_api_key.id, day=today, count=10)
        db_session.add(usage1)
        await db_session.commit()

        # Try to create duplicate for same api_key and day
        usage2 = DailyUsage(api_key_id=test_api_key.id, day=today, count=20)
        db_session.add(usage2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_daily_usage_different_days(self, db_session, test_api_key):
        """Test creating usage records for different days."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        usage_today = DailyUsage(api_key_id=test_api_key.id, day=today, count=10)
        usage_yesterday = DailyUsage(api_key_id=test_api_key.id, day=yesterday, count=20)
        db_session.add_all([usage_today, usage_yesterday])
        await db_session.commit()

        # Query both
        result = await db_session.execute(select(DailyUsage).where(DailyUsage.api_key_id == test_api_key.id))
        usages = result.scalars().all()

        assert len(usages) == 2

    async def test_daily_usage_different_api_keys(self, db_session):
        """Test creating usage records for different API keys."""
        # Create two API keys
        key1 = APIKey(key_hash="key1_hash", name="Key 1")
        key2 = APIKey(key_hash="key2_hash", name="Key 2")
        db_session.add_all([key1, key2])
        await db_session.commit()

        today = date.today()

        # Create usage for both keys on same day
        usage1 = DailyUsage(api_key_id=key1.id, day=today, count=10)
        usage2 = DailyUsage(api_key_id=key2.id, day=today, count=20)
        db_session.add_all([usage1, usage2])
        await db_session.commit()

        # Both should be created successfully
        result1 = await db_session.execute(select(DailyUsage).where(DailyUsage.api_key_id == key1.id))
        result2 = await db_session.execute(select(DailyUsage).where(DailyUsage.api_key_id == key2.id))

        assert result1.scalar_one().count == 10
        assert result2.scalar_one().count == 20

    async def test_daily_usage_increment_count(self, db_session, test_api_key):
        """Test incrementing usage count."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=5)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        # Increment count
        usage.count += 1
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == 6

    async def test_daily_usage_repr(self, db_session, test_api_key):
        """Test string representation of DailyUsage."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=15)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        repr_str = repr(usage)
        assert "DailyUsage" in repr_str
        assert str(test_api_key.id) in repr_str
        assert str(today) in repr_str
        assert "count=15" in repr_str

    async def test_daily_usage_query_by_day(self, db_session, test_api_key):
        """Test querying usage by specific day."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        usage_today = DailyUsage(api_key_id=test_api_key.id, day=today, count=10)
        usage_yesterday = DailyUsage(api_key_id=test_api_key.id, day=yesterday, count=20)
        db_session.add_all([usage_today, usage_yesterday])
        await db_session.commit()

        # Query only today's usage
        result = await db_session.execute(
            select(DailyUsage).where(DailyUsage.api_key_id == test_api_key.id, DailyUsage.day == today)
        )
        usage = result.scalar_one()

        assert usage.count == 10
        assert usage.day == today

    async def test_daily_usage_query_date_range(self, db_session, test_api_key):
        """Test querying usage within a date range."""
        today = date.today()
        days = [today - timedelta(days=i) for i in range(7)]

        # Create usage for last 7 days
        for i, day in enumerate(days):
            usage = DailyUsage(api_key_id=test_api_key.id, day=day, count=i * 10)
            db_session.add(usage)
        await db_session.commit()

        # Query last 3 days
        three_days_ago = today - timedelta(days=2)
        result = await db_session.execute(
            select(DailyUsage).where(DailyUsage.api_key_id == test_api_key.id, DailyUsage.day >= three_days_ago)
        )
        usages = result.scalars().all()

        assert len(usages) == 3

    async def test_daily_usage_delete(self, db_session, test_api_key):
        """Test deleting a daily usage record."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=5)
        db_session.add(usage)
        await db_session.commit()
        usage_id = usage.id

        # Delete the record
        await db_session.delete(usage)
        await db_session.commit()

        # Verify deletion
        result = await db_session.execute(select(DailyUsage).where(DailyUsage.id == usage_id))
        found = result.scalar_one_or_none()

        assert found is None

    async def test_daily_usage_update_count(self, db_session, test_api_key):
        """Test updating count value."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=10)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        # Update count to new value
        usage.count = 100
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == 100


class TestDailyUsageFieldValidation:
    """Tests for DailyUsage field validation and constraints."""

    async def test_daily_usage_api_key_id_required(self, db_session):
        """Test that api_key_id field is required."""
        today = date.today()
        usage = DailyUsage(
            day=today,
            count=0,
            # api_key_id is missing
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_daily_usage_day_required(self, db_session, test_api_key):
        """Test that day field is required."""
        usage = DailyUsage(
            api_key_id=test_api_key.id,
            count=0,
            # day is missing
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_daily_usage_foreign_key_constraint(self, db_session):
        """Test foreign key constraint on api_key_id."""
        fake_uuid = uuid.uuid4()
        today = date.today()

        usage = DailyUsage(api_key_id=fake_uuid, day=today, count=0)  # Non-existent API key
        db_session.add(usage)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_daily_usage_count_zero(self, db_session, test_api_key):
        """Test that count can be zero."""
        today = date.today()
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=0)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == 0

    async def test_daily_usage_count_large_number(self, db_session, test_api_key):
        """Test that count can handle large numbers."""
        today = date.today()
        large_count = 999999
        usage = DailyUsage(api_key_id=test_api_key.id, day=today, count=large_count)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.count == large_count

    async def test_daily_usage_past_date(self, db_session, test_api_key):
        """Test creating usage for a past date."""
        past_date = date(2020, 1, 1)
        usage = DailyUsage(api_key_id=test_api_key.id, day=past_date, count=5)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.day == past_date

    async def test_daily_usage_future_date(self, db_session, test_api_key):
        """Test creating usage for a future date."""
        future_date = date.today() + timedelta(days=365)
        usage = DailyUsage(api_key_id=test_api_key.id, day=future_date, count=5)
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.day == future_date
