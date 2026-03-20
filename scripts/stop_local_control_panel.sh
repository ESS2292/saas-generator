#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_PID_FILE="$ROOT_DIR/.control-panel-web.pid"
WORKER_PID_FILE="$ROOT_DIR/.control-panel-worker.pid"

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "$label is not running."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped $label (PID $pid)."
  else
    echo "$label PID file existed, but process $pid was not running."
  fi
  rm -f "$pid_file"
}

stop_pid_file "$WEB_PID_FILE" "web server"
stop_pid_file "$WORKER_PID_FILE" "worker"
