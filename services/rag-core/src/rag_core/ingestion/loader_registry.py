"""Loader registry — maps file extensions to loader classes."""
from __future__ import annotations

from typing import Any

from rag_core.ingestion.html_loader import HtmlLoader
from rag_core.ingestion.pdf_loader import PdfLoader


class LoaderRegistry:
    """Registry mapping file extensions to document loaders."""

    def __init__(self) -> None:
        self._loaders: dict[str, Any] = {
            ".pdf": PdfLoader(),
            ".html": HtmlLoader(),
            ".htm": HtmlLoader(),
            ".md": _TextLoader(),
            ".txt": _TextLoader(),
        }

    def get(self, extension: str) -> Any:
        """Return loader for a given file extension."""
        loader = self._loaders.get(extension.lower())
        if loader is None:
            raise ValueError(f"No loader registered for extension: {extension}")
        return loader

    def register(self, extension: str, loader: Any) -> None:
        """Register a custom loader for an extension."""
        self._loaders[extension.lower()] = loader

    def supported_extensions(self) -> list[str]:
        return list(self._loaders.keys())


class _TextLoader:
    """Simple plain-text loader."""

    def load(self, file_path: str) -> list[dict[str, Any]]:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return [{"content": content, "metadata": {"source": file_path}}]
