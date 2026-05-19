#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/web_frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "[smapo] stopping services..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[smapo] missing command: $1" >&2
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

trap cleanup EXIT INT TERM

require_command "$PYTHON_BIN"
require_command npm
require_command lsof

if [[ ! -f "$ROOT_DIR/manage.py" ]]; then
  echo "[smapo] manage.py not found under $ROOT_DIR" >&2
  exit 1
fi

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "[smapo] package.json not found under $FRONTEND_DIR" >&2
  exit 1
fi

if port_in_use "$BACKEND_PORT"; then
  echo "[smapo] backend port $BACKEND_PORT is already in use" >&2
  lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >&2 || true
  exit 1
fi

if port_in_use "$FRONTEND_PORT"; then
  echo "[smapo] frontend port $FRONTEND_PORT is already in use" >&2
  lsof -nP -iTCP:"$FRONTEND_PORT" -sTCP:LISTEN >&2 || true
  exit 1
fi

echo "[smapo] starting backend: http://$BACKEND_HOST:$BACKEND_PORT"
(
  cd "$ROOT_DIR"
  "$PYTHON_BIN" manage.py runserver "$BACKEND_HOST:$BACKEND_PORT"
) &
BACKEND_PID="$!"

echo "[smapo] starting frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID="$!"

echo
echo "[smapo] frontend: http://$FRONTEND_HOST:$FRONTEND_PORT/"
echo "[smapo] backend:  http://$BACKEND_HOST:$BACKEND_PORT/"
echo "[smapo] press Ctrl+C to stop both services"
echo

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[smapo] backend process exited"
    exit 1
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "[smapo] frontend process exited"
    exit 1
  fi
  sleep 1
done
