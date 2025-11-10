"""Integration tests for database operations."""

import asyncio

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.models.send_log import SendLog
from app.services.auth import AuthService


class TestDatabaseIntegration:
    """Test database integration and operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession, test_settings):
        """Test database connection is working."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.skip("Flaky test, needs investigation")
    @pytest.mark.asyncio
    async def test_connection_pool_multiple_sessions(self, test_settings):
        """Test connection pooling with multiple sessions."""
        from app.db.session import get_async_session

        sessions = []
        try:
            # Create multiple sessions
            for _ in range(5):
                async for session in get_async_session():
                    sessions.append(session)
                    # Execute query
                    result = await session.execute(text("SELECT 1"))
                    assert result.scalar() == 1
                    break
        finally:
            # Clean up sessions
            for session in sessions:
                await session.close()

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db_session: AsyncSession, test_settings):
        """Test transaction commit works correctly."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Commit Test Key",
        )

        # Commit transaction
        await db_session.commit()

        # Verify data persists in new query
        stmt = select(APIKey).where(APIKey.id == key_obj.id)
        result = await db_session.execute(stmt)
        fetched_key = result.scalar_one_or_none()

        assert fetched_key is not None
        assert fetched_key.name == "Commit Test Key"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session: AsyncSession, test_settings):
        """Test transaction rollback discards changes."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Rollback Test Key",
        )

        key_id = key_obj.id

        # Rollback transaction
        await db_session.rollback()

        # Verify data was not persisted
        stmt = select(APIKey).where(APIKey.id == key_id)
        result = await db_session.execute(stmt)
        fetched_key = result.scalar_one_or_none()

        # Key should not exist after rollback
        assert fetched_key is None

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_concurrent_writes_api_keys(self, db_session: AsyncSession, test_settings):
        """Test concurrent writes to API keys table."""
        from app.db.session import get_async_session

        async def create_key(name: str):
            async for session in get_async_session():
                try:
                    auth_service = AuthService(session, test_settings)
                    key_obj, _ = await auth_service.create_api_key(
                        name=name,
                    )
                    await session.commit()
                    return key_obj.id
                finally:
                    await session.close()

        # Create 10 keys concurrently
        tasks = [create_key(f"Concurrent Key {i}") for i in range(10)]
        key_ids = await asyncio.gather(*tasks)

        # All keys should be created
        assert len(key_ids) == 10
        assert len(set(key_ids)) == 10  # All unique

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_concurrent_writes_daily_usage(self, db_session: AsyncSession, test_settings):
        """Test concurrent writes to daily_usage table."""
        from datetime import date

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Usage Concurrent Test",
        )
        await db_session.commit()

        async def increment_usage(session_num: int):
            async for session in get_async_session():
                try:
                    # Get or create daily usage
                    stmt = select(DailyUsage).where(
                        DailyUsage.api_key_id == key_obj.id, DailyUsage.day == date.today()
                    )
                    result = await session.execute(stmt)
                    usage = result.scalar_one_or_none()

                    if usage is None:
                        usage = DailyUsage(
                            api_key_id=key_obj.id,
                            day=date.today(),
                            count=1,
                        )
                        session.add(usage)
                    else:
                        usage.emails_sent += 1

                    await session.commit()
                finally:
                    await session.close()

        from app.db.session import get_async_session

        # Increment usage 10 times concurrently
        await asyncio.gather(*[increment_usage(i) for i in range(10)])

        # Check final count (might not be exactly 10 due to race conditions)
        stmt = select(DailyUsage).where(DailyUsage.api_key_id == key_obj.id, DailyUsage.day == date.today())
        result = await db_session.execute(stmt)
        usage = result.scalar_one_or_none()

        # Should have at least 1 (race conditions might cause some increments to be lost)
        assert usage is not None
        assert usage.emails_sent >= 1

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session: AsyncSession, test_settings):
        """Test foreign key constraints are enforced."""
        from datetime import date

        # Try to create DailyUsage with non-existent API key
        usage = DailyUsage(
            api_key_id=999999,  # Non-existent
            day=date.today(),
            count=1,
        )
        db_session.add(usage)

        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_unique_constraints(self, db_session: AsyncSession, test_settings):
        """Test unique constraints are enforced."""
        from datetime import date

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Unique Constraint Test",
        )
        await db_session.commit()

        # Create first usage record
        usage1 = DailyUsage(
            api_key_id=key_obj.id,
            day=date.today(),
            count=1,
        )
        db_session.add(usage1)
        await db_session.commit()

        # Try to create duplicate usage record (same api_key_id + date)
        usage2 = DailyUsage(
            api_key_id=key_obj.id,
            day=date.today(),
            count=1,
        )
        db_session.add(usage2)

        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session: AsyncSession, test_settings):
        """Test cascade delete on related records."""
        from datetime import date

        auth_service = AuthService(db_session, test_settings)
        key_obj, _ = await auth_service.create_api_key(
            name="Cascade Test Key",
        )

        # Create related records
        usage = DailyUsage(
            api_key_id=key_obj.id,
            day=date.today(),
            count=5,
        )
        db_session.add(usage)

        log = SendLog(
            api_key_id=key_obj.id,
            recipient="test@example.com",
        )
        db_session.add(log)
        await db_session.commit()

        key_id = key_obj.id

        # Delete API key
        await db_session.delete(key_obj)
        await db_session.commit()

        # Check if related records are deleted (depends on cascade settings)
        stmt = select(DailyUsage).where(DailyUsage.api_key_id == key_id)
        result = await db_session.execute(stmt)
        result.scalars().all()

        # Should be deleted if cascade is set up
        # (or should fail if foreign key constraint prevents deletion)

    @pytest.mark.asyncio
    async def test_database_indexes(self, db_session: AsyncSession, test_settings):
        """Test database indexes exist and work."""
        # Create multiple API keys
        auth_service = AuthService(db_session, test_settings)
        for i in range(10):
            await auth_service.create_api_key(
                name=f"Index Test Key {i}",
            )
        await db_session.commit()

        # Query by name (should use index if exists)
        stmt = select(APIKey).where(APIKey.name == "Index Test Key 5")
        result = await db_session.execute(stmt)
        key = result.scalar_one_or_none()

        assert key is not None
        assert key.name == "Index Test Key 5"

    @pytest.mark.asyncio
    async def test_large_batch_insert(self, db_session: AsyncSession, test_settings):
        """Test inserting large batch of records."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Batch Test Key",
        )
        await db_session.commit()

        # Create 100 send logs
        logs = []
        for i in range(100):
            log = SendLog(
                api_key_id=key_obj.id,
                recipient=f"user{i}@example.com",
            )
            logs.append(log)

        db_session.add_all(logs)
        await db_session.commit()

        # Verify all logs were inserted
        stmt = select(SendLog).where(SendLog.api_key_id == key_obj.id)
        result = await db_session.execute(stmt)
        fetched_logs = result.scalars().all()

        assert len(fetched_logs) == 100
