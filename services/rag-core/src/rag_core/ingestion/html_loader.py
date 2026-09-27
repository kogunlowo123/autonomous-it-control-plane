"""HTML loader — extracts text from HTML files using BeautifulSoup."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HtmlLoader:
    """Loads HTML files and returns text content stripped of markup."""

    def load(self, file_path: str) -> list[dict[str, Any]]:
        """Load an HTML file and return list of {content, metadata}."""
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise RuntimeError("beautifulsoup4 required: pip install beautifulsoup4") from exc

        path = Path(file_path)
        with open(path, encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else path.stem

        return [{
            "content": text,
            "metadata": {
                "source": str(path),
                "title": title_text,
                "file_type": "html",
            },
        }]
