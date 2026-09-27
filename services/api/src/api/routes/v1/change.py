"""Change management API routes.

POST /api/v1/change/submit         — Submit change request, trigger approval workflow
GET  /api/v1/change/{id}/status    — Get change status
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas.change import ChangeTier, ChangeRequest, ChangeResponse, ChangeStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_changes_schema(conn: psycopg2.extensions.connection) -> None:
    """Ensure the changes table exists."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS changes (
                id UUID PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                tier VARCHAR(10) NOT NULL,
                requestor VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                approved_at TIMESTAMPTZ,
                executed_at TIMESTAMPTZ,
                rolled_back_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'
            )
            """
        )
        conn.commit()


def _emit_change_event(
    sqs_client: Any,
    queue_url: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Emit a CloudEvent to SQS FIFO queue."""
    event = {
        "specversion": "1.0",
        "type": event_type,
        "source": "autonomous-it-control-plane/change",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": data,
    }
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(event),
        MessageGroupId=data.get("change_id", "default"),
        MessageDeduplicationId=event["id"],
    )
    logger.info("Emitted event type=%s change_id=%s", event_type, data.get("change_id"))


@router.post("/submit", response_model=ChangeResponse, status_code=status.HTTP_201_CREATED)
async def submit_change(
    request: Request,
    body: ChangeRequest,
) -> ChangeResponse:
    """Submit a change request.

    T1 changes proceed immediately.
    T2/T3 changes trigger an approval workflow via SQS and are held in
    'pending_approval' state until a human approver acts.
    """
    settings = request.app.state.settings
    change_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    requires_approval = body.tier in (ChangeTier.T2, ChangeTier.T3)
    initial_status = "pending_approval" if requires_approval else "pending"

    # Persist to PostgreSQL
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = False
        _ensure_changes_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO changes (id, title, description, tier, requestor, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (change_id, body.title, body.description, body.tier.value,
                 body.requestor, initial_status, now, now),
            )
            conn.commit()
        conn.close()
    except psycopg2.OperationalError as exc:
        logger.error("Database error persisting change %s: %s", change_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        ) from exc

    # Emit CloudEvent for T2/T3 changes
    if requires_approval and settings.sqs_change_queue_url:
        try:
            import boto3
            sqs = boto3.client("sqs", region_name=settings.aws_region)
            _emit_change_event(
                sqs_client=sqs,
                queue_url=settings.sqs_change_queue_url,
                event_type="change.submitted",
                data={
                    "change_id": change_id,
                    "tier": body.tier.value,
                    "title": body.title,
                    "description": body.description,
                    "requestor": body.requestor,
                    "requires_approval": True,
                    "submitted_at": now.isoformat(),
                },
            )
        except Exception as exc:
            # SQS failure is non-fatal — the change is already persisted
            logger.warning("Failed to emit change.submitted event for %s: %s", change_id, exc)

    message = (
        f"Change submitted and queued for approval. Tier {body.tier.value} requires human review."
        if requires_approval
        else "Change submitted and queued for processing."
    )

    return ChangeResponse(
        id=change_id,
        title=body.title,
        description=body.description,
        tier=body.tier,
        requestor=body.requestor,
        status=initial_status,
        created_at=now.isoformat(),
        message=message,
    )


@router.get("/{change_id}/status", response_model=ChangeStatusResponse)
async def get_change_status(change_id: str, request: Request) -> ChangeStatusResponse:
    """Get the current status of a change request by ID."""
    settings = request.app.state.settings

    try:
        conn = psycopg2.connect(settings.database_url)
        _ensure_changes_schema(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM changes WHERE id = %s::uuid", (change_id,))
            row = cur.fetchone()
        conn.close()
    except psycopg2.OperationalError as exc:
        logger.error("Database error fetching change %s: %s", change_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        ) from exc
    except Exception as exc:
        logger.error("Error fetching change %s: %s", change_id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid change ID format: {change_id}",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change {change_id} not found",
        )

    def _ts(v: Any) -> str | None:
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    return ChangeStatusResponse(
        id=str(row["id"]),
        status=row["status"],
        tier=row["tier"],
        title=row["title"],
        requestor=row["requestor"],
        created_at=_ts(row["created_at"]),
        updated_at=_ts(row["updated_at"]),
        approved_at=_ts(row["approved_at"]),
        executed_at=_ts(row["executed_at"]),
        rolled_back_at=_ts(row["rolled_back_at"]),
    )
