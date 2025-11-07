#!/usr/bin/env python3
"""
Create an initial API key for testing the mail gateway.
"""

import os
import sys
import asyncio

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.auth import AuthService


async def create_test_api_key():
    """Create a test API key."""
    print("🔑 Creating test API key...")
    
    try:
        settings = get_settings()
        
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(db, settings)
            
            # Create a test API key
            api_key_obj, plain_api_key = await auth_service.create_api_key(
                name="Test API Key",
                daily_limit=50,  # Higher limit for testing
            )
            
            await db.commit()
            
            print(f"✅ API Key created successfully!")
            print(f"   ID: {api_key_obj.id}")
            print(f"   Name: {api_key_obj.name}")
            print(f"   Daily Limit: {api_key_obj.daily_limit}")
            print(f"   Created: {api_key_obj.created_at}")
            print(f"")
            print(f"🔐 API KEY (save this, it won't be shown again):")
            print(f"   {plain_api_key}")
            print(f"")
            print(f"📝 Test command:")
            print(f'   curl -X POST "http://localhost:8000/api/v1/send" \\')
            print(f'     -H "X-API-Key: {plain_api_key}" \\')
            print(f'     -H "Content-Type: application/json" \\')
            print(f'     -d \'{{"to": ["test@example.com"], "subject": "Test", "body_text": "Hello!"}}\'')
            print(f"")
            print(f"📊 Check usage:")
            print(f'   curl -H "X-API-Key: {plain_api_key}" \\')
            print(f'     http://localhost:8000/api/v1/usage')
            
            return api_key_obj, plain_api_key
            
    except Exception as e:
        print(f"❌ Error creating API key: {e}")
        return None, None


if __name__ == "__main__":
    # Set test environment
    os.environ.update({
        'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost:5432/mailgw',
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_USER': 'test@example.com', 
        'SMTP_PASSWORD': 'testpassword',
        'FROM_EMAIL': 'noreply@example.com',
        'SECRET_KEY': 'test-secret-key-that-is-long-enough-to-pass-validation',
    })
    
    asyncio.run(create_test_api_key())