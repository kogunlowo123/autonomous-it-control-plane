"""Budget enforcer — prevents tenant LLM spend from exceeding limits."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cost per 1K tokens (USD) — approximate for Claude Sonnet on Bedrock
_COST_PER_1K_TOKENS = 0.003


class BudgetExceededError(Exception):
    pass


class BudgetEnforcer:
    """Enforces per-tenant LLM cost budgets."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._daily_limit = config.get("daily_limit_usd_per_tenant", 100.0)
        self._max_tokens = config.get("default_max_tokens_per_request", 4096)
        self._alert_threshold = config.get("alert_threshold_pct", 80) / 100
        self._usage: dict[str, float] = {}  # tenant_id → today's spend USD

    def check(self, tenant_id: str, estimated_tokens: int) -> None:
        """Raise BudgetExceededError if this request would exceed the daily limit."""
        estimated_cost = (estimated_tokens / 1000) * _COST_PER_1K_TOKENS
        current = self._usage.get(tenant_id, 0.0)

        if current + estimated_cost > self._daily_limit:
            raise BudgetExceededError(
                f"Tenant {tenant_id} daily budget ${self._daily_limit:.2f} would be exceeded "
                f"(current=${current:.4f}, estimated=${estimated_cost:.4f})"
            )

        if current + estimated_cost > self._daily_limit * self._alert_threshold:
            logger.warning(
                "Tenant %s budget alert: %.1f%% of daily limit consumed",
                tenant_id,
                (current + estimated_cost) / self._daily_limit * 100,
            )

    def record_usage(self, tenant_id: str, tokens_used: int) -> None:
        """Record actual token usage for a tenant."""
        cost = (tokens_used / 1000) * _COST_PER_1K_TOKENS
        self._usage[tenant_id] = self._usage.get(tenant_id, 0.0) + cost

    def get_usage(self, tenant_id: str) -> dict[str, float]:
        """Return current usage stats for a tenant."""
        spend = self._usage.get(tenant_id, 0.0)
        return {
            "spend_usd": spend,
            "limit_usd": self._daily_limit,
            "remaining_usd": max(0.0, self._daily_limit - spend),
        }
