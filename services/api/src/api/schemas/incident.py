"""Incident management request and response schemas."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IncidentPriority(str, Enum):
    """Incident priority classification.

    P1: Critical — service down, major business impact. Auto-escalates.
    P2: High — significant degradation. High-confidence resolution required.
    P3: Medium — partial degradation, workaround available.
    P4: Low — minor issue, cosmetic or informational.
    """

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentRequest(BaseModel):
    """Request body for incident resolution."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Short incident title",
        examples=["PostgreSQL max_connections exhausted on prod-db-01"],
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Detailed incident description including symptoms and timeline",
        examples=["Connection pool exhausted at 23:45 UTC. App servers reporting PG connection errors."],
    )
    priority: IncidentPriority = Field(
        default=IncidentPriority.P3,
        description="Incident priority: P1=critical, P2=high, P3=medium, P4=low",
    )
    affected_service: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the affected service or system",
        examples=["user-api"],
    )
    requestor: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Requestor or reporter identifier (email or user ID)",
        examples=["sre@company.com"],
    )


class IncidentResponse(BaseModel):
    """Response body after submitting an incident for resolution."""

    id: str = Field(..., description="Unique incident ID (UUID)")
    title: str
    status: str = Field(..., description="Initial status: 'investigating'")
    priority: IncidentPriority
    affected_service: str
    requestor: str
    created_at: str
    message: str = Field(..., description="Human-readable status message")
    agent_dispatched: bool = Field(..., description="Whether the ITSM resolver agent was dispatched")


class IncidentRecord(BaseModel):
    """Full incident record."""

    id: str
    title: str
    description: str
    priority: str
    affected_service: str
    requestor: str
    status: str = Field(
        ...,
        description="One of: open, investigating, resolved, escalated, failed",
    )
    resolution: Optional[str] = Field(default=None, description="Resolution steps applied")
    runbook_used: Optional[str] = Field(default=None, description="Runbook ID or title used")
    confidence: Optional[float] = Field(default=None, description="Resolution confidence score 0-1")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
