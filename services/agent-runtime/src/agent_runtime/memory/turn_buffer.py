"""Turn buffer — in-memory circular buffer for current conversation turns."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class TurnBuffer:
    """Fixed-capacity circular buffer for agent conversation turns."""

    def __init__(self, max_turns: int = 20) -> None:
        self._max_turns = max_turns
        self._buffer: deque[Turn] = deque(maxlen=max_turns)

    def append(self, role: str, content: str, **metadata: Any) -> None:
        self._buffer.append(Turn(role=role, content=content, metadata=metadata))

    def to_messages(self) -> list[dict[str, str]]:
        """Return buffer as list of {role, content} dicts for LLM context."""
        return [{"role": t.role, "content": t.content} for t in self._buffer]

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
