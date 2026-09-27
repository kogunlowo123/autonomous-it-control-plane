"""Recall@K evaluation for RAG retrieval."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Compute Recall@K.

    Args:
        retrieved_ids: Ordered list of retrieved document IDs (top K)
        relevant_ids: Set of ground-truth relevant document IDs
        k: Cut-off rank

    Returns:
        Recall@K score between 0.0 and 1.0
    """
    if not relevant_ids:
        return 1.0  # No relevant docs → trivially 100% recall

    top_k = set(retrieved_ids[:k])
    hits = top_k & relevant_ids
    return len(hits) / len(relevant_ids)


def evaluate_retrieval(
    queries: list[dict[str, Any]],
    retrieve_fn: Any,
    k_values: list[int] | None = None,
) -> dict[str, float]:
    """Evaluate retrieval over a set of queries.

    Args:
        queries: List of {query, relevant_ids} dicts
        retrieve_fn: Callable(query: str, top_k: int) → list of {id, ...}
        k_values: K values to evaluate (default [1, 3, 5, 10])

    Returns:
        Dict of {recall@k: avg_score}
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    max_k = max(k_values)
    scores: dict[int, list[float]] = {k: [] for k in k_values}

    for query_item in queries:
        query = query_item["query"]
        relevant_ids = set(query_item.get("relevant_ids", []))

        results = retrieve_fn(query, top_k=max_k)
        retrieved_ids = [str(r.get("id", "")) for r in results]

        for k in k_values:
            score = recall_at_k(retrieved_ids, relevant_ids, k)
            scores[k].append(score)

    return {
        f"recall@{k}": sum(v) / len(v) if v else 0.0
        for k, v in scores.items()
    }


def load_golden_dataset(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL golden dataset."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
