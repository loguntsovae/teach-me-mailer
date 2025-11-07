import pytest
import bcrypt
from unittest.mock import AsyncMock, patch

from app.models.api_key import APIKey
from app.services.auth import AuthService


class TestAuth:
    """Test authentication functionality."""
    
    async def test_auth_valid_api_key(self, test_session, test_settings, client):
        """Test authentication with valid API key."""
        # Create a test API key
        plain_key = "test-api-key-12345"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()
        
        api_key = APIKey(
            name="Test Key",
            key_hash=hashed_key,
            daily_limit=100,
            is_active=True
        )
        test_session.add(api_key)
        await test_session.commit()
        
        # Test valid authentication
        response = await client.get(
            "/api/v1/health",
            headers={"X-API-Key": plain_key}
        )
        
        assert response.status_code == 200
        # Should include request ID header
        assert "X-Request-ID" in response.headers
    
    async def test_auth_invalid_api_key(self, client):
        """Test authentication with invalid API key."""
        response = await client.post(
            "/api/v1/send",
            headers={"X-API-Key": "invalid-key"},
            json={"to": "test@example.com", "subject": "Test", "text": "Test message"}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    async def test_auth_missing_api_key(self, client):
        """Test authentication without API key header."""
        response = await client.post(
            "/api/v1/send",
            json={"to": "test@example.com", "subject": "Test", "text": "Test message"}
        )
        
        assert response.status_code == 401
        assert "missing" in response.json()["detail"].lower()
    
    async def test_auth_inactive_api_key(self, test_session, test_settings, client):
        """Test authentication with inactive API key."""
        # Create inactive API key
        plain_key = "inactive-key-12345"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()
        
        api_key = APIKey(
            name="Inactive Key",
            key_hash=hashed_key,
            daily_limit=100,
            is_active=False
        )
        test_session.add(api_key)
        await test_session.commit()
        
        # Test inactive key rejection
        response = await client.post(
            "/api/v1/send",
            headers={"X-API-Key": plain_key},
            json={"to": "test@example.com", "subject": "Test", "text": "Test message"}
        )
        
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()
    
    async def test_bcrypt_verification(self, test_session, test_settings):
        """Test bcrypt hash verification in AuthService."""
        auth_service = AuthService(test_session, test_settings)
        
        # Create API key with known hash
        plain_key = "test-password-123"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()
        
        api_key = APIKey(
            name="Test Key",
            key_hash=hashed_key,
            daily_limit=50,
            is_active=True
        )
        test_session.add(api_key)
        await test_session.commit()
        
        # Test correct password verification
        verified_key = await auth_service.validate_api_key(plain_key)
        assert verified_key is not None
        assert verified_key.id == api_key.id
        
        # Test incorrect password verification
        wrong_key = await auth_service.validate_api_key("wrong-password")
        assert wrong_key is None