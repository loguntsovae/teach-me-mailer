"""
Global test fixtures and configuration.

This module provides shared fixtures for all tests including:
- Database session management
- Test API keys
- HTTP test client
- Mock SMTP server
- Test settings
"""

import asyncio
import uuid
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.base import Base
from app.main import app as main_app
from app.models.api_key import APIKey

# Test database URL (PostgreSQL on localhost)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_teach_me_mailer"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with overrides using environment variables."""
    import os

    # Set test environment variables
    test_env = {
        "APP_NAME": "test-mail-gateway",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_STARTTLS": "true",
        "SMTP_FROM": "noreply@test.com",
        "DEFAULT_DAILY_LIMIT": "100",
        "RATE_WINDOW_DAYS": "1",
        "APP_SECRET_KEY": "test-secret-key-for-testing-only",
        "ALLOW_DOMAINS": "",
        "SENTRY_DSN": "",
    }

    # Save old values
    old_env = {}
    for key, value in test_env.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value

    # Create Settings with test values
    settings = Settings()

    # Restore old values
    for key, value in old_env.items():  # type: ignore[assignment]
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)

    return settings


@pytest.fixture(scope="session")
def test_settings_with_allowlist() -> Settings:
    """Create test settings with domain allowlist enabled."""
    import os

    test_env = {
        "APP_NAME": "test-mail-gateway",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@test.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_STARTTLS": "true",
        "SMTP_FROM": "noreply@test.com",
        "DEFAULT_DAILY_LIMIT": "100",
        "RATE_WINDOW_DAYS": "1",
        "APP_SECRET_KEY": "test-secret-key-for-testing-only",
        "ALLOW_DOMAINS": "example.com,test.com",  # Allowlist enabled
        "SENTRY_DSN": "",
    }

    old_env = {}
    for key, value in test_env.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value

    settings = Settings()

    for key, value in old_env.items():  # type: ignore[assignment]
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)

    return settings


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # Disable pooling for tests
    )

    # Create mailer schema and all tables
    async with engine.begin() as conn:
        # Create schema
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS mailer"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up after all tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Uses a transaction that is rolled back after the test.
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Rollback all changes after test


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession) -> APIKey:
    """Create a test API key for authentication tests."""
    import bcrypt

    # Generate test API key
    raw_key = "sk_test_demo_key_12345"

    # Hash the key
    salt = bcrypt.gensalt()
    hashed_key = bcrypt.hashpw(raw_key.encode("utf-8"), salt).decode("utf-8")

    # Create database record
    api_key = APIKey(
        id=uuid.uuid4(),
        key_hash=hashed_key,
        name="Test API Key",
        is_active=True,
        daily_limit=100,
        allowed_recipients=None,  # All recipients allowed
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    # Store raw key as attribute for use in tests
    api_key.raw_key = raw_key

    return api_key


@pytest_asyncio.fixture
async def test_api_key_inactive(db_session: AsyncSession) -> APIKey:
    """Create an inactive test API key."""
    import bcrypt

    raw_key = "sk_test_inactive_key_99999"
    salt = bcrypt.gensalt()
    hashed_key = bcrypt.hashpw(raw_key.encode("utf-8"), salt).decode("utf-8")

    api_key = APIKey(
        id=uuid.uuid4(),
        key_hash=hashed_key,
        name="Inactive Test API Key",
        is_active=False,
        daily_limit=100,
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    api_key.raw_key = raw_key

    return api_key


@pytest_asyncio.fixture
async def test_api_key_with_recipient_limit(db_session: AsyncSession) -> APIKey:
    """Create a test API key with allowed recipients restriction."""
    import bcrypt

    raw_key = "sk_test_limited_recipients_key"
    salt = bcrypt.gensalt()
    hashed_key = bcrypt.hashpw(raw_key.encode("utf-8"), salt).decode("utf-8")

    api_key = APIKey(
        id=uuid.uuid4(),
        key_hash=hashed_key,
        name="Limited Recipients Test Key",
        is_active=True,
        daily_limit=50,
        allowed_recipients=["allowed@test.com", "another@test.com"],
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    api_key.raw_key = raw_key

    return api_key


@pytest.fixture
def mock_smtp() -> AsyncMock:
    """Mock SMTP client for email sending tests."""
    mock = AsyncMock()
    # aiosmtplib.send returns a dict with recipient -> (code, message)
    mock.return_value = {"test@example.com": (250, "Message accepted")}
    return mock


@pytest.fixture(autouse=True)
def auto_mock_smtp(monkeypatch):
    """
    Automatically mock aiosmtplib.send for ALL tests to prevent real email sending.
    This is a critical safety measure to ensure no emails are sent during testing.
    """

    async def mock_send(*args, **kwargs):
        """Mock aiosmtplib.send - returns success response for any recipient."""
        # Extract 'to' recipients from message
        message = args[0] if args else kwargs.get("message")
        recipients = []

        if message is not None and hasattr(message, "get"):
            to_header = message.get("To", "")
            if to_header:
                recipients = [email.strip() for email in to_header.split(",")]

        # Default to single recipient if we can't parse
        if not recipients:
            recipients = ["test@example.com"]

        # Return dict with success status for each recipient
        return {recipient: (250, "Message accepted for delivery") for recipient in recipients}

    monkeypatch.setattr("aiosmtplib.send", mock_send)
    return mock_send


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create FastAPI test application with settings override."""
    from app.core.config import get_settings

    # Override settings dependency
    main_app.dependency_overrides[get_settings] = lambda: test_settings

    return main_app


@pytest_asyncio.fixture
async def test_client(app: FastAPI, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async HTTP client for API testing.
    Overrides database dependency to use test session.
    """
    from app.core.deps import get_db

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create test HTTP client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_mailer_service(monkeypatch):
    """Mock MailerService for unit tests."""
    mock = MagicMock()
    mock.send_email = AsyncMock(return_value="test-message-id-123")
    return mock


@pytest.fixture
def mock_rate_limit_service(monkeypatch):
    """Mock RateLimitService for unit tests."""
    mock = MagicMock()
    mock.check_daily_limit = AsyncMock(return_value=True)
    mock.record_request = AsyncMock()
    return mock


@pytest.fixture
def mock_sentry(monkeypatch):
    """Mock Sentry SDK to prevent real error reporting in tests."""
    mock_sentry = MagicMock()
    monkeypatch.setattr("sentry_sdk.init", MagicMock())
    monkeypatch.setattr("sentry_sdk.capture_exception", MagicMock())
    monkeypatch.setattr("sentry_sdk.capture_message", MagicMock())
    return mock_sentry


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests - isolated component tests")
    config.addinivalue_line("markers", "integration: Integration tests - component interaction tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests - full flow tests")
    config.addinivalue_line("markers", "slow: Slow tests that take longer to run")
    config.addinivalue_line("markers", "smtp: Tests that require SMTP mocking")
    config.addinivalue_line("markers", "database: Tests that require database access")
