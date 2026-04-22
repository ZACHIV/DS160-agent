#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0
REMOTE_DEBUGGING_PORT=9222
CEAC_URL="https://ceac.state.gov/genniv/"
CHROME_APP_NAME="Google Chrome"
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

resolve_chrome_app() {
  local candidate
  for candidate in "Google Chrome" "Google Chrome Canary" "Chromium"; do
    if [[ -d "/Applications/${candidate}.app" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  echo "Google Chrome/Chromium not found in /Applications. Install Chrome for DS-160 autofill." >&2
  exit 1
}

if [[ "$DRY_RUN" -ne 1 ]]; then
  CHROME_APP_NAME="$(resolve_chrome_app)"
fi

mkdir -p "$PROFILE_DIR"

COMMAND=(
  open
  -na
  "$CHROME_APP_NAME"
  --args
  "--remote-debugging-port=$REMOTE_DEBUGGING_PORT"
  "--user-data-dir=$PROFILE_DIR"
  --no-first-run
  --disable-extensions
  "$CEAC_URL"
)

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN: scripts/start-chrome-debug.sh"
  printf 'open -na "%s" --args --remote-debugging-port=%s --user-data-dir="%s" --no-first-run --disable-extensions "%s"\n' \
    "$CHROME_APP_NAME" \
    "$REMOTE_DEBUGGING_PORT" \
    "$PROFILE_DIR" \
    "$CEAC_URL"
  exit 0
fi

"${COMMAND[@]}"
echo "Chrome debug window launched on port ${REMOTE_DEBUGGING_PORT}."
