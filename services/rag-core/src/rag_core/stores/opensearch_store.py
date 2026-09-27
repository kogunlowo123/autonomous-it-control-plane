"""OpenSearch BM25 store for sparse retrieval."""
from __future__ import annotations

import logging
from typing import Any

from opensearchpy import OpenSearch, RequestsHttpConnection

from rag_core.config.settings import Settings
from rag_core.stores.vector_base import VectorStore

logger = logging.getLogger(__name__)

_settings = Settings()

_INDEX = "runbook-chunks"


class OpenSearchStore(VectorStore):
    """BM25 full-text store backed by Amazon OpenSearch."""

    def __init__(self) -> None:
        self._client = OpenSearch(
            hosts=[{"host": _settings.opensearch_host, "port": _settings.opensearch_port}],
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
        )
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self._client.indices.exists(index=_INDEX):
            self._client.indices.create(
                index=_INDEX,
                body={
                    "mappings": {
                        "properties": {
                            "content": {"type": "text", "analyzer": "english"},
                            "metadata": {"type": "object", "enabled": True},
                            "doc_id": {"type": "keyword"},
                        }
                    }
                },
            )

    def upsert(self, doc_id: str, content: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        self._client.index(
            index=_INDEX,
            id=doc_id,
            body={"doc_id": doc_id, "content": content, "metadata": metadata},
            refresh="wait_for",
        )

    def search(self, query_embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        # OpenSearch store does text search — embedding ignored here
        raise NotImplementedError("Use search_text() for OpenSearch BM25 search")

    def search_text(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """BM25 full-text search."""
        response = self._client.search(
            index=_INDEX,
            body={"query": {"match": {"content": query}}, "size": top_k},
        )
        results = []
        for hit in response.get("hits", {}).get("hits", []):
            results.append({
                "id": hit["_id"],
                "content": hit["_source"].get("content", ""),
                "metadata": hit["_source"].get("metadata", {}),
                "score": hit["_score"],
            })
        return results

    def delete(self, doc_id: str) -> None:
        try:
            self._client.delete(index=_INDEX, id=doc_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete %s from OpenSearch: %s", doc_id, exc)
