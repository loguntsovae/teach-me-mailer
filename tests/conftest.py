import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.core.config import Settings
from app.db.base import Base


# Test database URL (use sqlite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    TestSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost/testdb",
        SMTP_HOST="smtp.test.com",
        SMTP_PORT=587,
        SMTP_USER="test@test.com",
        SMTP_PASSWORD="testpass",
        FROM_EMAIL="test@test.com",
        SECRET_KEY="test-secret-key-32-chars-long-here",
        DEBUG=True,
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
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as ac:
        yield ac