"""Agent credential broker — issues short-lived JWT tokens for agent identities."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Token TTL by tier (seconds)
TTL_BY_TIER: dict[str, int] = {
    "T1": 3600,    # 1 hour
    "T2": 1800,    # 30 minutes
    "T3": 900,     # 15 minutes
}


def issue_agent_token(
    agent_id: str,
    agent_type: str,
    tier: str,
    tenant_id: str,
    secret_key: str,
    additional_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Issue a signed JWT token for an agent.

    Returns (token, expires_at).
    """
    import jwt

    ttl = TTL_BY_TIER.get(tier, 3600)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl)

    claims: dict[str, Any] = {
        "sub": agent_id,
        "iss": "autonomous-it-control-plane",
        "aud": "itsm-api",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expires_at,
        "agent_type": agent_type,
        "tier": tier,
        "tenant_id": tenant_id,
    }

    if additional_claims:
        claims.update(additional_claims)

    token = jwt.encode(claims, secret_key, algorithm="HS256")
    logger.info(
        "Issued token agent_id=%s tier=%s expires=%s",
        agent_id, tier, expires_at.isoformat(),
    )
    return token, expires_at


def revoke_token(jti: str, reason: str) -> None:
    """Mark a token as revoked in the revocation list.

    In production, this would write to a Redis revocation list
    checked by the AuthMiddleware.
    """
    logger.warning("Token %s revoked: %s", jti, reason)
    # Production: redis_client.setex(f"revoked:{jti}", TTL_MAX, reason)
