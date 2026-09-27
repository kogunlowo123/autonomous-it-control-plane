# Change Rollback Runbook

## Overview

Procedure for rolling back a change that has been executed via the Autonomous IT Control Plane.

## Automatic Rollback (Change Executor Agent)

When a change execution fails:
1. Agent detects failure in post-execution verification
2. Rollback steps are executed (generated during planning phase)
3. Change status updated to `rolled_back`
4. CloudEvent `change.rolledback` emitted to SQS
5. Incident created for root cause analysis

## Manual Rollback

```bash
# Emergency rollback script
./deploy/scripts/rollback_change.sh <change-id>
```

This script:
1. Looks up the change record in the database
2. Retrieves the rollback plan
3. Executes rollback steps in reverse order
4. Updates change status to `rolled_back`
5. Sends notification to on-call

## Rollback Decision Matrix

| Change Status | Can Auto-Rollback | Requires Human | Notes |
|--------------|-------------------|----------------|-------|
| executing | Yes (on failure) | No | Agent handles automatically |
| executed | No | Yes | Manual review required |
| rolled_back | N/A | N/A | Already rolled back |

## Common Rollback Scenarios

### Kubernetes Deployment Rollback
```bash
kubectl rollout undo deployment/<name> -n <namespace>
kubectl rollout status deployment/<name> -n <namespace>
```

### Database Migration Rollback
1. Execute DOWN migration script
2. Verify schema matches previous version
3. Restart affected services

### Configuration Change Rollback
1. Retrieve previous configuration from version control
2. Apply previous configuration
3. Restart affected services
4. Verify health checks pass

## Post-Rollback
1. Update change record with rollback reason
2. Create incident for root cause analysis
3. Review change approval and planning quality
4. Update runbook if rollback procedure improved
