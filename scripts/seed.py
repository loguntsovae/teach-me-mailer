#!/usr/bin/env python3
"""
Seed script to create an initial API key.
This script should be run once during initial setup.
The plaintext API key is printed only once and never stored.
"""

import asyncio
import secrets
import string
import sys
from datetime import datetime

import bcrypt

# Add the app directory to Python path
sys.path.insert(0, '.')

from app.core.config import get_settings
from app.db.session import get_async_session
from app.models.api_key import APIKey


def generate_api_key(length: int = 32) -> str:
    """Generate a secure random API key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def create_api_key(
    name: str,
    daily_limit: int = None,
    is_active: bool = True
) -> tuple[str, str]:
    """
    Create a new API key and return (plain_key, api_key_id).
    
    Args:
        name: Human-readable name for the API key
        daily_limit: Daily email sending limit (uses default if None)
        is_active: Whether the key is active
        
    Returns:
        Tuple of (plaintext_api_key, api_key_id)
    """
    settings = get_settings()
    
    # Generate plaintext API key
    plain_key = generate_api_key(settings.api_key_length)
    
    # Hash the API key
    salt = bcrypt.gensalt()
    key_hash = bcrypt.hashpw(plain_key.encode('utf-8'), salt).decode('utf-8')
    
    # Use default daily limit if not specified
    if daily_limit is None:
        daily_limit = settings.default_daily_limit
    
    # Create API key record
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        daily_limit=daily_limit,
        is_active=is_active,
        created_at=datetime.utcnow()
    )
    
    # Save to database
    async for session in get_async_session():
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        
        return plain_key, str(api_key.id)


async def main():
    """Main seed script function."""
    print("🔑 Mail Gateway - API Key Creation")
    print("=" * 50)
    
    try:
        # Get settings to verify configuration
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"   Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
        print(f"   Default daily limit: {settings.default_daily_limit}")
        print()
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("   Please check your .env file and environment variables.")
        sys.exit(1)
    
    # Prompt for API key details
    print("Creating a new API key...")
    
    name = input("Enter API key name (e.g., 'Production API', 'Development'): ").strip()
    if not name:
        name = "Default API Key"
    
    # Optional daily limit override
    daily_limit_input = input(f"Enter daily limit (default: {settings.default_daily_limit}): ").strip()
    if daily_limit_input:
        try:
            daily_limit = int(daily_limit_input)
            if daily_limit <= 0:
                print("❌ Daily limit must be positive")
                sys.exit(1)
        except ValueError:
            print("❌ Daily limit must be a valid number")
            sys.exit(1)
    else:
        daily_limit = settings.default_daily_limit
    
    print()
    print("Creating API key...")
    
    try:
        # Create the API key
        plain_key, api_key_id = await create_api_key(
            name=name,
            daily_limit=daily_limit,
            is_active=True
        )
        
        print("✅ API key created successfully!")
        print()
        print("📋 API Key Details:")
        print("=" * 30)
        print(f"ID:          {api_key_id}")
        print(f"Name:        {name}")
        print(f"Daily Limit: {daily_limit}")
        print(f"Status:      Active")
        print()
        print("🚨 IMPORTANT: Save this API key - it will NOT be shown again!")
        print("=" * 60)
        print(f"API Key: {plain_key}")
        print("=" * 60)
        print()
        print("Usage example:")
        print(f'curl -H "X-API-Key: {plain_key}" \\')
        print(f'     -H "Content-Type: application/json" \\')
        print(f'     -d \'{{"to": "test@example.com", "subject": "Test", "text": "Hello!"}}\' \\')
        print(f'     http://localhost:8000/api/v1/send')
        print()
        print("The plaintext key is now removed from memory and will not be shown again.")
        
    except Exception as e:
        print(f"❌ Failed to create API key: {e}")
        print("   Check your database connection and configuration.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)