#!/usr/bin/env python3
"""
Simple test script to verify Gmail SMTP configuration.
Usage: uv run python -m app.scripts.test_mail
"""
import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings
from app.services.mailer import MailerService

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_email_sending():
    """Test email sending with current configuration."""
    try:
        settings = get_settings()
        mailer = MailerService(settings)

        # Test configuration
        print("📧 Testing Gmail SMTP Configuration:")
        print(f"   SMTP Host: {settings.smtp_host}")
        print(f"   SMTP Port: {settings.smtp_port}")
        print(f"   SMTP User: {settings.smtp_user}")
        print(f"   FROM Email: {settings.from_email}")
        print(f"   STARTTLS: {settings.smtp_starttls}")
        print()

        # Check if Gmail App Password is set
        if (
            not settings.smtp_password
            or settings.smtp_password == "${GMAIL_APP_PASSWORD}"
        ):
            print("❌ SMTP_PASSWORD is not set correctly!")
            print("   Please set GMAIL_APP_PASSWORD environment variable")
            print("   or update the .env file with your Gmail App Password")
            return False

        # Send test email
        test_recipient = input("Enter email address to send test email to: ").strip()
        if not test_recipient:
            print("❌ No recipient email provided")
            return False

        print(f"📤 Sending test email to: {test_recipient}")

        subject = "Test Email from Mail Gateway Service"
        text_body = """Hello!

This is a test email from your Mail Gateway Service to verify Gmail SMTP configuration.

If you receive this email, your Gmail SMTP setup is working correctly!

Configuration details:
- SMTP Host: smtp.gmail.com
- SMTP Port: 587
- STARTTLS: Enabled

Best regards,
Mail Gateway Service
"""

        html_body = """
<html>
<body>
    <h2>🎉 Gmail SMTP Test Successful!</h2>
    <p>Hello!</p>
    <p>This is a test email from your <strong>Mail Gateway Service</strong> to verify Gmail SMTP configuration.</p>
    <p>If you receive this email, your Gmail SMTP setup is working correctly!</p>

    <h3>Configuration Details:</h3>
    <ul>
        <li><strong>SMTP Host:</strong> smtp.gmail.com</li>
        <li><strong>SMTP Port:</strong> 587</li>
        <li><strong>STARTTLS:</strong> Enabled</li>
    </ul>

    <p>Best regards,<br>
    <em>Mail Gateway Service</em></p>
</body>
</html>
"""

        message_id = await mailer.send_email(
            to=[test_recipient], subject=subject, text=text_body, html=html_body
        )

        if message_id:
            print("✅ Email sent successfully!")
            print(f"   Message ID: {message_id}")
            print("   Status: 250 OK (Gmail SMTP connection successful)")
            return True
        else:
            print("❌ Failed to send email")
            return False

    except Exception as e:
        print(f"❌ Error testing email: {e}")
        return False


async def main():
    """Main function to run the email test."""
    print("🔧 Gmail SMTP Configuration Test")
    print("=" * 40)

    success = await test_email_sending()

    print()
    if success:
        print("🎉 Gmail SMTP configuration is working correctly!")
        print("   Your email delivery logs should show status code 250 OK.")
    else:
        print("💡 Troubleshooting tips:")
        print("   1. Ensure Gmail 2FA is enabled on your account")
        print("   2. Generate a Gmail App Password (not your regular password)")
        print("   3. Set GMAIL_APP_PASSWORD environment variable")
        print("   4. Verify FROM_EMAIL matches your Gmail account")


if __name__ == "__main__":
    asyncio.run(main())
