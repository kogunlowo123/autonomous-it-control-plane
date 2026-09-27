"""Approval workflow engine for T2/T3 changes.

Approval lifecycle:
  create_approval_request() → PENDING
  check_approval_status()   → PENDING | APPROVED | DENIED | EXPIRED
  approve_change()          → APPROVED
  deny_change()             → DENIED
  (timeout)                 → EXPIRED (auto-deny)

Timeouts:
  T2 = 1800s (30 minutes)
  T3 =  900s (15 minutes)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Optional

import psycopg2
import psycopg2.extras

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUTS: dict[str, int] = {
    "T2": 1800,
    "T3": 900,
}


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


def _ensure_approvals_schema(conn: psycopg2.extensions.connection) -> None:
    """Idempotently create the approvals table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id UUID PRIMARY KEY,
                change_id UUID NOT NULL,
                tier VARCHAR(10) NOT NULL,
                approvers JSONB NOT NULL DEFAULT '[]',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                responded_by VARCHAR(255),
                responded_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_approvals_change_id ON approvals(change_id);
            CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
            """
        )
        conn.commit()


def create_approval_request(
    change_id: str,
    tier: str,
    approvers: list[str],
    settings: Settings,
) -> tuple[str, str]:
    """Create an approval request for a change.

    Returns (approval_id, expires_at_iso).
    Notifies approvers via SQS.
    """
    approval_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    timeout_seconds = APPROVAL_TIMEOUTS.get(tier, 1800)
    expires_at = now + timedelta(seconds=timeout_seconds)

    conn = psycopg2.connect(settings.database_url, connect_timeout=5)
    conn.autocommit = False
    try:
        _ensure_approvals_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO approvals (id, change_id, tier, approvers, status, created_at, expires_at)
                VALUES (%s, %s::uuid, %s, %s, 'pending', %s, %s)
                """,
                (approval_id, change_id, tier, json.dumps(approvers), now, expires_at),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()

    logger.info(
        "Approval request created id=%s change=%s tier=%s expires=%s",
        approval_id, change_id, tier, expires_at.isoformat(),
    )

    _notify_approvers_via_sqs(
        approval_id=approval_id,
        change_id=change_id,
        tier=tier,
        approvers=approvers,
        expires_at=expires_at,
        settings=settings,
    )

    return approval_id, expires_at.isoformat()


def check_approval_status(approval_id: str, settings: Settings) -> ApprovalStatus:
    """Return current approval status.

    Pending approvals past their expiry are automatically marked EXPIRED.
    """
    conn = psycopg2.connect(settings.database_url, connect_timeout=5)
    try:
        _ensure_approvals_schema(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM approvals WHERE id = %s::uuid", (approval_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError(f"Approval {approval_id} not found")

    current_status = ApprovalStatus(row["status"])

    if current_status == ApprovalStatus.PENDING:
        expires_at: datetime = row["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if now > expires_at:
            _set_approval_status(approval_id, "expired", approver=None, settings=settings)
            logger.warning(
                "Approval %s expired (was due %s)", approval_id, expires_at.isoformat()
            )
            return ApprovalStatus.EXPIRED

    return current_status


def approve_change(approval_id: str, approver: str, settings: Settings) -> bool:
    """Record an approval. Returns True if successfully recorded."""
    return _set_approval_status(approval_id, "approved", approver=approver, settings=settings)


def deny_change(approval_id: str, approver: str, settings: Settings) -> bool:
    """Record a denial. Returns True if successfully recorded."""
    return _set_approval_status(approval_id, "denied", approver=approver, settings=settings)


def _set_approval_status(
    approval_id: str,
    new_status: str,
    approver: Optional[str],
    settings: Settings,
) -> bool:
    """Atomically update approval status from 'pending' to new_status."""
    conn = psycopg2.connect(settings.database_url, connect_timeout=5)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            if approver:
                cur.execute(
                    """
                    UPDATE approvals
                    SET status = %s, responded_by = %s, responded_at = NOW()
                    WHERE id = %s::uuid AND status = 'pending'
                    RETURNING id
                    """,
                    (new_status, approver, approval_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE approvals SET status = %s, responded_at = NOW()
                    WHERE id = %s::uuid AND status = 'pending'
                    RETURNING id
                    """,
                    (new_status, approval_id),
                )
            updated = cur.fetchone()
    finally:
        conn.close()

    if updated is None:
        logger.warning(
            "Approval %s could not be set to %s (not found or not pending)",
            approval_id, new_status,
        )
        return False

    logger.info("Approval %s set to %s by %s", approval_id, new_status, approver or "system")
    return True


def _notify_approvers_via_sqs(
    approval_id: str,
    change_id: str,
    tier: str,
    approvers: list[str],
    expires_at: datetime,
    settings: Settings,
) -> None:
    """Send approval notification via SQS. Non-fatal on failure."""
    if not settings.sqs_approval_queue_url:
        logger.debug("No SQS approval queue configured, skipping notification")
        return

    try:
        import boto3
        sqs = boto3.client("sqs", region_name=settings.aws_region)
        event = {
            "specversion": "1.0",
            "type": "change.approval_requested",
            "source": "autonomous-it-control-plane/approvals",
            "id": str(uuid.uuid4()),
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "data": {
                "approval_id": approval_id,
                "change_id": change_id,
                "tier": tier,
                "approvers": approvers,
                "expires_at": expires_at.isoformat(),
                "approval_timeout_seconds": APPROVAL_TIMEOUTS.get(tier, 1800),
                "action": "Review and approve or deny this change request",
            },
        }
        sqs.send_message(
            QueueUrl=settings.sqs_approval_queue_url,
            MessageBody=json.dumps(event),
        )
        logger.info(
            "Approval notification sent approval_id=%s to %d approver(s)",
            approval_id, len(approvers),
        )
    except Exception as exc:
        logger.warning("Failed to send approval notification via SQS: %s", exc)
