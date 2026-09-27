#!/usr/bin/env bash
# break_glass.sh — Emergency access to production systems
# Usage: ./break_glass.sh <reason>
# This procedure creates an audited break-glass session with time-limited access.
set -euo pipefail

REASON="${1:-}"
if [[ -z "$REASON" ]]; then
  echo "Usage: $0 <reason>"
  echo "Example: $0 'Production P1 incident - database cluster unresponsive'"
  exit 1
fi

DB_URL="${DATABASE_URL:-postgresql://itsm:password@localhost:5432/itsm_db}"
OPERATOR="${OPERATOR:-$(whoami)}"
EXPIRY_MINUTES="${EXPIRY_MINUTES:-60}"

SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "=== BREAK GLASS PROCEDURE ==="
echo "Session ID: $SESSION_ID"
echo "Operator:   $OPERATOR"
echo "Reason:     $REASON"
echo "Expiry:     ${EXPIRY_MINUTES} minutes"
echo "Timestamp:  $TIMESTAMP"
echo ""
echo "WARNING: This session is fully audited and will be reviewed."
echo ""
read -r -p "Confirm break-glass procedure? [yes/no]: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Break-glass cancelled."
  exit 0
fi

# Record in audit ledger
psql "$DB_URL" -c "
  INSERT INTO identity.session_ledger
    (session_id, agent_id, agent_type, action, resource_type, resource_id, outcome, event_data)
  VALUES (
    '$SESSION_ID',
    '$OPERATOR',
    'human',
    'break_glass.initiated',
    'system',
    'production',
    'in_progress',
    jsonb_build_object(
      'reason', '$REASON',
      'operator', '$OPERATOR',
      'expiry_minutes', $EXPIRY_MINUTES,
      'initiated_at', '$TIMESTAMP'
    )
  )
" 2>/dev/null || echo "WARNING: Could not write audit log"

# Generate time-limited credentials (in production: call IAM STS assume-role)
echo ""
echo "=== Break-Glass Session Active ==="
echo "Session: $SESSION_ID"
echo "Valid for: ${EXPIRY_MINUTES} minutes from $TIMESTAMP"
echo ""
echo "IMPORTANT:"
echo "  1. Document ALL actions taken during this session"
echo "  2. Close session with: break_glass_close.sh $SESSION_ID"
echo "  3. Session auto-expires at: $(date -u -d "+${EXPIRY_MINUTES} minutes" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "Session token: BG-$SESSION_ID"

export BREAK_GLASS_SESSION="$SESSION_ID"
export BREAK_GLASS_EXPIRY="$EXPIRY_MINUTES"
