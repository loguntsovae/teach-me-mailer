import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "mail-gateway"
    assert "version" in data
    assert data["status"] == "running"


def test_send_endpoint_requires_api_key(client):
    """Test that send endpoint requires X-API-Key header."""
    response = client.post(
        "/api/v1/send",
        json={
            "to": ["test@example.com"],
            "subject": "Test",
            "body_text": "Hello!"
        }
    )
    assert response.status_code == 401  # Missing authentication
    
    # Test with invalid API key
    response = client.post(
        "/api/v1/send",
        headers={"X-API-Key": "invalid-key"},
        json={
            "to": ["test@example.com"],
            "subject": "Test", 
            "body_text": "Hello!"
        }
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "X-API-Key"


def test_usage_endpoint_requires_api_key(client):
    """Test that usage endpoint requires X-API-Key header."""
    response = client.get("/api/v1/usage")
    assert response.status_code == 401  # Missing authentication
    
    # Test with invalid API key
    response = client.get(
        "/api/v1/usage",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "X-API-Key"