"""Ticket creation tool — creates ITSM tickets in the database."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import psycopg2

from agent_runtime.settings import Settings
from agent_runtime.tools.base import BaseTool

logger = logging.getLogger(__name__)

_settings = Settings()


class TicketCreateTool(BaseTool):
    """Create or update ITSM tickets."""

    name = "ticket_create"
    description = "Create an ITSM ticket for an incident or change"

    async def run(  # type: ignore[override]
        self,
        title: str,
        description: str,
        priority: str = "P3",
        incident_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a ticket and return {ticket_id, status}."""
        ticket_id = str(uuid.uuid4())
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._create_sync,
            ticket_id,
            title,
            description,
            priority,
            incident_id,
            metadata or {},
        )

    def _create_sync(
        self,
        ticket_id: str,
        title: str,
        description: str,
        priority: str,
        incident_id: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            conn = psycopg2.connect(_settings.database_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO tickets (id, title, description, priority, incident_id, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (ticket_id, title, description, priority, incident_id, psycopg2.extras.Json(metadata)),
                    )
            conn.close()
            logger.info("Ticket created: %s", ticket_id)
            return {"ticket_id": ticket_id, "status": "created"}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to create ticket: %s", exc)
            return {"ticket_id": ticket_id, "status": "error", "error": str(exc)}
