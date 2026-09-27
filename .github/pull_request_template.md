## Summary

<!-- Describe what this PR does and why -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Infrastructure change (Terraform, Helm, Kubernetes)
- [ ] Documentation update
- [ ] CI/CD change

## Related Issues

<!-- Link related issues: Closes #123 -->

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All existing tests pass (`make test`)
- [ ] Tested locally with `make docker-up`

## Security Checklist

- [ ] No secrets or credentials committed
- [ ] `detect-secrets` pre-commit hook passed
- [ ] No new privileged container usage
- [ ] OPA policy updated if authorization logic changed
- [ ] T2+ changes have approval gate tests

## Agent Changes (if applicable)

- [ ] Agent confidence thresholds tested
- [ ] Escalation paths verified
- [ ] Runbook retrieval accuracy validated
- [ ] LangGraph state transitions documented

## Infrastructure Changes (if applicable)

- [ ] `terraform plan` output reviewed
- [ ] No unintended resource deletions
- [ ] IAM permissions follow least-privilege
- [ ] KMS encryption maintained
