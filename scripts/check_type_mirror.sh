#!/usr/bin/env bash
# Verifies that TypeScript API types stay in sync with the Python backend.
# When frontend/src/types/ does not yet exist the check is a no-op.
set -euo pipefail

TYPES_DIR="frontend/src/types"

if [[ ! -d "$TYPES_DIR" ]]; then
  echo "check_type_mirror: $TYPES_DIR not found — skipping."
  exit 0
fi

if [[ ! -f "scripts/generate_types.py" ]]; then
  echo "check_type_mirror: scripts/generate_types.py not found — skipping."
  exit 0
fi

GENERATED=$(python scripts/generate_types.py)
COMMITTED=$(cat "${TYPES_DIR}/api.ts")

if [[ "$GENERATED" != "$COMMITTED" ]]; then
  echo "ERROR: TypeScript types are out of sync with Python models."
  echo "Run: python scripts/generate_types.py > ${TYPES_DIR}/api.ts"
  diff <(echo "$COMMITTED") <(echo "$GENERATED") || true
  exit 1
fi

echo "check_type_mirror: types are in sync."
