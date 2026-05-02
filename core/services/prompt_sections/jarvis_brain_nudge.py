"""Post-web-search nudge — encourages remember_this after Jarvis uses web tools.

Heuristic detection: if the most recent tool message in the session has
URL content (http/https), assume it was web_search or web_scrape and
append a soft prompt to consider saving learnings.

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 4.2.
"""
from __future__ import annotations
import re

_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


_NUDGE_TEXT = (
    "[brain-nudge] Du har lige hentet ekstern info. Hvis du har lært "
    "noget der er værd at gemme — fakta, en god reference, en indsigt "
    "— brug `remember_this` med visibility=public_safe (og source_url "
    "hvis relevant). Det er ikke obligatorisk; spring over hvis intet "
    "stikker ud."
)


def build_brain_post_web_nudge(
    *,
    recent_tool_messages: list[dict[str, str]] | None,
) -> str:
    """Returnér nudge-tekst hvis seneste tool-message har URL-indhold, ellers "".

    Inspiserer kun *seneste* tool-message så nudgen ikke gentager sig efter
    Jarvis har responderet. Heuristic-baseret URL-detektion — robust nok
    for v1 hvor chat_messages-tabellen ikke gemmer tool_name.
    """
    if not recent_tool_messages:
        return ""
    last = recent_tool_messages[-1]
    content = str(last.get("content") or "")
    if not _URL_PATTERN.search(content):
        return ""
    return _NUDGE_TEXT
