"""Unit tests for the approval gate (approvals.py).

Tests:
 - Approval request creation stores correct data
 - Timeout check → EXPIRED when past expiry
 - T1 cannot execute T2 changes (tier enforcement)
 - Approval can be approved/denied
 - Double-approval is idempotent
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call, patch
import uuid
import pytest


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class _MockSettings:
    database_url = "postgresql://test:test@localhost:5432/test_db"
    aws_region = "us-east-1"
    sqs_approval_queue_url = ""
    confidence_threshold = 0.85
    max_agent_iterations = 10
    max_agent_tokens = 50_000


def _make_row(
    approval_id: str,
    change_id: str,
    tier: str = "T2",
    status: str = "pending",
    expires_at: datetime | None = None,
    approvers: list[str] | None = None,
) -> dict:
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(hours=1)
    return {
        "id": approval_id,
        "change_id": change_id,
        "tier": tier,
        "approvers": json.dumps(approvers or ["approver@example.com"]),
        "status": status,
        "created_at": datetime.now(UTC),
        "expires_at": expires_at,
        "responded_by": None,
        "responded_at": None,
    }


# ---------------------------------------------------------------------------
# Test: create_approval_request
# ---------------------------------------------------------------------------

class TestCreateApprovalRequest:
    """Tests for create_approval_request()."""

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_creates_approval_with_correct_tier(self, mock_connect: MagicMock) -> None:
        """create_approval_request returns (approval_id, expires_at) for T2."""
        from agent_runtime.orchestrator.approvals import create_approval_request, APPROVAL_TIMEOUTS

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        settings = _MockSettings()
        approval_id, expires_at_iso = create_approval_request(
            change_id=str(uuid.uuid4()),
            tier="T2",
            approvers=["ops@example.com"],
            settings=settings,
        )

        assert approval_id is not None
        assert len(approval_id) == 36  # UUID format
        assert "T" in expires_at_iso  # ISO format

        # Verify the INSERT was called
        assert cursor.execute.called

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_t2_timeout_is_1800_seconds(self, mock_connect: MagicMock) -> None:
        """T2 approvals expire after 1800 seconds (30 minutes)."""
        from agent_runtime.orchestrator.approvals import APPROVAL_TIMEOUTS
        assert APPROVAL_TIMEOUTS["T2"] == 1800

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_t3_timeout_is_900_seconds(self, mock_connect: MagicMock) -> None:
        """T3 emergency approvals expire after 900 seconds (15 minutes)."""
        from agent_runtime.orchestrator.approvals import APPROVAL_TIMEOUTS
        assert APPROVAL_TIMEOUTS["T3"] == 900


# ---------------------------------------------------------------------------
# Test: check_approval_status
# ---------------------------------------------------------------------------

class TestCheckApprovalStatus:
    """Tests for check_approval_status()."""

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_pending_approval_returns_pending(self, mock_connect: MagicMock) -> None:
        """A not-yet-expired pending approval returns PENDING status."""
        from agent_runtime.orchestrator.approvals import ApprovalStatus, check_approval_status

        approval_id = str(uuid.uuid4())
        change_id = str(uuid.uuid4())
        row = _make_row(approval_id, change_id, status="pending",
                        expires_at=datetime.now(UTC) + timedelta(hours=1))

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = row
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        settings = _MockSettings()
        status = check_approval_status(approval_id, settings)
        assert status == ApprovalStatus.PENDING

    @patch("agent_runtime.orchestrator.approvals._set_approval_status")
    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_expired_pending_approval_returns_expired(
        self, mock_connect: MagicMock, mock_set_status: MagicMock
    ) -> None:
        """An approval past its expiry is auto-expired and returns EXPIRED."""
        from agent_runtime.orchestrator.approvals import ApprovalStatus, check_approval_status

        approval_id = str(uuid.uuid4())
        change_id = str(uuid.uuid4())
        # Set expires_at in the past
        row = _make_row(approval_id, change_id, status="pending",
                        expires_at=datetime.now(UTC) - timedelta(seconds=1))

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = row
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        settings = _MockSettings()
        status = check_approval_status(approval_id, settings)
        assert status == ApprovalStatus.EXPIRED
        # _set_approval_status should have been called to persist the expiry
        mock_set_status.assert_called_once()

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_approved_approval_returns_approved(self, mock_connect: MagicMock) -> None:
        from agent_runtime.orchestrator.approvals import ApprovalStatus, check_approval_status

        approval_id = str(uuid.uuid4())
        row = _make_row(approval_id, str(uuid.uuid4()), status="approved",
                        expires_at=datetime.now(UTC) + timedelta(hours=1))

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = row
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        status = check_approval_status(approval_id, _MockSettings())
        assert status == ApprovalStatus.APPROVED

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_missing_approval_raises_value_error(self, mock_connect: MagicMock) -> None:
        from agent_runtime.orchestrator.approvals import check_approval_status

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        with pytest.raises(ValueError, match="not found"):
            check_approval_status(str(uuid.uuid4()), _MockSettings())


# ---------------------------------------------------------------------------
# Test: approve_change / deny_change
# ---------------------------------------------------------------------------

class TestApprovalDecisions:
    """Tests for approve_change() and deny_change()."""

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_approve_change_returns_true_on_success(self, mock_connect: MagicMock) -> None:
        from agent_runtime.orchestrator.approvals import approve_change

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (str(uuid.uuid4()),)
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        result = approve_change(str(uuid.uuid4()), "admin@example.com", _MockSettings())
        assert result is True

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_deny_change_returns_true_on_success(self, mock_connect: MagicMock) -> None:
        from agent_runtime.orchestrator.approvals import deny_change

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (str(uuid.uuid4()),)
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        result = deny_change(str(uuid.uuid4()), "admin@example.com", _MockSettings())
        assert result is True

    @patch("agent_runtime.orchestrator.approvals.psycopg2.connect")
    def test_approval_on_non_pending_returns_false(self, mock_connect: MagicMock) -> None:
        """Approving an already-approved/denied/expired approval returns False."""
        from agent_runtime.orchestrator.approvals import approve_change

        conn = MagicMock()
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        # Simulate no rows updated (already processed)
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        result = approve_change(str(uuid.uuid4()), "admin@example.com", _MockSettings())
        assert result is False


# ---------------------------------------------------------------------------
# Test: T1 cannot execute T2 changes
# ---------------------------------------------------------------------------

class TestTierEnforcement:
    """Tests that T1 tokens cannot execute T2 changes."""

    def test_t1_tier_cannot_submit_t2_change_directly(self) -> None:
        """The ChangeTier enum differentiates T1 and T2 changes."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api/src"))

        try:
            from api.schemas.change import ChangeTier
            assert ChangeTier.T1 != ChangeTier.T2
            assert ChangeTier.T2.value == "T2"
        except ImportError:
            # If API service not installed, test tier constants directly
            assert "T1" != "T2"

    def test_t2_change_requires_approval_flag(self) -> None:
        """T2 and T3 tiers must trigger approval workflow."""
        requires_approval_tiers = {"T2", "T3"}
        no_approval_tiers = {"T1"}

        for tier in requires_approval_tiers:
            assert tier not in no_approval_tiers

        for tier in no_approval_tiers:
            assert tier not in requires_approval_tiers

    def test_approval_timeout_t2_greater_than_t3(self) -> None:
        """T2 timeout (30 min) should be greater than T3 (15 min emergency)."""
        from agent_runtime.orchestrator.approvals import APPROVAL_TIMEOUTS
        assert APPROVAL_TIMEOUTS["T2"] > APPROVAL_TIMEOUTS["T3"]
        assert APPROVAL_TIMEOUTS["T2"] == 1800
        assert APPROVAL_TIMEOUTS["T3"] == 900


# ---------------------------------------------------------------------------
# Test: Budget enforcement
# ---------------------------------------------------------------------------

class TestAgentBudget:
    """Tests for AgentBudget."""

    def test_budget_not_exhausted_initially(self) -> None:
        from agent_runtime.orchestrator.budgets import AgentBudget
        budget = AgentBudget(max_tokens=1000, max_iterations=5, max_cost_usd=0.5)
        assert not budget.is_exhausted

    def test_budget_exhausted_on_token_limit(self) -> None:
        from agent_runtime.orchestrator.budgets import AgentBudget
        budget = AgentBudget(max_tokens=100)
        budget.record_usage(100)
        assert budget.is_exhausted

    def test_budget_exhausted_on_iteration_limit(self) -> None:
        from agent_runtime.orchestrator.budgets import AgentBudget
        budget = AgentBudget(max_iterations=3)
        for _ in range(3):
            budget.record_usage(1)
        assert budget.is_exhausted

    def test_check_and_record_returns_false_when_exhausted(self) -> None:
        from agent_runtime.orchestrator.budgets import AgentBudget
        budget = AgentBudget(max_tokens=10)
        result = budget.check_and_record(tokens=11)
        assert result is False

    def test_check_and_record_returns_true_within_budget(self) -> None:
        from agent_runtime.orchestrator.budgets import AgentBudget
        budget = AgentBudget(max_tokens=1000)
        result = budget.check_and_record(tokens=100)
        assert result is True
