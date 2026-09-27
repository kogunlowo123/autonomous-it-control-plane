"""Idempotency key tracking — prevents duplicate processing of SQS messages."""
from __future__ import annotations

import hashlib
import logging

import psycopg2

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


def _key_hash(idempotency_key: str) -> str:
    return hashlib.sha256(idempotency_key.encode()).hexdigest()


def is_duplicate(idempotency_key: str) -> bool:
    """Return True if this key was already processed."""
    key_hash = _key_hash(idempotency_key)
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM idempotency_keys WHERE key_hash = %s",
                (key_hash,),
            )
            found = cur.fetchone() is not None
        conn.close()
        return found
    except Exception as exc:  # noqa: BLE001
        logger.warning("Idempotency check failed: %s", exc)
        return False


def mark_processed(idempotency_key: str) -> None:
    """Record that this key has been processed."""
    key_hash = _key_hash(idempotency_key)
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO idempotency_keys (key_hash, original_key)
                    VALUES (%s, %s)
                    ON CONFLICT (key_hash) DO NOTHING
                    """,
                    (key_hash, idempotency_key[:512]),
                )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to mark key as processed: %s", exc)
