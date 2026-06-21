#!/bin/bash
# Script to run both backend and frontend concurrently in the quant-lttd-ichimoku

# Ensure we are in the script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# Free ports
BACKEND_PORT=8000
FRONTEND_PORT=5174

echo "Freeing ports $BACKEND_PORT (backend) and $FRONTEND_PORT (frontend)..."
for port in $BACKEND_PORT $FRONTEND_PORT; do
  PID=$(lsof -t -i:$port 2>/dev/null)
  if [ -n "$PID" ]; then
    echo "Killing process on port $port (PID: $PID)"
    kill -9 $PID 2>/dev/null
  fi
done

echo "=== STARTING QUANT LTTD ICHIMOKU SYSTEM ==="

cleanup() {
  echo "Stopping services..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "Starting backend server..."
export PYTHONPATH="$DIR/src"
python3 "$DIR/src/ichimoku_quant/server.py" &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend dev server..."
cd "$DIR/web"
bun run dev --port 5174 &
FRONTEND_PID=$!


# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
