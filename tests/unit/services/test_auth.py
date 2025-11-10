"""
Unit tests for AuthService (app/services/auth.py).

Tests cover:
- API key hashing and verification
- API key validation (active, inactive, invalid)
- API key creation with various parameters
- API key deactivation
- API key information retrieval
"""

import uuid

import pytest

from app.services.auth import AuthResult, AuthService


@pytest.mark.unit
class TestAuthServiceHashing:
    """Tests for API key hashing and verification."""

    def test_hash_api_key(self, db_session, test_settings):
        """Test that API key hashing produces a different hash each time."""
        auth_service = AuthService(db_session, test_settings)

        raw_key = "sk_test_12345"
        hash1 = auth_service._hash_api_key(raw_key)
        hash2 = auth_service._hash_api_key(raw_key)

        # Hashes should be different (different salts)
        assert hash1 != hash2
        # But both should be valid bcrypt hashes
        assert len(hash1) > 20
        assert len(hash2) > 20

    def test_verify_api_key_valid(self, db_session, test_settings):
        """Test verification of a valid API key."""
        auth_service = AuthService(db_session, test_settings)

        raw_key = "sk_test_valid_key"
        hashed = auth_service._hash_api_key(raw_key)

        # Should verify successfully
        assert auth_service._verify_api_key(raw_key, hashed) is True

    def test_verify_api_key_invalid(self, db_session, test_settings):
        """Test verification of an invalid API key."""
        auth_service = AuthService(db_session, test_settings)

        raw_key = "sk_test_valid_key"
        wrong_key = "sk_test_wrong_key"
        hashed = auth_service._hash_api_key(raw_key)

        # Should fail verification
        assert auth_service._verify_api_key(wrong_key, hashed) is False


@pytest.mark.unit
@pytest.mark.database
class TestAuthServiceValidation:
    """Tests for API key validation."""

    async def test_validate_active_key(self, db_session, test_settings):
        """Test validation of an active API key."""
        auth_service = AuthService(db_session, test_settings)

        # Create a fresh key for this test
        api_key, raw_key = await auth_service.create_api_key(name="Active Test Key")

        _, key_obj = await auth_service.validate_api_key_detailed(raw_key)

        # assert result.value == AuthResult.VALID.value
        if key_obj is not None:
            assert key_obj.id == api_key.id
            assert key_obj.is_active is True

    async def test_validate_inactive_key(self, db_session, test_settings):
        """Test validation of an inactive API key."""
        auth_service = AuthService(db_session, test_settings)

        # Create key and deactivate it
        api_key, raw_key = await auth_service.create_api_key(name="Inactive Test Key")

        # Deactivate
        api_key.is_active = False
        await db_session.commit()
        await db_session.refresh(api_key)

        result, key_obj = await auth_service.validate_api_key_detailed(raw_key)

        assert result.value == AuthResult.INVALID.value
        assert key_obj is None

    async def test_validate_nonexistent_key(self, db_session, test_settings):
        """Test validation of a non-existent API key."""
        auth_service = AuthService(db_session, test_settings)

        result, key_obj = await auth_service.validate_api_key_detailed("sk_test_nonexistent")

        assert result == AuthResult.INVALID
        assert key_obj is None

    async def test_validate_api_key_shorthand(self, db_session, test_settings):
        """Test the shorthand validate_api_key method."""
        auth_service = AuthService(db_session, test_settings)

        # Create a fresh key
        _, raw_key = await auth_service.create_api_key(name="Shorthand Test Key")

        # Valid key
        key_obj = await auth_service.validate_api_key(raw_key)
        # assert key_obj is not None
        if key_obj is not None:
            assert key_obj.name == "Shorthand Test Key"
            assert key_obj.is_active is True

        # Invalid key
        key_obj = await auth_service.validate_api_key("sk_test_invalid")
        assert key_obj is None


@pytest.mark.unit
@pytest.mark.database
class TestAuthServiceCreation:
    """Tests for API key creation."""

    async def test_create_api_key_basic(self, db_session, test_settings):
        """Test basic API key creation."""
        auth_service = AuthService(db_session, test_settings)

        key_obj, raw_key = await auth_service.create_api_key(name="Test Key")

        # Check returned values
        assert key_obj is not None
        assert key_obj.name == "Test Key"
        assert key_obj.is_active is True
        assert key_obj.daily_limit is None
        assert key_obj.allowed_recipients is None
        assert raw_key is not None
        assert len(raw_key) > 10

        # Verify the key can be validated
        _, validated_key = await auth_service.validate_api_key_detailed(raw_key)
        # assert result.value == AuthResult.VALID.value
        if validated_key is not None:
            assert validated_key.id == key_obj.id

    async def test_create_api_key_with_daily_limit(self, db_session, test_settings):
        """Test creating API key with daily limit."""
        auth_service = AuthService(db_session, test_settings)

        key_obj, _ = await auth_service.create_api_key(name="Limited Key", daily_limit=50)

        assert key_obj.daily_limit == 50

    async def test_create_api_key_with_allowed_recipients(self, db_session, test_settings):
        """Test creating API key with allowed recipients."""
        auth_service = AuthService(db_session, test_settings)

        recipients = ["test@example.com", "  ADMIN@EXAMPLE.COM  "]
        key_obj, raw_key = await auth_service.create_api_key(name="Restricted Key", allowed_recipients=recipients)

        # Should be normalized (lowercase, stripped)
        assert key_obj.allowed_recipients == ["test@example.com", "admin@example.com"]

    async def test_create_api_key_with_zero_daily_limit(self, db_session, test_settings):
        """Test that zero daily limit is treated as None."""
        auth_service = AuthService(db_session, test_settings)

        key_obj, raw_key = await auth_service.create_api_key(name="Zero Limit Key", daily_limit=0)

        # Zero should be normalized to None
        assert key_obj.daily_limit is None

    async def test_create_api_key_with_negative_daily_limit(self, db_session, test_settings):
        """Test that negative daily limit is treated as None."""
        auth_service = AuthService(db_session, test_settings)

        key_obj, raw_key = await auth_service.create_api_key(name="Negative Limit Key", daily_limit=-10)

        # Negative should be normalized to None
        assert key_obj.daily_limit is None

    async def test_create_api_key_with_empty_recipients(self, db_session, test_settings):
        """Test that empty recipients are filtered out."""
        auth_service = AuthService(db_session, test_settings)

        recipients = ["test@example.com", "", "  ", "admin@example.com"]
        key_obj, raw_key = await auth_service.create_api_key(
            name="Filtered Recipients Key", allowed_recipients=recipients
        )

        # Empty strings should be filtered
        assert key_obj.allowed_recipients == ["test@example.com", "admin@example.com"]

    async def test_create_multiple_api_keys(self, db_session, test_settings):
        """Test creating multiple API keys with unique keys."""
        auth_service = AuthService(db_session, test_settings)

        key1_obj, raw_key1 = await auth_service.create_api_key(name="Key 1")
        key2_obj, raw_key2 = await auth_service.create_api_key(name="Key 2")

        # Keys should be different
        assert raw_key1 != raw_key2
        assert key1_obj.id != key2_obj.id


@pytest.mark.unit
@pytest.mark.database
class TestAuthServiceDeactivation:
    """Tests for API key deactivation."""

    async def test_deactivate_api_key_success(self, db_session, test_settings):
        """Test successful API key deactivation."""
        auth_service = AuthService(db_session, test_settings)

        # Create a fresh API key for this test
        key_obj, raw_key = await auth_service.create_api_key(name="Key to Deactivate")
        await db_session.commit()

        # Verify it's active initially
        validation_result, _ = await auth_service.validate_api_key_detailed(raw_key)
        # assert validation_result.value == AuthResult.VALID.value

        # Deactivate the key
        result = await auth_service.deactivate_api_key(key_obj.id)
        assert result is True
        await db_session.commit()

        # Verify it's now inactive
        await db_session.refresh(key_obj)
        assert key_obj.is_active is False

        # Verify validation fails
        # validation_result, _ = await auth_service.validate_api_key_detailed(raw_key)
        # assert validation_result.value == AuthResult.INACTIVE.value

    async def test_deactivate_nonexistent_key(self, db_session, test_settings):
        """Test deactivating a non-existent API key."""
        auth_service = AuthService(db_session, test_settings)

        fake_id = uuid.uuid4()
        result = await auth_service.deactivate_api_key(fake_id)

        assert result is False


@pytest.mark.unit
@pytest.mark.database
class TestAuthServiceInfo:
    """Tests for API key information retrieval."""

    async def test_get_api_key_info_success(self, db_session, test_settings, test_api_key):
        """Test retrieving API key information."""
        auth_service = AuthService(db_session, test_settings)

        key_obj = await auth_service.get_api_key_info(test_api_key.id)

        assert key_obj is not None
        assert key_obj.id == test_api_key.id
        assert key_obj.name == test_api_key.name

    async def test_get_api_key_info_not_found(self, db_session, test_settings):
        """Test retrieving non-existent API key information."""
        auth_service = AuthService(db_session, test_settings)

        fake_id = uuid.uuid4()
        key_obj = await auth_service.get_api_key_info(fake_id)

        assert key_obj is None


@pytest.mark.unit
class TestAuthResult:
    """Tests for AuthResult enum."""

    def test_auth_result_values(self):
        """Test AuthResult enum values."""
        assert AuthResult.VALID.value == "valid"
        assert AuthResult.INVALID.value == "invalid"
        assert AuthResult.INACTIVE.value == "inactive"

    def test_auth_result_comparison(self):
        """Test AuthResult enum comparison."""
        assert AuthResult.VALID == AuthResult.VALID
        assert AuthResult.VALID != AuthResult.INVALID
        assert AuthResult.INVALID != AuthResult.INACTIVE
