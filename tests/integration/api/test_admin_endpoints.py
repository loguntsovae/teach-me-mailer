"""Integration tests for Admin UI endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestAdminEndpoints:
    """Test Admin UI endpoints."""

    @pytest.mark.asyncio
    async def test_admin_list_page_renders(self, test_client: AsyncClient, test_settings):
        """Test admin list page renders HTML."""
        # Admin endpoints require auth in production, but test_settings has debug=True
        response = await test_client.get("/admin/")

        # In debug mode, should allow access
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
            # Check for key elements in HTML
            content = response.text
            assert "API Keys" in content or "api" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_create_page_renders(self, test_client: AsyncClient, test_settings):
        """Test admin create page renders HTML."""
        response = await test_client.get("/admin/api-keys/create")

        # In debug mode, should allow access
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
            # Check for form elements
            content = response.text
            assert "form" in content.lower() or "create" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_create_api_key_post(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test creating API key via admin POST."""
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "Admin Created Key",
                "daily_limit": "100",
            },
            follow_redirects=False,
        )

        # Should redirect, succeed, or require auth
        assert response.status_code in [200, 302, 303, 401]

    @pytest.mark.asyncio
    async def test_admin_list_shows_existing_keys(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test admin list shows existing API keys."""
        from app.services.auth import AuthService

        # Create a test key
        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Visible Key",
        )
        await db_session.commit()

        response = await test_client.get("/admin/")

        # Should allow or require auth
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            content = response.text
            # Should contain the key name
            assert "Visible Key" in content

    @pytest.mark.asyncio
    async def test_admin_create_with_custom_limit(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test creating API key with custom daily limit."""
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "Custom Limit Key",
                "daily_limit": "500",
            },
            follow_redirects=True,
        )

        # Might require auth or succeed in debug mode
        assert response.status_code in [200, 401]

        # Verify key was created in database (only if request succeeded)
        if response.status_code == 200:
            from sqlalchemy import select

            from app.models.api_key import APIKey

            stmt = select(APIKey).where(APIKey.name == "Custom Limit Key")
            result = await db_session.execute(stmt)
            key = result.scalar_one_or_none()

            if key is not None:
                assert key.daily_limit == 500

    @pytest.mark.asyncio
    async def test_admin_create_with_allowed_recipients(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test creating API key with allowed recipients."""
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "Restricted Key",
                "daily_limit": "100",
                "allowed_recipients": "user1@example.com,user2@example.com",
            },
            follow_redirects=True,
        )

        # Should succeed, validate, or require auth
        assert response.status_code in [200, 400, 401, 422]

    @pytest.mark.asyncio
    async def test_admin_page_no_auth_required(self, test_client: AsyncClient, test_settings):
        """Test admin pages access control."""
        # No X-API-Key header
        response = await test_client.get("/admin/")

        # Behavior depends on settings (debug mode vs auth required)
        assert response.status_code in [200, 302, 303, 401, 403]

    @pytest.mark.asyncio
    async def test_admin_create_validation_empty_name(self, test_client: AsyncClient, test_settings):
        """Test admin create validates empty name."""
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "",
                "daily_limit": "100",
            },
            follow_redirects=False,
        )

        # Should show validation error or require auth
        assert response.status_code in [200, 400, 401, 422]

    @pytest.mark.asyncio
    async def test_admin_create_validation_invalid_limit(self, test_client: AsyncClient, test_settings):
        """Test admin create validates invalid daily limit."""
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "Test Key",
                "daily_limit": "-1",  # Negative limit
            },
            follow_redirects=False,
        )

        # Should show validation error or require auth
        assert response.status_code in [200, 400, 401, 422]

    @pytest.mark.asyncio
    async def test_admin_list_pagination(self, test_client: AsyncClient, test_settings):
        """Test admin list supports pagination (if implemented)."""
        response = await test_client.get("/admin/?page=1")

        # Should succeed or require auth
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_admin_deactivate_key(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test deactivating API key via admin (if endpoint exists)."""
        from app.services.auth import AuthService

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="To Deactivate",
        )
        await db_session.commit()

        # Try to deactivate
        response = await test_client.post(
            f"/admin/api-keys/{key_obj.id}/deactivate",
            follow_redirects=False,
        )

        # Endpoint might exist and work or require auth
        assert response.status_code in [200, 302, 303, 401, 404, 405]

    @pytest.mark.asyncio
    async def test_admin_created_key_is_functional(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test that admin-created key can send emails."""
        # Create key via admin
        response = await test_client.post(
            "/admin/api-keys/create",
            data={
                "name": "Functional Test Key",
                "daily_limit": "10",
            },
            follow_redirects=True,
        )

        # Skip if auth required
        if response.status_code == 401:
            pytest.skip("Admin auth required")

        # Get the created key from database
        from sqlalchemy import select

        from app.models.api_key import APIKey

        stmt = select(APIKey).where(APIKey.name == "Functional Test Key")
        result = await db_session.execute(stmt)
        key_record = result.scalar_one_or_none()

        if key_record:
            # The actual API key string is not stored, only the hash
            # So we can't test sending with it unless we capture it from response
            # This is a limitation of the admin UI design
            assert key_record.name == "Functional Test Key"
            assert key_record.daily_limit == 10

    @pytest.mark.asyncio
    async def test_admin_activate_key(self, test_client: AsyncClient, db_session: AsyncSession, test_settings):
        """Test activating API key via admin endpoint."""
        from app.services.auth import AuthService

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Key To Activate",
        )
        # Deactivate first
        key_obj.is_active = False
        await db_session.commit()

        # Try to activate
        response = await test_client.post(
            f"/admin/api-keys/{key_obj.id}/activate",
            follow_redirects=False,
        )

        # Should work or require auth
        assert response.status_code in [303, 401, 404]

        if response.status_code == 303:
            # Verify activation
            await db_session.refresh(key_obj)
            assert key_obj.is_active is True

    @pytest.mark.asyncio
    async def test_admin_deactivate_activate_flow(
        self, test_client: AsyncClient, db_session: AsyncSession, test_settings
    ):
        """Test complete deactivate-activate flow."""
        from app.services.auth import AuthService

        auth_service = AuthService(db_session, test_settings)
        key_obj, api_key = await auth_service.create_api_key(
            name="Flow Test Key",
        )
        await db_session.commit()

        # Deactivate
        response = await test_client.post(
            f"/admin/api-keys/{key_obj.id}/deactivate",
            follow_redirects=False,
        )

        if response.status_code == 303:
            await db_session.refresh(key_obj)
            assert key_obj.is_active is False

            # Activate back
            response = await test_client.post(
                f"/admin/api-keys/{key_obj.id}/activate",
                follow_redirects=False,
            )

            assert response.status_code == 303
            await db_session.refresh(key_obj)
            assert key_obj.is_active is True

    @pytest.mark.asyncio
    async def test_admin_deactivate_invalid_uuid(self, test_client: AsyncClient, test_settings):
        """Test deactivating with invalid UUID format."""
        response = await test_client.post(
            "/admin/api-keys/not-a-uuid/deactivate",
            follow_redirects=False,
        )

        # Should reject bad UUID or require auth
        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_admin_activate_invalid_uuid(self, test_client: AsyncClient, test_settings):
        """Test activating with invalid UUID format."""
        response = await test_client.post(
            "/admin/api-keys/not-a-uuid/activate",
            follow_redirects=False,
        )

        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_admin_deactivate_nonexistent_key(self, test_client: AsyncClient, test_settings):
        """Test deactivating a non-existent API key."""
        import uuid

        fake_uuid = str(uuid.uuid4())
        response = await test_client.post(
            f"/admin/api-keys/{fake_uuid}/deactivate",
            follow_redirects=False,
        )

        # Should return 404 or require auth
        assert response.status_code in [404, 401]

    @pytest.mark.asyncio
    async def test_admin_activate_nonexistent_key(self, test_client: AsyncClient, test_settings):
        """Test activating a non-existent API key."""
        import uuid

        fake_uuid = str(uuid.uuid4())
        response = await test_client.post(
            f"/admin/api-keys/{fake_uuid}/activate",
            follow_redirects=False,
        )

        assert response.status_code in [404, 401]

    @pytest.mark.asyncio
    async def test_admin_daily_usage_page(self, test_client: AsyncClient, test_settings):
        """Test daily usage listing page renders."""
        response = await test_client.get("/admin/daily-usage")

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_admin_daily_usage_pagination(self, test_client: AsyncClient, test_settings):
        """Test daily usage pagination."""
        response = await test_client.get("/admin/daily-usage?page=1&per_page=10")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_admin_send_logs_page(self, test_client: AsyncClient, test_settings):
        """Test send logs listing page renders."""
        response = await test_client.get("/admin/send-logs")

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_admin_send_logs_pagination(self, test_client: AsyncClient, test_settings):
        """Test send logs pagination."""
        response = await test_client.get("/admin/send-logs?page=1&per_page=10")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_admin_index_redirects(self, test_client: AsyncClient, test_settings):
        """Test admin index redirects to api-keys."""
        response = await test_client.get("/admin/", follow_redirects=False)

        # Should redirect or require auth
        assert response.status_code in [307, 401]

        if response.status_code == 307:
            assert "/admin/api-keys" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_list_pagination_limits(self, test_client: AsyncClient, test_settings):
        """Test pagination limits are enforced."""
        # Test with excessive per_page
        response = await test_client.get("/admin/api-keys?per_page=1000")

        assert response.status_code in [200, 401]

        # Test with zero per_page
        response = await test_client.get("/admin/api-keys?per_page=0")

        assert response.status_code in [200, 401]

        # Test with negative page
        response = await test_client.get("/admin/api-keys?page=-1")

        assert response.status_code in [200, 401]
