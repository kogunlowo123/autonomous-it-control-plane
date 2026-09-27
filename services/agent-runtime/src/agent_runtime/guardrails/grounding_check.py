"""Grounding check — verifies agent outputs are supported by retrieved sources."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def check_grounding(
    response: str,
    retrieved_docs: list[dict[str, Any]],
    min_docs: int = 1,
) -> tuple[bool, float, str]:
    """Check if an agent response is grounded in retrieved documents.

    Uses token-overlap heuristic. For production, replace with NLI-based
    grounding check (e.g., cross-encoder reranker).

    Returns:
        (is_grounded, confidence_score, explanation)
    """
    if not retrieved_docs:
        return False, 0.0, "No source documents available for grounding check"

    if not response or not response.strip():
        return False, 0.0, "Empty response cannot be grounded"

    # Compute token overlap between response and all source docs
    response_tokens = set(response.lower().split())
    if not response_tokens:
        return False, 0.0, "Response contains no tokens"

    total_overlap = 0
    for doc in retrieved_docs:
        content = doc.get("content", "")
        if not content:
            continue
        doc_tokens = set(content.lower().split())
        overlap = len(response_tokens & doc_tokens)
        total_overlap += overlap

    grounding_score = min(1.0, total_overlap / len(response_tokens) * 1.5)

    if grounding_score < 0.05:
        return (
            False,
            grounding_score,
            f"Response has very low overlap with source documents (score={grounding_score:.3f})",
        )

    return (
        True,
        grounding_score,
        f"Response is grounded in {len(retrieved_docs)} source document(s) (score={grounding_score:.3f})",
    )
