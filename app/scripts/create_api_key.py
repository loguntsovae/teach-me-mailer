#!/usr/bin/env python3
"""
Create API Key Script for Mail Gateway

This script creates a new API key with the specified name and daily limit.
The API key is securely generated, hashed with bcrypt, and stored in the database.

Usage:
    python -m app.scripts.create_api_key --name "default" --limit 15
    python -m app.scripts.create_api_key --name "production" --limit 100
    python -m app.scripts.create_api_key --name "test" --limit 5
"""

import argparse
import asyncio
import secrets
import string
import sys
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_engine
from app.models.api_key import APIKey


def generate_api_key(length: int = 32, prefix: str = "sk_") -> str:
    """Generate a secure API key with the specified length and prefix.
    
    Args:
        length: Total length of the key including prefix
        prefix: Prefix for the API key (default: "sk_")
        
    Returns:
        A securely generated API key string
    """
    # Calculate length needed for random part
    random_length = length - len(prefix)
    if random_length <= 0:
        raise ValueError(f"Length must be greater than prefix length ({len(prefix)})")
    
    # Use cryptographically secure random generation
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(random_length))
    
    return f"{prefix}{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt.
    
    Args:
        api_key: The plaintext API key to hash
        
    Returns:
        The bcrypt hash of the API key
    """
    # Use a reasonable cost factor for production (12 provides good security/performance balance)
    return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


async def check_name_exists(session: AsyncSession, name: str) -> bool:
    """Check if an API key with the given name already exists.
    
    Args:
        session: Database session
        name: Name to check for uniqueness
        
    Returns:
        True if name exists, False otherwise
    """
    result = await session.execute(
        select(APIKey).where(APIKey.name == name)
    )
    return result.scalar_one_or_none() is not None


async def create_api_key_record(
    session: AsyncSession, 
    name: str, 
    key_hash: str, 
    daily_limit: int
) -> APIKey:
    """Create and save an API key record to the database.
    
    Args:
        session: Database session
        name: Human-readable name for the API key
        key_hash: bcrypt hash of the API key
        daily_limit: Daily email limit for this key
        
    Returns:
        The created APIKey object
    """
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        daily_limit=daily_limit,
        is_active=True
    )
    
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    
    return api_key


async def main() -> None:
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="Create a new API key for Mail Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "default" --limit 15
  %(prog)s --name "production" --limit 100
  %(prog)s --name "test" --limit 5

The generated API key will be displayed once and cannot be retrieved again.
Make sure to save it securely.
        """
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Human-readable name for the API key (must be unique)"
    )
    
    parser.add_argument(
        "--limit", 
        type=int,
        default=15,
        help="Daily email limit for this API key (default: %(default)s)"
    )
    
    parser.add_argument(
        "--key-length",
        type=int,
        default=32,
        help="Total length of the generated API key (default: %(default)s)"
    )
    
    parser.add_argument(
        "--prefix",
        default="sk_",
        help="Prefix for the API key (default: %(default)s)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.limit <= 0:
        print("Error: Daily limit must be greater than 0", file=sys.stderr)
        sys.exit(1)
        
    if args.key_length < len(args.prefix) + 8:
        print(f"Error: Key length must be at least {len(args.prefix) + 8} characters", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create database session
        async with AsyncSession(async_engine) as session:
            # Check if name already exists
            if await check_name_exists(session, args.name):
                print(f"Error: API key with name '{args.name}' already exists", file=sys.stderr)
                sys.exit(1)
            
            # Generate API key
            print(f"Generating API key for '{args.name}'...")
            api_key = generate_api_key(length=args.key_length, prefix=args.prefix)
            
            # Hash the key
            print("Hashing API key...")
            key_hash = hash_api_key(api_key)
            
            # Create database record
            print("Saving to database...")
            api_key_record = await create_api_key_record(
                session=session,
                name=args.name,
                key_hash=key_hash,
                daily_limit=args.limit
            )
            
            # Success output
            print("\n" + "="*60)
            print("✅ API KEY CREATED SUCCESSFULLY")
            print("="*60)
            print(f"Name: {args.name}")
            print(f"ID: {api_key_record.id}")
            print(f"Daily Limit: {args.limit} emails")
            print(f"Status: Active")
            print(f"Created: {api_key_record.created_at}")
            print("\n" + "🔑 API KEY (save this immediately):")
            print("-"*60)
            print(f"{api_key}")
            print("-"*60)
            print("\n⚠️  IMPORTANT: This API key will not be shown again!")
            print("   Save it securely and use it in your X-API-Key header.")
            print("\n📖 Usage example:")
            print(f'   curl -H "X-API-Key: {api_key}" \\')
            print('        -H "Content-Type: application/json" \\')
            print('        -d \'{"to": "user@example.com", "subject": "Test", "text_body": "Hello!"}\' \\')
            print('        http://localhost:8000/api/v1/send')
            print()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error creating API key: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())