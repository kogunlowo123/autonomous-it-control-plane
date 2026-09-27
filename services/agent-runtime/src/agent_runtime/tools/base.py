"""Base tool interface for agent tools."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class for all agent tools."""

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
