"""RAG Core settings."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(default="postgresql://itsm:password@localhost:5432/itsm_db")
    pgvector_schema: str = Field(default="itsm")

    # OpenSearch
    opensearch_url: str = Field(default="https://localhost:9200")
    opensearch_index: str = Field(default="itsm-runbooks")

    # AWS
    aws_region: str = Field(default="us-east-1")
    s3_runbook_bucket: str = Field(default="itsm-runbooks-dev")
    aws_bedrock_model_id: str = Field(default="amazon.titan-embed-text-v2:0")

    # Embeddings
    embedding_model: str = Field(default="BAAI/bge-base-en-v1.5")
    embedding_dimension: int = Field(default=768)
    embedding_batch_size: int = Field(default=32)

    # Chunking
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)
    max_chunks_per_doc: int = Field(default=500)

    # Retrieval
    retrieval_top_k: int = Field(default=10)
    rerank_top_k: int = Field(default=5)
    min_similarity: float = Field(default=0.6)
