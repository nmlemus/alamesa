#!/usr/bin/env bash
# demo.sh — Mesa Digital end-to-end local demo
#
# Prerequisites:
#   1. python scripts/seed.py        # populate demo data
#   2. mesadigital-api               # start the API server (default :8000)
#
# Usage:
#   BASE_URL=http://localhost:8000 bash scripts/demo.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

# ── Helpers ──────────────────────────────────────────────────────────────────

say() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  printf "║  %-60s║\n" "$*"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
}

json_field() {
  python3 -c "import sys, json; print(json.load(sys.stdin)$1)"
}

# ── Health check ─────────────────────────────────────────────────────────────

say "Checking server health at $BASE_URL"
if ! curl -sf "$BASE_URL/health" > /dev/null; then
  echo "ERROR: server is not running at $BASE_URL" >&2
  echo "       Start it with: mesadigital-api" >&2
  exit 1
fi
echo "Server is up."

# ── Step 1: Register a diner ─────────────────────────────────────────────────

say "Step 1 — Register a new diner (customer)"
echo "POST $BASE_URL/api/diners/register"

# Use a timestamp-based phone so each demo run creates a fresh diner.
DEMO_PHONE="+34600$(date +%s | tail -c 7)"
REGISTER_JSON=$(curl -sf -X POST "$BASE_URL/api/diners/register" \
  -H "Content-Type: application/json" \
  -d "{\"restaurant_slug\":\"demo\",\"phone\":\"$DEMO_PHONE\",\"name\":\"Ana García\",\"password\":\"secret123\"}")
DINER_ID=$(echo "$REGISTER_JSON" | json_field "['id']")
echo "Registered diner id=$DINER_ID (phone=$DEMO_PHONE)"

# ── Step 2: Browse the menu ───────────────────────────────────────────────────

say "Step 2 — Browse the restaurant menu"
echo "GET $BASE_URL/api/restaurants/demo/menu"
MENU_JSON=$(curl -sf "$BASE_URL/api/restaurants/demo/menu")
echo "$MENU_JSON" | python3 -m json.tool

TABLE_ID=$(echo "$MENU_JSON" | json_field "['tables'][0]['id']")
ITEM1_ID=$(echo "$MENU_JSON" | json_field "['categories'][0]['items'][0]['id']")
ITEM2_ID=$(echo "$MENU_JSON" | json_field "['categories'][1]['items'][0]['id']")
echo ""
echo "Picked table_id=$TABLE_ID, item_ids=[$ITEM1_ID, $ITEM2_ID]"

# ── Step 3: Place an order ────────────────────────────────────────────────────

say "Step 3 — Place an order (status: pending)"
echo "POST $BASE_URL/api/orders"
ORDER_JSON=$(curl -sf -X POST "$BASE_URL/api/orders" \
  -H "Content-Type: application/json" \
  -d "{
    \"restaurant_slug\": \"demo\",
    \"table_id\": \"$TABLE_ID\",
    \"diner_id\": \"$DINER_ID\",
    \"items\": [
      {\"menu_item_id\": \"$ITEM1_ID\", \"quantity\": 2},
      {\"menu_item_id\": \"$ITEM2_ID\", \"quantity\": 1}
    ]
  }")
echo "$ORDER_JSON" | python3 -m json.tool
ORDER_ID=$(echo "$ORDER_JSON" | json_field "['id']")
echo ""
echo "Order id=$ORDER_ID created with status=pending"

# ── Step 4: Staff confirms the order ─────────────────────────────────────────

say "Step 4 — Staff confirms the order (pending → confirmed)"
echo "PATCH $BASE_URL/api/orders/$ORDER_ID/status"
curl -sf -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed"}' | python3 -m json.tool

# ── Step 5: Kitchen starts preparing ─────────────────────────────────────────

say "Step 5 — Kitchen starts preparing (confirmed → preparing)"
echo "PATCH $BASE_URL/api/orders/$ORDER_ID/status"
curl -sf -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"preparing"}' | python3 -m json.tool

# ── Step 6: Kitchen marks order ready ────────────────────────────────────────

say "Step 6 — Kitchen marks the order ready (preparing → ready)"
echo "PATCH $BASE_URL/api/orders/$ORDER_ID/status"
curl -sf -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"ready"}' | python3 -m json.tool

# ── Step 7: Close the order ───────────────────────────────────────────────────

say "Step 7 — Close the order after delivery (ready → closed)"
echo "PATCH $BASE_URL/api/orders/$ORDER_ID/status"
curl -sf -X PATCH "$BASE_URL/api/orders/$ORDER_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"closed"}' | python3 -m json.tool

# ── Summary ───────────────────────────────────────────────────────────────────

say "Demo complete"
echo "Full lifecycle for order $ORDER_ID:"
echo "  pending → confirmed → preparing → ready → closed"
echo ""
