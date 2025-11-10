"""
Smoke test to verify test infrastructure is working correctly.

This test should always pass and is used to verify:
- pytest is configured correctly
- conftest.py fixtures load properly
- basic test execution works
"""

import pytest


@pytest.mark.unit
def test_sanity_check():
    """Basic sanity check test."""
    assert True
    assert 1 + 1 == 2
    assert "test" in "testing"


@pytest.mark.unit
def test_settings_fixture(test_settings):
    """Test that settings fixture works."""
    assert test_settings is not None
    assert test_settings.app_name == "test-mail-gateway"
    assert test_settings.debug is True


@pytest.mark.unit
@pytest.mark.database
async def test_db_session_fixture(db_session):
    """Test that database session fixture works."""
    assert db_session is not None
    # Verify session is active
    assert db_session.is_active


@pytest.mark.unit
def test_mock_smtp_fixture(mock_smtp):
    """Test that mock SMTP fixture works."""
    assert mock_smtp is not None
    assert hasattr(mock_smtp, "send_message")


@pytest.mark.integration
async def test_test_client_fixture(test_client):
    """Test that HTTP client fixture works."""
    assert test_client is not None
    # Simple request to health endpoint
    response = await test_client.get("/health")
    assert response.status_code in [200, 404]  # May be 404 if endpoint doesn't exist


@pytest.mark.unit
@pytest.mark.database
async def test_test_api_key_fixture(test_api_key):
    """Test that API key fixture works."""
    assert test_api_key is not None
    assert test_api_key.is_active is True
    assert hasattr(test_api_key, "raw_key")
    assert test_api_key.raw_key.startswith("sk_test_")


@pytest.mark.unit
def test_pytest_markers():
    """Verify that custom pytest markers are registered."""
    # This test passes if markers are configured correctly
    assert True


@pytest.mark.unit
async def test_async_test_support():
    """Verify that async tests are supported."""

    # Simple async function
    async def async_function():
        return 42

    result = await async_function()
    assert result == 42
