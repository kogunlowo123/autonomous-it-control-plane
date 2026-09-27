"""Corrective RAG — detects low-relevance retrievals and triggers fallback."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_RELEVANCE_THRESHOLD = 0.40


def filter_relevant(
    documents: list[dict[str, Any]],
    threshold: float = _RELEVANCE_THRESHOLD,
) -> tuple[list[dict[str, Any]], bool]:
    """Filter documents below relevance threshold.

    Returns:
        (filtered_docs, needs_fallback) where needs_fallback=True means
        fewer than 2 documents passed the threshold.
    """
    relevant = [doc for doc in documents if doc.get("score", 0.0) >= threshold]
    needs_fallback = len(relevant) < 2
    if needs_fallback:
        logger.info(
            "Corrective RAG: only %d/%d docs above threshold %.2f — fallback needed",
            len(relevant), len(documents), threshold,
        )
    return relevant, needs_fallback


def corrective_retrieve(
    query: str,
    initial_docs: list[dict[str, Any]],
    fallback_fn: Any,
    threshold: float = _RELEVANCE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Apply corrective retrieval: use initial docs if sufficient, else fall back.

    Args:
        query: Original query
        initial_docs: Results from primary retrieval
        fallback_fn: Callable(query) that returns alternative documents
        threshold: Relevance score threshold

    Returns:
        Final document list
    """
    relevant, needs_fallback = filter_relevant(initial_docs, threshold)
    if needs_fallback:
        try:
            fallback_docs = fallback_fn(query)
            return fallback_docs
        except Exception as exc:  # noqa: BLE001
            logger.warning("Corrective RAG fallback failed: %s", exc)
    return relevant
