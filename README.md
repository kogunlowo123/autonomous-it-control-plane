# Autonomous IT Control Plane

[![CI](https://github.com/kogunlowo123/autonomous-it-control-plane/actions/workflows/ci.yml/badge.svg)](https://github.com/kogunlowo123/autonomous-it-control-plane/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Terraform](https://img.shields.io/badge/Terraform-1.8+-purple.svg)](https://terraform.io)

Enterprise AI platform for **autonomous IT operations** — AI agents that autonomously resolve IT incidents, manage changes, and operate ITSM workflows with proper approval gates.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Autonomous IT Control Plane                    │
│                                                                    │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ ITSM        │  │ Change           │  │ Incident             │ │
│  │ Resolver    │  │ Executor         │  │ Manager              │ │
│  │ Agent (T1)  │  │ Agent (T2)       │  │ Agent (T1/T2)        │ │
│  └──────┬──────┘  └────────┬─────────┘  └──────────┬───────────┘ │
│         │                  │                         │            │
│  ┌──────▼──────────────────▼─────────────────────────▼──────────┐│
│  │              LangGraph Orchestration Engine                    ││
│  │         (classify → retrieve → generate → validate)           ││
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │              RAG Core (Runbooks + Knowledge Base)            │ │
│  │   pgvector (Aurora) + OpenSearch  +  LiteLLM (Bedrock)      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐         ┌─────▼─────┐        ┌────▼────┐
    │  AWS    │         │  AWS SQS  │        │  OPA    │
    │ Bedrock │         │ (Approvals│        │ Policy  │
    │   LLM   │         │  + Events)│        │ Engine  │
    └─────────┘         └───────────┘        └─────────┘
```

## Features

- **Autonomous Incident Resolution**: T1 agent resolves L1/L2 incidents using runbook RAG with confidence gating
- **Change Management**: T2 change executor with mandatory human approval gates, rollback capabilities
- **Incident Management**: P1/P2 incident coordination with automatic escalation
- **Approval Workflow**: Real human-in-the-loop for T2+ changes via SQS + timeout enforcement
- **RAG over IT Knowledge**: Semantic search over runbooks, ServiceNow docs, change policies
- **CloudEvents**: Structured event emission for `change.submitted`, `incident.resolved`, `change.rolledback`
- **AWS-Native**: Bedrock LLM, Aurora pgvector, SQS, S3, EKS, KMS, IRSA

## Agent Families

| Agent | Tier | Responsibilities |
|-------|------|-----------------|
| `itsm-resolver` | T1 | Resolves L1/L2 incidents from runbook knowledge, creates ITSM tickets |
| `change-executor` | T2 | Executes approved changes, requires human approval, tracks rollback |
| `incident-manager` | T1/T2 | Manages P1/P2 incidents, escalates, coordinates response |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/change/submit` | Submit change request, trigger approval workflow |
| GET | `/api/v1/change/{id}/status` | Get change status (pending/approved/executed/rolled_back) |
| POST | `/api/v1/incident/resolve` | Attempt autonomous incident resolution |
| GET | `/api/v1/incident/{id}` | Get incident record |
| GET | `/api/v1/health` | Liveness probe |
| GET | `/api/v1/readiness` | Readiness probe with dependency checks |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/kogunlowo123/autonomous-it-control-plane.git
cd autonomous-it-control-plane

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials and settings

# Start all services
make docker-up

# Check health
curl http://localhost:8000/api/v1/health

# Submit a change request
curl -X POST http://localhost:8000/api/v1/change/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title":"Update nginx config","description":"Update SSL cert","tier":"T2","requestor":"ops@company.com"}'

# Resolve an incident
curl -X POST http://localhost:8000/api/v1/incident/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title":"Database connection pool exhausted","description":"PG max_connections hit","priority":"P2","affected_service":"user-api","requestor":"sre@company.com"}'
```

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker & Docker Compose
- Terraform 1.8+
- AWS CLI configured

### Install Dependencies

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
make install

# Install pre-commit hooks
make pre-commit-install
```

### Running Tests

```bash
# All tests
make test

# Unit tests only (no infrastructure required)
make test-unit

# Integration tests (requires docker-up)
make test-integration

# Security tests
make test-security
```

### Code Quality

```bash
# Lint and format
make lint
make format

# Type checking
make typecheck
```

## Infrastructure

Built on AWS with Terraform:

- **EKS**: Kubernetes cluster for service deployment
- **Aurora PostgreSQL + pgvector**: Vector store for RAG embeddings
- **OpenSearch**: Full-text search over runbooks
- **SQS FIFO**: Approval queues and CloudEvent emission
- **Bedrock**: LLM inference (Claude 3 Sonnet)
- **KMS**: Encryption at rest and in transit
- **S3**: Runbook storage
- **IRSA**: Service account IAM roles (no long-lived credentials)

```bash
# Initialize and deploy dev environment
make tf-init
make tf-plan
make tf-apply
```

## Deployment

### Helm + ArgoCD

```bash
# Deploy via ArgoCD app-of-apps
kubectl apply -f deploy/argocd/app-of-apps.yaml

# Or deploy individual services
helm upgrade --install autonomous-it-api deploy/helm/api/ \
  --namespace itsm-system \
  --values deploy/helm/api/values.yaml
```

### Emergency Rollback

```bash
# Break glass procedure
./deploy/scripts/break_glass.sh

# Rollback a specific change
./deploy/scripts/rollback_change.sh <change-id>
```

## Security

- OPA policy enforcement for all change operations
- JWT authentication with RS256 signing
- Kyverno policies: signed images, no privileged containers
- Sigma detection rules for unauthorized changes
- Secrets managed via AWS Secrets Manager + External Secrets Operator
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
