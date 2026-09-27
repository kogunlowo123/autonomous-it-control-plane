"""Structural chunker — splits on document structure (headers, sections)."""
from __future__ import annotations

import re
from typing import Any

from rag_core.chunking.base import BaseChunker, Chunk


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class StructuralChunker(BaseChunker):
    """Splits Markdown documents at header boundaries."""

    def __init__(self, min_chunk_size: int = 100) -> None:
        self._min_chunk_size = min_chunk_size

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        sections: list[tuple[str, str]] = []  # (header, content)
        last_end = 0
        last_header = ""

        for match in _HEADER_RE.finditer(text):
            section_text = text[last_end:match.start()].strip()
            if section_text and len(section_text) >= self._min_chunk_size:
                sections.append((last_header, section_text))
            last_header = match.group(2)
            last_end = match.end()

        remaining = text[last_end:].strip()
        if remaining and len(remaining) >= self._min_chunk_size:
            sections.append((last_header, remaining))

        if not sections:
            sections = [("", text)]

        return [
            Chunk(
                content=f"{header}\n{content}".strip() if header else content,
                metadata={**(metadata or {}), "section_header": header},
                chunk_index=i,
            )
            for i, (header, content) in enumerate(sections)
        ]
