"""
Unit tests for Pydantic schemas (app/schemas/mail.py).

Tests cover:
- MailRequest validation (email, subject, body)
- MailResponse serialization
- SendLogResponse model
- HealthResponse model
- Field validation and constraints
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.mail import HealthResponse, MailRequest, MailResponse, SendLogResponse


@pytest.mark.unit
class TestMailRequest:
    """Tests for MailRequest schema."""

    def test_mail_request_valid_html_only(self):
        """Test MailRequest with HTML body only."""
        data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "html": "<h1>Hello</h1>",
        }

        request = MailRequest(**data)

        assert request.to == "test@example.com"
        assert request.subject == "Test Subject"
        assert request.html == "<h1>Hello</h1>"
        assert request.text is None

    def test_mail_request_valid_text_only(self):
        """Test MailRequest with text body only."""
        data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "text": "Hello World",
        }

        request = MailRequest(**data)

        assert request.to == "test@example.com"
        assert request.subject == "Test Subject"
        assert request.html is None
        assert request.text == "Hello World"

    def test_mail_request_valid_both_formats(self):
        """Test MailRequest with both HTML and text."""
        data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "html": "<h1>Hello</h1>",
            "text": "Hello World",
        }

        request = MailRequest(**data)

        assert request.html == "<h1>Hello</h1>"
        assert request.text == "Hello World"

    def test_mail_request_with_custom_headers(self):
        """Test MailRequest with custom headers."""
        data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "html": "<h1>Hello</h1>",
            "headers": {"X-Custom": "value", "X-Priority": "high"},
        }

        request = MailRequest(**data)

        assert request.headers == {"X-Custom": "value", "X-Priority": "high"}

    def test_mail_request_invalid_no_body(self):
        """Test MailRequest fails when neither HTML nor text provided."""
        data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "html": None,
            "text": None,
        }

        with pytest.raises(ValidationError) as exc_info:
            MailRequest(**data)

        assert "Either html or text body is required" in str(exc_info.value)

    def test_mail_request_invalid_email_format(self):
        """Test MailRequest fails with invalid email format."""
        data = {
            "to": "invalid-email",
            "subject": "Test Subject",
            "html": "<h1>Hello</h1>",
        }

        with pytest.raises(ValidationError) as exc_info:
            MailRequest(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("to",) for e in errors)

    def test_mail_request_subject_too_long(self):
        """Test MailRequest fails when subject exceeds max length."""
        data = {
            "to": "test@example.com",
            "subject": "x" * 300,  # More than 256 characters
            "html": "<h1>Hello</h1>",
        }

        with pytest.raises(ValidationError) as exc_info:
            MailRequest(**data)

        errors = exc_info.value.errors()
        assert any("subject" in str(e["loc"]) for e in errors)

    def test_mail_request_missing_required_fields(self):
        """Test MailRequest fails when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            MailRequest()

        errors = exc_info.value.errors()
        # Should have errors for 'to' and 'subject'
        assert len(errors) >= 2

    def test_mail_request_empty_subject(self):
        """Test MailRequest accepts empty subject."""
        data = {
            "to": "test@example.com",
            "subject": "",
            "html": "<h1>Hello</h1>",
        }

        # Should be valid (subject can be empty, just not too long)
        request = MailRequest(**data)
        assert request.subject == ""

    def test_mail_request_special_characters_in_subject(self):
        """Test MailRequest with special characters in subject."""
        data = {
            "to": "test@example.com",
            "subject": "🚀 Test Email with émojis & spëcial ¢hars!",
            "html": "<h1>Hello</h1>",
        }

        request = MailRequest(**data)
        assert "🚀" in request.subject
        assert "émojis" in request.subject


@pytest.mark.unit
class TestMailResponse:
    """Tests for MailResponse schema."""

    def test_mail_response_valid(self):
        """Test MailResponse creation."""
        response = MailResponse(status="queued", remaining=95)

        assert response.status == "queued"
        assert response.remaining == 95

    def test_mail_response_serialization(self):
        """Test MailResponse JSON serialization."""
        response = MailResponse(status="queued", remaining=95)

        json_data = response.model_dump()

        assert json_data["status"] == "queued"
        assert json_data["remaining"] == 95

    def test_mail_response_missing_fields(self):
        """Test MailResponse fails when required fields are missing."""
        with pytest.raises(ValidationError):
            MailResponse(status="queued")  # Missing 'remaining'

        with pytest.raises(ValidationError):
            MailResponse(remaining=95)  # Missing 'status'


@pytest.mark.unit
class TestSendLogResponse:
    """Tests for SendLogResponse schema."""

    def test_send_log_response_minimal(self):
        """Test SendLogResponse with minimal required fields."""
        now = datetime.utcnow()

        response = SendLogResponse(
            id=1,
            api_key="sk_test_123",
            to_email="test@example.com",
            from_email="noreply@example.com",
            subject="Test",
            status="sent",
            created_at=now,
        )

        assert response.id == 1
        assert response.api_key == "sk_test_123"
        assert response.status == "sent"
        assert response.sent_at is None
        assert response.error_message is None

    def test_send_log_response_complete(self):
        """Test SendLogResponse with all fields."""
        now = datetime.utcnow()

        response = SendLogResponse(
            id=1,
            api_key="sk_test_123",
            to_email="test@example.com",
            from_email="noreply@example.com",
            subject="Test",
            status="sent",
            created_at=now,
            sent_at=now,
            error_message=None,
        )

        assert response.sent_at == now

    def test_send_log_response_with_error(self):
        """Test SendLogResponse with error message."""
        now = datetime.utcnow()

        response = SendLogResponse(
            id=1,
            api_key="sk_test_123",
            to_email="test@example.com",
            from_email="noreply@example.com",
            subject="Test",
            status="failed",
            created_at=now,
            error_message="SMTP connection failed",
        )

        assert response.status == "failed"
        assert response.error_message == "SMTP connection failed"


@pytest.mark.unit
class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_health_response_valid(self):
        """Test HealthResponse creation."""
        now = datetime.utcnow()

        response = HealthResponse(
            status="healthy",
            timestamp=now,
            version="0.1.0",
        )

        assert response.status == "healthy"
        assert response.timestamp == now
        assert response.version == "0.1.0"

    def test_health_response_serialization(self):
        """Test HealthResponse JSON serialization."""
        now = datetime.utcnow()

        response = HealthResponse(
            status="healthy",
            timestamp=now,
            version="0.1.0",
        )

        json_data = response.model_dump()

        assert json_data["status"] == "healthy"
        assert json_data["version"] == "0.1.0"

    def test_health_response_unhealthy_status(self):
        """Test HealthResponse with unhealthy status."""
        now = datetime.utcnow()

        response = HealthResponse(
            status="unhealthy",
            timestamp=now,
            version="0.1.0",
        )

        assert response.status == "unhealthy"


@pytest.mark.unit
class TestSchemaIntegration:
    """Integration tests for schema interactions."""

    def test_mail_request_to_dict(self):
        """Test converting MailRequest to dictionary."""
        data = {
            "to": "test@example.com",
            "subject": "Test",
            "html": "<h1>Hello</h1>",
        }

        request = MailRequest(**data)
        dict_data = request.model_dump()

        assert dict_data["to"] == "test@example.com"
        assert dict_data["subject"] == "Test"
        assert dict_data["html"] == "<h1>Hello</h1>"
        assert dict_data["text"] is None

    def test_schema_json_example(self):
        """Test that schema examples are valid."""
        # MailRequest example
        example = MailRequest.model_config.get("json_schema_extra", {}).get("example")
        if example:
            request = MailRequest(**example)
            assert request.to is not None

        # MailResponse example
        example = MailResponse.model_config.get("json_schema_extra", {}).get("example")
        if example:
            response = MailResponse(**example)
            assert response.status is not None
