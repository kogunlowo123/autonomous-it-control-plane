"""PII tagger — detects and tags PII in document chunks."""
from __future__ import annotations

import re
from typing import Any

_PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "aws_key": re.compile(r"\b(?:AKIA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b"),
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """Return a dict of PII type to list of found values."""
    found: dict[str, list[str]] = {}
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[pii_type] = matches
    return found


def tag_chunk_pii(metadata: dict[str, Any], content: str) -> dict[str, Any]:
    """Add pii_detected flag and types to chunk metadata."""
    found = detect_pii(content)
    return {
        **metadata,
        "pii_detected": bool(found),
        "pii_types": list(found.keys()),
    }


def redact_pii(text: str) -> str:
    """Replace detected PII values with [REDACTED] placeholders."""
    for pii_type, pattern in _PII_PATTERNS.items():
        text = pattern.sub(f"[{pii_type.upper()}_REDACTED]", text)
    return text
