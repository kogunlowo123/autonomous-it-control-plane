"""Cross-encoder reranker — reranks hybrid retrieval results."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks candidate documents using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self._model_name)
            except ImportError:
                logger.warning("sentence-transformers not installed — skipping reranking")
        return self._model

    def rerank(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Rerank documents by cross-encoder score.

        Args:
            query: The retrieval query
            documents: List of {id, content, metadata, score} dicts
            top_k: Number of top documents to return

        Returns:
            Reranked list with updated scores
        """
        model = self._get_model()
        if model is None or not documents:
            return documents[:top_k]

        pairs = [(query, doc["content"]) for doc in documents]
        scores = model.predict(pairs)

        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        reranked = sorted(documents, key=lambda d: d.get("rerank_score", 0.0), reverse=True)
        return reranked[:top_k]
