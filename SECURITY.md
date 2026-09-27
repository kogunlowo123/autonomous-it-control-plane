# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Report security vulnerabilities by emailing: **security@example.com**

Include in your report:
- Type of vulnerability (e.g., SQL injection, authentication bypass, privilege escalation)
- Affected component (API service, agent runtime, infrastructure)
- Steps to reproduce
- Potential impact assessment
- Any proof-of-concept code (if available)

### Response SLA

- **Acknowledgment**: Within 48 hours of receipt
- **Initial assessment**: Within 5 business days
- **Resolution timeline**: Depends on severity
  - Critical (CVSS 9.0+): 7 days
  - High (CVSS 7.0-8.9): 14 days
  - Medium (CVSS 4.0-6.9): 30 days
  - Low (CVSS < 4.0): 90 days

## Security Controls

This platform implements the following security controls:

### Authentication & Authorization
- JWT RS256 token validation on all API endpoints
- OPA (Open Policy Agent) for fine-grained authorization
- IRSA (IAM Roles for Service Accounts) — no long-lived AWS credentials

### Change Management
- Mandatory human approval gates for T2/T3 changes
- Approval timeout enforcement (T2: 30 min, T3: 15 min)
- Immutable audit trail of all change decisions

### Infrastructure Security
- Kyverno policies: signed container images required
- No privileged containers
- Secrets managed via AWS Secrets Manager + External Secrets Operator
- KMS encryption at rest for all data stores
- Network segmentation via VPC and security groups

### Detection
- Sigma rules for unauthorized change detection
- CloudWatch anomaly detection for unusual STS assume-role activity
- OpenTelemetry tracing for all agent operations

### Agent Safety
- Input screening for prompt injection
- Output grounding checks against source documents
- Citation validation
- Confidence thresholds enforced before autonomous action
