"""Gateway audit log — records LLM request/response metadata."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AuditLog:
    """Structured audit logging for gateway requests."""

    def log_request(
        self,
        path: str,
        tenant_id: str,
        model: str,
        extra: dict | None = None,
    ) -> None:
        """Log an incoming LLM request (never log prompt content)."""
        logger.info(
            "gateway.request path=%s tenant=%s model=%s ts=%s %s",
            path,
            tenant_id,
            model,
            datetime.now(tz=timezone.utc).isoformat(),
            extra or "",
        )

    def log_response(
        self,
        path: str,
        tenant_id: str,
        model: str,
        tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Log an LLM response (never log completion content)."""
        logger.info(
            "gateway.response path=%s tenant=%s model=%s tokens=%d latency_ms=%.1f ts=%s",
            path,
            tenant_id,
            model,
            tokens,
            latency_ms,
            datetime.now(tz=timezone.utc).isoformat(),
        )
