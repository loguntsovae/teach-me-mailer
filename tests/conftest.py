import asyncio
import os
import subprocess

import psycopg2
import pytest
from httpx import AsyncClient
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app

# Test database URL (use PostgreSQL for testing)
TEST_DATABASE_NAME = "devdb"
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://postgres:postgres@localhost:5432/{TEST_DATABASE_NAME}"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create test DB if missing, apply migrations before tests, rollback after."""
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    # Connect to default postgres database
    conn = psycopg2.connect(
        "dbname=postgres user=postgres password=postgres host=localhost"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DATABASE_NAME}'")
    exists = cur.fetchone()

    if not exists:
        print(f"Creating test database '{TEST_DATABASE_NAME}'...")
        cur.execute(f"CREATE DATABASE {TEST_DATABASE_NAME}")
    else:
        print(f"Database '{TEST_DATABASE_NAME}' already exists")

    cur.close()
    conn.close()

    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)
    yield
    subprocess.run(["uv", "run", "alembic", "downgrade", "base"], check=True)


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    # Create an AsyncSession directly to satisfy typing and avoid sessionmaker overload
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        DEBUG=True,
        DATABASE_URL=TEST_DATABASE_URL,
        SMTP_HOST="test_smtp_host",
        SMTP_USER="test_user",
        SMTP_PASSWORD="test_password",
        FROM_EMAIL="test@example.com",
        APP_SECRET_KEY="x" * 32,
    )


@pytest.fixture
async def test_app(test_session, test_settings):
    """Create test FastAPI application."""
    app = create_app()

    # Override dependencies
    from app.core.deps import get_db, get_settings_dependency

    async def override_get_db():
        yield test_session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings_dependency] = override_get_settings

    yield app

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app):
    """Create test HTTP client."""
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://testserver"
    ) as ac:
        yield ac
