"""Jarvis Mind-hub — Centralen som ÉT samlingspunkt for alt MC viser.

Bjørn 2026-06-23: MC poller ~190 separate endpoints = mange sandheder, rod, load. Filosofien
(CLAUDE.md Eventbus Rule) er at MC LÆSER projektioner af sandhed — den opfinder ikke en anden.
Jarvis Mind realiserer det: ÉT live-vindue mod Centralen i stedet for 190 polls.

Dette modul er en PROJEKTIONS-HUB, ikke et data-lager: hver sektion LÆSER en eksisterende
(cachet) builder on-demand og projicerer den. Ingen duplikering → ét ground truth. Sektionerne
følger Jarvis Mind-fanerne (= MC-dæknings-kontrakten). Self-safe: en sektions-fejl må aldrig
vælte hub'en — den returnerer bare {error} for den sektion.

Realtime-modellen: Jarvis Mind åbner Centralens SSE-stream (/central/stream) for det LEVENDE
puls/feed (nerve-fyringer) + henter den aktive sektions snapshot herfra (stream-when-visible).
"""
from __future__ import annotations

from typing import Any, Callable

# Sektioner = Jarvis Mind-faner. label vises i sub-navbaren; ready=False → endnu ikke projiceret
# (placeholder i UI'et) men kendt, så fane-strukturen er komplet fra start.
_SECTION_ORDER: list[tuple[str, str]] = [
    ("overview", "Oversigt"),
    ("mind", "Sind"),
    ("observability", "Observabilitet"),
    ("agency", "Agentur"),
    ("memory", "Hukommelse"),
    ("council", "Council"),
    ("skills", "Skills"),
    ("reflection", "Refleksion"),
    ("lab", "Lab"),
    ("hardening", "Hærdning"),
]


def _safe(builder: Callable[[], Any]) -> dict[str, Any]:
    try:
        out = builder()
        return out if isinstance(out, dict) else {"value": out}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:200], "active": False}


# ── sektions-byggere (LÆSER eksisterende projektioner — opfinder ingen sandhed) ──
def _build_overview() -> dict[str, Any]:
    """Centralens egen puls = Jarvis Mind-rygraden (status/dækning/processer/clusters)."""
    from core.services.central_realtime import realtime_snapshot
    s = realtime_snapshot(trace_limit=12)
    return {
        "status": s.get("status"),
        "coverage": s.get("coverage"),
        "diagnose": s.get("diagnose"),
        "processes": s.get("processes"),
        "clusters": s.get("clusters"),
        "active": True,
    }


def _build_observability() -> dict[str, Any]:
    """Det levende vindue: nerve-feed + incidents + anomalier + læring + breakers."""
    from core.services.central_realtime import realtime_snapshot
    s = realtime_snapshot(trace_limit=40)
    return {
        "feed": s.get("feed"),
        "incidents": s.get("incidents"),
        "anomalies": s.get("anomalies"),
        "open_breakers": s.get("open_breakers"),
        "learning": s.get("learning"),
        "active": True,
    }


def _build_mind() -> dict[str, Any]:
    """De ~70 cognitive surfaces (server-cachet 75s) — Jarvis' indre liv."""
    from core.services.cognitive_architecture_surface import (
        build_cognitive_architecture_surface,
    )
    return build_cognitive_architecture_surface()


_BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "overview": _build_overview,
    "observability": _build_observability,
    "mind": _build_mind,
    # agency/memory/council/skills/reflection/lab/hardening: fyldes tab-for-tab (læser deres
    # eksisterende MC-surface-builders), så hub'en forbliver ét ground truth.
}


def mind_index() -> list[dict[str, Any]]:
    """Alle Jarvis Mind-sektioner + om de er projiceret endnu. Til sub-navbaren. Self-safe."""
    return [
        {"section": key, "label": label, "ready": key in _BUILDERS}
        for key, label in _SECTION_ORDER
    ]


def mind_section(section: str) -> dict[str, Any]:
    """Projektionen for ÉN sektion (læser den cachede kilde). Self-safe.
    Ukendt/endnu-ikke-projiceret sektion → {pending:True}."""
    key = str(section or "").strip()
    builder = _BUILDERS.get(key)
    if builder is None:
        known = {k for k, _ in _SECTION_ORDER}
        if key in known:
            return {"section": key, "pending": True, "active": False}
        return {"section": key, "error": "ukendt sektion", "active": False}
    data = _safe(builder)
    data.setdefault("section", key)
    return data


def mind_snapshot(*, sections: list[str] | None = None) -> dict[str, Any]:
    """Hub-snapshot: index + (valgfrit) fulde data for bestemte sektioner. Default = kun index
    (let). Jarvis Mind henter den AKTIVE sektion via mind_section, så vi ikke bygger alt hver
    gang. Self-safe."""
    out: dict[str, Any] = {"index": mind_index(), "sections": {}}
    for s in (sections or []):
        out["sections"][s] = mind_section(s)
    return out
