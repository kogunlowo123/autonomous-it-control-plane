"""Local BGE embedding using sentence-transformers."""
from __future__ import annotations

import logging
from functools import lru_cache

from rag_core.embeddings.base import BaseEmbedder

logger = logging.getLogger(__name__)


class LocalBGEEmbedder(BaseEmbedder):
    """BGE embedder using sentence-transformers (CPU/GPU local inference)."""

    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer model: %s on %s", model_name, device)
        self._model = SentenceTransformer(model_name, device=device)
        self._model_name = model_name
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info("Model loaded — embedding dimension: %d", self._dimension)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query with BGE instruction prefix."""
        # BGE models benefit from instruction prefix for retrieval queries
        prefixed = f"Represent this sentence: {text}"
        result = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return result.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension  # type: ignore[return-value]
