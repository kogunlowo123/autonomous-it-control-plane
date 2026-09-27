"""Recursive character text splitter."""
from __future__ import annotations

from typing import Any

from rag_core.chunking.base import BaseChunker, Chunk


class RecursiveChunker(BaseChunker):
    """Splits text recursively on a hierarchy of separators."""

    _SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        raw_chunks = self._split(text)
        return [
            Chunk(content=c, metadata=metadata or {}, chunk_index=i)
            for i, c in enumerate(raw_chunks)
        ]

    def _split(self, text: str) -> list[str]:
        if len(text) <= self._chunk_size:
            return [text]

        for sep in self._SEPARATORS:
            if sep and sep in text:
                parts = text.split(sep)
                chunks: list[str] = []
                current = ""
                for part in parts:
                    candidate = (current + sep + part).strip() if current else part.strip()
                    if len(candidate) <= self._chunk_size:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = part.strip()
                if current:
                    chunks.append(current)

                # Add overlap
                result: list[str] = []
                for i, chunk in enumerate(chunks):
                    if i > 0 and self._chunk_overlap > 0:
                        prev_words = chunks[i - 1].split()[-self._chunk_overlap // 5:]
                        chunk = " ".join(prev_words) + " " + chunk
                    result.append(chunk)
                return result

        # No separator found — hard split
        return [
            text[i:i + self._chunk_size]
            for i in range(0, len(text), self._chunk_size - self._chunk_overlap)
        ]
