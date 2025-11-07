import secrets
from datetime import datetime
from typing import Optional, Tuple
import uuid
from enum import Enum

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

import structlog

from app.core.config import Settings
from app.models.api_key import APIKey


logger = structlog.get_logger(__name__)


class AuthResult(Enum):
    """Authentication result types."""
    VALID = "valid"
    INVALID = "invalid"
    INACTIVE = "inactive"


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(api_key.encode('utf-8'), salt).decode('utf-8')

    def _verify_api_key(self, api_key: str, hashed: str) -> bool:
        """Verify API key against hash."""
        return bcrypt.checkpw(api_key.encode('utf-8'), hashed.encode('utf-8'))

    async def validate_api_key_detailed(self, api_key: str) -> Tuple[AuthResult, Optional[APIKey]]:
        """Validate an API key and return detailed result.
        
        Returns:
            tuple: (AuthResult, APIKey object if valid)
        """
        try:
            # Get all API keys (both active and inactive)
            stmt = select(APIKey)
            result = await self.db.execute(stmt)
            api_keys = result.scalars().all()

            # Check each key hash
            for key_obj in api_keys:
                if self._verify_api_key(api_key, key_obj.key_hash):
                    if key_obj.is_active:
                        logger.info(
                            "API key validated successfully",
                            api_key_id=str(key_obj.id),
                            name=key_obj.name,
                            daily_limit=key_obj.daily_limit,
                        )
                        return (AuthResult.VALID, key_obj)
                    else:
                        logger.warning(
                            "API key is inactive",
                            api_key_id=str(key_obj.id),
                            name=key_obj.name,
                        )
                        return (AuthResult.INACTIVE, None)

            logger.warning("Invalid API key")
            return (AuthResult.INVALID, None)

        except Exception as e:
            logger.error(
                "Error validating API key",
                error=str(e),
            )
            return (AuthResult.INVALID, None)

    async def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key and return the APIKey object if valid."""
        result, key_obj = await self.validate_api_key_detailed(api_key)
        return key_obj if result == AuthResult.VALID else None

    async def create_api_key(
        self,
        name: str,
        daily_limit: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key.
        
        Returns:
            tuple: (APIKey object, plain text API key)
        """
        # Generate secure random key
        api_key = secrets.token_urlsafe(self.settings.api_key_length)
        
        # Hash the API key
        key_hash = self._hash_api_key(api_key)

        # Create API key object
        key_obj = APIKey(
            key_hash=key_hash,
            name=name,
            daily_limit=daily_limit,
            is_active=True,
        )

        self.db.add(key_obj)
        await self.db.flush()

        logger.info(
            "API key created",
            api_key_id=str(key_obj.id),
            name=name,
            daily_limit=daily_limit,
        )

        return key_obj, api_key

    async def deactivate_api_key(self, api_key_id: uuid.UUID) -> bool:
        """Deactivate an API key by ID."""
        try:
            stmt = select(APIKey).where(APIKey.id == api_key_id)
            result = await self.db.execute(stmt)
            key_obj = result.scalar_one_or_none()

            if key_obj:
                key_obj.is_active = False
                await self.db.flush()

                logger.info(
                    "API key deactivated",
                    api_key_id=str(api_key_id),
                    name=key_obj.name,
                )
                return True
            else:
                logger.warning(
                    "API key not found for deactivation",
                    api_key_id=str(api_key_id),
                )
                return False

        except Exception as e:
            logger.error(
                "Error deactivating API key",
                api_key_id=str(api_key_id),
                error=str(e),
            )
            return False

    async def get_api_key_info(self, api_key_id: uuid.UUID) -> Optional[APIKey]:
        """Get API key information by ID."""
        try:
            stmt = select(APIKey).where(APIKey.id == api_key_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Error getting API key info",
                api_key_id=str(api_key_id),
                error=str(e),
            )
            return None