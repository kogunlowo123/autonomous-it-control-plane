"""Abstract chunker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    """A single text chunk with metadata."""

    content: str
    metadata: dict[str, Any]
    chunk_index: int = 0
    parent_id: str | None = None


class BaseChunker(ABC):
    """Base class for all text chunkers."""

    @abstractmethod
    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text into chunks."""
