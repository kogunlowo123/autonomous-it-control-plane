"""Agent runtime settings."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AWS
    aws_region: str = Field(default="us-east-1")
    aws_bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")

    # Database
    database_url: str = Field(default="postgresql://itsm:password@localhost:5432/itsm_db")
    pgvector_schema: str = Field(default="itsm")

    # OpenSearch
    opensearch_url: str = Field(default="https://localhost:9200")
    opensearch_index: str = Field(default="itsm-runbooks")

    # SQS
    sqs_approval_queue_url: str = Field(default="")
    sqs_change_queue_url: str = Field(default="")

    # S3
    s3_runbook_bucket: str = Field(default="itsm-runbooks-dev")

    # OPA
    opa_url: str = Field(default="http://localhost:8181")

    # Agent behavior
    confidence_threshold: float = Field(default=0.85)
    max_agent_iterations: int = Field(default=10)
    max_agent_tokens: int = Field(default=50000)
