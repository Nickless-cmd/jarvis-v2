"""Guards for tool turns that end in hollow final prose."""
from __future__ import annotations

import re
from typing import Any

_HOLLOW_RE = re.compile(
    r"^\s*(done|ok|okay|færdig|klar|completed|finished|det er gjort|sådan)\.?\s*$",
    re.IGNORECASE,
)


def tool_call_count(exchanges: list[Any]) -> int:
    return sum(len(getattr(ex, "tool_calls", []) or []) for ex in exchanges or [])


def is_hollow_post_tool_answer(answer_text: str, exchanges: list[Any]) -> bool:
    if tool_call_count(exchanges) <= 0:
        return False
    text = " ".join(str(answer_text or "").split()).strip()
    if not text:
        return True
    return bool(_HOLLOW_RE.match(text))


def should_replace_with_synthesis(current_text: str, candidate_text: str) -> bool:
    return len(str(candidate_text or "").strip()) >= max(24, len(str(current_text or "").strip()) + 12)
