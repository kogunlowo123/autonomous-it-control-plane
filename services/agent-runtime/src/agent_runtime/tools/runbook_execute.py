"""Runbook execution tool — validates and executes approved runbook steps."""
from __future__ import annotations

import logging
from typing import Any

from agent_runtime.guardrails.input_screen import screen_input
from agent_runtime.tools.base import BaseTool

logger = logging.getLogger(__name__)

_BLOCKED_COMMANDS = frozenset([
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "fork bomb",
])


class RunbookExecuteTool(BaseTool):
    """Execute validated runbook steps with safety guardrails."""

    name = "runbook_execute"
    description = "Execute a specific runbook step after validation"

    async def run(  # type: ignore[override]
        self,
        step: str,
        context: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Validate and optionally execute a runbook step.

        Args:
            step: The runbook step to execute
            context: Execution context (incident_id, change_id, etc.)
            dry_run: If True, validate without executing (default: True for safety)

        Returns:
            {success: bool, output: str, dry_run: bool}
        """
        # Screen for injection / dangerous patterns
        is_safe, reason = screen_input(step)
        if not is_safe:
            logger.warning("Runbook step blocked by guardrail: %s", reason)
            return {
                "success": False,
                "output": f"Step blocked by guardrail: {reason}",
                "dry_run": dry_run,
            }

        # Block known destructive commands
        step_lower = step.lower()
        for blocked in _BLOCKED_COMMANDS:
            if blocked in step_lower:
                return {
                    "success": False,
                    "output": f"Step contains blocked command: {blocked}",
                    "dry_run": dry_run,
                }

        if dry_run:
            logger.info("Dry run — step validated but not executed: %.80s", step)
            return {
                "success": True,
                "output": f"[DRY RUN] Step validated: {step[:200]}",
                "dry_run": True,
            }

        # In production this would dispatch to an execution engine (e.g., SSM, Ansible)
        logger.info("Executing runbook step: %.80s", step)
        return {
            "success": True,
            "output": f"Step executed: {step[:200]}",
            "dry_run": False,
        }
