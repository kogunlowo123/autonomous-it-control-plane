"""API service settings."""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # Database
    database_url: str = Field(default="postgresql://itsm:password@localhost:5432/itsm_db")
    pgvector_schema: str = Field(default="itsm")

    # AWS
    aws_region: str = Field(default="us-east-1")
    aws_account_id: str = Field(default="")
    aws_bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")

    # SQS
    sqs_approval_queue_url: str = Field(default="")
    sqs_change_queue_url: str = Field(default="")

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="RS256")
    jwt_public_key_path: str = Field(default="")

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # Rate limiting
    rate_limit_calls: int = Field(default=100)
    rate_limit_period: int = Field(default=60)

    # OPA
    opa_url: str = Field(default="http://localhost:8181")

    # Tenancy
    default_tenant_id: str = Field(default="default")

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = Field(default="")

    # S3
    s3_runbook_bucket: str = Field(default="itsm-runbooks-dev")

    # KMS
    kms_key_arn: str = Field(default="")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper
