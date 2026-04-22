#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0
REMOTE_DEBUGGING_PORT=9222
CEAC_URL="https://ceac.state.gov/genniv/"
PROFILE_DIR="$ROOT_DIR/.visible-browser-profile"

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

resolve_chrome_bin() {
  local candidate
  for candidate in google-chrome google-chrome-stable chromium-browser chromium; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return
    fi
  done
  echo "Google Chrome/Chromium not found in PATH. Install Chrome for DS-160 autofill." >&2
  exit 1
}

CHROME_BIN="google-chrome"
if [[ "$DRY_RUN" -ne 1 ]]; then
  CHROME_BIN="$(resolve_chrome_bin)"
fi

mkdir -p "$PROFILE_DIR"

COMMAND=(
  "$CHROME_BIN"
  "--remote-debugging-port=$REMOTE_DEBUGGING_PORT"
  "--user-data-dir=$PROFILE_DIR"
  --no-first-run
  --disable-extensions
  "$CEAC_URL"
)

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN: scripts/start-chrome-debug-ubuntu.sh"
  printf '"%s" --remote-debugging-port=%s --user-data-dir="%s" --no-first-run --disable-extensions "%s"\n' \
    "$CHROME_BIN" \
    "$REMOTE_DEBUGGING_PORT" \
    "$PROFILE_DIR" \
    "$CEAC_URL"
  exit 0
fi

"${COMMAND[@]}" >/dev/null 2>&1 &
disown || true
echo "Chrome debug window launched on port ${REMOTE_DEBUGGING_PORT}."
