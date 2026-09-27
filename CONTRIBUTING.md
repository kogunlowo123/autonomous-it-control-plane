# Contributing to Autonomous IT Control Plane

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) 0.2+
- Docker & Docker Compose v2
- Terraform 1.8+
- Git

### Initial Setup

```bash
git clone https://github.com/kogunlowo123/autonomous-it-control-plane.git
cd autonomous-it-control-plane

# Install dependencies
make install

# Set up pre-commit hooks
make pre-commit-install

# Copy and configure environment
cp .env.example .env
# Edit .env with your values

# Start local infrastructure
make docker-up
```

## Code Style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check for issues
make lint

# Auto-fix and format
make format

# Type checking
make typecheck
```

Configuration in `pyproject.toml`:
- Line length: 100
- Python target: 3.12
- Rules: E, F, I, N, W, UP

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `infra`

Examples:
```
feat(agent): add P1 incident auto-escalation in incident-manager
fix(approvals): handle timezone-naive datetime in expiry check
docs(runbooks): add database connection pool runbook
test(unit): add approval gate timeout tests
infra(eks): upgrade node group to t3.large
```

## Testing

All changes must include appropriate tests.

```bash
# Run unit tests
make test-unit

# Run integration tests (requires docker-up)
make test-integration

# Run security tests
make test-security

# Full test suite with coverage
make test
```

Test files live in `tests/`:
- `tests/unit/` — Unit tests, no external dependencies
- `tests/integration/` — Integration tests, requires running services
- `tests/security/` — Security-focused tests

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes with tests
4. Run `make lint format test` — all must pass
5. Commit with conventional commit message
6. Push and open a PR against `main`
7. Fill out the PR template completely
8. Wait for review from a CODEOWNER

### PR Requirements

- [ ] All CI checks pass
- [ ] Test coverage maintained or improved
- [ ] No new security findings from bandit/safety
- [ ] Documentation updated if API changes
- [ ] ADR created for significant architectural decisions

## Architecture Decisions

Significant changes require an Architecture Decision Record (ADR) in `docs/adr/`.

Format: `docs/adr/XXXX-short-title.md`

See `docs/adr/0001-human-gate-t2.md` for an example.

## Security

See [SECURITY.md](SECURITY.md) for reporting security vulnerabilities.

Do not commit secrets, credentials, or PII. The pre-commit hooks include `detect-secrets`.
