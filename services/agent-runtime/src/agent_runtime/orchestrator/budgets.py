"""Agent budget enforcement — limits token usage, iterations, and cost per run."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentBudget:
    """Per-run budget tracker for an agent invocation."""

    max_tokens: int = 50_000
    max_iterations: int = 10
    max_cost_usd: float = 1.0

    tokens_used: int = field(default=0, init=False)
    iterations: int = field(default=0, init=False)
    cost_usd: float = field(default=0.0, init=False)

    def record_usage(self, tokens: int, cost_usd: float = 0.0) -> None:
        """Record token and cost usage for one LLM call."""
        self.tokens_used += tokens
        self.cost_usd += cost_usd
        self.iterations += 1

    @property
    def is_exhausted(self) -> bool:
        """True when any budget limit has been reached."""
        return (
            self.tokens_used >= self.max_tokens
            or self.iterations >= self.max_iterations
            or self.cost_usd >= self.max_cost_usd
        )

    def check_and_record(self, tokens: int = 0, cost_usd: float = 0.0) -> bool:
        """Record usage and return False (exhausted) or True (budget available)."""
        self.record_usage(tokens, cost_usd)
        if self.is_exhausted:
            logger.warning(
                "Budget exhausted: tokens=%d/%d iter=%d/%d cost=$%.4f/$%.4f",
                self.tokens_used, self.max_tokens,
                self.iterations, self.max_iterations,
                self.cost_usd, self.max_cost_usd,
            )
            return False
        return True

    def summary(self) -> dict[str, float | int]:
        return {
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "cost_usd": round(self.cost_usd, 6),
            "max_cost_usd": self.max_cost_usd,
        }
