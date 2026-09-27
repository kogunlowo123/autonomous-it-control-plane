"""Abstract base for vector stores."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    """Base interface for vector stores."""

    @abstractmethod
    def upsert(self, doc_id: str, content: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        """Insert or update a document with its embedding."""

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        """Return top_k nearest neighbours for the query embedding."""

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove a document by ID."""
