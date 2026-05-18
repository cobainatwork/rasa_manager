#!/usr/bin/env bash
set -euo pipefail

echo "Running Alembic migrations..."
alembic upgrade head

echo "Running seed..."
python -m api.seed || echo "[seed] non-fatal failure, continuing"

echo "Starting uvicorn..."
exec uvicorn main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8050}"
