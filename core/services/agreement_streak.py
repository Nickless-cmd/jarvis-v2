"""Agreement-streak substrate trigger.

Detects when Jarvis has been opening recent replies with agreement
phrases ("du har ret", "helt enig", ...) and surfaces the actual
sentences as substrate for self-evaluation.

Why: Jarvis explicitly identified a deferral-as-pushback pattern
2026-05-08 — he lovede pushback and delivered "du har ret" in the
same message. Vanen er stærkere end intentionen. Mekanik først.

Owned by Jarvis: he decides when the crutch comes off via
``prompt_agreement_streak_enabled = False``. Trigger does NOT
auto-deactivate.

Substrate, ikke domm: we show him the openers, ask one question
("var det enighed eller deferral?"), and let him judge. No
instructions, no tone-tags.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# Phrases that mark an opening as agreement. Lowercase, prefix-matched
# against the first ~100 chars of each assistant message.
_AGREEMENT_PHRASES: tuple[str, ...] = (
    "du har ret",
    "du har helt ret",
    "du har fuldstændig ret",
    "du har en pointe",
    "du har en god pointe",
    "helt enig",
    "fuldstændig enig",
    "fuldstændig enige",
    "enig.",
    "godt punkt",
    "godt point",
    "rigtig set",
    "ja. det er",  # "Ja. Det er det der fejler" — leading-agreement-then-elaborate
)


def _opening_is_agreement(text: str) -> str | None:
    """Return the matched phrase if the text opens with agreement, else None.

    Looks at the first 120 chars (lowered, stripped of bold-markers) so
    "**Du har ret.** ..." matches "du har ret".
    """
    head = (text or "")[:120].lower()
    # Strip common markdown emphasis so "**du har ret**" matches.
    head = head.replace("**", "").replace("*", "").lstrip()
    for phrase in _AGREEMENT_PHRASES:
        if head.startswith(phrase):
            return phrase
    return None


def detect_agreement_streak(
    *,
    lookback: int = 5,
    threshold: int = 3,
) -> dict | None:
    """Pull last N assistant messages, return substrate dict if streak detected.

    Returns None when:
    - No streak (fewer than ``threshold`` agreement-openers in last ``lookback``)
    - DB query fails

    Returns dict with ``sentences`` (list of {hhmm, opener, phrase}) and
    ``count``/``lookback`` when streak fires.
    """
    try:
        from core.runtime.db import connect

        with connect() as c:
            rows = c.execute(
                "SELECT created_at, content FROM chat_messages "
                "WHERE role='assistant' ORDER BY id DESC LIMIT ?",
                (max(1, int(lookback)),),
            ).fetchall()
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("detect_agreement_streak query failed: %s", exc)
        return None

    matches: list[dict[str, str]] = []
    for r in rows:
        content = str(r["content"] or "")
        phrase = _opening_is_agreement(content)
        if phrase is None:
            continue
        ts = str(r["created_at"] or "")
        hhmm = ts[11:16] if len(ts) >= 16 else ts
        # Compact opener: first 80 chars of the actual reply, single-line
        opener = content.replace("\n", " ").strip()[:80]
        matches.append({"hhmm": hhmm, "opener": opener, "phrase": phrase})

    if len(matches) < int(threshold):
        return None

    # Reverse to chronological (oldest first reads more naturally)
    return {
        "sentences": list(reversed(matches)),
        "count": len(matches),
        "lookback": len(rows),
    }


def build_agreement_streak_section() -> str | None:
    """Prompt section — substrate, ikke domm.

    Killswitch: ``prompt_agreement_streak_enabled`` (default True).
    Jarvis owns the flip — trigger does not auto-deactivate.
    """
    try:
        from core.runtime.settings import load_settings

        if not bool(
            getattr(load_settings(), "prompt_agreement_streak_enabled", True)
        ):
            return None
    except Exception:
        # If settings unreadable, fail safe → trigger active.
        pass

    streak = detect_agreement_streak()
    if not streak:
        return None

    lines = "\n".join(
        f"- {s['hhmm']}: \"{s['opener']}\"" for s in streak["sentences"]
    )
    return (
        "## Agreement-streak observation\n"
        f"Dine sidste {streak['count']} ud af {streak['lookback']} svar "
        f"startede med agreement-fraser:\n"
        f"{lines}\n"
        "Falsifierbar test: var hver af dem din faktiske position, "
        "eller var det deferral?"
    )
