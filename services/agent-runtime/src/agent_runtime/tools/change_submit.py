"""Change submit tool — submits change requests through approval workflow."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import psycopg2

from agent_runtime.orchestrator.approvals import create_approval_request
from agent_runtime.settings import Settings
from agent_runtime.tools.base import BaseTool

logger = logging.getLogger(__name__)

_settings = Settings()


class ChangeSubmitTool(BaseTool):
    """Submit change requests requiring T2/T3 approval."""

    name = "change_submit"
    description = "Submit a T2 or T3 change request for human approval"

    async def run(  # type: ignore[override]
        self,
        title: str,
        description: str,
        tier: str,
        execution_steps: list[str],
        rollback_steps: list[str],
        requested_by: str = "agent",
    ) -> dict[str, Any]:
        """Submit a change request and create approval workflow.

        Args:
            title: Short change title
            description: Detailed change description
            tier: Change tier (T1, T2, T3)
            execution_steps: Ordered list of execution steps
            rollback_steps: Ordered list of rollback steps
            requested_by: Agent or user that requested the change

        Returns:
            {change_id, approval_id, status}
        """
        change_id = str(uuid.uuid4())
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._submit_sync,
            change_id,
            title,
            description,
            tier,
            execution_steps,
            rollback_steps,
            requested_by,
        )

    def _submit_sync(
        self,
        change_id: str,
        title: str,
        description: str,
        tier: str,
        execution_steps: list[str],
        rollback_steps: list[str],
        requested_by: str,
    ) -> dict[str, Any]:
        import json

        try:
            conn = psycopg2.connect(_settings.database_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO changes
                          (id, title, description, tier, status, requested_by, metadata)
                        VALUES (%s, %s, %s, %s, 'pending_approval', %s, %s::jsonb)
                        """,
                        (
                            change_id,
                            title,
                            description,
                            tier,
                            requested_by,
                            json.dumps({
                                "execution_steps": execution_steps,
                                "rollback_steps": rollback_steps,
                            }),
                        ),
                    )
            conn.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to insert change: %s", exc)
            return {"change_id": change_id, "status": "error", "error": str(exc)}

        if tier in ("T2", "T3"):
            approval_id = create_approval_request(change_id=change_id, tier=tier)
            return {
                "change_id": change_id,
                "approval_id": approval_id,
                "status": "pending_approval",
            }

        return {"change_id": change_id, "approval_id": None, "status": "approved"}
