"""Small text helpers shared by visible-run outcome persistence."""
from __future__ import annotations


def preview_text(text: str, limit: int = 320) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def mark_mid_word_truncation(text: str) -> str:
    """Mark a likely sentence cut off in the middle of its final word."""
    if not text:
        return text
    stripped = text.rstrip()
    if not stripped:
        return text
    last_line = stripped.splitlines()[-1].strip()
    if not last_line or len(last_line.split()) < 3:
        return text
    if not last_line[-1].isalnum():
        return text
    return stripped + "…"


def origin_of_session(session_id: str) -> str:
    """«auto-dream-20260902» → «dream»; empty for ordinary chats."""
    value = str(session_id or "")
    if not value.startswith("auto-"):
        return ""
    parts = value.split("-")
    return parts[1] if len(parts) >= 2 else ""

