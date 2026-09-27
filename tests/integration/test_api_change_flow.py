"""Integration tests for the change management API flow.

Requires: running PostgreSQL at DATABASE_URL.
Run with: pytest tests/integration/ -v
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Generator

import pytest

# Add services to path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "services/api/src"))

# Skip all tests if psycopg2 or fastapi not available
pytest.importorskip("psycopg2")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")


@pytest.fixture(scope="module")
def test_settings():
    """Build Settings from environment variables."""
    from api.settings import Settings
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://itsm:password@localhost:5432/itsm_db"
        ),
        jwt_secret_key="test-integration-secret",
        jwt_algorithm="HS256",
        sqs_change_queue_url="",
        sqs_approval_queue_url="",
        default_tenant_id="test-tenant",
        otel_exporter_otlp_endpoint="",
    )


@pytest.fixture(scope="module")
def app(test_settings):
    """Create test FastAPI app."""
    from api.main import create_app
    return create_app(settings=test_settings)


@pytest.fixture(scope="module")
def client(app):
    """Create test HTTP client."""
    from httpx import AsyncClient
    return app


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate a valid JWT for testing."""
    import jwt
    from datetime import UTC, datetime, timedelta

    token = jwt.encode(
        {
            "sub": "test-user@example.com",
            "roles": ["operator"],
            "tier": "T2",
            "tenant_id": "test-tenant",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "test-integration-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(app) -> None:
    """GET /api/v1/health returns 200 with status=ok."""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_submit_change_returns_201(app, auth_headers) -> None:
    """POST /api/v1/change/submit creates a change and returns 201."""
    from httpx import AsyncClient, ASGITransport

    payload = {
        "title": f"Test change {uuid.uuid4().hex[:8]}",
        "description": "Integration test change for CI",
        "tier": "T1",  # T1 to avoid SQS dependency
        "requestor": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/change/submit",
            json=payload,
            headers=auth_headers,
        )

    if resp.status_code == 503:
        pytest.skip("Database not available in this environment")

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["tier"] == "T1"
    assert data["status"] in ("pending", "pending_approval")


@pytest.mark.asyncio
async def test_get_change_status_not_found(app, auth_headers) -> None:
    """GET /api/v1/change/{id}/status returns 404 for unknown ID."""
    from httpx import AsyncClient, ASGITransport

    nonexistent_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/change/{nonexistent_id}/status",
            headers=auth_headers,
        )

    if resp.status_code == 503:
        pytest.skip("Database not available")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_change_submit_and_retrieve_status(app, auth_headers) -> None:
    """Submit a change then retrieve its status — full round trip."""
    from httpx import AsyncClient, ASGITransport

    payload = {
        "title": f"Round-trip test {uuid.uuid4().hex[:8]}",
        "description": "Testing submit + status retrieval",
        "tier": "T1",
        "requestor": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/change/submit",
            json=payload,
            headers=auth_headers,
        )

        if create_resp.status_code == 503:
            pytest.skip("Database not available")

        assert create_resp.status_code == 201
        change_id = create_resp.json()["id"]

        status_resp = await client.get(
            f"/api/v1/change/{change_id}/status",
            headers=auth_headers,
        )

    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == change_id
    assert status_data["title"] == payload["title"]
    assert status_data["tier"] == "T1"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(app) -> None:
    """Requests without Bearer token are rejected with 401."""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/change/submit",
            json={"title": "X", "description": "Y", "tier": "T1", "requestor": "x@x.com"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_resolve_incident_creates_record(app, auth_headers) -> None:
    """POST /api/v1/incident/resolve creates a record and returns 201."""
    from httpx import AsyncClient, ASGITransport

    payload = {
        "title": f"Test incident {uuid.uuid4().hex[:8]}",
        "description": "High CPU on app servers — integration test",
        "priority": "P3",
        "affected_service": "test-service",
        "requestor": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/incident/resolve",
            json=payload,
            headers=auth_headers,
        )

    if resp.status_code == 503:
        pytest.skip("Database not available")

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["agent_dispatched"] is True
    assert data["status"] == "investigating"
