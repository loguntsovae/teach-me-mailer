from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class MailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., max_length=256, description="Email subject")
    html: Optional[str] = Field(None, description="HTML email body")
    text: Optional[str] = Field(None, description="Plain text email body")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom email headers")

    @validator("html", "text")
    def validate_body_required(cls, v, values):
        """Ensure either html or text is provided."""
        html = values.get("html") if "html" in values else v
        text = values.get("text") if "text" in values else v

        if not html and not text:
            raise ValueError("Either html or text body is required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "to": "user@example.com",
                "subject": "Test Email",
                "html": "<h1>Hello</h1><p>This is a test email!</p>",
                "text": "Hello, this is a test email!",
                "headers": {"X-Custom": "v"},
            }
        }


class MailResponse(BaseModel):
    status: str = Field(..., description="Email status (queued)")
    remaining: int = Field(..., description="Remaining emails in daily limit")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "remaining": 95,
            }
        }


class SendLogResponse(BaseModel):
    id: int
    api_key: str
    to_email: str
    from_email: str
    subject: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "0.1.0",
            }
        }


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., description="Name for the API key")
    daily_limit: Optional[int] = Field(
        None, description="Optional daily email limit for the key"
    )


class CreateAPIKeyResponse(BaseModel):
    id: str = Field(..., description="API key record ID")
    plain_key: str = Field(
        ..., description="Plain API key (save this; shown only once)"
    )
    name: str
    daily_limit: Optional[int]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "plain_key": "sk_test_abcdefghijklmnop",
                "name": "service-integration",
                "daily_limit": 100,
            }
        }
