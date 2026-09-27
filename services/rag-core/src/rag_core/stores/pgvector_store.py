"""pgvector document store for ITSM runbooks."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class PGVectorStore:
    """Stores and retrieves runbook documents with pgvector embeddings."""

    def __init__(self, database_url: str, schema: str = "itsm") -> None:
        self.database_url = database_url
        self.schema = schema
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the runbooks table with pgvector extension."""
        try:
            conn = psycopg2.connect(self.database_url, connect_timeout=5)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.runbooks (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        title VARCHAR(500) NOT NULL,
                        content TEXT NOT NULL,
                        source_url VARCHAR(1000),
                        doc_type VARCHAR(50) DEFAULT 'runbook',
                        embedding vector(768),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema}_runbooks_embedding
                    ON {self.schema}.runbooks USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                    """
                )
            conn.close()
            logger.info("pgvector schema initialized: %s.runbooks", self.schema)
        except Exception as exc:
            logger.warning("Failed to initialize pgvector schema: %s", exc)

    def upsert(
        self,
        title: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        source_url: str = "",
        doc_type: str = "runbook",
        doc_id: str | None = None,
    ) -> str:
        """Insert or update a document with its embedding. Returns doc_id."""
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        metadata = metadata or {}
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"

        try:
            conn = psycopg2.connect(self.database_url, connect_timeout=5)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.schema}.runbooks
                      (id, title, content, source_url, doc_type, embedding, metadata, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s::vector, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                      title = EXCLUDED.title,
                      content = EXCLUDED.content,
                      embedding = EXCLUDED.embedding,
                      metadata = EXCLUDED.metadata,
                      updated_at = NOW()
                    """,
                    (doc_id, title, content, source_url, doc_type,
                     embedding_str, json.dumps(metadata)),
                )
            conn.close()
            return doc_id
        except Exception as exc:
            logger.error("Failed to upsert document %s: %s", doc_id, exc)
            raise

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Search by cosine similarity."""
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        try:
            conn = psycopg2.connect(self.database_url, connect_timeout=5)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, title, content, metadata, source_url,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM {self.schema}.runbooks
                    WHERE 1 - (embedding <=> %s::vector) >= %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding_str, embedding_str, min_similarity, embedding_str, top_k),
                )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("pgvector search failed: %s", exc)
            return []
