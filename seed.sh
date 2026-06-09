#!/usr/bin/env bash
set -euo pipefail

API="http://localhost:8000/api/v1"

echo "=== ClauseGuard Seed Script ==="
echo ""

echo "Checking backend health..."
STATUS=$(curl -s "$API/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [ "$STATUS" != "healthy" ]; then
  echo "ERROR: Backend is not healthy (status=$STATUS). Start it first."
  exit 1
fi
echo "Backend is healthy."
echo ""

for f in sample_contracts/*.txt; do
  FILENAME=$(basename "$f")
  echo "--- Uploading: $FILENAME ---"
  RESPONSE=$(curl -s --max-time 300 -X POST "$API/contracts/upload" -F "file=@$f")
  if echo "$RESPONSE" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    NUM_CLAUSES=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['num_clauses'])")
    TYPES=$(echo "$RESPONSE" | python3 -c "import sys,json; print(', '.join(json.load(sys.stdin)['clause_types_found']))")
    echo "  Clauses: $NUM_CLAUSES | Types: $TYPES"
  else
    echo "  ERROR: $RESPONSE"
  fi
  echo ""
done

echo "=== Seed complete ==="
echo ""

echo "Contracts in system:"
curl -s "$API/contracts/" | python3 -c "
import sys, json
contracts = json.load(sys.stdin)
for c in contracts:
    print(f\"  {c['filename']:45s} {c['num_clauses']:3d} clauses  [{', '.join(c['clause_types_found'])}]\")
print(f\"\nTotal: {len(contracts)} contracts, {sum(c['num_clauses'] for c in contracts)} clauses\")
"
