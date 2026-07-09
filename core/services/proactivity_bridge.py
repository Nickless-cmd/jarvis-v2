# core/services/proactivity_bridge.py
"""Proaktivitets-broen — samler Jarvis' indre spørgsmål/initiativer/undren og overflader dem til
Bjørn gennem en presence-bevidst contact-gate + delte caps. Hybrid: urgent-item straks, ellers
'mens du var væk'-digest, ellers observe-suppressed (synlig, ikke sendt). Live-governed via
kill-switch; fail-closed for afsendelse. Self-safe — kaster aldrig i cadence-hot-path."""
from __future__ import annotations

from typing import Any

_DIGEST_MAX = 5           # højst så mange normale items i én digest
_PRESENT_WINDOW_S = 900   # owner regnes "til stede" hvis synlig < 15 min siden
_AWAY_MIN_S = 3600        # digest kræver ≥1t fravær (urgent kræver ikke)
_URGENT_PRIORITIES = {"high", "critical"}
_URGENT_KINDS = {"critical_impulse"}


def classify(candidate: dict[str, Any]) -> str:
    """'urgent' hvis høj/kritisk prioritet eller kritisk kind; ellers 'normal'. Ren."""
    if str(candidate.get("priority") or "").lower() in _URGENT_PRIORITIES:
        return "urgent"
    if str(candidate.get("kind") or "") in _URGENT_KINDS:
        return "urgent"
    return "normal"


def select(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Dedup på source_id, split i urgent/normal, sortér (urgent først/friskest), cap normal-listen."""
    seen: set[str] = set()
    urgent: list[dict[str, Any]] = []
    normal: list[dict[str, Any]] = []
    for c in candidates or []:
        sid = str(c.get("source_id") or "")
        if sid and sid in seen:
            continue
        if sid:
            seen.add(sid)
        (urgent if classify(c) == "urgent" else normal).append(c)
    normal.sort(key=lambda c: str(c.get("ts") or ""), reverse=True)
    return {"urgent": urgent, "normal": normal[:_DIGEST_MAX]}


def should_reach_owner(*, owner_present: bool, is_quiet: bool, sent_today: int, cap: int,
                       within_cooldown: bool, urgent: bool) -> tuple[bool, str]:
    """Ren contact-gate (kalderen injicerer signalerne). Rækkefølge = spam-værn:
    owner til stede → aldrig afbryd; quiet-hours blokerer normal (urgent må bryde); daily-cap;
    cooldown. Returnér (ok, reason) — reason bruges til observe ved suppression."""
    if owner_present:
        return (False, "owner_present")
    if is_quiet and not urgent:
        return (False, "quiet_hours")
    if sent_today >= cap:
        return (False, "daily_cap")
    if within_cooldown:
        return (False, "cooldown")
    return (True, "ok")


def build_urgent(item: dict[str, Any]) -> str:
    """Enkelt-item besked (urgent-gren)."""
    text = str(item.get("text") or "").strip()
    kind = str(item.get("kind") or "note")
    return f"💭 Jarvis ({kind}): {text}"


def build_digest(normal: list[dict[str, Any]]) -> str:
    """'Mens du var væk'-digest af normale items (kort, prioriteret)."""
    lines = ["💭 Mens du var væk tænkte jeg på:"]
    for c in (normal or [])[:_DIGEST_MAX]:
        text = str(c.get("text") or "").strip()
        if text:
            lines.append(f"  • {text}")
    return "\n".join(lines)
