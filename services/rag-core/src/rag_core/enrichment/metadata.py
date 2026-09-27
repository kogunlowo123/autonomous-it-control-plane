"""Metadata enrichment — attaches source, timestamps, and version info."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def enrich_metadata(
    chunk_metadata: dict[str, Any],
    source_uri: str,
    document_id: str,
    doc_version: str = "1",
) -> dict[str, Any]:
    """Add standard metadata fields to a chunk."""
    return {
        **chunk_metadata,
        "source_uri": source_uri,
        "document_id": document_id,
        "doc_version": doc_version,
        "ingested_at": datetime.now(tz=timezone.utc).isoformat(),
    }
