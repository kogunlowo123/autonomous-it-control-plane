"""ACL stamper — attaches access control labels to document chunks."""
from __future__ import annotations

from typing import Any


def stamp_acl(
    metadata: dict[str, Any],
    allowed_roles: list[str] | None = None,
    tenant_id: str | None = None,
    classification: str = "internal",
) -> dict[str, Any]:
    """Attach ACL fields to chunk metadata.

    Args:
        metadata: Existing chunk metadata
        allowed_roles: List of role names allowed to read this chunk
        tenant_id: Tenant scope (None = all tenants)
        classification: Data classification label

    Returns:
        Updated metadata dict
    """
    return {
        **metadata,
        "acl": {
            "allowed_roles": allowed_roles or ["operator", "admin"],
            "tenant_id": tenant_id,
            "classification": classification,
        },
    }


def check_acl(metadata: dict[str, Any], user_roles: list[str], tenant_id: str | None) -> bool:
    """Return True if the user is allowed to access this chunk."""
    acl = metadata.get("acl", {})
    allowed_roles = acl.get("allowed_roles", [])
    chunk_tenant = acl.get("tenant_id")

    if chunk_tenant and tenant_id and chunk_tenant != tenant_id:
        return False

    return any(role in allowed_roles for role in user_roles)
