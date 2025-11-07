#!/usr/bin/env python3
"""
Demo seed script for development environment.
Creates a predictable API key for easy testing.
"""

import asyncio
import sys
from datetime import datetime

import bcrypt

# Add the app directory to Python path
sys.path.insert(0, ".")

from app.core.config import get_settings
from app.db.session import get_async_session
from app.models.api_key import APIKey


async def create_demo_api_key():
    """Create a demo API key for development."""
    # Use a predictable key for development
    demo_key = "sk_test_demo_key_12345"

    # Hash the demo key
    salt = bcrypt.gensalt()
    key_hash = bcrypt.hashpw(demo_key.encode("utf-8"), salt).decode("utf-8")

    # Create demo API key record
    api_key = APIKey(
        name="Demo API Key",
        key_hash=key_hash,
        daily_limit=100,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    # Save to database
    async for session in get_async_session():
        # Check if demo key already exists
        from sqlalchemy import select

        result = await session.execute(
            select(APIKey).where(APIKey.name == "Demo API Key")
        )
        existing_key = result.scalar_one_or_none()

        if existing_key:
            print("🔑 Demo API key already exists")
            return demo_key, str(existing_key.id)

        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        return demo_key, str(api_key.id)


async def main():
    """Create demo API key."""
    print("🚀 Creating demo API key for development...")

    try:
        demo_key, key_id = await create_demo_api_key()

        print("✅ Demo API key ready!")
        print()
        print("📋 Demo Credentials:")
        print("=" * 30)
        print(f"API Key: {demo_key}")
        print(f"Key ID:  {key_id}")
        print(f"Limit:   100 emails/day")
        print()
        print("🧪 Test with curl:")
        print(
            f"""curl -X POST "http://localhost:8000/api/v1/send" \\
  -H "X-API-Key: {demo_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "to": "test@example.com",
    "subject": "Hello from Teach Me Mailer! 👋",
    "html_body": "<h1>Welcome!</h1><p>Your email service is working perfectly.</p>",
    "text_body": "Welcome! Your email service is working perfectly."
  }}'"""
        )
        print()

    except Exception as e:
        print(f"❌ Failed to create demo API key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
