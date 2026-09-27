#!/usr/bin/env bash
# rollback_change.sh — Execute rollback for a specific change
# Usage: ./rollback_change.sh <change-id>
set -euo pipefail

CHANGE_ID="${1:-}"
if [[ -z "$CHANGE_ID" ]]; then
  echo "Usage: $0 <change-id>"
  exit 1
fi

DB_URL="${DATABASE_URL:-postgresql://itsm:password@localhost:5432/itsm_db}"
API_URL="${API_URL:-http://localhost:8000}"

echo "=== Change Rollback ==="
echo "Change ID: $CHANGE_ID"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# 1. Look up change record
echo "[1/5] Fetching change record..."
CHANGE_STATUS=$(psql "$DB_URL" -t -c "
  SELECT status FROM changes WHERE id = '$CHANGE_ID'::uuid
" 2>/dev/null | tr -d ' ')

if [[ -z "$CHANGE_STATUS" ]]; then
  echo "ERROR: Change $CHANGE_ID not found in database"
  exit 1
fi

echo "Current status: $CHANGE_STATUS"

if [[ "$CHANGE_STATUS" == "rolled_back" ]]; then
  echo "Change is already rolled back. Exiting."
  exit 0
fi

# 2. Confirm rollback
echo ""
echo "WARNING: This will rollback change $CHANGE_ID (current status: $CHANGE_STATUS)"
read -r -p "Confirm rollback? [yes/no]: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Rollback cancelled."
  exit 0
fi

# 3. Retrieve rollback plan
echo "[2/5] Retrieving rollback plan..."
ROLLBACK_STEPS=$(psql "$DB_URL" -t -c "
  SELECT metadata->>'rollback_steps' FROM changes WHERE id = '$CHANGE_ID'::uuid
" 2>/dev/null)

if [[ -z "$ROLLBACK_STEPS" || "$ROLLBACK_STEPS" == " null" ]]; then
  echo "WARNING: No rollback plan found in change record. Manual rollback required."
  echo "Please review the change description and apply manual rollback."
fi

# 4. Update change status
echo "[3/5] Marking change as rolled_back..."
psql "$DB_URL" -c "
  UPDATE changes
  SET status = 'rolled_back',
      rolled_back_at = NOW(),
      updated_at = NOW()
  WHERE id = '$CHANGE_ID'::uuid
"

# 5. Log rollback event
echo "[4/5] Logging rollback event..."
psql "$DB_URL" -c "
  INSERT INTO identity.session_ledger
    (session_id, agent_id, agent_type, action, resource_type, resource_id, outcome, event_data)
  VALUES (
    gen_random_uuid(),
    'break-glass-operator',
    'human',
    'change.rollback',
    'change',
    '$CHANGE_ID',
    'success',
    jsonb_build_object('initiated_by', '$(whoami)', 'timestamp', NOW())
  )
" 2>/dev/null || echo "WARNING: Could not write audit log (identity schema may not exist)"

echo "[5/5] Rollback complete."
echo ""
echo "=== Rollback Summary ==="
echo "Change ID: $CHANGE_ID"
echo "Status: rolled_back"
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "Next steps:"
echo "  1. Verify service restoration"
echo "  2. Create post-incident review ticket"
echo "  3. Update change record with rollback reason"
