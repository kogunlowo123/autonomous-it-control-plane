"""Hybrid retrieval combining dense vector search (pgvector) and sparse (OpenSearch BM25)."""
from __future__ import annotations

import logging
from typing import Any

from rag_core.retrieval.rrf import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines dense (pgvector) and sparse (OpenSearch) retrieval with RRF fusion."""

    def __init__(
        self,
        database_url: str,
        opensearch_url: str,
        opensearch_index: str,
        embedder: Any,
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> None:
        self.database_url = database_url
        self.opensearch_url = opensearch_url
        self.opensearch_index = opensearch_index
        self.embedder = embedder
        self.top_k = top_k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Retrieve documents using hybrid dense+sparse search with RRF fusion."""
        k = top_k or self.top_k
        query_embedding = self.embedder.embed_query(query)

        dense_results = self._dense_search(query_embedding, k=k * 2)
        sparse_results = self._sparse_search(query, k=k * 2)

        fused = reciprocal_rank_fusion([dense_results, sparse_results], k=k)
        return fused[:k]

    def _dense_search(self, embedding: list[float], k: int) -> list[dict[str, Any]]:
        """pgvector cosine similarity search."""
        try:
            import psycopg2
            import psycopg2.extras

            embedding_str = f"[{','.join(str(x) for x in embedding)}]"
            conn = psycopg2.connect(self.database_url, connect_timeout=5)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, title, content, metadata,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM itsm.runbooks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding_str, embedding_str, k),
                )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Dense search failed: %s", exc)
            return []

    def _sparse_search(self, query: str, k: int) -> list[dict[str, Any]]:
        """OpenSearch BM25 full-text search."""
        try:
            from opensearchpy import OpenSearch

            client = OpenSearch(self.opensearch_url)
            response = client.search(
                index=self.opensearch_index,
                body={
                    "query": {"match": {"content": query}},
                    "size": k,
                },
            )
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "title": hit["_source"].get("title", ""),
                    "content": hit["_source"].get("content", ""),
                    "metadata": hit["_source"].get("metadata", {}),
                    "similarity": hit["_score"] / 10.0,  # Normalize BM25 score
                })
            return results
        except Exception as exc:
            logger.warning("Sparse search failed: %s", exc)
            return []
