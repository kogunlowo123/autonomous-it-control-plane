"""Faithfulness evaluation — measures how well generated responses are supported by sources."""
from __future__ import annotations

from typing import Any


def faithfulness_score(
    response: str,
    source_docs: list[dict[str, Any]],
    n_gram_size: int = 3,
) -> float:
    """Estimate faithfulness using n-gram overlap between response and sources.

    A score of 1.0 means all response n-grams appear in source documents.
    A score of 0.0 means no overlap (likely hallucination).

    Args:
        response: Generated response text
        source_docs: List of {content: str} source documents
        n_gram_size: N-gram size for overlap calculation

    Returns:
        Faithfulness score 0.0-1.0
    """
    if not response.strip():
        return 0.0
    if not source_docs:
        return 0.0

    # Build response n-grams
    response_tokens = response.lower().split()
    response_ngrams = {
        tuple(response_tokens[i:i + n_gram_size])
        for i in range(len(response_tokens) - n_gram_size + 1)
    }

    if not response_ngrams:
        return 0.0

    # Build source n-grams
    source_ngrams: set[tuple[str, ...]] = set()
    for doc in source_docs:
        content = doc.get("content", "")
        tokens = content.lower().split()
        for i in range(len(tokens) - n_gram_size + 1):
            source_ngrams.add(tuple(tokens[i:i + n_gram_size]))

    supported = response_ngrams & source_ngrams
    return len(supported) / len(response_ngrams)


def batch_faithfulness(
    pairs: list[dict[str, Any]],
    n_gram_size: int = 3,
) -> dict[str, float]:
    """Compute faithfulness scores for a batch of (response, sources) pairs.

    Args:
        pairs: List of {id, response, source_docs} dicts
        n_gram_size: N-gram size

    Returns:
        {id: score, ..., "mean": mean_score}
    """
    scores: dict[str, float] = {}
    for pair in pairs:
        score = faithfulness_score(
            pair.get("response", ""),
            pair.get("source_docs", []),
            n_gram_size=n_gram_size,
        )
        scores[pair["id"]] = score

    if scores:
        scores["mean"] = sum(scores.values()) / len(scores)
    return scores
