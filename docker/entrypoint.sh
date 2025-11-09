#!/bin/bash
set -euo pipefail

# Forward signals to child process so Docker can stop the container cleanly
_child_pid=0
term() {
  if [ "${_child_pid}" -ne 0 ]; then
    kill -TERM "${_child_pid}" 2>/dev/null || true
    wait "${_child_pid}" 2>/dev/null || true
  fi
  exit 0
}
# Use portable signal names (some /bin/sh implementations reject the SIG prefix)
trap term TERM INT

# Wait for DB to be ready
if [ -n "${DATABASE_URL-}" ]; then
  echo "Waiting for database..."
  DB_HOST=$(echo "${DATABASE_URL}" | sed -E 's|.*@([^:/]+):([0-9]+).*|\1|')
  DB_PORT=$(echo "${DATABASE_URL}" | sed -E 's|.*@([^:/]+):([0-9]+).*|\2|')
  until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" >/dev/null 2>&1; do
    sleep 1
  done
fi

echo "Database is ready."

# Run migrations
echo "Running migrations..."
# execute via `uv run` to use the environment managed by the `uv` tool
uv run alembic upgrade head

# Start FastAPI app with Uvicorn
echo "Starting app (uvicorn)..."
# Start uvicorn directly via `uv run` so it runs in the installed environment
uv run uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${APP_PORT:-8088}" \
  --workers "${WORKERS:-2}" &

# Save child PID so trap can forward signals
_child_pid=$!
wait "${_child_pid}"
