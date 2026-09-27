"""Auto tagger — infers topic tags from chunk content using keyword matching."""
from __future__ import annotations

import re
from typing import Any

_TAG_RULES: dict[str, list[str]] = {
    "database": ["postgres", "postgresql", "mysql", "aurora", "rds", "sql", "pgvector"],
    "kubernetes": ["kubernetes", "k8s", "pod", "deployment", "kubectl", "helm", "namespace"],
    "networking": ["vpc", "subnet", "security group", "nacl", "route table", "load balancer"],
    "security": ["iam", "role", "policy", "kms", "encryption", "tls", "certificate", "secret"],
    "incident": ["incident", "outage", "p1", "p2", "sev1", "sev2", "on-call", "escalation"],
    "change": ["change", "deployment", "rollout", "rollback", "maintenance", "upgrade"],
    "monitoring": ["cloudwatch", "grafana", "alert", "alarm", "metric", "dashboard"],
    "storage": ["s3", "bucket", "efs", "ebs", "volume", "backup"],
}


def auto_tag(content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect topic tags from content and return updated metadata."""
    content_lower = content.lower()
    tags: list[str] = []

    for tag, keywords in _TAG_RULES.items():
        if any(kw in content_lower for kw in keywords):
            tags.append(tag)

    return {**(metadata or {}), "auto_tags": tags}
