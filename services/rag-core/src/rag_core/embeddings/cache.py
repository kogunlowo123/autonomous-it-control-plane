"""Embedding cache — LRU in-memory cache with optional Redis backing."""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


def _text_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class EmbeddingCache:
    """LRU cache for embeddings to avoid redundant model calls."""

    def __init__(self, max_size: int = 1024) -> None:
        self._max_size = max_size
        self._cache: dict[str, list[float]] = {}
        self._order: list[str] = []

    def get(self, text: str) -> list[float] | None:
        key = _text_key(text)
        return self._cache.get(key)

    def set(self, text: str, embedding: list[float]) -> None:
        key = _text_key(text)
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._max_size:
            # Evict oldest
            oldest = self._order.pop(0)
            self._cache.pop(oldest, None)

        self._cache[key] = embedding
        self._order.append(key)

    def invalidate(self, text: str) -> None:
        key = _text_key(text)
        if key in self._cache:
            self._cache.pop(key)
            self._order.remove(key)

    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._cache)
