"""RAG search tool — hybrid retrieval over runbook knowledge base."""
from __future__ import annotations

import logging
from typing import Any

import psycopg2
from opensearchpy import OpenSearch

from agent_runtime.settings import Settings
from agent_runtime.tools.base import BaseTool

logger = logging.getLogger(__name__)

_settings = Settings()


class RagSearchTool(BaseTool):
    """Hybrid BM25 + vector search over runbook knowledge base."""

    name = "rag_search"
    description = "Search runbooks and knowledge base using hybrid retrieval"

    def __init__(self) -> None:
        self._pg_conn: Any = None
        self._os_client: Any = None

    def _get_pg(self) -> Any:
        if self._pg_conn is None or self._pg_conn.closed:
            self._pg_conn = psycopg2.connect(_settings.database_url)
        return self._pg_conn

    def _get_os(self) -> Any:
        if self._os_client is None:
            self._os_client = OpenSearch(
                hosts=[{"host": _settings.opensearch_host, "port": _settings.opensearch_port}],
                use_ssl=False,
                verify_certs=False,
            )
        return self._os_client

    async def run(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:  # type: ignore[override]
        """Search runbooks and return ranked results.

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            List of {id, content, score, metadata} dicts
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._search_sync, query, top_k
        )

    def _search_sync(self, query: str, top_k: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        # pgvector dense search
        try:
            conn = self._get_pg()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, metadata,
                           1 - (embedding <=> %s::vector) AS score
                    FROM runbook_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query, query, top_k * 2),
                )
                for row in cur.fetchall():
                    results.append({
                        "id": str(row[0]),
                        "content": row[1],
                        "metadata": row[2] or {},
                        "score": float(row[3]),
                        "source": "pgvector",
                    })
        except Exception as exc:  # noqa: BLE001
            logger.warning("pgvector search failed: %s", exc)

        # OpenSearch BM25 search
        try:
            os_client = self._get_os()
            response = os_client.search(
                index="runbook-chunks",
                body={
                    "query": {"match": {"content": query}},
                    "size": top_k * 2,
                },
            )
            for hit in response.get("hits", {}).get("hits", []):
                results.append({
                    "id": hit["_id"],
                    "content": hit["_source"].get("content", ""),
                    "metadata": hit["_source"].get("metadata", {}),
                    "score": hit["_score"],
                    "source": "opensearch",
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenSearch search failed: %s", exc)

        # Deduplicate by id, keep highest score
        seen: dict[str, dict[str, Any]] = {}
        for item in results:
            doc_id = item["id"]
            if doc_id not in seen or item["score"] > seen[doc_id]["score"]:
                seen[doc_id] = item

        ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]
