.PHONY: help install test test-unit test-integration test-security lint format typecheck \
        docker-up docker-down docker-build build-api build-agent \
        tf-init tf-plan tf-apply clean

PYTHON ?= python3
UV ?= uv
BASE_DIR := $(shell pwd)
SERVICES := services/api services/agent-runtime services/rag-core

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies via uv
	@for svc in $(SERVICES); do \
		echo "Installing $$svc..."; \
		cd $(BASE_DIR)/$$svc && $(UV) sync --all-groups && cd $(BASE_DIR); \
	done

test: ## Run all tests
	$(UV) run pytest tests/ -v --tb=short --cov=services --cov-report=term-missing

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests (requires running services)
	$(UV) run pytest tests/integration/ -v --tb=short

test-security: ## Run security tests
	$(UV) run pytest tests/security/ -v --tb=short

lint: ## Run linting checks
	$(UV) run ruff check services/ tests/ platform/ evals/
	$(UV) run ruff format --check services/ tests/ platform/ evals/

format: ## Auto-format code
	$(UV) run ruff format services/ tests/ platform/ evals/
	$(UV) run ruff check --fix services/ tests/ platform/ evals/

typecheck: ## Run mypy type checking
	$(UV) run mypy services/api/src services/agent-runtime/src services/rag-core/src --ignore-missing-imports

docker-up: ## Start all services with docker compose
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker compose ps

docker-down: ## Stop all services
	docker compose down

docker-build: build-api build-agent ## Build all Docker images

build-api: ## Build API Docker image
	docker build -t autonomous-it-api:latest -t autonomous-it-api:0.1.0 services/api/

build-agent: ## Build agent-runtime Docker image
	docker build -t autonomous-it-agent:latest -t autonomous-it-agent:0.1.0 services/agent-runtime/

build-rag: ## Build RAG core Docker image
	docker build -t autonomous-it-rag:latest services/rag-core/

tf-init: ## Initialize Terraform for dev environment
	terraform -chdir=infra/envs/aws/dev init

tf-plan: ## Plan Terraform changes for dev
	terraform -chdir=infra/envs/aws/dev plan

tf-apply: ## Apply Terraform changes for dev (requires confirmation)
	terraform -chdir=infra/envs/aws/dev apply

tf-fmt: ## Format Terraform files
	terraform fmt -recursive infra/

tf-validate: ## Validate Terraform configuration
	terraform -chdir=infra/envs/aws/dev validate

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

health-check: ## Check API health endpoint
	curl -sf http://localhost:8000/api/v1/health | python3 -m json.tool

db-migrate: ## Run database migrations
	$(UV) run python -c "from services.api.src.api.routes.v1.change import _ensure_schema; import psycopg2; conn = psycopg2.connect('$(DATABASE_URL)'); _ensure_schema(conn)"

.DEFAULT_GOAL := help
