#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.cursor/workspaces/gdocs-runtime"
VENV_DIR="$RUNTIME_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$RUNTIME_DIR"

MARKDOWN_FILE=""
for ((i=1; i<=$#; i++)); do
  if [[ "${!i}" == "--markdown-file" ]]; then
    j=$((i+1))
    if [[ $j -le $# ]]; then
      MARKDOWN_FILE="${!j}"
    fi
    break
  fi
done

# Prevent persistent local markdown artifacts in the project workspace.
if [[ -n "$MARKDOWN_FILE" ]]; then
  ABS_MARKDOWN_FILE="$(python3 - <<'PY' "$MARKDOWN_FILE"
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
)"
  if [[ "$ABS_MARKDOWN_FILE" == "$ROOT_DIR/"* ]] && [[ "${ALLOW_PROJECT_MARKDOWN_FILE:-0}" != "1" ]]; then
    echo "ERROR: --markdown-file points inside project workspace: $ABS_MARKDOWN_FILE" >&2
    echo "Use stdin or /tmp markdown path. Set ALLOW_PROJECT_MARKDOWN_FILE=1 only if explicitly requested by user." >&2
    exit 2
  fi
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade \
  google-auth \
  google-auth-oauthlib \
  google-api-python-client \
  cryptography

exec "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/publish_test_plan_to_gdocs.py" "$@"
