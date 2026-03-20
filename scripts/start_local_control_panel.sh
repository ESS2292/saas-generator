#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$ROOT_DIR/agent-env/bin"
WEB_LOG="$ROOT_DIR/.control-panel-web.log"
WORKER_LOG="$ROOT_DIR/.control-panel-worker.log"
WEB_PID_FILE="$ROOT_DIR/.control-panel-web.pid"
WORKER_PID_FILE="$ROOT_DIR/.control-panel-worker.pid"

if [[ ! -x "$VENV_BIN/python" ]] || [[ ! -x "$VENV_BIN/uvicorn" ]]; then
  echo "Expected agent-env with python and uvicorn under $VENV_BIN"
  exit 1
fi

cd "$ROOT_DIR"

if [[ -f "$WEB_PID_FILE" ]] && kill -0 "$(cat "$WEB_PID_FILE")" 2>/dev/null; then
  echo "Web server already running with PID $(cat "$WEB_PID_FILE")"
  exit 1
fi

if [[ -f "$WORKER_PID_FILE" ]] && kill -0 "$(cat "$WORKER_PID_FILE")" 2>/dev/null; then
  echo "Worker already running with PID $(cat "$WORKER_PID_FILE")"
  exit 1
fi

echo "Starting control panel web server..."
"$VENV_BIN/uvicorn" web_app:app --host 127.0.0.1 --port 8000 >"$WEB_LOG" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" >"$WEB_PID_FILE"

echo "Starting control panel worker..."
"$VENV_BIN/python" control_panel_worker.py >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!
echo "$WORKER_PID" >"$WORKER_PID_FILE"

sleep 2

if ! kill -0 "$WEB_PID" 2>/dev/null; then
  echo "Web server failed to start. See $WEB_LOG"
  exit 1
fi

if ! kill -0 "$WORKER_PID" 2>/dev/null; then
  echo "Worker failed to start. See $WORKER_LOG"
  exit 1
fi

cat <<EOF
Control panel started.

URL: http://127.0.0.1:8000
Web PID: $WEB_PID
Worker PID: $WORKER_PID

Logs:
- $WEB_LOG
- $WORKER_LOG

Stop both services with:
./scripts/stop_local_control_panel.sh
EOF
