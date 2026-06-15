#!/usr/bin/env bash
# check_type_mirror.sh
#
# Compares OrderStatus and RestaurantUserRole string values between
# shared/contracts.py and every frontend/*/src/types.ts file.
# Exits non-zero when drift is detected.
#
# Assumptions for TypeScript files:
#   Each type is a single-line union: export type Foo = "a" | "b";

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS="$REPO_ROOT/shared/contracts.py"

if [[ ! -f "$CONTRACTS" ]]; then
  echo "ERROR: $CONTRACTS not found" >&2
  exit 1
fi

shopt -s nullglob
TS_FILES=("$REPO_ROOT"/frontend/*/src/types.ts)
if [[ ${#TS_FILES[@]} -eq 0 ]]; then
  echo "ERROR: no frontend/*/src/types.ts files found under $REPO_ROOT/frontend/" >&2
  exit 1
fi

errors=0

# Extract sorted string values for an enum from shared/contracts.py
py_enum_values() {
  local enum_name="$1"
  python3 - <<PYEOF
import importlib.util, sys
spec = importlib.util.spec_from_file_location("contracts", "$CONTRACTS")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cls = getattr(mod, "$enum_name", None)
if cls is None:
    print("ERROR: $enum_name not found in contracts.py", file=sys.stderr)
    sys.exit(1)
for m in sorted(cls, key=lambda x: x.value):
    print(m.value)
PYEOF
}

# Extract sorted string values for a union type from a TypeScript file.
# Expects: export type Foo = "a" | "b" | "c";
# Outputs nothing (empty) when the type is absent, which the caller treats as drift.
ts_type_values() {
  local ts_file="$1"
  local type_name="$2"
  local line
  line=$(grep -E "^export type ${type_name}[[:space:]]*=" "$ts_file" || true)
  if [[ -z "$line" ]]; then
    echo "ERROR: $type_name not found in $ts_file" >&2
    return 0
  fi
  echo "$line" | grep -oE '"[^"]+"' | tr -d '"' | sort
}

check_enum() {
  local enum_name="$1"
  local py_vals
  py_vals=$(py_enum_values "$enum_name")

  for ts_file in "${TS_FILES[@]}"; do
    local ts_vals
    ts_vals=$(ts_type_values "$ts_file" "$enum_name")

    if [[ "$py_vals" != "$ts_vals" ]]; then
      echo "DRIFT: $enum_name" >&2
      echo "  Python ($CONTRACTS):" >&2
      echo "$py_vals" | sed 's/^/    /' >&2
      echo "  TypeScript ($(realpath --relative-to="$REPO_ROOT" "$ts_file")):" >&2
      echo "$ts_vals" | sed 's/^/    /' >&2
      errors=$((errors + 1))
    else
      local rel_ts
      rel_ts=$(realpath --relative-to="$REPO_ROOT" "$ts_file")
      echo "OK: $enum_name matches in $rel_ts"
    fi
  done
}

check_enum "OrderStatus"
check_enum "RestaurantUserRole"

if [[ $errors -gt 0 ]]; then
  echo "" >&2
  echo "check_type_mirror: $errors drift(s) detected — fix before merging" >&2
  exit 1
fi

echo "check_type_mirror: all types in sync"
