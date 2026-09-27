"""Query rewriter — expands or reformulates queries for better retrieval."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_STOP_WORDS = frozenset([
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "can", "could", "may", "might", "shall", "must", "it", "its", "this",
    "that", "these", "those", "with", "from", "for", "to", "of", "in", "on",
])


def expand_query(query: str) -> str:
    """Expand query with synonyms and related IT operations terms."""
    expansions: dict[str, list[str]] = {
        "down": ["unavailable", "unreachable", "failed", "error"],
        "slow": ["latency", "timeout", "performance degradation"],
        "crash": ["exception", "error", "failure", "core dump"],
        "deploy": ["deployment", "release", "rollout"],
        "rollback": ["revert", "undo", "restore previous"],
        "disk full": ["storage exhausted", "ENOSPC", "no space left"],
        "oom": ["out of memory", "memory exhausted", "memory limit"],
    }

    expanded = query
    query_lower = query.lower()
    for term, synonyms in expansions.items():
        if term in query_lower:
            expanded += " " + " ".join(synonyms)
    return expanded.strip()


def keyword_extract(query: str) -> list[str]:
    """Extract meaningful keywords from a query for BM25 search."""
    tokens = re.findall(r"\b\w+\b", query.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]


def rewrite_query(query: str, llm_fn: Any | None = None) -> str:
    """Rewrite query for improved retrieval.

    If llm_fn is provided, uses LLM for semantic rewriting.
    Otherwise applies rule-based expansion.
    """
    if llm_fn is not None:
        try:
            prompt = (
                f"Rewrite this IT operations search query to be more specific "
                f"and include relevant technical terms. "
                f"Return only the rewritten query, nothing else.\n\nQuery: {query}"
            )
            return llm_fn(prompt).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM query rewrite failed: %s — using rule-based fallback", exc)

    return expand_query(query)
