"""MEMORY.md selection by SECTION for the visible prompt (memory repair 2026-09-04, R2).

Before: MEMORY.md (67 KB, 93 sections) was split into bare lines without their
headings, scored by a hard-coded keyword list, and when nothing matched the
LAST FOUR LINES of the file were injected — 4 lines × 280 chars. The answer to
"hvor ligger pfsense-nøglen" was in the file; the prompt got two lines about
"inner voice, boredom and reflective noise".

Now: the existing `memory_search` index already chunks MEMORY.md per heading
and embeds each chunk. We ask it for the top sections for the user's message
and render them WITH their heading. Falls back to the old heuristic (caller's
responsibility) when the index yields nothing.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MIN_SCORE = 0.30


def _render(section: str, text: str, *, max_chars: int) -> str:
    heading = " ".join((section or "").split()).strip()
    body = " ".join((text or "").split()).strip()
    line = f"§ {heading}: {body}" if heading else body
    if len(line) > max_chars:
        line = line[: max_chars - 1].rstrip() + "…"
    return line


def select_memory_md_sections(
    user_message: str,
    *,
    workspace_dir: Path,
    max_sections: int = 3,
    max_chars: int = 1500,
    min_score: float = _MIN_SCORE,
) -> list[str]:
    """Return up to ``max_sections`` rendered MEMORY.md sections, most relevant first.

    - one line per section, ``§ <heading>: <text>``, deduplicated by heading
    - total length ≤ ``max_chars`` (each line ≤ max_chars // max_sections … but a
      single strong section may take up to max_chars // 2)
    - empty list when the message is too short or nothing scores ≥ ``min_score``
    """
    msg = " ".join((user_message or "").split()).strip()
    if len(msg) < 8:
        return []
    try:
        from core.services.memory_search import search_memory

        hits = search_memory(
            msg, limit=max(max_sections * 3, 6), sources=["MEMORY.md"],
            workspace_dir=workspace_dir,
        )
    except Exception as exc:
        logger.debug("memory_md_selection: search failed: %s", exc)
        return []

    per_line_cap = max(200, max_chars // 2)
    out: list[str] = []
    seen: set[str] = set()
    used = 0
    for h in hits:
        if float(h.get("score") or 0.0) < min_score:
            continue
        section = str(h.get("section") or "")
        key = section.strip().lower()
        if key in seen:
            continue
        line = _render(section, str(h.get("text") or ""), max_chars=per_line_cap)
        if not line:
            continue
        if used + len(line) > max_chars and out:
            break
        seen.add(key)
        out.append(line)
        used += len(line)
        if len(out) >= max_sections:
            break
    return out
