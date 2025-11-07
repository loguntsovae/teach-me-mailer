import uuid
from typing import Dict, List, Optional

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage

import structlog

from app.core.config import Settings


logger = structlog.get_logger(__name__)


class MailerService:
    """SMTP email service using aiosmtplib with domain allowlist support."""
    
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_email(
        self,
        to: List[str],
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        from_email: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send email using aiosmtplib.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            html: HTML email body (optional)
            text: Plain text email body (optional)
            headers: Additional email headers (optional)
            from_email: Sender email (optional, uses default if not provided)
            
        Returns:
            SMTP message ID if available, None on failure
        """
        if not to:
            raise ValueError("At least one recipient is required")
        
        if not html and not text:
            raise ValueError("Either HTML or text body is required")
        
        # Domain allowlist check
        if self.settings.allow_domains:
            for email in to:
                if not self._is_domain_allowed(email):
                    raise ValueError(f"Domain not allowed for recipient: {email}")
        
        from_addr = from_email or self.settings.from_email
        
        # Create message
        if html and text:
            # Multipart message with both HTML and text
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = ", ".join(to)
            
            # Add custom headers
            if headers:
                for key, value in headers.items():
                    msg[key] = value
            
            # Attach text and HTML parts
            text_part = MIMEText(text, "plain", "utf-8")
            html_part = MIMEText(html, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)
            
        else:
            # Simple message with single content type
            content = html or text
            content_type = "html" if html else "plain"
            
            msg = MIMEText(content, content_type, "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = ", ".join(to)
            
            # Add custom headers
            if headers:
                for key, value in headers.items():
                    msg[key] = value

        try:
            logger.info(
                "Sending email",
                to_count=len(to),
                subject=subject[:50],
                has_html=bool(html),
                has_text=bool(text),
                smtp_host=self.settings.smtp_host,
                smtp_port=self.settings.smtp_port,
                # Never log SMTP credentials
            )
            
            # Send email with STARTTLS if configured
            result = await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_user,
                password=self.settings.smtp_password,
                start_tls=self.settings.smtp_starttls,
                use_tls=False,  # Use STARTTLS instead of implicit TLS
            )
            
            # Extract message ID from SMTP response
            message_id = self._extract_message_id(result) or f"msg_{uuid.uuid4().hex[:12]}"
            
            logger.info(
                "Email sent successfully",
                message_id=message_id,
                to_count=len(to),
                smtp_response=str(result)[:100],
            )
            
            return message_id
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                error=str(e),
                to_count=len(to),
                smtp_host=self.settings.smtp_host,
                smtp_port=self.settings.smtp_port,
                # Never log SMTP credentials
            )
            return None

    def _is_domain_allowed(self, email: str) -> bool:
        """Check if email domain is in allowlist."""
        if not self.settings.allow_domains:
            return True
        
        domain = email.split("@")[-1].lower()
        allowed_domains = [d.lower() for d in self.settings.allow_domains]
        return domain in allowed_domains

    def _extract_message_id(self, smtp_result) -> Optional[str]:
        """Extract message ID from SMTP result."""
        try:
            # aiosmtplib returns a dict with server responses
            if hasattr(smtp_result, 'get'):
                # Look for message ID in server response
                for recipient, (code, message) in smtp_result.items():
                    if isinstance(message, str) and "Message-ID" in message:
                        # Extract Message-ID from response if present
                        import re
                        match = re.search(r'Message-ID:\s*<([^>]+)>', message)
                        if match:
                            return match.group(1)
            
            # Fallback: generate unique ID based on timestamp
            return None
            
        except Exception:
            return None