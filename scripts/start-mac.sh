#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0
SERVER_SCRIPT="$ROOT_DIR/scripts/start-server.sh"
CHROME_SCRIPT="$ROOT_DIR/scripts/start-chrome-debug.sh"
LOG_DIR="$ROOT_DIR/.logs"
SERVER_LOG="$LOG_DIR/server.log"

while (($# > 0)); do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

file_url() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve().as_uri())
PY
}

server_is_up() {
  curl -fsS "http://127.0.0.1:8765/status" >/dev/null 2>&1
}

INTAKE_URL="$(file_url "$ROOT_DIR/app/intake.html")"
ASSISTANT_URL="$(file_url "$ROOT_DIR/app/ds160-assistant.html")"

if [[ "$DRY_RUN" -eq 1 ]]; then
  bash "$CHROME_SCRIPT" --dry-run
  bash "$SERVER_SCRIPT" --dry-run
  echo 'DRY RUN: open -a "Safari" "'"$INTAKE_URL"'"'
  echo 'DRY RUN: open -a "Safari" "'"$ASSISTANT_URL"'"'
  exit 0
fi

mkdir -p "$LOG_DIR"

bash "$CHROME_SCRIPT"

if server_is_up; then
  echo "FastAPI server is already running on http://127.0.0.1:8765"
else
  nohup bash "$SERVER_SCRIPT" >"$SERVER_LOG" 2>&1 &
  SERVER_PID=$!
  echo "Starting FastAPI server (pid $SERVER_PID), log: $SERVER_LOG"

  for _ in {1..15}; do
    if server_is_up; then
      break
    fi
    sleep 1
  done

  if ! server_is_up; then
    echo "FastAPI server did not become ready. Recent log output:" >&2
    tail -n 20 "$SERVER_LOG" >&2 || true
    exit 1
  fi
fi

open -a Safari "$INTAKE_URL"
open -a Safari "$ASSISTANT_URL"

cat <<EOF
Mac startup complete.

- Safari intake page: $INTAKE_URL
- Safari assistant page: $ASSISTANT_URL
- FastAPI service: http://127.0.0.1:8765
- Chrome remote debugging: http://127.0.0.1:9222/json/version

Note: Safari is used for local intake/assistant pages.
DS-160 autofill still depends on Google Chrome/Chromium because the backend uses Chrome DevTools Protocol.
EOF
