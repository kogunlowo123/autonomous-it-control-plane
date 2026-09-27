"""Unit tests for incident resolution workflow."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest


class _MockSettings:
    database_url = "postgresql://test:test@localhost:5432/test_db"
    aws_region = "us-east-1"
    aws_bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    sqs_approval_queue_url = ""
    confidence_threshold = 0.85


class TestValidateSteps:
    """Tests for the validate_steps graph node."""

    def test_validates_safe_steps(self) -> None:
        """Safe resolution steps pass validation."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import validate_steps
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="High CPU usage",
                description="CPU at 95%",
                priority=IncidentPriority.P3,
                confidence=0.90,
                resolution_steps=["Check running processes", "Restart problematic service", "Verify CPU normalizes"],
            )
            result = validate_steps(state, _MockSettings())
            # Should not set requires_human for safe, high-confidence steps
            assert not result.get("requires_human", False)
        except ImportError:
            pytest.skip("Agent runtime not installed")

    def test_blocks_dangerous_operations(self) -> None:
        """Steps containing dangerous keywords trigger escalation."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import validate_steps
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Storage full",
                description="Disk at 100%",
                priority=IncidentPriority.P2,
                confidence=0.95,
                resolution_steps=["rm -rf /var/log/*", "Verify disk space"],
            )
            result = validate_steps(state, _MockSettings())
            assert result.get("requires_human") is True
            assert "destructive" in result.get("escalation_reason", "").lower() or "dangerous" in result.get("escalation_reason", "").lower()
        except ImportError:
            pytest.skip("Agent runtime not installed")

    def test_p1_incident_low_confidence_escalates(self) -> None:
        """P1 incidents with confidence < 0.95 are escalated."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import validate_steps
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Complete service outage",
                description="All services down",
                priority=IncidentPriority.P1,
                confidence=0.88,  # Below P1 threshold of 0.95
                resolution_steps=["Restart all pods", "Check load balancer"],
            )
            result = validate_steps(state, _MockSettings())
            assert result.get("requires_human") is True
        except ImportError:
            pytest.skip("Agent runtime not installed")

    def test_empty_steps_triggers_escalation(self) -> None:
        """No resolution steps available triggers human escalation."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import validate_steps
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Unknown error",
                description="Something went wrong",
                priority=IncidentPriority.P2,
                confidence=0.90,
                resolution_steps=[],  # No steps
            )
            result = validate_steps(state, _MockSettings())
            assert result.get("requires_human") is True
        except ImportError:
            pytest.skip("Agent runtime not installed")


class TestShouldEscalate:
    """Tests for the _should_escalate conditional edge."""

    def test_high_confidence_goes_to_create_ticket(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import _should_escalate
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Test",
                description="Test",
                priority=IncidentPriority.P3,
                confidence=0.90,
                requires_human=False,
            )
            assert _should_escalate(state) == "create_ticket"
        except ImportError:
            pytest.skip("Agent runtime not installed")

    def test_low_confidence_goes_to_escalate(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import _should_escalate, CONFIDENCE_THRESHOLD
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Test",
                description="Test",
                priority=IncidentPriority.P3,
                confidence=CONFIDENCE_THRESHOLD - 0.01,
                requires_human=False,
            )
            assert _should_escalate(state) == "escalate"
        except ImportError:
            pytest.skip("Agent runtime not installed")

    def test_requires_human_flag_escalates(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))
        try:
            from agent_runtime.orchestrator.graph import _should_escalate
            from agent_runtime.orchestrator.state import IncidentState, IncidentPriority

            state = IncidentState(
                incident_id=str(uuid.uuid4()),
                title="Test",
                description="Test",
                priority=IncidentPriority.P3,
                confidence=0.99,  # High confidence, but requires_human override
                requires_human=True,
            )
            assert _should_escalate(state) == "escalate"
        except ImportError:
            pytest.skip("Agent runtime not installed")


class TestIncidentSchemas:
    """Tests for incident Pydantic schemas."""

    def test_incident_priority_values(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api/src"))
        try:
            from api.schemas.incident import IncidentPriority
            assert IncidentPriority.P1.value == "P1"
            assert IncidentPriority.P2.value == "P2"
            assert IncidentPriority.P3.value == "P3"
            assert IncidentPriority.P4.value == "P4"
        except ImportError:
            pytest.skip("API service not installed")

    def test_incident_request_validation(self) -> None:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api/src"))
        try:
            from api.schemas.incident import IncidentRequest, IncidentPriority
            req = IncidentRequest(
                title="DB failure",
                description="PostgreSQL down on prod",
                priority=IncidentPriority.P1,
                affected_service="user-api",
                requestor="sre@example.com",
            )
            assert req.priority == IncidentPriority.P1
            assert req.affected_service == "user-api"
        except ImportError:
            pytest.skip("API service not installed")
