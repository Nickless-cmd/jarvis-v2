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
    """Compatibility no-op; the authoritative current-query bundle owns recall."""
    return ""
