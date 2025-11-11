"""Integration tests for authentication flows."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.services.auth import AuthService


class TestAuthFlow:
    """Test end-to-end authentication scenarios."""

    @pytest.mark.asyncio
    async def test_api_key_authentication_success(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test successful API key authentication."""
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": test_api_key.raw_key},
            json={
                "to": "test@example.com",
                "subject": "Auth Test",
                "text_body": "Test body",
            },
        )

        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_api_key_authentication_missing_header(self, test_client: AsyncClient):
        """Test authentication fails without API key header."""
        response = await test_client.post(
            "/api/v1/send",
            json={
                "to": "test@example.com",
                "subject": "Auth Test",
                "text_body": "Test body",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_authentication_invalid_format(self, test_client: AsyncClient):
        """Test authentication fails with invalid key format."""
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": "invalid_key_format"},
            json={
                "to": "test@example.com",
                "subject": "Auth Test",
                "text_body": "Test body",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_authentication_non_existent(self, test_client: AsyncClient):
        """Test authentication fails with non-existent key."""
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": "sk_nonexistent_12345678901234567890123456789012"},
            json={
                "to": "test@example.com",
                "subject": "Auth Test",
                "text_body": "Test body",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_api_key_rejection(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test inactive API keys are rejected."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Inactive Auth Test",
        )
        # Deactivate the key
        key_obj.is_active = False
        await db_session.commit()

        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test@example.com",
                "subject": "Auth Test",
                "text_body": "Test body",
            },
        )

        assert response.status_code in [401, 403]  # Inactive keys return 401 or 403

    @pytest.mark.asyncio
    async def test_api_key_deactivation_flow(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test API key can be deactivated mid-session."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Deactivation Test",
        )
        await db_session.commit()

        # First request succeeds
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test1@example.com",
                "subject": "Test 1",
                "text_body": "Body 1",
            },
        )
        assert response.status_code in [200, 202]

        # Deactivate the key
        key_obj.is_active = False
        await db_session.commit()

        # Second request should fail
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test2@example.com",
                "subject": "Test 2",
                "text_body": "Body 2",
            },
        )
        assert response.status_code in [401, 403]  # Inactive keys return 401 or 403

    @pytest.mark.asyncio
    async def test_api_key_reactivation_flow(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test API key can be reactivated."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Reactivation Test",
        )
        # Deactivate it first
        key_obj.is_active = False
        await db_session.commit()

        # First request fails (inactive)
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        assert response.status_code in [401, 403]  # Inactive keys return 401 or 403

        # Reactivate the key
        key_obj.is_active = True
        await db_session.commit()

        # Second request should succeed
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_multiple_api_keys_independence(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test multiple API keys work independently."""
        auth_service = AuthService(db_session, test_settings)

        key_obj1, key1 = await auth_service.create_api_key(
            name="Key 1",
        )
        key_obj2, key2 = await auth_service.create_api_key(
            name="Key 2",
        )
        await db_session.commit()

        # Both keys should work
        response1 = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": key1},
            json={
                "to": "test1@example.com",
                "subject": "Test 1",
                "text_body": "Body 1",
            },
        )
        assert response1.status_code in [200, 202]

        response2 = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": key2},
            json={
                "to": "test2@example.com",
                "subject": "Test 2",
                "text_body": "Body 2",
            },
        )
        assert response2.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_api_key_prefix_validation(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test API keys must have correct prefix."""
        # Try with wrong prefix
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": "pk_wrongprefix_12345678901234567890123456789012"},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_length_validation(self, test_client: AsyncClient):
        """Test API keys must have correct length."""
        # Too short
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": "sk_short"},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_with_case_sensitive_key(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test API key authentication is case-sensitive."""
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Case Test",
        )
        await db_session.commit()

        # Correct case succeeds
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        assert response.status_code in [200, 202]

        # Wrong case should fail
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": api_key.upper()},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_error_message(self, test_client: AsyncClient):
        """Test authentication error messages are informative."""
        response = await test_client.post(
            "/api/v1/send",
            headers={"X-API-Key": "sk_invalid_12345678901234567890123456789012"},
            json={
                "to": "test@example.com",
                "subject": "Test",
                "text_body": "Body",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_auth_persists_across_requests(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test authentication works across multiple requests."""
        for i in range(5):
            response = await test_client.post(
                "/api/v1/send",
                headers={"X-API-Key": test_api_key.raw_key},
                json={
                    "to": f"test{i}@example.com",
                    "subject": f"Test {i}",
                    "text_body": f"Body {i}",
                },
            )
            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_auth_header_name_case_insensitive(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test X-API-Key header name is case-insensitive (HTTP standard)."""
        # Try different casings
        headers_variants = [
            {"X-API-Key": test_api_key.raw_key},
            {"x-api-key": test_api_key.raw_key},
            {"X-Api-Key": test_api_key.raw_key},
        ]

        for headers in headers_variants:
            response = await test_client.post(
                "/api/v1/send",
                headers=headers,
                json={
                    "to": "test@example.com",
                    "subject": "Test",
                    "text_body": "Body",
                },
            )
            # Should succeed with any casing
            assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_auth_with_usage_endpoint(self, test_client: AsyncClient, test_api_key: APIKey):
        """Test authentication works for usage endpoint."""
        response = await test_client.get(
            "/api/v1/usage",
            headers={"X-API-Key": test_api_key.raw_key},
        )

        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_auth_with_health_endpoint_no_key_required(self, test_client: AsyncClient):
        """Test health endpoint doesn't require authentication."""
        response = await test_client.get("/health")

        # Should succeed without API key
        assert response.status_code in [200, 202]
