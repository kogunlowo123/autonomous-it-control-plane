"""Change execution planner — generates execution and rollback plans via LLM."""
from __future__ import annotations

import logging
import re

try:
    import litellm
except ImportError:  # pragma: no cover
    litellm = None  # type: ignore[assignment]

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)


def plan_change_execution(
    change_id: str,
    title: str,
    description: str,
    tier: str,
    settings: Settings,
) -> tuple[list[str], list[str]]:
    """Generate execution and rollback plans for a change.

    Returns (execution_steps, rollback_steps).
    """
    try:
        if litellm is None:
            raise ImportError("litellm not available")

        prompt = (
            "You are an IT change management expert. Generate a detailed execution plan and rollback plan.\n\n"
            f"Change: {title}\nDescription: {description}\nTier: {tier}\n\n"
            "Format your response EXACTLY as:\n\n"
            "EXECUTION PLAN:\n1. Step one\n2. Step two\n3. ...\n\n"
            "ROLLBACK PLAN:\n1. Rollback step one\n2. Rollback step two\n3. ..."
        )
        response = litellm.completion(
            model=f"bedrock/{settings.aws_bedrock_model_id}",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.1,
        )
        content = str(response.choices[0].message.content)
        return _parse_plan(content)
    except Exception as exc:
        logger.warning("LLM plan generation failed for change %s: %s", change_id, exc)
        return _default_plan(title, description)


def _parse_plan(content: str) -> tuple[list[str], list[str]]:
    """Parse LLM output into (exec_steps, rollback_steps)."""
    exec_steps: list[str] = []
    rollback_steps: list[str] = []
    current: list[str] | None = None

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "EXECUTION PLAN" in line.upper():
            current = exec_steps
        elif "ROLLBACK PLAN" in line.upper():
            current = rollback_steps
        elif current is not None:
            cleaned = re.sub(r"^\d+[.)]\s*", "", line).strip()
            if cleaned:
                current.append(cleaned)

    if not exec_steps:
        exec_steps = ["Execute change as described"]
    if not rollback_steps:
        rollback_steps = ["Revert change to prior state"]

    return exec_steps, rollback_steps


def _default_plan(title: str, description: str) -> tuple[list[str], list[str]]:
    """Return a generic plan when LLM is unavailable."""
    exec_steps = [
        f"Pre-flight check: verify prerequisites for '{title}'",
        "Create snapshot or backup of affected resources",
        f"Execute: {description[:120]}",
        "Verify successful execution",
        "Update change record status to 'executed'",
    ]
    rollback_steps = [
        "Halt change execution immediately",
        "Restore from snapshot/backup created in step 2",
        "Verify service restoration to prior state",
        "Update change record status to 'rolled_back'",
        "Document rollback reason and timeline",
    ]
    return exec_steps, rollback_steps
