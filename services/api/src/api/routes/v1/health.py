"""Health and readiness check endpoints."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    """Liveness probe — returns 200 when the process is running."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe — checks all downstream dependencies."""
    settings = request.app.state.settings
    checks: dict[str, str] = {}
    overall_ok = True

    # Check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(settings.database_url, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", exc)
        checks["database"] = f"error: {type(exc).__name__}"
        overall_ok = False

    # Check OPA (optional dependency)
    try:
        import urllib.request
        req = urllib.request.urlopen(f"{settings.opa_url}/health", timeout=2)
        if req.status == 200:
            checks["opa"] = "ok"
        else:
            checks["opa"] = f"error: status {req.status}"
    except Exception as exc:
        logger.debug("OPA readiness check failed (non-critical): %s", exc)
        checks["opa"] = "unavailable"

    http_status = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content=ReadinessResponse(
            status="ok" if overall_ok else "degraded",
            checks=checks,
        ).model_dump(),
    )
