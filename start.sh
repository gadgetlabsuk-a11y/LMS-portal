#!/bin/bash
# LMS Course Builder - Start Script
# Usage: ./start.sh [--port PORT]

set -e

PORT=${1:-8000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "============================================"
echo "  LMS Course Builder v2.0.0"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
cd "$BACKEND_DIR"
pip install -r requirements.txt --break-system-packages -q 2>/dev/null || \
pip install -r requirements.txt -q

# Create uploads directory
mkdir -p "$BACKEND_DIR/uploads"

# Set environment variables if .env doesn't exist
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "Creating .env from template..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env" 2>/dev/null || true
fi

echo ""
echo "Running database migrations..."
cd "$BACKEND_DIR"
python3 -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo "ERROR: alembic upgrade head failed. Aborting start."
    exit 1
fi

echo ""
echo "Starting server on http://localhost:$PORT"
echo "Admin login: admin / (see .env or first-run log for password)"
echo "API docs: http://localhost:$PORT/docs"
echo "Press Ctrl+C to stop"
echo ""

cd "$BACKEND_DIR"
python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
