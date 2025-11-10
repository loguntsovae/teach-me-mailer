#!/usr/bin/env python3
"""
Script to create and setup the test database for teach-me-mailer.

This script:
1. Creates the test database if it doesn't exist
2. Runs Alembic migrations on the test database
3. Verifies the database is ready for testing

Usage:
    python scripts/setup_test_db.py
"""

import asyncio
import sys
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config

# Test database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_NAME = "test_teach_me_mailer"


async def create_test_database():
    """Create test database if it doesn't exist."""
    try:
        # Connect to default 'postgres' database
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres",
        )

        # Check if test database exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME)

        if exists:
            print(f"✓ Test database '{DB_NAME}' already exists")
        else:
            # Create test database
            await conn.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"✓ Created test database '{DB_NAME}'")

        await conn.close()

    except Exception as e:
        print(f"✗ Error creating test database: {e}")
        sys.exit(1)


async def verify_test_database():
    """Verify test database connection and create mailer schema."""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )

        # Create mailer schema if it doesn't exist
        await conn.execute("CREATE SCHEMA IF NOT EXISTS mailer")
        print("✓ Schema 'mailer' created/verified")

        # Test connection
        version = await conn.fetchval("SELECT version()")
        print("✓ Connected to test database")
        print(f"  PostgreSQL version: {version.split(',')[0]}")

        await conn.close()

    except Exception as e:
        print(f"✗ Error connecting to test database: {e}")
        sys.exit(1)


def run_migrations():
    """Run Alembic migrations on test database."""
    try:
        # Get project root directory
        project_root = Path(__file__).parent.parent
        alembic_ini = project_root / "alembic.ini"

        if not alembic_ini.exists():
            print(f"✗ alembic.ini not found at {alembic_ini}")
            sys.exit(1)

        # Load Alembic config
        alembic_cfg = Config(str(alembic_ini))

        # Override database URL for test database
        test_db_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        # Run migrations
        print("Running Alembic migrations on test database...")
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations completed successfully")

    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        sys.exit(1)


async def main():
    """Main setup function."""
    print("=" * 60)
    print("Setting up test database for teach-me-mailer")
    print("=" * 60)
    print()

    # Step 1: Create database
    print("Step 1: Creating test database...")
    await create_test_database()
    print()

    # Step 2: Run migrations
    print("Step 2: Running migrations...")
    run_migrations()
    print()

    # Step 3: Verify connection
    print("Step 3: Verifying connection...")
    await verify_test_database()
    print()

    print("=" * 60)
    print("✓ Test database setup completed successfully!")
    print("=" * 60)
    print()
    print("You can now run tests with: pytest")
    print("Or run specific test suites:")
    print("  - pytest tests/unit/")
    print("  - pytest tests/integration/")
    print("  - pytest tests/e2e/")


if __name__ == "__main__":
    asyncio.run(main())
