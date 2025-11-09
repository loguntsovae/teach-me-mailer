#!/usr/bin/env python3
"""
Demo seed script for development environment.
Creates a predictable API key for easy testing.
"""

import asyncio
import sys
from datetime import datetime

import bcrypt
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.api_key import APIKey

# Add the app directory to Python path
sys.path.insert(0, ".")


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
        result = await session.execute(
            select(APIKey).where(APIKey.name == "Demo API Key")
        )
        existing_key = result.scalar_one_or_none()

        if existing_key:
            print("Demo API key already exists")
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
        print("API Key: " + demo_key)
        print("Key ID:  " + key_id)
        print("Limit:   100 emails/day")
        print()
        print("🧪 Test with curl:")
        print(
            "curl -X POST 'http://localhost:8000/api/v1/send' \\\n"
            "  -H 'X-API-Key: " + demo_key + "' \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\n"
            '    "to": "test@example.com",\n'
            '    "subject": "Hello from Teach Me Mailer! 👋",\n'
            '    "html_body": "<h1>Welcome!</h1><p>Your email service is working perfectly.</p>",\n'
            '    "text_body": "Welcome! Your email service is working perfectly."\n'
            "  }'"
        )
        print()

    except Exception as e:
        print("❌ Failed to create demo API key: " + str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
