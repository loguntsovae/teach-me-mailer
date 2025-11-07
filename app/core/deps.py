from typing import AsyncGenerator, Optional
import uuid

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, Settings
from app.db.session import get_async_session
from app.services.auth import AuthService, AuthResult
from app.models.api_key import APIKey


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async for session in get_async_session():
        yield session


def get_settings_dependency() -> Settings:
    """Dependency to get settings."""
    return get_settings()


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dependency),
) -> AuthService:
    """Dependency to get auth service."""
    return AuthService(db, settings)


async def get_current_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIKey:
    """Dependency to validate API key via X-API-Key header and return the APIKey object."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    result, api_key_obj = await auth_service.validate_api_key_detailed(x_api_key)
    
    if result == AuthResult.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is disabled",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    elif result == AuthResult.INVALID or not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    return api_key_obj