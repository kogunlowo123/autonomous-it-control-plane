"""Session store — persists agent session state to PostgreSQL."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


def create_session(agent_type: str, incident_id: str | None = None) -> str:
    """Create a new agent session and return session_id."""
    session_id = str(uuid.uuid4())
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO identity.session_ledger
                      (session_id, agent_id, agent_type, action, resource_type,
                       resource_id, outcome, event_data)
                    VALUES (%s, %s, %s, 'session.start', 'session', %s, 'in_progress', %s::jsonb)
                    """,
                    (
                        session_id,
                        session_id,
                        agent_type,
                        incident_id or session_id,
                        json.dumps({"started_at": datetime.now(tz=timezone.utc).isoformat()}),
                    ),
                )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to create session record: %s", exc)

    return session_id


def close_session(session_id: str, outcome: str = "success") -> None:
    """Close a session by recording completion in the audit ledger."""
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO identity.session_ledger
                      (session_id, agent_id, agent_type, action, resource_type,
                       resource_id, outcome, event_data)
                    VALUES (%s, %s, 'agent', 'session.end', 'session', %s, %s, %s::jsonb)
                    """,
                    (
                        session_id,
                        session_id,
                        session_id,
                        outcome,
                        json.dumps({"ended_at": datetime.now(tz=timezone.utc).isoformat()}),
                    ),
                )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to close session record: %s", exc)


def get_session_events(session_id: str) -> list[dict[str, Any]]:
    """Retrieve all events for a session from the audit ledger."""
    events: list[dict[str, Any]] = []
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT action, resource_type, resource_id, outcome, event_data, created_at
                FROM identity.session_ledger
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            for row in cur.fetchall():
                events.append({
                    "action": row[0],
                    "resource_type": row[1],
                    "resource_id": row[2],
                    "outcome": row[3],
                    "event_data": row[4] or {},
                    "created_at": row[5].isoformat() if row[5] else None,
                })
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch session events: %s", exc)

    return events
