"""PDF loader — extracts text from PDF files using pypdf."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PdfLoader:
    """Loads PDF files and returns page-level text chunks."""

    def load(self, file_path: str) -> list[dict[str, Any]]:
        """Load a PDF and return list of {content, metadata} dicts (one per page)."""
        try:
            import pypdf
        except ImportError as exc:
            raise RuntimeError("pypdf is required for PDF loading: pip install pypdf") from exc

        path = Path(file_path)
        documents: list[dict[str, Any]] = []

        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    documents.append({
                        "content": text,
                        "metadata": {
                            "source": str(path),
                            "page_number": page_num + 1,
                            "total_pages": len(reader.pages),
                            "file_type": "pdf",
                        },
                    })

        logger.info("Loaded %d pages from %s", len(documents), path.name)
        return documents
