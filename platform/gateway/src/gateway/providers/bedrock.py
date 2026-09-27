"""AWS Bedrock provider for the LLM gateway."""
from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockProvider:
    """Invokes AWS Bedrock foundation models."""

    def __init__(self, region: str, default_model: str) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._default_model = default_model

    def invoke(self, model: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke a Bedrock model and return the response."""
        model_id = model or self._default_model

        # Format for Anthropic Claude models
        if "anthropic" in model_id:
            body = self._format_anthropic(payload)
        else:
            body = json.dumps(payload)

        try:
            response = self._client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            return json.loads(response["body"].read())
        except ClientError as exc:
            logger.error("Bedrock invoke failed for model %s: %s", model_id, exc)
            raise

    def _format_anthropic(self, payload: dict[str, Any]) -> str:
        """Format payload for Anthropic Claude API via Bedrock."""
        messages = payload.get("messages", [])
        return json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": payload.get("max_tokens", 1024),
            "messages": messages,
            "temperature": payload.get("temperature", 0.0),
        })
