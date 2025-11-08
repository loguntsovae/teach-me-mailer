from unittest.mock import patch

import bcrypt

from app.models.api_key import APIKey


class TestSendEndpoint:
    """Test the send email endpoint with mocked SMTP."""

    @patch("app.services.mailer.MailerService.send_email")
    async def test_send_email_happy_path(self, mock_send_email, test_session, client):
        """Test successful email sending flow."""
        # Setup mock
        mock_send_email.return_value = "msg_12345abc"

        # Create API key
        plain_key = "test-send-key"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        api_key = APIKey(name="Send Test Key", key_hash=hashed_key, daily_limit=100, is_active=True)
        test_session.add(api_key)
        await test_session.commit()

        # Test successful send
        request_data = {
            "to": "test@example.com",
            "subject": "Test Email",
            "html": "<h1>Hello</h1>",
            "text": "Hello",
            "headers": {"X-Test": "true"},
        }

        response = await client.post("/api/v1/send", json=request_data, headers={"X-API-Key": plain_key})

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["remaining"] >= 98  # Should be close to 99 (100 - 1 email sent)

        # Verify mock was called with correct parameters
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["to"] == ["test@example.com"]
        assert call_args["subject"] == "Test Email"
        assert call_args["html"] == "<h1>Hello</h1>"
        assert call_args["text"] == "Hello"
        assert call_args["headers"] == {"X-Test": "true"}

    async def test_send_email_rate_limit_exceeded(self, test_session, client):
        """Test send email when rate limit is exceeded."""
        # Create API key with low limit
        plain_key = "rate-limit-key"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        api_key = APIKey(
            name="Rate Limit Key",
            key_hash=hashed_key,
            daily_limit=1,  # Very low limit
            is_active=True,
        )
        test_session.add(api_key)
        await test_session.commit()

        request_data = {
            "to": "test@example.com",
            "subject": "First Email",
            "html": "<h1>First</h1>",
        }

        # First request should succeed
        response1 = await client.post("/api/v1/send", json=request_data, headers={"X-API-Key": plain_key})
        assert response1.status_code == 202
        assert response1.json()["remaining"] == 0

        # Second request should fail with 429
        request_data["subject"] = "Second Email (should fail)"
        response2 = await client.post("/api/v1/send", json=request_data, headers={"X-API-Key": plain_key})

        assert response2.status_code == 429
        assert "Retry-After" in response2.headers
        assert "exceeded" in response2.json()["detail"]

    async def test_send_email_validation_errors(self, test_session, client):
        """Test send email with various validation errors."""
        # Create API key
        plain_key = "validation-key"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        api_key = APIKey(name="Validation Key", key_hash=hashed_key, daily_limit=10, is_active=True)
        test_session.add(api_key)
        await test_session.commit()

        # Test missing body (both html and text)
        response = await client.post(
            "/api/v1/send",
            json={"to": "test@example.com", "subject": "No Body"},
            headers={"X-API-Key": plain_key},
        )
        assert response.status_code == 422

        # Test invalid email
        response = await client.post(
            "/api/v1/send",
            json={
                "to": "not-an-email",
                "subject": "Invalid Email",
                "text": "Some text",
            },
            headers={"X-API-Key": plain_key},
        )
        assert response.status_code == 422

        # Test subject too long
        long_subject = "A" * 300  # Exceeds 256 char limit
        response = await client.post(
            "/api/v1/send",
            json={
                "to": "test@example.com",
                "subject": long_subject,
                "text": "Some text",
            },
            headers={"X-API-Key": plain_key},
        )
        assert response.status_code == 422

    @patch("app.services.mailer.MailerService.send_email")
    async def test_send_email_smtp_failure(self, mock_send_email, test_session, client):
        """Test send email when SMTP sending fails."""
        # Setup mock to return None (failure)
        mock_send_email.return_value = None

        # Create API key
        plain_key = "smtp-fail-key"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        api_key = APIKey(name="SMTP Fail Key", key_hash=hashed_key, daily_limit=10, is_active=True)
        test_session.add(api_key)
        await test_session.commit()

        request_data = {
            "to": "test@example.com",
            "subject": "SMTP Fail Test",
            "text": "This should fail to send",
        }

        # Should still return 202 (queued) since we respond before sending
        response = await client.post("/api/v1/send", json=request_data, headers={"X-API-Key": plain_key})

        assert response.status_code == 202
        assert response.json()["status"] == "queued"
        # Even if SMTP fails, the rate limit is still consumed
        assert response.json()["remaining"] == 9

    async def test_send_email_domain_validation(self, test_session, test_settings, client):
        """Test domain allowlist validation in mailer service."""
        # Override settings to include domain restrictions
        test_settings.allow_domains = ["allowed.com", "trusted.org"]

        # Create API key
        plain_key = "domain-key"
        hashed_key = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        api_key = APIKey(name="Domain Key", key_hash=hashed_key, daily_limit=10, is_active=True)
        test_session.add(api_key)
        await test_session.commit()

        # Test allowed domain
        with patch("app.services.mailer.MailerService.send_email") as mock_send:
            mock_send.return_value = "msg_allowed"

            response = await client.post(
                "/api/v1/send",
                json={
                    "to": "user@allowed.com",
                    "subject": "Allowed Domain",
                    "text": "This should work",
                },
                headers={"X-API-Key": plain_key},
            )
            assert response.status_code == 202
