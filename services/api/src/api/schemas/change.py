"""Change management request and response schemas."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChangeTier(str, Enum):
    """Change tier classification.

    T1: Low-risk, automated. Executes without human approval.
    T2: Standard change. Requires human approval (30-minute timeout).
    T3: Emergency change. Expedited approval (15-minute timeout).
    """

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class ChangeRequest(BaseModel):
    """Request body for submitting a change."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Short, descriptive title for the change",
        examples=["Update nginx TLS certificate on prod-web-01"],
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Detailed description of the change, including scope and impact",
        examples=["Replace expiring wildcard TLS cert with renewed certificate. No downtime expected."],
    )
    tier: ChangeTier = Field(
        default=ChangeTier.T2,
        description="Change tier: T1=autonomous, T2=human approval required, T3=emergency expedited",
    )
    requestor: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Requestor identifier (email or user ID)",
        examples=["ops@company.com"],
    )


class ChangeResponse(BaseModel):
    """Response body after submitting a change."""

    id: str = Field(..., description="Unique change ID (UUID)")
    title: str
    description: str
    tier: ChangeTier
    requestor: str
    status: str = Field(..., description="Initial status: 'pending' or 'pending_approval'")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    message: str = Field(..., description="Human-readable status message")


class ChangeStatusResponse(BaseModel):
    """Response body for change status query."""

    id: str
    status: str = Field(
        ...,
        description="One of: pending, pending_approval, approved, rejected, executing, executed, rolled_back, failed",
    )
    tier: str
    title: str
    requestor: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
