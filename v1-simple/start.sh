#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8500}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo '{"timestamp":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","level":"INFO","message":"Starting LMS Course Builder","port":'"$PORT"'}'

exec python -m uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')"
