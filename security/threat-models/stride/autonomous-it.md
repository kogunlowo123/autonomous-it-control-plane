# STRIDE Threat Model — Autonomous IT Control Plane

## Scope

This document covers the threat surface of the autonomous IT control plane, including:
- LangGraph agent orchestration
- FastAPI REST endpoints
- Aurora pgvector knowledge base
- SQS approval queues
- OPA authorization policy engine
- AWS Bedrock LLM inference

---

## Trust Boundaries

1. **Internet → API Gateway**: Public internet to internal API
2. **API → Agent Runtime**: Authenticated internal service call
3. **Agent Runtime → Bedrock**: AWS service boundary (IRSA)
4. **Agent Runtime → Aurora**: Private VPC boundary
5. **Agent Runtime → SQS**: AWS service boundary (IRSA)
6. **Human Approver → SQS**: External approval channel

---

## STRIDE Analysis

### Spoofing

| Threat | Asset | Mitigation |
|--------|-------|------------|
| Forged JWT tokens | API authentication | RS256 signed JWTs, token revocation list |
| Agent impersonation | Agent identity | Agent-specific JWT with tier claim, OPA policy |
| SQS message spoofing | Approval events | KMS message signing on SQS FIFO |

### Tampering

| Threat | Asset | Mitigation |
|--------|-------|------------|
| Runbook content modification | pgvector store | Document checksums, immutable S3 versioning |
| Approval status manipulation | PostgreSQL approvals table | Row-level locking, status transition validation |
| LLM prompt injection | Agent inputs | Input screening guardrail, blocked pattern list |
| Change plan modification in-flight | SQS messages | KMS encryption + HMAC integrity |

### Repudiation

| Threat | Asset | Mitigation |
|--------|-------|------------|
| Deny executing a change | Change workflow | Append-only session ledger with CloudEvents |
| Deny approving a change | Approval workflow | Immutable approval audit trail with timestamp |

### Information Disclosure

| Threat | Asset | Mitigation |
|--------|-------|------------|
| PII leakage in LLM context | Runbook content | PII tagger + redaction before embedding |
| Secrets in telemetry | OTEL traces | PII scrub processor on OTEL collector |
| Database connection string exposure | Environment | AWS Secrets Manager + External Secrets rotation |
| LLM prompt/completion logging | Bedrock | No prompt logging enabled, trace sanitization |

### Denial of Service

| Threat | Asset | Mitigation |
|--------|-------|------------|
| API flood | FastAPI endpoints | Rate limiting middleware (per-IP sliding window) |
| SQS queue exhaustion | Incident queue | DLQ + message visibility timeout |
| LLM budget exhaustion | Bedrock inference | AgentBudget token + cost limits per session |
| pgvector index degradation | Aurora | Connection pooling, query timeouts |

### Elevation of Privilege

| Threat | Asset | Mitigation |
|--------|-------|------------|
| T1 agent executing T2 change | Agent runtime | OPA policy: tier enforcement at execution time |
| Bypassing approval gate | Change workflow | Database status lock, OPA `can_execute_change` check |
| IRSA role confusion | EKS pods | Kyverno policy: restrict IAM role annotations |
| Jailbreak via prompt injection | LLM | Input screening blocks `ignore previous instructions` |

---

## High-Risk Flows

### Flow 1: Incident Auto-Resolution (P1)

```
SQS → classify_incident → retrieve_runbook → generate_resolution
    → validate_steps (confidence ≥ 0.95 required for P1)
    → create_ticket
```

**Key controls**: P1 confidence threshold 0.95, dangerous keyword blocking, session ledger

### Flow 2: T2 Change Execution

```
API /change/submit → DB insert (status=pending_approval)
    → SQS notification → human approval
    → check_approval_status (APPROVED + not expired + no freeze)
    → OPA can_execute_change
    → execute_change
```

**Key controls**: 1800s approval timeout, OPA enforcement, freeze window check

---

## Residual Risks

| Risk | Likelihood | Impact | Accepted By |
|------|-----------|--------|------------|
| Advanced prompt injection bypassing screen | Low | High | Engineering — quarterly red team review |
| Aurora credentials leak via misconfigured pod | Very Low | Critical | Platform — Kyverno non-root enforcement |
| LLM hallucinated rollback steps executed | Low | High | Engineering — dry_run=True default |
