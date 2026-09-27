"""LangGraph state definitions for IT control plane agents."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class IncidentPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ResolutionStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED = "failed"


class IncidentState(BaseModel):
    """State for the ITSM resolver LangGraph agent."""

    # Input
    incident_id: str = Field(..., description="Unique incident ID")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")
    priority: IncidentPriority = Field(default=IncidentPriority.P3)
    affected_service: str = Field(default="")
    requestor: str = Field(default="")

    # Processing
    classification: Optional[str] = Field(default=None)
    retrieved_runbooks: list[dict[str, Any]] = Field(default_factory=list)
    resolution_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0)

    # Output
    ticket_id: Optional[str] = Field(default=None)
    status: ResolutionStatus = Field(default=ResolutionStatus.OPEN)
    resolution_summary: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    # Escalation
    requires_human: bool = Field(default=False)
    escalation_reason: Optional[str] = Field(default=None)

    # Metadata
    iterations: int = Field(default=0)
    messages: list[dict[str, Any]] = Field(default_factory=list)


class ChangeState(BaseModel):
    """State for the change executor LangGraph agent."""

    change_id: str
    title: str
    description: str
    tier: str
    requestor: str

    # Approval
    approval_id: Optional[str] = Field(default=None)
    approval_status: Optional[str] = Field(default=None)
    approved_by: Optional[str] = Field(default=None)

    # Execution
    execution_plan: list[str] = Field(default_factory=list)
    executed_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)

    # Status
    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)
    iterations: int = Field(default=0)
