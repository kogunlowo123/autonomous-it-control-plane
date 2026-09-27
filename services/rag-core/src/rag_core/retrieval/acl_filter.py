"""ACL filter — removes documents the requesting user cannot access."""
from __future__ import annotations

from typing import Any

from rag_core.enrichment.acl_stamper import check_acl


def filter_by_acl(
    documents: list[dict[str, Any]],
    user_roles: list[str],
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """Filter out documents the user is not authorized to read.

    Args:
        documents: List of {id, content, metadata, score} dicts
        user_roles: Roles the requesting user holds
        tenant_id: Tenant scope of the requesting user

    Returns:
        Filtered list with unauthorized documents removed
    """
    return [
        doc for doc in documents
        if check_acl(doc.get("metadata", {}), user_roles, tenant_id)
    ]
