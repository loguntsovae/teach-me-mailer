#!/usr/bin/env python3
"""Check if 'devdb' exists on local Postgres and create it if missing.

This script uses psycopg2 (sync) and expects local Postgres reachable with
username/password from .env: postgres/postgres and port 5432.
"""
import sys

import psycopg2

MASTER_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
DEV_URL = "postgresql://postgres:postgres@localhost:5432/devdb"

try:
    conn = psycopg2.connect(MASTER_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", ("devdb",))
    if cur.fetchone():
        print("✅ Database devdb exists")
    else:
        print("ℹ️ Database devdb not found, creating...")
        cur.execute("CREATE DATABASE devdb")
        print("✅ Created database devdb")
    cur.close()
    conn.close()

    # Connect to devdb and show number of tables in public schema
    conn2 = psycopg2.connect(DEV_URL)
    cur2 = conn2.cursor()
    cur2.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
    count = cur2.fetchone()[0]
    print(f"Tables in devdb.public: {count}")
    cur2.close()
    conn2.close()

except Exception as exc:
    print("❌ Error connecting to Postgres:", exc)
    sys.exit(2)
