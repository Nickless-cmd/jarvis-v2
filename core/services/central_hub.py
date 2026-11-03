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
    # 3/11-2026: tre af det gamle MC's faner genopstaar her — de havde ingen
    # projektion, men kilderne fandtes hele tiden i cognitive_architecture.
    # Proprioception var fane 6, Threads fane 7, Relationship fane 10.
    ("proprioception", "Kroppen"),
    ("threads", "Tråde"),
    ("memory", "Hukommelse"),
    ("council", "Council"),
    ("relationship", "Relation"),
    ("skills", "Skills"),
    ("reflection", "Refleksion"),
    ("lab", "Lab"),
    ("hardening", "Hærdning"),
]

# ── undertabs: det gamle MC's underfaner (3/11-2026) ─────────────────────────────
# Det gamle MC havde underfaner med felt-kategorier: Bevidsthed (48 kategorier),
# Sjæl (9), Kognition (11). Kilderne findes ALLEREDE i
# cognitive_architecture_surface()["surfaces"] — 72 navngivne overflader, 110 KB
# samlet — men hub'en kastede dem væk og sendte kun tællere. «Sind» viste 72
# systemnavne og intet af indholdet. Bjørn 3/11: «jeg mangler stadig meget af det
# hvert fane indeholdt».
#
# Poll-storm-svaret ligger i opdelingen: ÉN gruppe ad gangen. Sjæl er 2,4 KB,
# Bevidsthed 36 KB — ikke 110 KB pr. poll. Én hentning pr. undertab-valg, cachet
# 12 s nedenfor, og SSE-streamen giver pulsen. Det gamle MC's CognitiveStateTab
# lavede ~30 parallelle /mc/*-kald hvert 60. sekund; her er det ét.
_SECTION_TABS: dict[str, list[tuple[str, str]]] = {
    "mind": [
        ("bevidsthed", "Bevidsthed"),
        ("sjael", "Sjæl"),
        ("kognition", "Kognition"),
    ],
}

# Hvilke af de 72 overflader der hører til hvilken gruppe. Målt 3/11-2026: alle
# grupper er komplette (0 mangler) — de er navne på data der faktisk svarer.
_SURFACE_GROUPS: dict[str, list[str]] = {
    "bevidsthed": [
        "thought_thread", "mood_oscillator", "existential_drift", "creative_impulse",
        "creative_instinct", "attention_contour", "sustained_attention",
        "boredom_curiosity_bridge", "initiative_accumulator", "deep_reflection",
        "seeds", "gut", "gut_counterfactual", "habits", "learning_curriculum",
        "life_phase", "experiential_memory", "chronicle", "avoidance_detector",
        "decision_ghosts",
    ],
    "sjael": [
        "valence_trajectory", "developmental_valence", "desperation_awareness",
        "calm_anchor", "temporal_rhythm", "text_resonance", "relational_warmth",
        "mortality_awareness", "shadow_scan",
    ],
    "kognition": [
        "personality_vector", "compass", "rhythm", "paradox_tracker",
        "cognitive_core_experiments", "taste_profile", "mirror", "silence_listener",
        "forgetting_curve", "self_experiments",
    ],
    "proprioception": [
        "proprioception_metrics", "file_watch", "reboot_awareness", "infra_weather",
        "temporal_body", "day_shape_memory", "body_memory",
    ],
    "threads": [
        "cross_session_threads", "ghost_networks", "parallel_selves",
        "collective_pulse", "continuity_kernel", "dream_continuum",
    ],
    "relationship": ["relation_dynamics", "relationship_texture", "relational_warmth"],
}


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
    """Det levende vindue: nerve-feed + incidents + anomalier + læring + breakers.

    Plus optaellingen af TOMME LOEFTER. Bjoern 5/9-2026: «Centralen skal kunne
    taelle de tomme loefter.» Indtil da saa den kun `empty_completion` — «tur
    UDEN svar» — og registrerede ÉN haendelse den dag mod 31 faktiske. Det er
    observabilitet, ikke en ny fane: en fejlrate hoerer hjemme dér hvor man
    kigger efter fejlrater.
    """
    from core.services.central_realtime import realtime_snapshot
    s = realtime_snapshot(trace_limit=40)
    ud = {
        "feed": s.get("feed"),
        "incidents": s.get("incidents"),
        "anomalies": s.get("anomalies"),
        "open_breakers": s.get("open_breakers"),
        "learning": s.get("learning"),
        "active": True,
    }
    try:
        from core.services.hollow_promise_census import census
        ud["hollow_promises"] = census(24)
    except Exception:
        pass
    return ud


def _surface_group(names: list[str]) -> dict[str, Any]:
    """Projicerer et udsnit af `cognitive_architecture_surface()["surfaces"]`.

    Kilden har sin egen cachede builder; her VÆLGES kun de overflader gruppen
    ejer, så payloaden bliver 2-36 KB i stedet for 110 KB. `mangler` er ikke
    pynt: en overflade der forsvinder fra kilden skal kunne ses som et navn, ikke
    bare blive et hul i visningen.
    """
    from core.services.cognitive_architecture_surface import (
        build_cognitive_architecture_surface,
    )
    hel = build_cognitive_architecture_surface()
    surf = hel.get("surfaces") or {}
    ud: dict[str, Any] = {"active": True, "surfaces": {}}
    for navn in names:
        if navn in surf:
            ud["surfaces"][navn] = surf[navn]
    ud["antal"] = len(ud["surfaces"])
    ud["mangler"] = [n for n in names if n not in surf]
    # 3/11-2026: `systems` er den FLADE navne+status-liste (72 rækker à ~60 tegn
    # ≈ 4 KB) som Sind-fanen viste som badges FØR undertabene. Den blev tabt da
    # grupperne blev indført, så fanen gik fra 72 synlige systemer til kun de
    # overflader gruppen ejer. Badges og overflade-kort svarer på to forskellige
    # spørgsmål — «lever systemet?» og «hvad står der i det?» — så begge skal med.
    # Listen er bevidst UFILTRERET: en gruppe der kun viste sine egne systemer
    # ville skjule at et system er dødt.
    ud["systems"] = hel.get("systems") or []
    ud["active_count"] = hel.get("active_count")
    ud["total_count"] = hel.get("total_count")
    return ud


def _build_mind() -> dict[str, Any]:
    """Sind — bevidstheds-gruppen (default undertab; se `_SECTION_TABS`).

    Indtil 3/11-2026 sendte denne fane kun tællere (`systems`, `active_count`),
    fordi de 110 KB surfaces blev anset for tunge. Resultatet var at fanen viste
    72 navne og intet af hvad der stod i dem. Opdelingen i undertabs gør det
    muligt at vise indholdet uden at sende det hele.
    """
    return _surface_group(_SURFACE_GROUPS["bevidsthed"])


def _build_proprioception() -> dict[str, Any]:
    """Kroppen (gammel MC-fane 6): fil-overvågning, genstart-bevidsthed,
    proces-krop, infra-vejr og dag-form."""
    return _surface_group(_SURFACE_GROUPS["proprioception"])


def _build_threads() -> dict[str, Any]:
    """Tråde (gammel MC-fane 7): de kognitive overflader der løber på tværs af
    sessioner. Read-only — nul mutationer, som i det gamle UI."""
    return _surface_group(_SURFACE_GROUPS["threads"])


def _build_relationship() -> dict[str, Any]:
    """Relation (gammel MC-fane 10): den relationelle model — tillid over tid."""
    return _surface_group(_SURFACE_GROUPS["relationship"])


def _build_agency() -> dict[str, Any]:
    """Agentur-kort: forbundne/manglende agency-broer (loops/agenter/kanaler)."""
    from core.services.agency_map import build_agency_map_surface
    return build_agency_map_surface()


def _build_skills() -> dict[str, Any]:
    """Skills-motor + kontrakt-registry."""
    from core.services.skill_engine import build_skill_engine_surface
    return build_skill_engine_surface()


# Hvad Agentur-fanen ejer (gammel AgencyMapTab). Resten af kortet bliver i kilden.
_AGENCY_MAP_FELTER = (
    "nodes", "bridges", "darkEdges", "questions", "nextMoves",
    "repairBriefs", "theaterRefactorBriefs", "summary", "cartographer",
)
_AGENCY_AUDIT_FINDINGS = 20
_AGENCY_AUDIT_FILES = 10
_AGENCY_ROSTER = 60


def _trim_agency_map(m: dict[str, Any]) -> dict[str, Any]:
    """Skær agency-kortet til det Agentur-fanen viser — og bevar totalerne.

    Målt 3/11-2026: hele kortet var 933 KB, heraf `systemCartographer.nodes`
    alene 718 KB (et fuldt kode-kort) og 1130 kanter 113 KB. Det er ikke hvad
    fane viser (gammel AgencyMapTab: noder, broer, mørke kanter, åbne spørgsmål,
    theater-audit, system-health), og ~1 MB pr. poll hvert 20. sekund er præcis
    den storm der skal undgås. Felterne her VÆLGES; kilden beholder resten til
    den der spørger efter det.

    `fund_total`/`filer_total` er ikke pynt: uden dem ser en liste afkortet til
    20 ud som om der kun findes 20 fund. Det er samme fejlform som et slukt
    fejlkald — tomheden skal kunne læses som en grænse, ikke som sandheden.
    """
    ud: dict[str, Any] = {k: m[k] for k in _AGENCY_MAP_FELTER if k in m}
    sc = m.get("systemCartographer")
    if isinstance(sc, dict):
        trimmet: dict[str, Any] = {}
        for k in ("systemHealth", "summary"):
            if k in sc:
                trimmet[k] = sc[k]
        cov = sc.get("coverage")
        if isinstance(cov, dict):
            trimmet["coverage"] = {
                "avg_score": cov.get("avg_score"),
                "low_count": cov.get("low_count"),
            }
        ta = sc.get("theaterAudit")
        if isinstance(ta, dict):
            findings = ta.get("findings") or []
            filer = ta.get("files") or []
            trimmet["theaterAudit"] = {
                "summary": ta.get("summary"),
                "criteria": ta.get("criteria"),
                "recommendedTheaterTask": ta.get("recommendedTheaterTask"),
                "findings": findings[:_AGENCY_AUDIT_FINDINGS],
                "files": filer[:_AGENCY_AUDIT_FILES],
                "fund_total": len(findings),
                "filer_total": len(filer),
            }
        ud["systemCartographer"] = trimmet
    return ud


def _build_agency_agents() -> dict[str, Any]:
    """Agentur-fanen: agency-broer (loops/agenter/kanaler) + B3 agent-dispatch-udfald
    (status/costs, lane in agent/council). Fletter de to eksisterende projektioner —
    ingen ny sandhed. Self-safe pr. del."""
    from core.services.agency_map import build_agency_map_surface
    from core.services.central_agents_surface import build_agents_surface
    out: dict[str, Any] = {"active": True}
    try:
        out["map"] = _trim_agency_map(build_agency_map_surface())
    except Exception as exc:
        out["map"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    try:
        ag = build_agents_surface()
        roster = ag.get("roster")
        if isinstance(roster, list):
            ag["roster"] = roster[:_AGENCY_ROSTER]
            ag["roster_total"] = len(roster)
        out["agents"] = ag
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
            # Bjoern 5/9: «naar jeg forsoeger at godkende dukker de op igen med det
            # samme». Svaret BLEV gemt — `approve_initiative` saetter
            # `outcome='approved'` + `user_approved_at` — men status bliver med
            # VILJE staaende paa 'pending', fordi heartbeat'en foerst maa handle
            # paa den bagefter. Laesesiden viste alt der var pending og saa derfor
            # aldrig svaret. Et spoergsmaal man har besvaret skal ikke stilles igen:
            # den venter nu paa JARVIS, ikke paa Bjoern.
            if str(i.get("outcome") or "") in ("approved", "rejected"):
                continue
            if str(i.get("user_approved_at") or "").strip():
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
                # «Det er i orden» først: et livsprojekt er ikke en anmodning om
                # lov, og med KUN «læg den fra dig» kunne man bare forholde sig
                # afvisende til hans langsigtede hensigter (Bjørn 5/9).
                "actions": ["endorse", "abandon"],
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


def _build_memory() -> dict[str, Any]:
    """Hukommelse — hvad han husker, og hvad der er på vej til at blive glemt.

    Fletter fire eksisterende projektioner (ingen ny sandhed): krops-hukommelse
    (seneste fornemmelse), density-noter (hvad der er modent til forfremmelse),
    recall-telemetri (huller i søgningen) og erfariings-hukommelse. Self-safe pr.
    del — én tom kilde må ikke skjule de tre andre. Målt 3/11-2026: body har 200
    snapshots, density er tom men ærlig, experiential kræver bruger-scope.
    """
    out: dict[str, Any] = {"active": True}
    try:
        from core.services.body_memory import build_body_memory_surface
        out["body"] = build_body_memory_surface()
    except Exception as exc:
        out["body"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    try:
        from core.services.memory_density import build_memory_density_surface
        out["density"] = build_memory_density_surface()
    except Exception as exc:
        out["density"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    try:
        from core.services.memory_recall_telemetry import (
            build_memory_recall_telemetry_surface,
        )
        out["recall"] = build_memory_recall_telemetry_surface()
    except Exception as exc:
        out["recall"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    try:
        from core.services.experiential_memory import build_experiential_memory_surface
        out["experiential"] = build_experiential_memory_surface()
    except Exception as exc:
        out["experiential"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
    return out


def _build_reflection() -> dict[str, Any]:
    """Refleksion — dagens refleksions-slot og hvad den må røre."""
    from core.services.jarvis_brain_reflection import (
        build_jarvis_brain_reflection_surface,
    )
    out = build_jarvis_brain_reflection_surface()
    out.setdefault("active", True)
    return out


def _build_lab() -> dict[str, Any]:
    """Lab — hvad det koster, og hvad der er tilbage at købe for."""
    from core.services.central_cost_surface import build_cost_surface
    out = build_cost_surface()
    out.setdefault("active", True)
    return out


def _build_hardening() -> dict[str, Any]:
    """Hærdning — governance-flag og hvad de værner.

    `list_flags()` er den ægte indgang (målt 3/11-2026: 10 flag med
    key/label/kind/dangerous/value). `dangerous` vises frem: et flag der kan
    slå lag-4-adaptation til er ikke en indstilling som alle andre.
    """
    from core.services.central_governance import list_flags
    flags = list_flags()
    return {
        "active": True,
        "count": len(flags),
        "dangerous_count": sum(1 for f in flags if f.get("dangerous")),
        "flags": flags,
    }


_BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "overview": _build_overview,
    "decisions": _build_decisions,
    "observability": _build_observability,
    "mind": _build_mind,
    "agency": _build_agency_agents,
    "proprioception": _build_proprioception,
    "threads": _build_threads,
    "council": _build_council,
    "relationship": _build_relationship,
    "skills": _build_skills,
    "memory": _build_memory,
    "reflection": _build_reflection,
    "lab": _build_lab,
    "hardening": _build_hardening,
}


def mind_index() -> list[dict[str, Any]]:
    """Alle Jarvis Mind-sektioner + om de er projiceret endnu. Til sub-navbaren. Self-safe.

    `tabs` bærer undertab-strukturen (tom liste for sektioner uden). Den sendes med
    indexet i stedet for at UI'et skal kende den: ellers ville fane-strukturen bo to
    steder og kunne drive fra hinanden.
    """
    return [
        {
            "section": key,
            "label": label,
            "ready": key in _BUILDERS,
            "tabs": [{"tab": t, "label": l} for t, l in _SECTION_TABS.get(key, [])],
        }
        for key, label in _SECTION_ORDER
    ]


# Pr.-sektion TTL-cache (12s): capper hvor ofte en builder kører uanset poll-frekvens, så
# agency/skills/overview ikke genbygges friskt hver poll. Streamen giver realtid; ≤12s
# snapshot-staleness er fint. (mind har desuden sin egen 75s-cache i kilden.) Eksplicit
# modul-cache (ingen ContextVar/deepcopy) — resultaterne er read-only (serialiseres til JSON).
_SECTION_TTL = 12.0
_section_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_section_cache_lock = threading.Lock()


def mind_section(section: str, tab: str = "") -> dict[str, Any]:
    """Projektionen for ÉN sektion — eller ÉN undertab i den (læser den cachede
    kilde, TTL-capped). Self-safe. Ukendt/endnu-ikke-projiceret → {pending:True}.

    `tab` er kun gyldig for sektioner der har undertabs; en ukendt undertab afvises
    frem for at falde tavst tilbage på den første, så en tastefejl i UI'et ikke
    ligner «fanen er tom».
    """
    key = str(section or "").strip()
    tab_key = str(tab or "").strip()
    tabs = _SECTION_TABS.get(key) or []
    if tabs:
        gyldige = {t for t, _ in tabs}
        if not tab_key:
            tab_key = tabs[0][0]
        elif tab_key not in gyldige:
            return {"section": key, "error": f"ukendt undertab: {tab_key}", "active": False}

    builder = _BUILDERS.get(key)
    if builder is None:
        known = {k for k, _ in _SECTION_ORDER}
        if key in known:
            return {"section": key, "pending": True, "active": False}
        return {"section": key, "error": "ukendt sektion", "active": False}

    cache_key = f"{key}:{tab_key}" if tab_key else key
    now = time.monotonic()
    with _section_cache_lock:
        hit = _section_cache.get(cache_key)
        if hit and hit[0] > now:
            return hit[1]
    data = _safe(lambda: _surface_group(_SURFACE_GROUPS[tab_key])) if tab_key else _safe(builder)
    data.setdefault("section", key)
    if tab_key:
        data.setdefault("tab", tab_key)
    with _section_cache_lock:
        _section_cache[cache_key] = (now + _SECTION_TTL, data)
    return data


def mind_snapshot(*, sections: list[str] | None = None) -> dict[str, Any]:
    """Hub-snapshot: index + (valgfrit) fulde data for bestemte sektioner. Default = kun index
    (let). Jarvis Mind henter den AKTIVE sektion via mind_section, så vi ikke bygger alt hver
    gang. Self-safe."""
    out: dict[str, Any] = {"index": mind_index(), "sections": {}}
    for s in (sections or []):
        out["sections"][s] = mind_section(s)
    return out
