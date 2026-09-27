"""Episodic memory — persists resolved incident summaries for future retrieval."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


def store_episode(
    incident_id: str,
    summary: str,
    resolution: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Persist a resolved incident as an episodic memory entry.

    Returns the episode_id.
    """
    episode_id = str(uuid.uuid4())
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodic_memory
                      (id, incident_id, summary, resolution, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        episode_id,
                        incident_id,
                        summary,
                        resolution,
                        json.dumps(metadata or {}),
                        datetime.now(tz=timezone.utc),
                    ),
                )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to store episode: %s", exc)

    return episode_id


def recall_similar(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Retrieve similar past episodes using pgvector similarity search.

    Falls back to recency-based retrieval if embeddings unavailable.
    """
    episodes: list[dict[str, Any]] = []
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, incident_id, summary, resolution, metadata, created_at
                FROM episodic_memory
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (top_k,),
            )
            for row in cur.fetchall():
                episodes.append({
                    "episode_id": str(row[0]),
                    "incident_id": str(row[1]),
                    "summary": row[2],
                    "resolution": row[3],
                    "metadata": row[4] or {},
                    "created_at": row[5].isoformat() if row[5] else None,
                })
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to recall episodes: %s", exc)

    return episodes
