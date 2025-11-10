"""Unit tests for core components."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings, get_settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_settings_defaults(self):
        """Test that settings can be loaded."""
        settings = Settings()

        # Just verify settings object is created
        assert settings.app_name is not None
        assert settings.smtp_port > 0
        assert settings.default_daily_limit > 0
        assert settings.rate_window_days > 0

    def test_settings_from_env(self):
        """Test loading settings from environment."""
        # Set environment variables
        os.environ["APP_NAME"] = "test-app"
        os.environ["DEBUG"] = "true"
        os.environ["SMTP_PORT"] = "2525"
        os.environ["DEFAULT_DAILY_LIMIT"] = "200"

        settings = Settings()

        assert settings.app_name == "test-app"
        assert settings.debug is True
        assert settings.smtp_port == 2525
        assert settings.default_daily_limit == 200

        # Cleanup
        del os.environ["APP_NAME"]
        del os.environ["DEBUG"]
        del os.environ["SMTP_PORT"]
        del os.environ["DEFAULT_DAILY_LIMIT"]

    def test_settings_smtp_port_validation(self):
        """Test SMTP port must be valid."""
        os.environ["SMTP_PORT"] = "99999"  # Invalid port

        with pytest.raises(Exception):  # Pydantic validation error
            Settings()

        del os.environ["SMTP_PORT"]

    def test_settings_case_insensitive(self):
        """Test environment variables are case insensitive."""
        os.environ["app_name"] = "lowercase-app"

        settings = Settings()

        assert settings.app_name == "lowercase-app"

        del os.environ["app_name"]

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_allow_domains_parsing(self):
        """Test parsing allow_domains from comma-separated string."""
        os.environ["ALLOW_DOMAINS"] = "example.com,test.com"

        settings = Settings()

        assert settings.allow_domains == ["example.com", "test.com"]

        del os.environ["ALLOW_DOMAINS"]

    def test_settings_empty_allow_domains(self):
        """Test empty allow_domains."""
        os.environ["ALLOW_DOMAINS"] = ""

        settings = Settings()

        # Empty string may become None or []
        assert settings.allow_domains in [None, []]

        del os.environ["ALLOW_DOMAINS"]


class TestDeps:
    """Tests for FastAPI dependencies."""

    async def test_get_db_returns_session(self):
        """Test that get_db dependency returns database session."""
        from app.core.deps import get_db

        # This is an async generator, iterate it
        gen = get_db()
        session = await gen.__anext__()

        assert session is not None

        # Cleanup
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
