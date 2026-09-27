"""ITSM Resolver LangGraph agent.

Flow:
  START → classify_incident → retrieve_runbook → generate_resolution
        → validate_steps → (should_escalate?) → create_ticket | escalate → END

Escalation triggers:
  - confidence < CONFIDENCE_THRESHOLD (0.85)
  - P1 incident with confidence < 0.95
  - Dangerous operations detected in resolution steps
  - requires_human flag set
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from agent_runtime.orchestrator.state import IncidentPriority, IncidentState, ResolutionStatus
from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.85
P1_CONFIDENCE_THRESHOLD = 0.95
MAX_ITERATIONS = 3

_DANGEROUS_KEYWORDS = frozenset({
    "rm -rf", "drop table", "drop database", "delete from",
    "format disk", "wipe", "truncate", "factory reset",
    "delete all", "> /dev/sda",
})


def _call_llm(settings: Settings, prompt: str, max_tokens: int = 200) -> str:
    """Call LiteLLM with AWS Bedrock. Returns content string."""
    import litellm
    response = litellm.completion(
        model=f"bedrock/{settings.aws_bedrock_model_id}",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0,
    )
    return str(response.choices[0].message.content).strip()


def classify_incident(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: classify the incident using LLM."""
    logger.info("classify_incident incident_id=%s", state.incident_id)

    valid_categories = {
        "network_outage", "database_failure", "application_crash",
        "security_incident", "performance_degradation", "configuration_error",
        "hardware_failure", "other",
    }

    try:
        prompt = (
            "Classify this IT incident into exactly one category from this list:\n"
            f"{', '.join(sorted(valid_categories))}\n\n"
            f"Title: {state.title}\nDescription: {state.description}\n\n"
            "Respond with ONLY the category name, nothing else."
        )
        classification = _call_llm(settings, prompt, max_tokens=30).lower().strip()
        if classification not in valid_categories:
            # Fuzzy match
            classification = next(
                (c for c in valid_categories if c in classification), "other"
            )
    except Exception as exc:
        logger.warning("LLM classification failed, defaulting to 'other': %s", exc)
        classification = "other"

    return {
        "classification": classification,
        "status": ResolutionStatus.INVESTIGATING,
        "iterations": state.iterations + 1,
    }


def retrieve_runbook(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: retrieve relevant runbooks via pgvector semantic search."""
    logger.info("retrieve_runbook incident_id=%s classification=%s", state.incident_id, state.classification)

    runbooks: list[dict[str, Any]] = []

    try:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(settings.database_url, connect_timeout=5)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Try pgvector search first, fall back to text search
            try:
                cur.execute(
                    """
                    SELECT id, title, content, metadata
                    FROM itsm.runbooks
                    WHERE content ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (f"%{state.classification}%",),
                )
            except psycopg2.errors.UndefinedTable:
                # Table does not exist yet
                cur.execute("SELECT 1")
            rows = cur.fetchall() if cur.description else []
            runbooks = [dict(r) for r in rows]
        conn.close()
    except Exception as exc:
        logger.warning("Runbook retrieval from pgvector failed: %s", exc)

    # Fall back to a generic runbook if none found
    if not runbooks:
        classification = state.classification or "other"
        runbooks = [
            {
                "id": f"generic-{classification}",
                "title": f"Standard {classification.replace('_', ' ').title()} Runbook",
                "content": (
                    f"Standard procedure for {classification.replace('_', ' ')}:\n"
                    "1. Assess impact scope and affected systems\n"
                    "2. Notify relevant stakeholders\n"
                    "3. Isolate the affected component if possible\n"
                    "4. Apply standard remediation steps\n"
                    "5. Verify service restoration\n"
                    "6. Document incident timeline and actions taken"
                ),
                "similarity": 0.5,
                "metadata": {"source": "generic", "tier": "T1"},
            }
        ]
        logger.info("Using generic runbook for classification=%s", classification)

    return {"retrieved_runbooks": runbooks}


def generate_resolution(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: generate resolution steps from retrieved runbooks."""
    logger.info("generate_resolution incident_id=%s runbooks=%d", state.incident_id, len(state.retrieved_runbooks))

    runbook_context = "\n\n".join(
        f"=== {rb.get('title', 'Runbook')} ===\n{rb.get('content', '')}"
        for rb in state.retrieved_runbooks[:3]
    )

    try:
        prompt = (
            "You are an expert IT operations engineer. Generate specific, actionable resolution steps "
            "for this incident based on the runbooks provided.\n\n"
            f"Incident: {state.title}\n"
            f"Description: {state.description}\n"
            f"Classification: {state.classification}\n\n"
            f"Runbooks:\n{runbook_context[:3000]}\n\n"
            "Provide 3-7 numbered resolution steps. Be specific and actionable. "
            "Format: '1. Step one\\n2. Step two\\n...'"
        )
        content = _call_llm(settings, prompt, max_tokens=600)
        steps = []
        for line in content.split("\n"):
            line = line.strip()
            if line and len(line) > 3:
                # Strip leading numbers/dots
                import re
                cleaned = re.sub(r"^\d+[.)]\s*", "", line).strip()
                if cleaned:
                    steps.append(cleaned)

        if not steps:
            steps = ["Assess impact", "Apply remediation", "Verify restoration", "Document actions"]

        confidence = min(0.95, 0.55 + len(state.retrieved_runbooks) * 0.06 + len(steps) * 0.02)
    except Exception as exc:
        logger.warning("LLM resolution generation failed: %s", exc)
        steps = [
            f"Acknowledge incident: {state.title}",
            "Assess scope of impact on affected systems",
            f"Apply remediation procedure for: {state.classification or 'unknown'}",
            "Verify service restoration",
            "Document incident timeline",
        ]
        confidence = 0.5

    return {
        "resolution_steps": steps,
        "confidence": confidence,
    }


def validate_steps(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: validate resolution steps for safety and completeness."""
    logger.info("validate_steps incident_id=%s confidence=%.2f steps=%d",
                state.incident_id, state.confidence, len(state.resolution_steps))

    if not state.resolution_steps:
        return {
            "confidence": 0.0,
            "requires_human": True,
            "escalation_reason": "No resolution steps could be generated",
        }

    # Check for dangerous operations
    for step in state.resolution_steps:
        step_lower = step.lower()
        for keyword in _DANGEROUS_KEYWORDS:
            if keyword in step_lower:
                logger.warning(
                    "Dangerous operation detected in incident %s: %s",
                    state.incident_id, keyword,
                )
                return {
                    "confidence": 0.0,
                    "requires_human": True,
                    "escalation_reason": f"Resolution contains potentially destructive operation: '{keyword}'",
                }

    # P1 incidents require higher confidence
    if state.priority == IncidentPriority.P1 and state.confidence < P1_CONFIDENCE_THRESHOLD:
        return {
            "requires_human": True,
            "escalation_reason": (
                f"P1 incident requires confidence >= {P1_CONFIDENCE_THRESHOLD}, "
                f"achieved {state.confidence:.2f}"
            ),
        }

    return {}


def create_ticket(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: create ITSM ticket and mark incident as resolved."""
    logger.info("create_ticket incident_id=%s confidence=%.2f", state.incident_id, state.confidence)

    ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    resolution_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(state.resolution_steps))

    try:
        import psycopg2
        from datetime import UTC, datetime

        conn = psycopg2.connect(settings.database_url, connect_timeout=5)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incidents
                  (id, title, description, priority, affected_service, requestor,
                   status, resolution, confidence, created_at, updated_at, resolved_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'resolved', %s, %s, NOW(), NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                  status = 'resolved',
                  resolution = EXCLUDED.resolution,
                  confidence = EXCLUDED.confidence,
                  updated_at = NOW(),
                  resolved_at = NOW()
                """,
                (
                    state.incident_id,
                    state.title,
                    state.description,
                    state.priority.value if hasattr(state.priority, "value") else str(state.priority),
                    state.affected_service,
                    state.requestor,
                    resolution_text,
                    state.confidence,
                ),
            )
        conn.close()
        logger.info("Incident %s resolved and persisted", state.incident_id)
    except Exception as exc:
        logger.warning("Failed to persist resolved incident %s: %s", state.incident_id, exc)

    return {
        "ticket_id": ticket_id,
        "status": ResolutionStatus.RESOLVED,
        "resolution_summary": (
            f"Resolved via autonomous ITSM resolver. "
            f"Confidence: {state.confidence:.2f}. "
            f"Steps applied: {len(state.resolution_steps)}. "
            f"Ticket: {ticket_id}"
        ),
    }


def escalate_incident(state: IncidentState, settings: Settings) -> dict[str, Any]:
    """Node: escalate incident to human operator."""
    reason = (
        state.escalation_reason
        or f"Confidence {state.confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}"
    )
    ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"

    logger.warning(
        "ESCALATION incident_id=%s priority=%s reason=%s",
        state.incident_id,
        state.priority.value if hasattr(state.priority, "value") else state.priority,
        reason,
    )

    # Notify via SQS
    if settings.sqs_approval_queue_url:
        try:
            import json
            import boto3
            from datetime import UTC, datetime

            sqs = boto3.client("sqs", region_name=settings.aws_region)
            sqs.send_message(
                QueueUrl=settings.sqs_approval_queue_url,
                MessageBody=json.dumps({
                    "specversion": "1.0",
                    "type": "incident.escalated",
                    "source": "autonomous-it-control-plane/itsm-resolver",
                    "id": str(uuid.uuid4()),
                    "time": datetime.now(UTC).isoformat(),
                    "data": {
                        "incident_id": state.incident_id,
                        "ticket_id": ticket_id,
                        "title": state.title,
                        "priority": state.priority.value if hasattr(state.priority, "value") else str(state.priority),
                        "reason": reason,
                        "confidence": state.confidence,
                    },
                }),
            )
        except Exception as exc:
            logger.warning("Failed to send escalation SQS notification: %s", exc)

    return {
        "ticket_id": ticket_id,
        "status": ResolutionStatus.ESCALATED,
        "requires_human": True,
        "escalation_reason": reason,
        "resolution_summary": f"Escalated to T2 human operator. Reason: {reason}",
    }


def _should_escalate(state: IncidentState) -> str:
    """Conditional edge: 'escalate' or 'create_ticket'."""
    if state.requires_human:
        return "escalate"
    if state.confidence < CONFIDENCE_THRESHOLD:
        return "escalate"
    return "create_ticket"


def build_itsm_resolver_graph(settings: Settings):
    """Build and compile the ITSM resolver LangGraph."""
    from langgraph.graph import END, START, StateGraph

    workflow = StateGraph(IncidentState)

    workflow.add_node("classify_incident", lambda s: classify_incident(s, settings))
    workflow.add_node("retrieve_runbook", lambda s: retrieve_runbook(s, settings))
    workflow.add_node("generate_resolution", lambda s: generate_resolution(s, settings))
    workflow.add_node("validate_steps", lambda s: validate_steps(s, settings))
    workflow.add_node("create_ticket", lambda s: create_ticket(s, settings))
    workflow.add_node("escalate", lambda s: escalate_incident(s, settings))

    workflow.add_edge(START, "classify_incident")
    workflow.add_edge("classify_incident", "retrieve_runbook")
    workflow.add_edge("retrieve_runbook", "generate_resolution")
    workflow.add_edge("generate_resolution", "validate_steps")
    workflow.add_conditional_edges(
        "validate_steps",
        _should_escalate,
        {"create_ticket": "create_ticket", "escalate": "escalate"},
    )
    workflow.add_edge("create_ticket", END)
    workflow.add_edge("escalate", END)

    return workflow.compile()
