"""Token estimation utilities — heuristic only, no tokenizer required."""
from __future__ import annotations

_CHARS_PER_TOKEN: float = 3.5  # Conservative for Danish/English mix


def estimate_tokens(text: str) -> int:
    """Estimate token count from raw text."""
    return int(len(str(text or "")) / _CHARS_PER_TOKEN)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens for a list of chat messages."""
    total = 0
    for m in messages:
        content = m.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        total += estimate_tokens(content)
    return total
