# Incident Response Runbook

## Overview

Standard procedure for responding to IT incidents via the Autonomous IT Control Plane.

## P1/P2 Incidents (Critical/High)

### Automatic Actions (ITSM Resolver Agent)
1. Incident created via `POST /api/v1/incident/resolve`
2. Agent classifies incident (LLM classification)
3. Relevant runbooks retrieved from pgvector store
4. Resolution steps generated (confidence scored)
5. P1: confidence threshold 0.95 — auto-escalate if below
6. P2: confidence threshold 0.90 — auto-escalate if below
7. If confidence sufficient: execute resolution steps, create ticket
8. If confidence insufficient: escalate to incident-manager agent (T2)

### Manual Escalation
When auto-resolution fails, an SQS message is sent to the on-call queue:
- `type: incident.escalated`
- `priority: P1/P2`
- `reason: <confidence/safety reason>`
- `incident_id: <uuid>`

**Response SLA**:
- P1: Acknowledge within 5 minutes
- P2: Acknowledge within 15 minutes

## P3/P4 Incidents (Medium/Low)

Standard auto-resolution path. Confidence threshold 0.85.

## Common Incident Classifications

### database_failure
1. Check connection pool utilization
2. Check for blocking queries: `SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock'`
3. Restart connection pooler if pool exhausted
4. Increase max_connections if persistent
5. Escalate to DBA if root cause unclear

### network_outage
1. Verify DNS resolution from affected hosts
2. Check security group rules for recent changes
3. Test connectivity to gateway
4. Review VPC flow logs for dropped packets
5. Check route tables for missing routes

### application_crash
1. Check application logs for stack trace
2. Check recent deployments (last 2 hours)
3. Verify dependent service availability
4. Roll back last deployment if crash started post-deploy
5. Scale up replicas if OOM-related

### performance_degradation
1. Check CPU/memory utilization on affected nodes
2. Identify top resource consumers
3. Check for slow queries in RDS Performance Insights
4. Check CloudWatch metrics for anomalies
5. Trigger autoscaling if CPU > 85%

## Post-Incident
1. Update incident record with resolution steps taken
2. Create post-incident review ticket (P1 only)
3. Update runbook if new procedure discovered
4. Submit runbook to S3 for RAG ingestion
