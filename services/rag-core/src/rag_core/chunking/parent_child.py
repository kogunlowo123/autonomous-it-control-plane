"""Parent-child chunker — large parent chunks with small child retrieval chunks."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from rag_core.chunking.base import Chunk
from rag_core.chunking.recursive import RecursiveChunker


@dataclass
class ParentChildChunks:
    parent: Chunk
    children: list[Chunk] = field(default_factory=list)


class ParentChildChunker:
    """Creates large parent chunks and smaller child chunks for retrieval.

    Children embed the parent content for context-aware retrieval.
    """

    def __init__(
        self,
        parent_chunk_size: int = 2048,
        child_chunk_size: int = 256,
        chunk_overlap: int = 32,
    ) -> None:
        self._parent_chunker = RecursiveChunker(
            chunk_size=parent_chunk_size, chunk_overlap=chunk_overlap
        )
        self._child_chunker = RecursiveChunker(
            chunk_size=child_chunk_size, chunk_overlap=chunk_overlap // 2
        )

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ParentChildChunks]:
        parent_chunks = self._parent_chunker.chunk(text, metadata)
        result: list[ParentChildChunks] = []

        for parent in parent_chunks:
            parent_id = str(uuid.uuid4())
            parent.metadata["chunk_id"] = parent_id

            children = self._child_chunker.chunk(parent.content, parent.metadata)
            for child in children:
                child.parent_id = parent_id
                child.metadata["parent_id"] = parent_id

            result.append(ParentChildChunks(parent=parent, children=children))

        return result
