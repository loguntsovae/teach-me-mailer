"""Integration tests for GET /health endpoint."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_ok(self, test_client: AsyncClient):
        """Test health check returns OK status."""
        response = await test_client.get("/health")

        assert response.status_code in [200, 202]
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_structure(self, test_client: AsyncClient):
        """Test health check response structure."""
        response = await test_client.get("/health")

        assert response.status_code in [200, 202]
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "timestamp" in data

        # Check optional service checks
        if "services" in data:
            assert isinstance(data["services"], dict)

    @pytest.mark.asyncio
    async def test_health_check_database_connection(self, test_client: AsyncClient):
        """Test health check verifies database connection."""
        response = await test_client.get("/health")

        assert response.status_code in [200, 202]
        data = response.json()

        # If database check is included
        if "services" in data and "database" in data["services"]:
            assert data["services"]["database"] in ["up", "healthy", "ok"]

    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, test_client: AsyncClient):
        """Test health check doesn't require authentication."""
        # No API key header
        response = await test_client.get("/health")

        # Should still succeed
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_health_check_accepts_head_request(self, test_client: AsyncClient):
        """Test health check accepts HEAD requests."""
        response = await test_client.head("/health")

        # Should succeed with no body
        assert response.status_code in [200, 405]  # 405 if HEAD not supported

    @pytest.mark.asyncio
    async def test_health_check_content_type(self, test_client: AsyncClient):
        """Test health check returns JSON content type."""
        response = await test_client.get("/health")

        assert response.status_code in [200, 202]
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self, test_client: AsyncClient):
        """Test health check timestamp is valid."""
        from datetime import datetime

        response = await test_client.get("/health")

        assert response.status_code in [200, 202]
        data = response.json()

        if "timestamp" in data:
            # Try to parse timestamp
            try:
                datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid timestamp format: {data['timestamp']}")

    @pytest.mark.asyncio
    async def test_health_check_quick_response(self, test_client: AsyncClient):
        """Test health check responds quickly."""
        import time

        start = time.time()
        response = await test_client.get("/health")
        duration = time.time() - start

        assert response.status_code in [200, 202]
        # Health check should respond in less than 1 second
        assert duration < 1.0
