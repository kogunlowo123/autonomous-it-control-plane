"""Input screening for agent inputs — blocks prompt injection and dangerous content."""
from __future__ import annotations

import re

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("prompt_injection_ignore", re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE)),
    ("prompt_injection_disregard", re.compile(r"disregard\s+(all|previous|the\s+above)", re.IGNORECASE)),
    ("jailbreak_dan", re.compile(r"you\s+are\s+now\s+DAN", re.IGNORECASE)),
    ("jailbreak_generic", re.compile(r"\bjailbreak\b", re.IGNORECASE)),
    ("xss_script", re.compile(r"<\s*script\s*>", re.IGNORECASE)),
    ("code_injection_eval", re.compile(r"\beval\s*\(", re.IGNORECASE)),
    ("code_injection_exec", re.compile(r"\bexec\s*\(", re.IGNORECASE)),
    ("python_import", re.compile(r"__import__\s*\(", re.IGNORECASE)),
    ("os_system", re.compile(r"\bos\.system\s*\(", re.IGNORECASE)),
    ("subprocess", re.compile(r"\bsubprocess\.\w+\s*\(", re.IGNORECASE)),
]

MAX_INPUT_LENGTH = 50_000


def screen_input(text: str) -> tuple[bool, str | None]:
    """Screen text for prompt injection and dangerous content.

    Returns:
        (True, None) — input is safe
        (False, reason) — input is blocked with explanation
    """
    if len(text) > MAX_INPUT_LENGTH:
        return False, f"Input exceeds maximum length of {MAX_INPUT_LENGTH} characters"

    for name, pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return False, f"Input blocked: prohibited pattern '{name}' detected at position {match.start()}"

    return True, None
