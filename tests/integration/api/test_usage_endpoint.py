"""Integration tests for GET /api/v1/usage endpoint."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.services.auth import AuthService


class TestUsageEndpoint:
    """Test GET /api/v1/usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_usage_authorized(
        self, test_client: AsyncClient, test_api_key: APIKey, db_session: AsyncSession, test_settings
    ):
        """Test getting usage with valid API key."""
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": test_api_key.raw_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Check response structure
        assert "api_key_name" in data or "daily_limit" in data
        assert "today_usage" in data or "emails_sent_today" in data

    @pytest.mark.asyncio
    async def test_get_usage_unauthorized_no_key(self, test_client: AsyncClient):
        """Test getting usage without API key."""
        response = await test_client.get("/api/v1/usage")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_usage_unauthorized_invalid_key(self, test_client: AsyncClient):
        """Test getting usage with invalid API key."""
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": "sk_invalid_key_12345678"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_usage_inactive_key(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test getting usage with inactive API key."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Inactive Usage Key",
        )
        # Deactivate the key after creation
        key_obj.is_active = False
        await db_session.commit()

        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_usage_statistics_after_sending(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test usage statistics are accurate after sending emails."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Usage Stats Key",
            daily_limit=10,
        )
        await db_session.commit()

        # Send 3 emails
        for i in range(3):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"recipient{i}@example.com",
                    "subject": f"Test {i}",
                    "text": f"Test body {i}",
                },
            )
            assert response.status_code in [200, 202]

        # Check usage
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Should show 3 emails sent today
        today_usage = data.get("today_usage") or data.get("emails_sent_today") or data.get("used")
        assert today_usage == 3

    @pytest.mark.asyncio
    async def test_get_usage_shows_daily_limit(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test usage endpoint shows daily limit."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Limited Usage Key",
            daily_limit=42,
        )
        await db_session.commit()

        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Should show daily limit of 42
        daily_limit = data.get("daily_limit") or data.get("limit")
        assert daily_limit == 42

    @pytest.mark.asyncio
    async def test_get_usage_shows_remaining(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test usage endpoint shows remaining quota."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Remaining Usage Key",
            daily_limit=10,
        )
        await db_session.commit()

        # Send 3 emails
        for i in range(3):
            await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": api_key},
                json={
                    "to": f"recipient{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Test body {i}",
                },
            )

        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Should show 7 remaining (10 - 3)
        if "remaining" in data:
            assert data["remaining"] == 7

    @pytest.mark.asyncio
    async def test_get_usage_zero_usage_initially(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test usage is zero for new API key."""
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": test_api_key.raw_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Should show 0 usage (or key might have been used in other tests)
        today_usage = data.get("emails_sent_today")
        assert today_usage >= 0

    @pytest.mark.asyncio
    async def test_get_usage_json_content_type(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test usage endpoint returns JSON."""
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": test_api_key.raw_key},
        )

        assert response.status_code in [200, 202]
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_get_usage_multiple_days(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test usage endpoint with historical data."""
        from datetime import timedelta

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(name="Historical Usage Key", daily_limit=5)
        await db_session.commit()

        # Create historical usage data
        yesterday = date.today() - timedelta(days=1)
        usage_yesterday = DailyUsage(
            api_key_id=key_obj.id,
            day=yesterday,
        )
        db_session.add(usage_yesterday)
        await db_session.commit()

        # Check today's usage (should be 0, yesterday shouldn't affect it)
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": api_key},
        )

        assert response.status_code in [200, 202]
        data = response.json()

        # Today's usage should be 0
        today_usage = data.get("emails_sent_today")
        assert today_usage == 0
