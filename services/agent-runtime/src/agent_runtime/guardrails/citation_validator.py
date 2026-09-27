"""Citation validator — ensures citations in agent responses correspond to real sources."""
from __future__ import annotations

import re
from typing import Any

# Matches [1], [2], or (source: runbook-name)
_CITATION_PATTERN = re.compile(r"\[(\d+)\]|\(source:\s*([^)]+)\)", re.IGNORECASE)


def validate_citations(
    response: str,
    source_docs: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Validate citations in a response against source documents.

    Returns:
        (all_valid, list_of_invalid_citations)
    """
    matches = _CITATION_PATTERN.findall(response)
    if not matches:
        return True, []

    valid_ids = {str(doc.get("id", "")) for doc in source_docs}
    valid_titles = {doc.get("title", "").lower().strip() for doc in source_docs}

    invalid: list[str] = []
    for numeric_ref, text_ref in matches:
        if numeric_ref:
            idx = int(numeric_ref) - 1
            if idx < 0 or idx >= len(source_docs):
                invalid.append(f"[{numeric_ref}]")
        elif text_ref:
            text_ref_clean = text_ref.strip()
            if text_ref_clean not in valid_ids and text_ref_clean.lower() not in valid_titles:
                invalid.append(f"(source: {text_ref_clean})")

    return len(invalid) == 0, invalid
