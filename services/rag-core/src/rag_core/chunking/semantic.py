"""Semantic chunker — splits at semantic boundaries using sentence embeddings."""
from __future__ import annotations

import logging
from typing import Any

from rag_core.chunking.base import BaseChunker, Chunk

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """Splits text at points of high semantic dissimilarity between sentences."""

    def __init__(
        self,
        breakpoint_threshold: float = 0.85,
        max_chunk_size: int = 1024,
    ) -> None:
        self._threshold = breakpoint_threshold
        self._max_chunk_size = max_chunk_size
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("BAAI/bge-base-en-v1.5")
            except ImportError:
                logger.warning("sentence-transformers not installed — using RecursiveChunker fallback")
        return self._model

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        model = self._get_model()
        if model is None:
            # Fallback to paragraph split
            from rag_core.chunking.recursive import RecursiveChunker
            return RecursiveChunker(chunk_size=self._max_chunk_size).chunk(text, metadata)

        sentences = [s.strip() for s in text.split(". ") if s.strip()]
        if not sentences:
            return []

        embeddings = model.encode(sentences, normalize_embeddings=True)

        import numpy as np
        chunks: list[Chunk] = []
        current_sentences = [sentences[0]]

        for i in range(1, len(sentences)):
            similarity = float(np.dot(embeddings[i - 1], embeddings[i]))
            if similarity < self._threshold or len(". ".join(current_sentences)) > self._max_chunk_size:
                chunks.append(Chunk(
                    content=". ".join(current_sentences),
                    metadata=metadata or {},
                    chunk_index=len(chunks),
                ))
                current_sentences = [sentences[i]]
            else:
                current_sentences.append(sentences[i])

        if current_sentences:
            chunks.append(Chunk(
                content=". ".join(current_sentences),
                metadata=metadata or {},
                chunk_index=len(chunks),
            ))

        return chunks
