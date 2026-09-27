"""AWS Bedrock embedding model — Titan Embeddings V2."""
from __future__ import annotations

import json
import logging

import boto3

from rag_core.embeddings.base import BaseEmbedder

logger = logging.getLogger(__name__)

_BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"


class BedrockEmbedder(BaseEmbedder):
    """Generates embeddings via Amazon Bedrock Titan Embeddings V2."""

    def __init__(self, model_id: str = _BEDROCK_EMBEDDING_MODEL, region: str = "us-east-1") -> None:
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text})
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self.embed(query)
