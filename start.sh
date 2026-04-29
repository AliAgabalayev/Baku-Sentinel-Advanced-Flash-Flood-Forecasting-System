#!/usr/bin/env bash
set -e

# Load backend .env if present
[ -f .env ] && export $(grep -v '^#' .env | xargs)

echo "Starting Baku Sentinel..."

uvicorn api:app --port 8000 --reload &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

echo ""
echo "  Backend  → http://localhost:8000/docs"
echo "  Frontend → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop."
echo ""

wait
