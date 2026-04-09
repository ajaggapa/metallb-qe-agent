#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/validate_and_publish_detailed_test_plan.sh \"<Google Docs title>\"" >&2
  echo "Reads markdown content from stdin, validates detailed plan structure, then publishes." >&2
  exit 2
fi

TITLE="$1"
TMP_MD="$(mktemp /tmp/metallb-detailed-test-plan-XXXXXX.md)"
trap 'rm -f "$TMP_MD"' EXIT

cat > "$TMP_MD"

python3 "$ROOT_DIR/scripts/validate_detailed_test_plan.py" "$TMP_MD"
"$ROOT_DIR/scripts/run_gdocs_publisher.sh" --title "$TITLE" --markdown-file "$TMP_MD"
