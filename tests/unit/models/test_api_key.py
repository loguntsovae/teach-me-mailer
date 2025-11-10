"""Unit tests for APIKey model."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.api_key import APIKey


class TestAPIKeyModel:
    """Tests for APIKey model creation and validation."""

    async def test_create_api_key_minimal(self, db_session):
        """Test creating an API key with minimal required fields."""
        api_key = APIKey(key_hash="test_hash_123", name="Test Key")
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.id is not None
        assert isinstance(api_key.id, uuid.UUID)
        assert api_key.key_hash == "test_hash_123"
        assert api_key.name == "Test Key"
        assert api_key.is_active is True  # Default value
        assert api_key.daily_limit is None
        assert api_key.allowed_recipients is None
        assert api_key.created_at is not None
        assert isinstance(api_key.created_at, datetime)

    async def test_create_api_key_with_daily_limit(self, db_session):
        """Test creating an API key with custom daily limit."""
        api_key = APIKey(key_hash="test_hash_456", name="Limited Key", daily_limit=100)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.daily_limit == 100

    async def test_create_api_key_with_allowed_recipients(self, db_session):
        """Test creating an API key with allowed recipients list."""
        recipients = ["user1@example.com", "user2@example.com"]
        api_key = APIKey(key_hash="test_hash_789", name="Restricted Key", allowed_recipients=recipients)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.allowed_recipients == recipients
        assert len(api_key.allowed_recipients) == 2
        assert "user1@example.com" in api_key.allowed_recipients

    async def test_create_api_key_inactive(self, db_session):
        """Test creating an inactive API key."""
        api_key = APIKey(key_hash="test_hash_inactive", name="Inactive Key", is_active=False)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.is_active is False

    async def test_api_key_unique_hash_constraint(self, db_session):
        """Test that key_hash must be unique."""
        api_key1 = APIKey(key_hash="duplicate_hash", name="Key 1")
        db_session.add(api_key1)
        await db_session.commit()

        # Try to create another key with the same hash
        api_key2 = APIKey(key_hash="duplicate_hash", name="Key 2")
        db_session.add(api_key2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_api_key_repr(self, db_session):
        """Test string representation of APIKey."""
        api_key = APIKey(
            key_hash="test_hash_repr", name="Repr Key", is_active=True, allowed_recipients=["test@example.com"]
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        repr_str = repr(api_key)
        assert "APIKey" in repr_str
        assert "Repr Key" in repr_str
        assert "active=True" in repr_str
        assert "test@example.com" in repr_str

    async def test_api_key_query_by_hash(self, db_session):
        """Test querying API key by hash."""
        api_key = APIKey(key_hash="query_hash_123", name="Query Key")
        db_session.add(api_key)
        await db_session.commit()

        # Query by hash
        result = await db_session.execute(select(APIKey).where(APIKey.key_hash == "query_hash_123"))
        found_key = result.scalar_one_or_none()

        assert found_key is not None
        assert found_key.name == "Query Key"
        assert found_key.key_hash == "query_hash_123"

    async def test_api_key_query_active_only(self, db_session):
        """Test querying only active API keys."""
        # Create active key
        active_key = APIKey(key_hash="active_hash", name="Active Key", is_active=True)
        # Create inactive key
        inactive_key = APIKey(key_hash="inactive_hash", name="Inactive Key", is_active=False)
        db_session.add_all([active_key, inactive_key])
        await db_session.commit()

        # Query only active keys
        result = await db_session.execute(select(APIKey).where(APIKey.is_active == True))
        active_keys = result.scalars().all()

        assert len(active_keys) >= 1
        assert all(key.is_active for key in active_keys)

    async def test_api_key_update_is_active(self, db_session):
        """Test updating is_active field."""
        api_key = APIKey(key_hash="update_hash", name="Update Key", is_active=True)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        # Update to inactive
        api_key.is_active = False
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.is_active is False

    async def test_api_key_update_allowed_recipients(self, db_session):
        """Test updating allowed_recipients field."""
        api_key = APIKey(
            key_hash="update_recipients_hash", name="Update Recipients Key", allowed_recipients=["old@example.com"]
        )
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        # Update recipients
        api_key.allowed_recipients = ["new1@example.com", "new2@example.com"]
        await db_session.commit()
        await db_session.refresh(api_key)

        assert len(api_key.allowed_recipients) == 2
        assert "new1@example.com" in api_key.allowed_recipients
        assert "old@example.com" not in api_key.allowed_recipients

    async def test_api_key_delete(self, db_session):
        """Test deleting an API key."""
        api_key = APIKey(key_hash="delete_hash", name="Delete Key")
        db_session.add(api_key)
        await db_session.commit()
        key_id = api_key.id

        # Delete the key
        await db_session.delete(api_key)
        await db_session.commit()

        # Verify deletion
        result = await db_session.execute(select(APIKey).where(APIKey.id == key_id))
        found_key = result.scalar_one_or_none()

        assert found_key is None

    async def test_api_key_empty_allowed_recipients(self, db_session):
        """Test creating API key with empty allowed_recipients list."""
        api_key = APIKey(key_hash="empty_recipients_hash", name="Empty Recipients Key", allowed_recipients=[])
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.allowed_recipients == []
        assert isinstance(api_key.allowed_recipients, list)

    async def test_api_key_created_at_auto_set(self, db_session):
        """Test that created_at is automatically set by the database."""
        api_key = APIKey(key_hash="auto_timestamp_hash", name="Auto Timestamp Key")
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.created_at is not None
        assert isinstance(api_key.created_at, datetime)
        # Just verify it's set, timezone handling can vary


class TestAPIKeyFieldValidation:
    """Tests for APIKey field validation and constraints."""

    async def test_api_key_name_required(self, db_session):
        """Test that name field is required."""
        api_key = APIKey(
            key_hash="test_hash_no_name",
            # name is missing
        )
        db_session.add(api_key)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_api_key_hash_required(self, db_session):
        """Test that key_hash field is required."""
        api_key = APIKey(
            name="No Hash Key",
            # key_hash is missing
        )
        db_session.add(api_key)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_api_key_name_max_length(self, db_session):
        """Test API key name with maximum length."""
        long_name = "A" * 255
        api_key = APIKey(key_hash="long_name_hash", name=long_name)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.name == long_name
        assert len(api_key.name) == 255

    async def test_api_key_daily_limit_zero(self, db_session):
        """Test API key with daily_limit set to zero."""
        api_key = APIKey(key_hash="zero_limit_hash", name="Zero Limit Key", daily_limit=0)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.daily_limit == 0

    async def test_api_key_daily_limit_negative(self, db_session):
        """Test API key with negative daily_limit (should be allowed by DB)."""
        api_key = APIKey(key_hash="negative_limit_hash", name="Negative Limit Key", daily_limit=-1)
        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.daily_limit == -1
