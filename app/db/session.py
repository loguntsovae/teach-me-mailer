from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Use async_sessionmaker which is typed for AsyncSession
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
