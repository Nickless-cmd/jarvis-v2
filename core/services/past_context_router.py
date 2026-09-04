"""Past-context cue router for visible prompts."""
from __future__ import annotations

import re
from typing import Any

_CUE_RE = re.compile(
    r"\b("
    r"det|den|de|denne|dette|sidste|forrige|tidligere|vores|min|mit|mine|"
    r"vi\s+(besluttede|aftalte|lavede|sagde|snakkede|talte)|"
    r"kan\s+du\s+huske|hvad\s+var\s+det|"
    r"that|this|those|previous|earlier|last|our|my|"
    r"we\s+(decided|agreed|made|said|discussed)|"
    r"do\s+you\s+remember|what\s+was\s+that"
    r")\b",
    re.IGNORECASE,
)


def needs_past_context(user_message: str) -> bool:
    """Return True when a user turn likely depends on prior conversation."""
    text = " ".join(str(user_message or "").split()).strip()
    if len(text.split()) < 3:
        return False
    return bool(_CUE_RE.search(text))


def build_past_context_section(
    user_message: str,
    *,
    session_id: str | None = None,
    limit: int = 3,
) -> str:
    """Render a compact context block from summaries/chat when cues warrant it."""
    if not needs_past_context(user_message):
        return ""
    try:
        from core.services.recall import recall

        result: dict[str, Any] = recall(
            user_message,
            limit=max(1, min(5, int(limit or 3))),
            sources=["session_summary", "chat"],
            session_id=session_id,
            min_score=0.2,
            per_source=4,
        )
    except Exception:
        return ""
    rows = list(result.get("results") or [])
    if not rows:
        return ""
    lines = ["Relevant tidligere kontekst:"]
    for row in rows[:limit]:
        source = str(row.get("source") or "memory")
        text = " ".join(str(row.get("text") or "").split())
        if text:
            lines.append(f"- [{source}] {text[:360]}")
    return "\n".join(lines) if len(lines) > 1 else ""
