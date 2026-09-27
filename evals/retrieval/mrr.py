"""Mean Reciprocal Rank (MRR) evaluation for RAG retrieval."""
from __future__ import annotations

from typing import Any


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Compute reciprocal rank for a single query.

    Returns 1/rank of the first relevant document, or 0 if none found.
    """
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    queries: list[dict[str, Any]],
    retrieve_fn: Any,
    top_k: int = 10,
) -> float:
    """Compute MRR over a set of queries.

    Args:
        queries: List of {query, relevant_ids} dicts
        retrieve_fn: Callable(query: str, top_k: int) → list of {id, ...}
        top_k: Number of results to retrieve per query

    Returns:
        MRR score between 0.0 and 1.0
    """
    if not queries:
        return 0.0

    rr_scores: list[float] = []
    for query_item in queries:
        query = query_item["query"]
        relevant_ids = set(query_item.get("relevant_ids", []))

        if not relevant_ids:
            continue

        results = retrieve_fn(query, top_k=top_k)
        retrieved_ids = [str(r.get("id", "")) for r in results]

        rr = reciprocal_rank(retrieved_ids, relevant_ids)
        rr_scores.append(rr)

    return sum(rr_scores) / len(rr_scores) if rr_scores else 0.0
