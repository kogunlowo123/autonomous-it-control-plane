package it_control

import future.keywords.if
import future.keywords.in

# =============================================================================
# Default deny — all operations denied unless explicitly allowed
# =============================================================================

default allow := false
default can_execute_change := false
default can_resolve_incident := false

# =============================================================================
# Change execution policy
#
# A change execution is allowed when ALL of the following are true:
#   1. The JWT token tier is T2 or T3 (T1 tokens cannot execute T2/T3 changes)
#   2. A valid approval exists for this change
#   3. The approval has not expired
#   4. No change freeze is currently active
# =============================================================================

can_execute_change if {
    # Input must include change_id, tier, approval
    input.change_id
    input.tier
    input.approval_status

    # T1 changes can always execute (no approval required)
    input.tier == "T1"
    not input.change_freeze_active
}

can_execute_change if {
    # T2 and T3 require approval
    input.change_id
    input.tier
    input.approval_status

    input.tier in {"T2", "T3"}
    input.approval_status == "approved"
    not approval_expired
    not input.change_freeze_active
}

# An approval is expired when the current time exceeds its expiry
approval_expired if {
    input.approval_expires_at_unix
    input.current_time_unix
    input.current_time_unix > input.approval_expires_at_unix
}

# =============================================================================
# Incident resolution policy
#
# T1 agents can always attempt incident resolution.
# T2 agents require an explicit escalation authorization.
# =============================================================================

can_resolve_incident if {
    input.agent_tier == "T1"
    input.incident_id
}

can_resolve_incident if {
    input.agent_tier == "T2"
    input.incident_id
    input.escalation_authorized == true
}

# =============================================================================
# General allow — used for API authorization checks
# =============================================================================

allow if {
    can_execute_change
}

allow if {
    can_resolve_incident
}

# Allow health and readiness checks unconditionally
allow if {
    input.action == "health_check"
}

# =============================================================================
# Audit log — every decision is annotated
# =============================================================================

audit := {
    "allowed": allow,
    "change_execution_allowed": can_execute_change,
    "incident_resolution_allowed": can_resolve_incident,
    "tier": object.get(input, "tier", "unknown"),
    "change_id": object.get(input, "change_id", ""),
    "approval_status": object.get(input, "approval_status", ""),
    "approval_expired": approval_expired,
    "change_freeze": object.get(input, "change_freeze_active", false),
}
