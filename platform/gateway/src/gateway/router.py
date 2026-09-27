"""LLM Gateway router — routes requests to providers with budget enforcement."""
from __future__ import annotations

import logging
from typing import Any

import yaml

from gateway.audit_log import AuditLog
from gateway.budget_enforcer import BudgetEnforcer
from gateway.providers.bedrock import BedrockProvider

logger = logging.getLogger(__name__)

_CONFIG_PATH = "config.yaml"
_ROUTING_PATH = "routing.yaml"


class GatewayRouter:
    """Routes LLM inference requests to configured providers."""

    def __init__(self, config_path: str = _CONFIG_PATH, routing_path: str = _ROUTING_PATH) -> None:
        with open(config_path) as f:
            self._config = yaml.safe_load(f)

        with open(routing_path) as f:
            self._routing = yaml.safe_load(f)

        self._bedrock = BedrockProvider(
            region=self._config["providers"]["bedrock"]["region"],
            default_model=self._config["providers"]["bedrock"]["default_model"],
        )
        self._budget = BudgetEnforcer(self._config["budget"])
        self._audit = AuditLog()

    def route(
        self,
        path: str,
        payload: dict[str, Any],
        tenant_id: str,
        agent_tier: str,
    ) -> dict[str, Any]:
        """Route an LLM request and return the response."""
        route = self._find_route(path, agent_tier)
        if route is None:
            raise PermissionError(f"No route found for path={path} tier={agent_tier}")

        # Budget check
        self._budget.check(tenant_id=tenant_id, estimated_tokens=payload.get("max_tokens", 512))

        model = route.get("model_override") or self._config["providers"]["bedrock"]["default_model"]

        self._audit.log_request(path=path, tenant_id=tenant_id, model=model)

        response = self._bedrock.invoke(model=model, payload=payload)

        self._budget.record_usage(
            tenant_id=tenant_id,
            tokens_used=response.get("usage", {}).get("total_tokens", 0),
        )
        self._audit.log_response(path=path, tenant_id=tenant_id, model=model)

        return response

    def _find_route(self, path: str, tier: str) -> dict[str, Any] | None:
        for route in self._routing.get("routes", []):
            if route["path"] == path and tier in route.get("allowed_tiers", []):
                return route
        return None
