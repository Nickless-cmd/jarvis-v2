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

import threading
import time
from typing import Any, Callable

# Sektioner = Jarvis Mind-faner. label vises i sub-navbaren; ready=False → endnu ikke projiceret
# (placeholder i UI'et) men kendt, så fane-strukturen er komplet fra start.
_SECTION_ORDER: list[tuple[str, str]] = [
    ("overview", "Oversigt"),
    # 2026-09-05: «Beslutninger» ligger nummer to med vilje. Maalt samme dag:
    # 48 initiativer i koeen — 6 ventende, 26 UDLOEBET uden svar, og NUL
    # nogensinde godkendt eller afvist i systemets levetid. Ruterne fandtes
    # (/mc/initiatives/{id}/approve|reject, /mc/life-projects/{id}/abandon) —
    # der var bare ingen knap nogen steder. Han spurgte 48 gange og fik intet
    # svar, fordi spoergsmaalet aldrig naaede et menneske.
    ("decisions", "Beslutninger"),
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
    """De ~70 cognitive surfaces — Jarvis' indre liv. Sender KUN den lette projektion (systems-
    liste + tællere), IKKE den fulde 140KB surfaces-dict (Bjørn: 'lidt tung'). Den underliggende
    build er server-cachet 75s; her trimmer vi payloaden så fanen er let at hente+rendere."""
    from core.services.cognitive_architecture_surface import (
        build_cognitive_architecture_surface,
    )
    s = build_cognitive_architecture_surface()
    return {
        "systems": s.get("systems"),
        "active_count": s.get("active_count"),
        "total_count": s.get("total_count"),
        "summary": s.get("summary"),
        "active": True,
    }


def _build_agency() -> dict[str, Any]:
    """Agentur-kort: forbundne/manglende agency-broer (loops/agenter/kanaler)."""
    from core.services.agency_map import build_agency_map_surface
    return build_agency_map_surface()


def _build_skills() -> dict[str, Any]:
    """Skills-motor + kontrakt-registry."""
    from core.services.skill_engine import build_skill_engine_surface
    return build_skill_engine_surface()


def _build_agency_agents() -> dict[str, Any]:
    """Agentur-fanen: agency-broer (loops/agenter/kanaler) + B3 agent-dispatch-udfald
    (status/costs, lane in agent/council). Fletter de to eksisterende projektioner —
    ingen ny sandhed. Self-safe pr. del."""
    from core.services.agency_map import build_agency_map_surface
    from core.services.central_agents_surface import build_agents_surface
    out: dict[str, Any] = {"active": True}
    try:
        out["map"] = build_agency_map_surface()
    except Exception as exc:
        out["map"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    try:
        out["agents"] = build_agents_surface()
    except Exception as exc:
        out["agents"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    return out


def _build_council() -> dict[str, Any]:
    """Council-fanen (B3): convocations/deadlocks/roller. Empty-safe."""
    from core.services.central_agents_surface import build_council_surface
    out = build_council_surface()
    out.setdefault("active", True)
    return out


def _build_decisions() -> dict[str, Any]:
    """Hvad venter paa et menneske — samlet ét sted.

    Projicerer eksisterende sandhed (initiativ-koeen, livsprojekter,
    godkendelser); opfinder ingen ny. Sorteret saa det aeldste staar oeverst —
    en ting der har ventet i tre uger er mere presserende end en fra i morges.
    """
    ventende: list[dict[str, Any]] = []

    try:
        from core.services.initiative_queue import get_initiative_queue_state
        st = get_initiative_queue_state() or {}
        from core.services.initiative_queue import _er_ikke_et_initiativ
        for i in (st.get("pending") or []):
            # Porten gaelder ogsaa paa LAESESIDEN. Den stopper nye poster ved
            # kilden, men koeen rummer stadig det der blev gemt foer den fandtes
            # — «Use JSON format with thought…» og «What might the next move
            # be?». De maa ikke staa foran et menneske som beslutninger der
            # venter. De udloeber af sig selv; indtil da vises de bare ikke.
            if _er_ikke_et_initiativ(str(i.get("focus") or "")):
                continue
            ventende.append({
                "kind": "initiative",
                "id": str(i.get("initiative_id") or ""),
                "text": str(i.get("focus") or "")[:200],
                "why": str(i.get("why_text") or i.get("rationale") or "")[:240],
                "priority": str(i.get("priority") or "medium"),
                "created_at": str(i.get("created_at") or ""),
                "actions": ["approve", "reject"],
            })
        koe = {
            "pending": int(st.get("pending_count") or 0),
            "expired_unanswered": int(st.get("expired_count") or 0),
            "answered": int(st.get("approved_count") or 0) + int(st.get("rejected_count") or 0),
        }
    except Exception:
        koe = {}

    try:
        from core.services.life_projects import build_life_projects_surface
        lp = build_life_projects_surface() or {}
        for p_ in (lp.get("items") or []):
            ventende.append({
                "kind": "life_project",
                "id": str(p_.get("initiative_id") or ""),
                "text": str(p_.get("focus") or "")[:200],
                "why": str(p_.get("why_text") or "")[:240],
                "priority": "low",
                "created_at": str(p_.get("created_at") or ""),
                "actions": ["abandon"],
            })
    except Exception:
        pass

    ventende.sort(key=lambda x: str(x.get("created_at") or ""))
    return {
        "active": True,
        "count": len(ventende),
        "queue": koe,
        # Tallet der goer ondt, og som skal staa oeverst: hvor mange spoergsmaal
        # der udloeb uden at nogen svarede.
        "unanswered_note": (
            "%d initiativer er udloebet uden svar" % int(koe.get("expired_unanswered") or 0)
            if koe.get("expired_unanswered") else ""
        ),
        "items": ventende[:40],
    }


_BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "overview": _build_overview,
    "decisions": _build_decisions,
    "observability": _build_observability,
    "mind": _build_mind,
    "agency": _build_agency_agents,
    "council": _build_council,
    "skills": _build_skills,
    # memory/reflection/lab/hardening: fyldes tab-for-tab (læser deres eksisterende
    # service-surface-builders), så hub'en forbliver ét ground truth.
}


def mind_index() -> list[dict[str, Any]]:
    """Alle Jarvis Mind-sektioner + om de er projiceret endnu. Til sub-navbaren. Self-safe."""
    return [
        {"section": key, "label": label, "ready": key in _BUILDERS}
        for key, label in _SECTION_ORDER
    ]


# Pr.-sektion TTL-cache (12s): capper hvor ofte en builder kører uanset poll-frekvens, så
# agency/skills/overview ikke genbygges friskt hver poll. Streamen giver realtid; ≤12s
# snapshot-staleness er fint. (mind har desuden sin egen 75s-cache i kilden.) Eksplicit
# modul-cache (ingen ContextVar/deepcopy) — resultaterne er read-only (serialiseres til JSON).
_SECTION_TTL = 12.0
_section_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_section_cache_lock = threading.Lock()


def mind_section(section: str) -> dict[str, Any]:
    """Projektionen for ÉN sektion (læser den cachede kilde, TTL-capped). Self-safe.
    Ukendt/endnu-ikke-projiceret sektion → {pending:True}."""
    key = str(section or "").strip()
    builder = _BUILDERS.get(key)
    if builder is None:
        known = {k for k, _ in _SECTION_ORDER}
        if key in known:
            return {"section": key, "pending": True, "active": False}
        return {"section": key, "error": "ukendt sektion", "active": False}

    now = time.monotonic()
    with _section_cache_lock:
        hit = _section_cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    data = _safe(builder)
    data.setdefault("section", key)
    with _section_cache_lock:
        _section_cache[key] = (now + _SECTION_TTL, data)
    return data


def mind_snapshot(*, sections: list[str] | None = None) -> dict[str, Any]:
    """Hub-snapshot: index + (valgfrit) fulde data for bestemte sektioner. Default = kun index
    (let). Jarvis Mind henter den AKTIVE sektion via mind_section, så vi ikke bygger alt hver
    gang. Self-safe."""
    out: dict[str, Any] = {"index": mind_index(), "sections": {}}
    for s in (sections or []):
        out["sections"][s] = mind_section(s)
    return out
