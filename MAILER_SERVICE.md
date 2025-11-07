# MailerService Implementation

## Overview
A clean, async SMTP service using `aiosmtplib` with domain allowlist support.

## Features

### ✅ Core Email Functionality
- **`send_email(to, subject, html, text, headers, from_email)`** - Main email sending method
- **Multiple recipients** - Pass list of email addresses in `to` parameter
- **HTML + Text support** - Send multipart emails or single format
- **Custom headers** - Add any additional email headers as dict

### ✅ SMTP Configuration
- **STARTTLS support** - Enabled via `SMTP_STARTTLS=1` environment variable
- **Flexible authentication** - Username/password via SMTP_USER/SMTP_PASSWORD
- **Configurable server** - Any SMTP server via SMTP_HOST/SMTP_PORT

### ✅ Security & Validation
- **Domain allowlist** - Restrict recipients via `ALLOW_DOMAINS` (comma-separated)
- **Message ID return** - Returns SMTP message ID for tracking
- **Error handling** - Comprehensive logging and error reporting

## Usage Examples

### Basic Email
```python
from app.services.mailer import MailerService

mailer = MailerService(settings)

message_id = await mailer.send_email(
    to=["user@example.com"],
    subject="Hello World",
    text="Plain text content",
    html="<h1>HTML content</h1>"
)
```

### Advanced Usage
```python
# Custom headers and sender
message_id = await mailer.send_email(
    to=["user1@example.com", "user2@example.com"],
    subject="Newsletter #1",
    html="<h1>Newsletter</h1><p>Content here</p>",
    headers={"X-Campaign": "newsletter-2024"},
    from_email="newsletter@mycompany.com"
)
```

### Environment Configuration
```bash
# Required SMTP settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com

# Optional settings
SMTP_STARTTLS=1                          # Enable STARTTLS
ALLOW_DOMAINS=gmail.com,company.com      # Domain allowlist
```

## Integration with Mail Gateway

The MailerService integrates seamlessly with the mail gateway's rate limiting and authentication:

1. **Rate limiting** happens before email sending (atomic transaction)
2. **Domain validation** happens in MailerService (if ALLOW_DOMAINS set)
3. **Message tracking** via returned SMTP message IDs
4. **Error handling** with proper HTTP status codes

## Error Scenarios

- **Domain not allowed**: Raises `ValueError` if recipient domain not in allowlist
- **Missing content**: Raises `ValueError` if neither HTML nor text provided
- **SMTP failure**: Returns `None` instead of message ID
- **No recipients**: Raises `ValueError` if `to` list is empty

## STARTTLS Configuration

When `SMTP_STARTTLS=1`:
- Connects to SMTP server on standard port
- Upgrades connection to TLS via STARTTLS command
- **More compatible** than implicit TLS (port 465)
- **Recommended** for most providers (Gmail, Outlook, etc.)

## Message ID Handling

- **Returns actual SMTP message ID** when available from server response
- **Fallback to generated ID** if server doesn't provide one
- **Format**: `msg_abc123def456` for generated IDs
- **Used for tracking** and correlation with external systems