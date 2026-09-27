"""TTL-based memory expiry — purges stale entries from agent memory stores."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import psycopg2

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()

# Default TTLs in seconds
_TTL_DEFAULTS = {
    "turn_buffer": 3600,       # 1 hour
    "episodic_memory": 2592000,  # 30 days
    "session_ledger": 7776000,   # 90 days
}


def purge_expired_entries(table: str, ttl_seconds: int | None = None) -> int:
    """Delete rows from table older than ttl_seconds.

    Returns count of deleted rows.
    """
    ttl = ttl_seconds or _TTL_DEFAULTS.get(table, 86400)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=ttl)

    deleted = 0
    try:
        conn = psycopg2.connect(_settings.database_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {table} WHERE created_at < %s",  # noqa: S608
                    (cutoff,),
                )
                deleted = cur.rowcount
        conn.close()
        logger.info("Purged %d expired rows from %s (cutoff=%s)", deleted, table, cutoff)
    except Exception as exc:  # noqa: BLE001
        logger.warning("TTL purge failed for %s: %s", table, exc)

    return deleted
