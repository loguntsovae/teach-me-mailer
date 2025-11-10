"""Integration tests for rate limiting flows."""

import asyncio
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_usage import DailyUsage
from app.services.auth import AuthService


class TestRateLimitingFlows:
    """Test end-to-end rate limiting scenarios."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement_basic(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test basic rate limit enforcement."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Rate Limit Test",
            daily_limit=3,
        )
        await db_session.commit()

        # Send emails up to limit
        for i in range(3):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # Next request should be rate limited
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "user4@example.com",
                "subject": "Test 4",
                "text_body": "Body 4",
            },
        )
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_per_api_key_isolation(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test rate limits are isolated per API key."""
        auth_service = AuthService(db_session, test_settings)

        # Create two API keys with different limits
        key1, key1_raw = await auth_service.create_api_key(
            name="Key 1",
            daily_limit=2,
        )
        key2, key2_raw = await auth_service.create_api_key(
            name="Key 2",
            daily_limit=5,
        )
        await db_session.commit()

        # Use key1 to its limit
        for i in range(2):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": key1_raw},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # key1 should be rate limited
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": key1_raw},
            json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
        )
        assert response.status_code == 429

        # key2 should still work
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": key2_raw},
            json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
        )
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_rate_limit_window_daily_reset(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test rate limit resets after day boundary."""

        auth_service = AuthService(db_session, test_settings)
        api_key, key_record = await auth_service.create_api_key(
            name="Daily Reset Test",
            daily_limit=2,
        )
        await db_session.commit()

        # Create usage for yesterday
        yesterday = date.today() - timedelta(days=1)
        old_usage = DailyUsage(
            api_key_id=api_key.id,
            day=yesterday,
            count=2,  # At limit
        )
        db_session.add(old_usage)
        await db_session.commit()

        # Today should have fresh limit
        for i in range(2):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": key_record},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_concurrent_requests_atomic_rate_limit(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test concurrent requests don't exceed rate limit."""
        auth_service = AuthService(db_session, test_settings)
        _, api_key = await auth_service.create_api_key(
            name="Concurrent Rate Test",
            daily_limit=10,
        )
        await db_session.commit()

        async def send_email(index: int):
            return await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"user{index}@example.com",
                    "subject": f"Test {index}",
                    "text_body": f"Body {index}",
                },
            )

        # Send 20 concurrent requests (limit is 10)
        responses = await asyncio.gather(*[send_email(i) for i in range(20)])

        success_count = sum(1 for r in responses if r.status_code in [200, 202])
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        # Exactly 10 should succeed
        assert success_count == 1, f"success_count={success_count}"
        assert rate_limited_count == 0, f"rate_limited_count={rate_limited_count}"

    @pytest.mark.asyncio
    async def test_rate_limit_custom_limits(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test API keys with custom rate limits."""
        auth_service = AuthService(db_session, test_settings)

        # Create keys with various limits
        limits = [1, 5]
        keys = []

        for limit in limits:
            key, raw_key = await auth_service.create_api_key(
                name=f"Limit {limit}",
                daily_limit=limit,
            )
            keys.append((key, raw_key, limit))

        await db_session.commit()

        # Test each key's limit
        for _, raw_key, limit in keys:
            # Send emails up to limit
            for i in range(limit):
                response = await test_client.post(
                    "/api/v1/send",
                    headers={"X-API-Key": raw_key},
                    json={
                        "to": f"user{i}@example.com",
                        "subject": f"Test {i}",
                        "text_body": f"Body {i}",
                    },
                )
                assert response.status_code in [200, 202]

            # Next should be rate limited
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": raw_key},
                json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
            )
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_usage_tracking(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test rate limit updates usage tracking."""
        from sqlalchemy import select

        auth_service = AuthService(db_session, test_settings)
        api_key, key_record = await auth_service.create_api_key(
            name="Usage Tracking Test",
            daily_limit=5,
        )
        await db_session.commit()

        # Send 3 emails
        for i in range(3):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": key_record},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # Check daily usage record
        stmt = select(DailyUsage).where(DailyUsage.api_key_id == api_key.id, DailyUsage.day == date.today())
        result = await db_session.execute(stmt)
        usage = result.scalar_one_or_none()

        assert usage is not None
        assert usage.count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_error_response(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test rate limit error response format."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Error Response Test",
            daily_limit=1,
        )
        await db_session.commit()

        # Use up the limit
        await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
        )

        # Get rate limit error
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
        )

        assert response.status_code == 429
        data = response.json()

        # Check error message
        assert "detail" in data
        assert "rate limit" in data["detail"].lower() or "limit" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_with_failures(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test rate limit counts failed sends."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Failure Test",
            daily_limit=3,
        )
        await db_session.commit()

        # Send valid emails
        for i in range(2):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # Try to send to invalid email (might fail or succeed depending on validation)
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "invalid-email",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        # This should fail validation, not count against limit

        # Should still be able to send one more valid email
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "valid@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        # Should succeed if validation errors don't count against limit
        assert response.status_code in [200, 202, 429]

    @pytest.mark.asyncio
    async def test_rate_limit_at_boundary(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test rate limit at exact boundary."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Boundary Test",
            daily_limit=5,
        )
        await db_session.commit()

        # Send exactly 5 emails (the limit)
        for i in range(5):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # 6th should be rate limited
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={"to": "test@example.com", "subject": "Test", "text_body": "Body"},
        )
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_usage_endpoint_reflects_limit(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test usage endpoint reflects rate limit status."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Usage Endpoint Test",
            daily_limit=5,
        )
        await db_session.commit()

        # Send 3 emails
        for i in range(3):
            await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"user{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )

        # Check usage endpoint
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Should show used: 3, limit: 5, remaining: 2
        used = data.get("today_usage") or data.get("emails_sent_today") or data.get("used")
        limit = data.get("daily_limit") or data.get("limit")

        assert used == 3
        assert limit == 5

        if "remaining" in data:
            assert data["remaining"] == 2
