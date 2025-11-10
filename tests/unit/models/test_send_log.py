"""Unit tests for SendLog model."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.send_log import SendLog


class TestSendLogModel:
    """Tests for SendLog model creation and validation."""

    async def test_create_send_log_minimal(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test creating a send log with minimal required fields."""
        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.api_key_id == test_api_key.id
        assert log.recipient == "test@example.com"
        assert log.sent_at is not None
        assert isinstance(log.sent_at, datetime)
        assert log.message_id is None

    async def test_create_send_log_with_message_id(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test creating a send log with message_id."""
        message_id = "<unique-msg-id-123@example.com>"
        log = SendLog(api_key_id=test_api_key.id, recipient="user@example.com", message_id=message_id)
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message_id == message_id

    async def test_send_log_sent_at_auto_set(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test that sent_at is automatically set by the database."""
        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.sent_at is not None
        assert isinstance(log.sent_at, datetime)
        # Just verify it's set, timezone handling can vary

    async def test_send_log_multiple_logs_same_key(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test creating multiple logs for same API key."""
        log1 = SendLog(api_key_id=test_api_key.id, recipient="user1@example.com", message_id="msg-1")
        log2 = SendLog(api_key_id=test_api_key.id, recipient="user2@example.com", message_id="msg-2")
        log3 = SendLog(api_key_id=test_api_key.id, recipient="user3@example.com", message_id="msg-3")
        db_session.add_all([log1, log2, log3])
        await db_session.commit()

        # Query all logs for this key
        result = await db_session.execute(select(SendLog).where(SendLog.api_key_id == test_api_key.id))
        logs = result.scalars().all()

        assert len(logs) >= 3

    async def test_send_log_multiple_logs_different_keys(self, db_session: AsyncSession):
        """Test creating logs for different API keys."""
        # Create two API keys with unique hashes
        key1 = APIKey(key_hash=f"key1_hash_{uuid.uuid4().hex[:8]}", name="Key 1")
        key2 = APIKey(key_hash=f"key2_hash_{uuid.uuid4().hex[:8]}", name="Key 2")
        db_session.add_all([key1, key2])
        await db_session.commit()

        log1 = SendLog(api_key_id=key1.id, recipient="user1@example.com")
        log2 = SendLog(api_key_id=key2.id, recipient="user2@example.com")
        db_session.add_all([log1, log2])
        await db_session.commit()

        # Query logs for each key
        result1 = await db_session.execute(select(SendLog).where(SendLog.api_key_id == key1.id))
        result2 = await db_session.execute(select(SendLog).where(SendLog.api_key_id == key2.id))

        assert result1.scalar_one().recipient == "user1@example.com"
        assert result2.scalar_one().recipient == "user2@example.com"

    async def test_send_log_repr(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test string representation of SendLog."""
        log = SendLog(api_key_id=test_api_key.id, recipient="repr@example.com", message_id="repr-msg-id")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        repr_str = repr(log)
        assert "SendLog" in repr_str
        assert "repr@example.com" in repr_str
        assert "sent_at=" in repr_str

    async def test_send_log_query_by_recipient(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test querying logs by recipient email."""
        target_email = "target@example.com"

        log1 = SendLog(api_key_id=test_api_key.id, recipient=target_email)
        log2 = SendLog(api_key_id=test_api_key.id, recipient="other@example.com")
        db_session.add_all([log1, log2])
        await db_session.commit()

        # Query by specific recipient
        result = await db_session.execute(select(SendLog).where(SendLog.recipient == target_email))
        logs = result.scalars().all()

        assert len(logs) >= 1
        assert all(log.recipient == target_email for log in logs)

    async def test_send_log_query_by_message_id(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test querying logs by message_id."""
        message_id = "unique-message-id-xyz"

        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com", message_id=message_id)
        db_session.add(log)
        await db_session.commit()

        # Query by message_id
        result = await db_session.execute(select(SendLog).where(SendLog.message_id == message_id))
        found_log = result.scalar_one_or_none()

        assert found_log is not None
        assert found_log.message_id == message_id

    async def test_send_log_delete(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test deleting a send log."""
        log = SendLog(api_key_id=test_api_key.id, recipient="delete@example.com")
        db_session.add(log)
        await db_session.commit()
        log_id = log.id

        # Delete the log
        await db_session.delete(log)
        await db_session.commit()

        # Verify deletion
        result = await db_session.execute(select(SendLog).where(SendLog.id == log_id))
        found = result.scalar_one_or_none()

        assert found is None

    async def test_send_log_recipient_email_formats(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test various email formats in recipient field."""
        email_formats = [
            "simple@example.com",
            "with.dots@example.com",
            "with+plus@example.com",
            "123numbers@example.com",
            "under_score@example.com",
        ]

        logs = []
        for email in email_formats:
            log = SendLog(api_key_id=test_api_key.id, recipient=email)
            logs.append(log)

        db_session.add_all(logs)
        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(select(SendLog).where(SendLog.api_key_id == test_api_key.id))
        created_logs = result.scalars().all()

        assert len(created_logs) >= len(email_formats)

    async def test_send_log_long_message_id(self, db_session, test_api_key):
        """Test send log with long message_id."""
        long_message_id = "x" * 500  # Long message ID

        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com", message_id=long_message_id)
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message_id == long_message_id

    async def test_send_log_update_message_id(self, db_session, test_api_key):
        """Test updating message_id after creation."""
        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com", message_id="original-id")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        # Update message_id
        log.message_id = "updated-id"
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message_id == "updated-id"


class TestSendLogFieldValidation:
    """Tests for SendLog field validation and constraints."""

    async def test_send_log_api_key_id_required(self, db_session):
        """Test that api_key_id field is required."""
        log = SendLog(
            recipient="test@example.com"
            # api_key_id is missing
        )
        db_session.add(log)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_send_log_recipient_required(self, db_session, test_api_key):
        """Test that recipient field is required."""
        log = SendLog(
            api_key_id=test_api_key.id
            # recipient is missing
        )
        db_session.add(log)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_send_log_foreign_key_constraint(self, db_session):
        """Test foreign key constraint on api_key_id."""
        fake_uuid = uuid.uuid4()

        log = SendLog(api_key_id=fake_uuid, recipient="test@example.com")  # Non-existent API key
        db_session.add(log)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_send_log_recipient_max_length(self, db_session, test_api_key):
        """Test recipient field with maximum length."""
        long_email = "a" * 240 + "@example.com"  # ~255 chars

        log = SendLog(api_key_id=test_api_key.id, recipient=long_email)
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.recipient == long_email

    async def test_send_log_null_message_id(self, db_session, test_api_key):
        """Test that message_id can be null."""
        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com", message_id=None)
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message_id is None

    async def test_send_log_empty_message_id(self, db_session, test_api_key):
        """Test that message_id can be empty string."""
        log = SendLog(api_key_id=test_api_key.id, recipient="test@example.com", message_id="")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message_id == ""

    async def test_send_log_duplicate_message_ids(self, db_session, test_api_key):
        """Test that duplicate message_ids are allowed (no unique constraint)."""
        message_id = "duplicate-id"

        log1 = SendLog(api_key_id=test_api_key.id, recipient="user1@example.com", message_id=message_id)
        log2 = SendLog(api_key_id=test_api_key.id, recipient="user2@example.com", message_id=message_id)
        db_session.add_all([log1, log2])
        await db_session.commit()

        # Both should be created successfully
        result = await db_session.execute(select(SendLog).where(SendLog.message_id == message_id))
        logs = result.scalars().all()

        assert len(logs) >= 2
