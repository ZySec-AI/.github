#!/usr/bin/env bash
# Validate all GitHub Actions workflow YAML files parse correctly.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0

while IFS= read -r -d '' file; do
  if python3 - "$file" <<'PY'
import sys, yaml
path = sys.argv[1]
try:
    with open(path) as f:
        yaml.safe_load(f)
except Exception as e:
    print(f"FAIL {path}: {e}", file=sys.stderr)
    sys.exit(1)
PY
  then
    echo "OK $file"
  else
    FAIL=1
  fi
done < <(find "$ROOT/.github/workflows" "$ROOT/workflow-templates" -name '*.yml' -print0)

if [ "$FAIL" -ne 0 ]; then
  echo "Workflow YAML validation failed." >&2
  exit 1
fi

echo "All workflow YAML files are valid."
