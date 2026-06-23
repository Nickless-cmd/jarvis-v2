"""Session-milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter.

Bjørn 2026-06-23: jarvis-desk's "saved rail" ankrede på HVER user-besked (en lang session =
hundredevis af dashes). Den skal i stedet vise MILEPÆLE: samtalen segmenteret i ~kapitler med
korte titler, ankret på den user-besked der starter hvert kapitel.

Genereres med den BILLIGE lane (ikke visible-modellen), cached i shared_cache pr. session +
turn-antal, og regenereres kun når der er kommet nok nye turns (ingen LLM-kald pr. poll).
Self-safe: enhver fejl → fald tilbage til de rå user-turns, så rail'en aldrig forsvinder.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "session_milestones:"
_CACHE_TTL = 6 * 3600          # 6t — regenereres alligevel når turn-antal vokser nok
_REGEN_DELTA = 3               # regenerér først når der er ≥3 nye user-turns siden cache
_PER_TURN_MAX = 6              # ≤6 turns: ét kapitel pr. turn (ingen LLM nødvendig)
_MAX_MILESTONES = 12           # loft på antal kapitler i rail'en


def _user_turns(session_id: str) -> list[dict[str, str]]:
    """[(message_id, text)] for user-beskederne i kronologisk orden. Self-safe → []."""
    try:
        from core.runtime.db_core import connect
        sid = (session_id or "").strip()
        if not sid:
            return []
        with connect() as conn:
            rows = conn.execute(
                "SELECT message_id, content FROM chat_messages "
                "WHERE session_id = ? AND role = 'user' ORDER BY id ASC",
                (sid,),
            ).fetchall()
        out: list[dict[str, str]] = []
        for r in rows:
            txt = " ".join(str(r["content"] or "").split()).strip()
            if txt:
                out.append({"id": str(r["message_id"]), "text": txt})
        return out
    except Exception:
        return []


def _short_title(text: str, n: int = 60) -> str:
    t = text.strip()
    return (t[: n - 1].rstrip() + "…") if len(t) > n else t


def _per_turn_milestones(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"anchor_id": t["id"], "title": _short_title(t["text"])} for t in turns]


def _llm_segment(turns: list[dict[str, str]]) -> list[dict[str, str]] | None:
    """Bed den billige lane segmentere samtalen i kapitler. Returnerer milepæle eller None."""
    numbered = "\n".join(f"{i}: {t['text'][:200]}" for i, t in enumerate(turns))
    prompt = (
        "Her er en brugers beskeder i en samtale, nummereret. Inddel dem i sammenhængende "
        f"KAPITLER (emneskift) — max {_MAX_MILESTONES}. For hvert kapitel: det laveste besked-"
        "nummer hvor kapitlet starter, og en KORT dansk titel (max 6 ord, ingen punktum). "
        "Svar KUN med en JSON-liste: [{\"start\": <nummer>, \"title\": \"...\"}, ...].\n\n"
        + numbered
    )
    try:
        from core.context.compact_llm import call_compact_llm
        raw = call_compact_llm(prompt, max_tokens=400) or ""
    except Exception as exc:
        logger.warning("milestones: LLM-segmentering fejlede (%s)", exc)
        return None
    # Træk JSON-listen ud (modellen kan pakke den i prosa/kodeblok).
    start = raw.find("[")
    end = raw.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        items = json.loads(raw[start: end + 1])
    except Exception:
        return None
    out: list[dict[str, str]] = []
    seen: set[int] = set()
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        try:
            idx = int(it.get("start"))
        except Exception:
            continue
        if idx < 0 or idx >= len(turns) or idx in seen:
            continue
        title = " ".join(str(it.get("title") or "").split()).strip()[:60]
        if not title:
            title = _short_title(turns[idx]["text"])
        seen.add(idx)
        out.append({"anchor_id": turns[idx]["id"], "title": title})
    out.sort(key=lambda m: list(t["id"] for t in turns).index(m["anchor_id"]))
    return out[:_MAX_MILESTONES] or None


def _generate(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(turns) <= _PER_TURN_MAX:
        return _per_turn_milestones(turns)
    return _llm_segment(turns) or _per_turn_milestones(turns)[:_MAX_MILESTONES]


def get_session_milestones(session_id: str) -> list[dict[str, str]]:
    """Milepæle for rail'en: [{anchor_id, title}]. Cached pr. session+turn-antal; regenereres
    kun når der er kommet ≥_REGEN_DELTA nye user-turns. Self-safe → rå turns ved fejl."""
    turns = _user_turns(session_id)
    if not turns:
        return []
    if len(turns) <= _PER_TURN_MAX:
        return _per_turn_milestones(turns)

    key = _CACHE_PREFIX + (session_id or "").strip()
    try:
        from core.services import shared_cache
        cached = shared_cache.get(key)
        if isinstance(cached, dict):
            prev_count = int(cached.get("turn_count") or 0)
            ms = cached.get("milestones")
            if isinstance(ms, list) and abs(len(turns) - prev_count) < _REGEN_DELTA:
                return ms  # frisk nok
    except Exception:
        pass

    milestones = _generate(turns)
    try:
        from core.services import shared_cache
        shared_cache.set(key, {"turn_count": len(turns), "milestones": milestones},
                         ttl_seconds=_CACHE_TTL)
    except Exception:
        pass
    return milestones
