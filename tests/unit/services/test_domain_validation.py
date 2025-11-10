"""Unit tests for DomainValidationService."""

import pytest

from app.services.domain_validation import DomainValidationService


class TestDomainValidationService:
    """Tests for domain validation."""

    def test_is_domain_allowed_no_allowlist(self, test_settings):
        """Test all domains allowed when no allowlist."""
        service = DomainValidationService(test_settings)

        # No allowlist = all allowed
        assert service.is_domain_allowed("user@anydomain.com") is True
        assert service.is_domain_allowed("test@example.org") is True

    def test_is_domain_allowed_with_allowlist(self, test_settings_with_allowlist):
        """Test domain checking with allowlist."""
        service = DomainValidationService(test_settings_with_allowlist)

        # Allowed domains
        assert service.is_domain_allowed("user@example.com") is True
        assert service.is_domain_allowed("user@test.com") is True

        # Blocked domain
        assert service.is_domain_allowed("user@blocked.com") is False

    def test_is_domain_allowed_case_insensitive(self, test_settings_with_allowlist):
        """Test domain check is case insensitive."""
        service = DomainValidationService(test_settings_with_allowlist)

        assert service.is_domain_allowed("user@EXAMPLE.COM") is True
        assert service.is_domain_allowed("user@Example.Com") is True

    def test_is_domain_allowed_invalid_email(self, test_settings):
        """Test handling invalid email format."""
        service = DomainValidationService(test_settings)

        assert service.is_domain_allowed("invalid") is False
        assert service.is_domain_allowed("@example.com") is False
        assert service.is_domain_allowed("") is False

    def test_filter_allowed_emails(self, test_settings_with_allowlist):
        """Test filtering emails by allowlist."""
        service = DomainValidationService(test_settings_with_allowlist)

        emails = ["user1@example.com", "user2@blocked.com", "user3@test.com", "user4@denied.org"]

        allowed, blocked = service.filter_allowed_emails(emails)

        assert len(allowed) == 2
        assert "user1@example.com" in allowed
        assert "user3@test.com" in allowed
        assert len(blocked) == 2
        assert "user2@blocked.com" in blocked
        assert "user4@denied.org" in blocked
