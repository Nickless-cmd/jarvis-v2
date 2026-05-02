"""Visible Jarvis' værktøjer til hjernen.

Tools:
  - remember_this: skriv en post i hjernen (5/turn, 20/day cap)
  - search_jarvis_brain: embedding-søg (visibility-filtreret)
  - read_brain_entry: hent fuld content for én post
  - archive_brain_entry: arkivér post
  - adopt_brain_proposal: stempl en daemon-foreslået post som rigtig hjerne
  - discard_brain_proposal: smid forslag væk

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 4 + 5.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

# Default caps; overridable via RuntimeSettings (Task 17 wires this).
_DEFAULT_PER_TURN_CAP = 5
_DEFAULT_PER_DAY_CAP = 20

# In-memory counters. Genstart nulstiller — det er ok, dag-cap er soft beskyttelse.
_turn_counts: dict[str, int] = defaultdict(int)
_day_counts: dict[str, int] = defaultdict(int)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _get_caps() -> tuple[int, int]:
    """Read caps from RuntimeSettings if available, else defaults."""
    try:
        from core.runtime.settings import load_settings  # type: ignore
        s = load_settings()
        return (
            getattr(s, "jarvis_brain_remember_per_turn_cap", _DEFAULT_PER_TURN_CAP),
            getattr(s, "jarvis_brain_remember_per_day_cap", _DEFAULT_PER_DAY_CAP),
        )
    except Exception:
        return (_DEFAULT_PER_TURN_CAP, _DEFAULT_PER_DAY_CAP)


def remember_this(
    *,
    kind: str,
    title: str,
    content: str,
    visibility: str,
    domain: str,
    session_id: str,
    turn_id: str,
    related: list[str] | None = None,
    source_url: str | None = None,
    source_chronicle: str | None = None,
) -> dict[str, Any]:
    """Skriv en post i Jarvis' egen hjerne.

    Returnerer dict med status="ok" og id, eller status="error" med detalje.
    """
    now = _now()

    # Validation
    if kind not in {"fakta", "indsigt", "observation", "reference"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid kind: {kind}"}
    if visibility not in {"public_safe", "personal", "intimate"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid visibility: {visibility}"}
    if not title.strip():
        return {"status": "error", "error": "validation_failed",
                "details": "empty title"}
    if len(content) > 4096:
        return {"status": "error", "error": "validation_failed",
                "details": "content too long (max 4096 bytes)"}

    # Rate limits
    per_turn_cap, per_day_cap = _get_caps()
    turn_key = f"{session_id}:{turn_id}"
    if _turn_counts[turn_key] >= per_turn_cap:
        return {"status": "error", "error": "rate_limit_turn",
                "details": f"max {per_turn_cap} per turn"}
    day_key = _day_key(now)
    if _day_counts[day_key] >= per_day_cap:
        return {"status": "error", "error": "rate_limit_day",
                "details": f"max {per_day_cap} per day"}

    # Persist
    try:
        from core.services import jarvis_brain
        new_id = jarvis_brain.write_entry(
            kind=kind, title=title, content=content,
            visibility=visibility, domain=domain,
            trigger="spontaneous", related=related or [],
            source_url=source_url, source_chronicle=source_chronicle,
            now=now,
        )
    except Exception as exc:
        return {"status": "error", "error": "disk_write_failed",
                "details": str(exc)}

    _turn_counts[turn_key] += 1
    _day_counts[day_key] += 1

    return {"status": "ok", "id": new_id}
