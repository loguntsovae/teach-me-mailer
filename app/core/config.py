from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Application
    app_name: str = Field(default="mail-gateway", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database (REQUIRED)
    database_url: str = Field(
        ...,  # Required field
        alias="DATABASE_URL",
        description="PostgreSQL connection URL",
    )

    # Mail Settings (REQUIRED)
    smtp_host: str = Field(
        ...,  # Required field
        alias="SMTP_HOST",
        description="SMTP server hostname",
    )
    smtp_port: int = Field(
        default=587,
        alias="SMTP_PORT",
        ge=1,
        le=65535,
        description="SMTP server port",
    )
    smtp_user: str = Field(
        ...,  # Required field
        alias="SMTP_USER",
        description="SMTP username",
    )
    smtp_password: str = Field(
        ...,  # Required field
        alias="SMTP_PASSWORD",
        description="SMTP password",
    )
    smtp_starttls: bool = Field(
        default=True,
        alias="SMTP_STARTTLS",
        description="Use STARTTLS for SMTP",
    )
    from_email: str = Field(
        ...,  # Required field
        alias="FROM_EMAIL",
        description="Default sender email address",
    )

    # Rate Limiting
    default_daily_limit: int = Field(
        default=15,
        alias="DEFAULT_DAILY_LIMIT",
        ge=1,
        description="Default daily email limit per API key",
    )
    rate_window_days: int = Field(
        default=1,
        alias="RATE_WINDOW_DAYS",
        ge=1,
        description="Rate limiting window in days",
    )

    # Security (REQUIRED)
    app_secret_key: str = Field(
        ...,  # Required field
        alias="APP_SECRET_KEY",
        min_length=32,
        description="Secret key for signing tokens",
    )
    api_key_length: int = Field(
        default=32,
        alias="API_KEY_LENGTH",
        ge=16,
        le=128,
        description="Length of generated API keys",
    )

    # Sentry DSN (optional)
    sentry_dsn: Optional[str] = Field(
        default=None,
        alias="SENTRY_DSN",
        description="Sentry DSN for error tracking (optional)",
    )

    # Security settings
    cors_origins: Optional[List[str]] = Field(
        default=None,
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins",
    )
    max_request_size: int = Field(
        default=262144,  # 256KB
        alias="MAX_REQUEST_SIZE",
        ge=1024,
        le=10485760,  # 1KB to 10MB
        description="Maximum request body size in bytes",
    )

    # Domain Restrictions (Optional)
    allow_domains: Optional[List[str]] = Field(
        default=None,
        alias="ALLOW_DOMAINS",
        description="Comma-separated list of allowed domains for recipients",
    )

    LOG_JSON: bool = True
    APP_PORT: int = 8088
    PUBLISH_APP_PORT: int = 8088

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("allow_domains", pre=True)
    def parse_domains(cls, v):
        """Parse comma-separated domains."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [domain.strip() for domain in v.split(",") if domain.strip()]
        return v

    @validator("smtp_starttls", pre=True)
    def parse_smtp_starttls(cls, v):
        """Parse SMTP_STARTTLS as boolean from string."""
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return bool(v)

    @validator("database_url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        # Require PostgreSQL URLs for all environments
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v

    @validator("from_email")
    def validate_from_email(cls, v):
        """Basic email validation."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("FROM_EMAIL must be a valid email address")
        return v

    def model_post_init(self, __context):
        """Validate critical configuration after initialization."""
        # Log configuration summary (without sensitive data)
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info(
            "Configuration loaded",
            app_name=self.app_name,
            debug=self.debug,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            daily_limit=self.default_daily_limit,
            rate_window=self.rate_window_days,
            allow_domains=self.allow_domains,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        # mypy sees required named args on the generated Settings signature;
        # in runtime pydantic reads environment variables so calling with no
        # args is valid. Silence the false-positive here.
        return Settings(
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/devdb",
            SMTP_HOST="smtp.example.com",
            SMTP_USER="user@example.com",
            SMTP_PASSWORD="password",
            FROM_EMAIL="noreply@example.com",
            APP_SECRET_KEY="x" * 32,
        )
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        print("💡 Check your environment variables and .env file")
        raise SystemExit(1) from e
