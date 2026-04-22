#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=0

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

resolve_python_bin() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  echo "Python not found. Install python3 or create .venv first." >&2
  exit 1
}

PYTHON_BIN="$(resolve_python_bin)"
COMMAND=(env "PYTHONPATH=$ROOT_DIR/src" "$PYTHON_BIN" -m visa_agent.server)

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN: scripts/start-server.sh"
  printf 'env PYTHONPATH="%s/src" "%s" -m visa_agent.server\n' "$ROOT_DIR" "$PYTHON_BIN"
  exit 0
fi

cd "$ROOT_DIR"
exec "${COMMAND[@]}"
