# ADR 0001: Mandatory Human Approval Gate for T2 Changes

**Date**: 2024-01-01
**Status**: Accepted
**Deciders**: kogunlowo123

## Context

The autonomous IT control plane executes changes against production infrastructure.
Fully autonomous execution of all changes creates unacceptable operational risk:
- A misconfigured agent could cause widespread outages
- Prompt injection attacks could manipulate agents into destructive actions
- Compliance frameworks (SOC 2, ISO 27001) require change approval evidence

We need to decide: which changes require human approval, and how should that gate be enforced?

## Decision

We adopt a three-tier change classification:

| Tier | Description | Approval Required | Timeout |
|------|-------------|-------------------|---------|
| T1 | Low-risk, automated, reversible | None | N/A |
| T2 | Standard changes, moderate risk | Human (at least 1 approver) | 30 minutes |
| T3 | Emergency changes | Expedited human approval | 15 minutes |

**T2 and T3 changes are hard-blocked from execution until a human explicitly approves them.**

The approval gate is enforced at three layers:
1. **OPA policy** (`it_control.rego`): Evaluates approval status at execution time
2. **Application layer** (`approvals.py`): Enforces timeout-based auto-denial
3. **Database constraints**: Change records cannot transition from `pending_approval` to `executing` without `approved_at` timestamp

## Consequences

**Positive**:
- Clear audit trail of who approved what and when
- Compliance-ready change management
- Protection against prompt injection and runbook abuse
- Operational confidence in autonomous execution

**Negative**:
- Human latency in the change pipeline (up to 30 minutes for T2)
- Expired approvals cause change delays and require resubmission
- Additional operational overhead for approver on-call rotation

**Mitigations**:
- T1 tier for low-risk automated changes eliminates approval overhead for routine tasks
- T3 tier provides expedited 15-minute window for emergencies
- SQS notifications to mobile devices ensure approvers can respond quickly
