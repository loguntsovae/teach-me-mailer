"""Unit tests for MailerService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mailer import MailerService


class TestMailerService:
    """Tests for MailerService email sending."""

    async def test_send_email_text_only(self, test_settings, mock_smtp):
        """Test sending plain text email."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["test@example.com"], subject="Test Subject", text="Plain text body"
            )

        assert message_id is not None
        mock_smtp.assert_called_once()
        call_args = mock_smtp.call_args

        # Check SMTP configuration
        assert call_args.kwargs["hostname"] == test_settings.smtp_host
        assert call_args.kwargs["port"] == test_settings.smtp_port
        assert call_args.kwargs["username"] == test_settings.smtp_user
        assert call_args.kwargs["password"] == test_settings.smtp_password
        assert call_args.kwargs["start_tls"] == test_settings.smtp_starttls

    async def test_send_email_html_only(self, test_settings, mock_smtp):
        """Test sending HTML email."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["test@example.com"], subject="HTML Email", html="<h1>HTML body</h1>"
            )

        assert message_id is not None
        mock_smtp.assert_called_once()

    async def test_send_email_both_html_and_text(self, test_settings, mock_smtp):
        """Test sending email with both HTML and text."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["test@example.com"], subject="Multipart Email", html="<p>HTML version</p>", text="Text version"
            )

        assert message_id is not None
        mock_smtp.assert_called_once()

    async def test_send_email_multiple_recipients(self, test_settings, mock_smtp):
        """Test sending email to multiple recipients."""
        mailer = MailerService(test_settings)
        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(to=recipients, subject="Multi-recipient", text="Test message")

        assert message_id is not None
        mock_smtp.assert_called_once()

    async def test_send_email_with_custom_headers(self, test_settings, mock_smtp):
        """Test sending email with custom headers."""
        mailer = MailerService(test_settings)
        custom_headers = {"X-Custom-Header": "custom-value", "Reply-To": "reply@example.com"}

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["test@example.com"], subject="Custom Headers", text="Test", headers=custom_headers
            )

        assert message_id is not None
        mock_smtp.assert_called_once()

    async def test_send_email_with_custom_from(self, test_settings, mock_smtp):
        """Test sending email with custom from address."""
        mailer = MailerService(test_settings)
        custom_from = "custom@example.com"

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["test@example.com"], subject="Custom From", text="Test", from_email=custom_from
            )

        assert message_id is not None
        mock_smtp.assert_called_once()

    async def test_send_email_no_recipients(self, test_settings):
        """Test that empty recipient list raises ValueError."""
        mailer = MailerService(test_settings)

        with pytest.raises(ValueError, match="At least one recipient is required"):
            await mailer.send_email(to=[], subject="Test", text="Test")

    async def test_send_email_no_body(self, test_settings):
        """Test that missing body raises ValueError."""
        mailer = MailerService(test_settings)

        with pytest.raises(ValueError, match="Either HTML or text body is required"):
            await mailer.send_email(
                to=["test@example.com"],
                subject="Test",
                # No html or text provided
            )

    async def test_send_email_smtp_failure(self, test_settings):
        """Test handling SMTP connection failure."""
        mailer = MailerService(test_settings)

        mock_send = AsyncMock(side_effect=Exception("SMTP connection failed"))

        with patch("app.services.mailer.aiosmtplib.send", new=mock_send):
            message_id = await mailer.send_email(to=["test@example.com"], subject="Test", text="Test")

        assert message_id is None  # Returns None on failure

    async def test_send_email_smtp_timeout(self, test_settings):
        """Test handling SMTP timeout."""
        mailer = MailerService(test_settings)

        mock_send = AsyncMock(side_effect=TimeoutError("Connection timeout"))

        with patch("app.services.mailer.aiosmtplib.send", new=mock_send):
            message_id = await mailer.send_email(to=["test@example.com"], subject="Test", text="Test")

        assert message_id is None


class TestMailerDomainAllowlist:
    """Tests for domain allowlist functionality."""

    async def test_send_email_allowed_domain(self, test_settings_with_allowlist, mock_smtp):
        """Test sending email to allowed domain."""
        mailer = MailerService(test_settings_with_allowlist)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["user@example.com"], subject="Test", text="Test"  # example.com is in allowlist
            )

        assert message_id is not None

    async def test_send_email_blocked_domain(self, test_settings_with_allowlist):
        """Test sending email to blocked domain raises ValueError."""
        mailer = MailerService(test_settings_with_allowlist)

        with pytest.raises(ValueError, match="Domain not allowed"):
            await mailer.send_email(to=["user@blocked.com"], subject="Test", text="Test")  # Not in allowlist

    async def test_send_email_mixed_domains(self, test_settings_with_allowlist):
        """Test sending to mixed allowed/blocked domains."""
        mailer = MailerService(test_settings_with_allowlist)

        # Should fail because blocked.com is not allowed
        with pytest.raises(ValueError, match="Domain not allowed"):
            await mailer.send_email(to=["user@example.com", "user@blocked.com"], subject="Test", text="Test")

    async def test_send_email_case_insensitive_domain(self, test_settings_with_allowlist, mock_smtp):
        """Test domain check is case-insensitive."""
        mailer = MailerService(test_settings_with_allowlist)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(
                to=["user@EXAMPLE.COM"], subject="Test", text="Test"  # Uppercase should work
            )

        assert message_id is not None

    async def test_send_email_no_allowlist(self, test_settings, mock_smtp):
        """Test that with no allowlist, all domains are allowed."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp):
            message_id = await mailer.send_email(to=["user@anydomain.com"], subject="Test", text="Test")

        assert message_id is not None


class TestMailerHelperMethods:
    """Tests for MailerService helper methods."""

    def test_is_domain_allowed_with_allowlist(self, test_settings_with_allowlist):
        """Test domain checking with allowlist configured."""
        mailer = MailerService(test_settings_with_allowlist)

        assert mailer._is_domain_allowed("user@example.com") is True
        assert mailer._is_domain_allowed("user@test.com") is True
        assert mailer._is_domain_allowed("user@blocked.com") is False

    def test_is_domain_allowed_without_allowlist(self, test_settings):
        """Test domain checking without allowlist (all allowed)."""
        mailer = MailerService(test_settings)

        assert mailer._is_domain_allowed("user@anydomain.com") is True
        assert mailer._is_domain_allowed("user@example.org") is True

    def test_is_domain_allowed_case_insensitive(self, test_settings_with_allowlist):
        """Test domain checking is case-insensitive."""
        mailer = MailerService(test_settings_with_allowlist)

        assert mailer._is_domain_allowed("user@EXAMPLE.COM") is True
        assert mailer._is_domain_allowed("user@Example.Com") is True
        assert mailer._is_domain_allowed("USER@example.com") is True

    def test_extract_message_id_from_dict(self, test_settings):
        """Test extracting message ID from SMTP response dict."""
        mailer = MailerService(test_settings)

        # Simulate SMTP response with Message-ID
        smtp_result = {"user@example.com": (250, "Message-ID: <abc123@mail.example.com>")}

        message_id = mailer._extract_message_id(smtp_result)
        assert message_id == "abc123@mail.example.com"

    def test_extract_message_id_no_id(self, test_settings):
        """Test extracting message ID when not present."""
        mailer = MailerService(test_settings)

        smtp_result = {"user@example.com": (250, "OK")}

        message_id = mailer._extract_message_id(smtp_result)
        assert message_id is None

    def test_extract_message_id_invalid_format(self, test_settings):
        """Test extracting message ID with invalid format."""
        mailer = MailerService(test_settings)

        smtp_result = "invalid format"

        message_id = mailer._extract_message_id(smtp_result)
        assert message_id is None

    def test_extract_message_id_exception_handling(self, test_settings):
        """Test exception handling in message ID extraction."""
        mailer = MailerService(test_settings)

        # Pass something that will cause an exception
        smtp_result = None

        message_id = mailer._extract_message_id(smtp_result)
        assert message_id is None


class TestMailerMessageConstruction:
    """Tests for email message construction."""

    async def test_message_has_required_headers(self, test_settings, mock_smtp):
        """Test that constructed message has required headers."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp) as mock:
            await mailer.send_email(to=["test@example.com"], subject="Required Headers", text="Test")

            # Get the message object passed to send()
            msg = mock.call_args.args[0]
            assert msg["Subject"] == "Required Headers"
            assert msg["From"] == test_settings.from_email
            assert msg["To"] == "test@example.com"

    async def test_message_multipart_structure(self, test_settings, mock_smtp):
        """Test multipart message structure with HTML and text."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp) as mock:
            await mailer.send_email(to=["test@example.com"], subject="Multipart", html="<p>HTML</p>", text="Text")

            msg = mock.call_args.args[0]
            assert msg.is_multipart()

    async def test_message_single_part_text(self, test_settings, mock_smtp):
        """Test single-part text message structure."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp) as mock:
            await mailer.send_email(to=["test@example.com"], subject="Single Part", text="Plain text only")

            msg = mock.call_args.args[0]
            assert not msg.is_multipart()

    async def test_message_single_part_html(self, test_settings, mock_smtp):
        """Test single-part HTML message structure."""
        mailer = MailerService(test_settings)

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp) as mock:
            await mailer.send_email(to=["test@example.com"], subject="Single Part HTML", html="<h1>HTML only</h1>")

            msg = mock.call_args.args[0]
            assert not msg.is_multipart()

    async def test_message_multiple_recipients_header(self, test_settings, mock_smtp):
        """Test To header with multiple recipients."""
        mailer = MailerService(test_settings)

        recipients = ["user1@example.com", "user2@example.com"]

        with patch("app.services.mailer.aiosmtplib.send", new=mock_smtp) as mock:
            await mailer.send_email(to=recipients, subject="Multiple Recipients", text="Test")

            msg = mock.call_args.args[0]
            assert msg["To"] == "user1@example.com, user2@example.com"
