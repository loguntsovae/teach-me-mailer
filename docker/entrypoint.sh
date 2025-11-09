#!/bin/sh
set -e

# Wait for DB to be ready
if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+):([0-9]+).*|\1|')
  DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+):([0-9]+).*|\2|')
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; do
    sleep 1
  done
fi

echo "Database is ready."

# Run migrations
echo "Running migrations..."
uv run alembic upgrade head

# Start FastAPI app with hui (ASGI)
echo "Starting app..."
exec uv run gunicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8088} --workers ${WORKERS:-2}
