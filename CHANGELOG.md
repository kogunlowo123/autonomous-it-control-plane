# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-01

### Added

- **ITSM Resolver Agent (T1)**: LangGraph-based agent for autonomous L1/L2 incident resolution
  - Incident classification via LLM (AWS Bedrock)
  - Runbook retrieval via pgvector semantic search
  - Resolution step generation with confidence scoring
  - Automatic escalation when confidence < 0.85 or P1 incidents
  - ITSM ticket creation on resolution

- **Change Executor Agent (T2)**: Approval-gated change execution
  - Mandatory human approval workflow for T2/T3 changes
  - Approval timeout enforcement (T2: 30 min, T3: 15 min)
  - Rollback plan generation
  - CloudEvent emission: `change.submitted`, `change.approved`, `change.executed`

- **Incident Manager Agent (T1/T2)**: P1/P2 incident coordination
  - Automatic P1 escalation
  - SQS-based stakeholder notification
  - Incident lifecycle management

- **FastAPI Service**: Production REST API
  - `POST /api/v1/change/submit`: Submit change requests
  - `GET /api/v1/change/{id}/status`: Query change status
  - `POST /api/v1/incident/resolve`: Autonomous incident resolution
  - `GET /api/v1/incident/{id}`: Retrieve incident records
  - JWT RS256 authentication middleware
  - OPA authorization integration
  - Rate limiting and tenant isolation
  - OpenTelemetry distributed tracing

- **RAG Core Service**: Knowledge retrieval infrastructure
  - PDF and HTML document loaders
  - Recursive, semantic, and structural chunking strategies
  - AWS Bedrock Titan embeddings
  - pgvector and OpenSearch dual-store support
  - Hybrid retrieval with Reciprocal Rank Fusion (RRF)
  - Corrective RAG with query rewriting

- **Identity & Authorization**:
  - OPA policy: `it_control.rego` — change execution requires T2+ token + valid approval
  - Agent credential broker with TTL policies
  - Session audit ledger schema

- **Infrastructure (Terraform)**:
  - EKS cluster with IRSA
  - Aurora PostgreSQL + pgvector extension
  - OpenSearch domain
  - SQS FIFO queues for approvals and events
  - KMS keys for data encryption
  - S3 buckets for runbook storage
  - VPC with public/private subnets

- **Security**:
  - Kyverno: require signed images, disallow privileged containers
  - Sigma detection rules for unauthorized changes and runbook abuse
  - External Secrets Operator integration
  - STRIDE threat model documentation

- **Observability**:
  - OpenTelemetry collector configuration
  - Grafana dashboards: platform overview, cost-by-tenant
  - PII scrubbing processor

- **Testing**:
  - Unit tests: change workflow, approval gate, incident resolution
  - Integration tests: API change flow
  - Security tests: unapproved change rejection

- **CI/CD**:
  - GitHub Actions: CI, Terraform, security scanning, release
  - Dependabot for pip, terraform, docker, github-actions
  - Pre-commit hooks: ruff, mypy, detect-secrets, hadolint

[Unreleased]: https://github.com/kogunlowo123/autonomous-it-control-plane/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kogunlowo123/autonomous-it-control-plane/releases/tag/v0.1.0
