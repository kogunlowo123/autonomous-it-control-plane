"""Ingestion sync — processes documents from S3 into vector stores."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rag_core.chunking.recursive import RecursiveChunker
from rag_core.config.settings import Settings
from rag_core.enrichment.acl_stamper import stamp_acl
from rag_core.enrichment.auto_tagger import auto_tag
from rag_core.enrichment.metadata import enrich_metadata
from rag_core.enrichment.pii_tagger import tag_chunk_pii
from rag_core.ingestion.loader_registry import LoaderRegistry
from rag_core.stores.pgvector_store import PGVectorStore

logger = logging.getLogger(__name__)

_settings = Settings()


def ingest_file(
    file_path: str,
    embedder: Any,
    tenant_id: str | None = None,
) -> int:
    """Ingest a single file into the vector store.

    Returns count of chunks ingested.
    """
    path = Path(file_path)
    registry = LoaderRegistry()
    loader = registry.get(path.suffix)

    documents = loader.load(file_path)
    chunker = RecursiveChunker(
        chunk_size=_settings.chunk_size,
        chunk_overlap=64,
    )

    store = PGVectorStore()
    ingested = 0

    for doc in documents:
        chunks = chunker.chunk(doc["content"], doc.get("metadata", {}))
        for chunk in chunks:
            meta = enrich_metadata(
                chunk.metadata,
                source_uri=file_path,
                document_id=path.stem,
            )
            meta = tag_chunk_pii(meta, chunk.content)
            meta = auto_tag(chunk.content, meta)
            meta = stamp_acl(meta, tenant_id=tenant_id)

            embedding = embedder.embed(chunk.content)
            import uuid
            store.upsert(
                doc_id=str(uuid.uuid4()),
                content=chunk.content,
                embedding=embedding,
                metadata=meta,
            )
            ingested += 1

    logger.info("Ingested %d chunks from %s", ingested, path.name)
    return ingested
