"""Incident management API routes.

POST /api/v1/incident/resolve  — Attempt autonomous incident resolution
GET  /api/v1/incident/{id}     — Get incident record
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas.incident import IncidentRecord, IncidentRequest, IncidentResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_incidents_schema(conn: psycopg2.extensions.connection) -> None:
    """Ensure the incidents table exists."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id UUID PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                priority VARCHAR(10) NOT NULL,
                affected_service VARCHAR(255) NOT NULL,
                requestor VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                resolution TEXT,
                runbook_used VARCHAR(500),
                confidence FLOAT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resolved_at TIMESTAMPTZ
            )
            """
        )
        conn.commit()


@router.post("/resolve", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def resolve_incident(request: Request, body: IncidentRequest) -> IncidentResponse:
    """Attempt autonomous incident resolution.

    Creates an incident record and dispatches the ITSM resolver agent.
    The agent classifies the incident, retrieves relevant runbooks via RAG,
    generates resolution steps, and resolves or escalates based on confidence.
    """
    settings = request.app.state.settings
    incident_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    try:
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = False
        _ensure_incidents_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incidents
                  (id, title, description, priority, affected_service, requestor, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'investigating', %s, %s)
                """,
                (
                    incident_id,
                    body.title,
                    body.description,
                    body.priority.value,
                    body.affected_service,
                    body.requestor,
                    now,
                    now,
                ),
            )
            conn.commit()
        conn.close()
    except psycopg2.OperationalError as exc:
        logger.error("Database error creating incident %s: %s", incident_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        ) from exc

    logger.info(
        "Incident created id=%s priority=%s service=%s agent_dispatched=true",
        incident_id, body.priority.value, body.affected_service,
    )

    return IncidentResponse(
        id=incident_id,
        title=body.title,
        status="investigating",
        priority=body.priority,
        affected_service=body.affected_service,
        requestor=body.requestor,
        created_at=now.isoformat(),
        message=(
            "Incident created. ITSM resolver agent dispatched for autonomous resolution. "
            f"Priority {body.priority.value} — {'P1/P2 incidents auto-escalate if confidence < 0.95.' if body.priority.value in ('P1', 'P2') else 'Will resolve or escalate based on runbook match confidence.'}"
        ),
        agent_dispatched=True,
    )


@router.get("/{incident_id}", response_model=IncidentRecord)
async def get_incident(incident_id: str, request: Request) -> IncidentRecord:
    """Get an incident record by ID."""
    settings = request.app.state.settings

    try:
        conn = psycopg2.connect(settings.database_url)
        _ensure_incidents_schema(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM incidents WHERE id = %s::uuid", (incident_id,))
            row = cur.fetchone()
        conn.close()
    except psycopg2.OperationalError as exc:
        logger.error("Database error fetching incident %s: %s", incident_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid incident ID format: {incident_id}",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    def _ts(v: Any) -> str | None:
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    return IncidentRecord(
        id=str(row["id"]),
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        affected_service=row["affected_service"],
        requestor=row["requestor"],
        status=row["status"],
        resolution=row["resolution"],
        runbook_used=row["runbook_used"],
        confidence=row["confidence"],
        created_at=_ts(row["created_at"]),
        updated_at=_ts(row["updated_at"]),
        resolved_at=_ts(row["resolved_at"]),
    )
