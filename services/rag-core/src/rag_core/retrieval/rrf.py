"""Reciprocal Rank Fusion for combining multiple retrieval result lists."""
from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    result_lists: list[list[dict[str, Any]]],
    k: int = 60,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Combine multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    RRF score = sum(1 / (k + rank)) for each result list.
    Higher scores indicate better-ranked documents across all lists.

    Args:
        result_lists: List of ranked result lists (each is [{id, content, ...}])
        k: RRF constant (higher k reduces impact of individual rankings)
        top_n: Number of top results to return (None = all)

    Returns:
        Merged and re-ranked list of documents.
    """
    scores: dict[str, float] = {}
    doc_store: dict[str, dict[str, Any]] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list, start=1):
            doc_id = str(doc.get("id", f"doc_{rank}"))
            rrf_score = 1.0 / (k + rank)
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score
            if doc_id not in doc_store:
                doc_store[doc_id] = doc

    # Sort by RRF score descending
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)

    results = []
    for doc_id in sorted_ids:
        doc = dict(doc_store[doc_id])
        doc["rrf_score"] = scores[doc_id]
        results.append(doc)

    if top_n is not None:
        return results[:top_n]
    return results
