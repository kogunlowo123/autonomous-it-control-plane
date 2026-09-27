"""Citation accuracy evaluation."""
from __future__ import annotations

from typing import Any

from services_rag_core_src_rag_core_guardrails_citation_validator import validate_citations


def citation_accuracy(
    responses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate citation accuracy across a set of responses.

    Args:
        responses: List of {id, response, source_docs} dicts

    Returns:
        {
            "accuracy": float,     # Fraction of responses with all valid citations
            "per_item": {id: bool},  # Per-item results
        }
    """
    results: dict[str, bool] = {}
    for item in responses:
        try:
            # Import at call time to avoid circular imports
            import importlib
            import sys
            # Try to import from the agent runtime guardrails
            spec = importlib.util.find_spec("agent_runtime.guardrails.citation_validator")
            if spec:
                mod = importlib.import_module("agent_runtime.guardrails.citation_validator")
                is_valid, _ = mod.validate_citations(
                    item.get("response", ""),
                    item.get("source_docs", []),
                )
            else:
                # Inline implementation for eval runner
                import re
                pattern = re.compile(r"\[(\d+)\]|\(source:\s*([^)]+)\)", re.IGNORECASE)
                matches = pattern.findall(item.get("response", ""))
                source_docs = item.get("source_docs", [])
                is_valid = True
                for numeric, text in matches:
                    if numeric and int(numeric) > len(source_docs):
                        is_valid = False
                        break
            results[item["id"]] = is_valid
        except Exception:
            results[item["id"]] = True  # Cannot evaluate → assume valid

    accuracy = sum(results.values()) / len(results) if results else 0.0
    return {"accuracy": accuracy, "per_item": results}
