"""Central-absorb routes — MC-kategorier PROJICERET som levende central-nerver.

Hver route her tager en eksisterende producent-service (den samme data som et
``/mc/*``-endpoint viser) og:

  1. **Projicerer** producentens surface uændret ud til owner (owner-gated).
  2. **Absorberer** en kompakt liveness-værdi som en levende central-nerve via
     ``central_absorb.absorb`` (fuld behandling: observe + trace + flag + notif
     + learning-hook).

Dette er første skridt i "Centralen absorberer ALT": hver MC-kategori flyttes
ind i Centralen som en nerve, før MC-delen afmonteres.

SELF-SAFE: en producent-fejl må aldrig vælte routen — den falder tilbage til en
tom liste og svarer 200. Owner-gaten håndhæves altid først.
"""
from __future__ import annotations

from fastapi import APIRouter

from apps.api.jarvis_api.routes.central_auth import require_central_owner
from core.services.central_absorb import absorb

router = APIRouter(prefix="/central", tags=["central-agents"])


@router.get("/agents")
async def get_agents() -> dict:
    """Projicér agent-runtime-surfacen (samme som ``/mc/agents``) + absorbér den.

    Owner-gated. Self-safe: producent-fejl → tom roster, stadig 200.
    """
    require_central_owner()

    try:
        from core.services.agent_runtime import build_agent_runtime_surface
        surface = build_agent_runtime_surface()
    except Exception:
        surface = {}

    if isinstance(surface, dict):
        agents = surface.get("agents")
    else:
        agents = surface
    agents = agents or []

    # Absorbér som levende nerve — tæller + flag hvis der ingen agenter er.
    absorb(
        "agent",
        "roster",
        {"count": len(agents)},
        flag_if=lambda v: v["count"] == 0,
        flag_reason="ingen aktive agenter",
    )

    return {"agents": agents, "count": len(agents)}


@router.get("/costs-daily")
async def get_costs_daily() -> dict:
    """Projicér cost-timeserien (samme data som ``/mc/costs``) + absorbér den.

    Owner-gated. Self-safe: hver producent-fejl → tom/nul-fallback, stadig 200.
    Absorberer en kompakt dags-omkostnings-værdi som en levende central-nerve og
    flagger hvis i dag > 150% af i går.
    """
    require_central_owner()

    from core.costing import ledger

    try:
        days = ledger.daily_cost_summary()
    except Exception:
        days = []
    if not isinstance(days, list):
        days = []

    try:
        today = float(ledger.today_cost())
    except Exception:
        today = 0.0

    try:
        week = float(ledger.this_week_cost())
    except Exception:
        week = 0.0

    try:
        summary = ledger.telemetry_summary()
    except Exception:
        summary = {}
    if not isinstance(summary, dict):
        summary = {}

    # Dag-over-dag: aggregér total_cost pr. dag (sum over lanes). ──────────────
    per_day: dict[str, float] = {}
    order: list[str] = []
    for row in days:
        if not isinstance(row, dict):
            continue
        day = row.get("day")
        if not isinstance(day, str):
            continue
        try:
            cost = float(row.get("total_cost") or 0.0)
        except Exception:
            cost = 0.0
        if day not in per_day:
            per_day[day] = 0.0
            order.append(day)
        per_day[day] += cost

    today_total = per_day[order[0]] if len(order) >= 1 else 0.0
    prev_total = per_day[order[1]] if len(order) >= 2 else 0.0

    absorb(
        "cost",
        "daily",
        {"today": today_total, "prev": prev_total, "usd_today": today},
        flag_if=lambda v: v["prev"] > 0 and v["today"] > v["prev"] * 1.5,
        flag_reason="dags-omkostning >150% af går",
        learn_key="cost_daily",
    )

    return {
        "days": days,
        "today_cost": today,
        "week_cost": week,
        "summary": summary,
        "today_total": today_total,
        "prev_total": prev_total,
    }


@router.get("/council")
async def get_council() -> dict:
    """Projicér råds-/swarm-surfacen (samme som ``/mc/council``) + absorbér den.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200.
    Flagger hvis der ingen råds-sessioner er.
    """
    require_central_owner()

    try:
        from core.services.agent_runtime import build_council_surface
        surface = build_council_surface(limit=40)
    except Exception:
        surface = {}

    sessions = (
        (surface.get("sessions") or surface.get("councils") or [])
        if isinstance(surface, dict)
        else []
    )

    absorb(
        "council",
        "sessions",
        {"count": len(sessions)},
        flag_if=lambda v: v["count"] == 0,
        flag_reason="ingen aktive råd",
    )

    return {
        "council": surface if isinstance(surface, dict) else {},
        "sessions": sessions,
        "count": len(sessions),
    }


@router.get("/queues/scheduled")
async def get_scheduled() -> dict:
    """Projicér ventende planlagte opgaver + absorbér antallet som nerve.

    Owner-gated. Self-safe: producent-fejl → tom liste, stadig 200.
    Flagger hvis der er mange (>20) ventende opgaver.
    """
    require_central_owner()

    try:
        from core.services.scheduled_tasks import list_pending_for_current_user
        tasks = list_pending_for_current_user()
    except Exception:
        tasks = []
    tasks = tasks or []

    absorb(
        "queue",
        "scheduled",
        {"count": len(tasks)},
        flag_if=lambda v: v["count"] > 20,
        flag_reason="mange ventende opgaver",
    )

    return {"tasks": tasks, "count": len(tasks)}


@router.get("/events")
async def get_events(limit: int = 50, family: str | None = None) -> dict:
    """Projicér eventbus-feedet (recent / recent_by_family) + absorbér en tæller.

    Owner-gated. Self-safe: producent-fejl → tom liste, stadig 200. Kun en
    kompakt tæller absorberes — aldrig event-payloads i nerve-værdien.
    """
    require_central_owner()

    try:
        from core.eventbus.bus import event_bus
        if family:
            items = event_bus.recent_by_family(family, limit=max(limit, 1))
        else:
            items = event_bus.recent(limit=max(limit, 1))
    except Exception:
        items = []
    items = items or []

    absorb("events", "feed", {"count": len(items), "family": family or "all"})

    return {"items": items, "count": len(items), "family": family}


@router.get("/memory-health")
async def get_memory_health() -> dict:
    """Projicér memory-pipeline-surfacen (genbrug ``mc_memory_pipeline``) + absorbér.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200. Flagger
    hvis dagens journal endnu mangler.
    """
    require_central_owner()

    try:
        from apps.api.jarvis_api.routes.mission_control import mc_memory_pipeline
        surface = mc_memory_pipeline(limit=10)
    except Exception:
        surface = {}
    if not isinstance(surface, dict):
        surface = {}

    brain = surface.get("jarvis_brain") or {}
    added_today = brain.get("added_today") or 0
    journal = surface.get("daily_journal") or {}
    journal_today = bool(journal.get("today_exists"))

    absorb(
        "memory",
        "pipeline",
        {"added_today": added_today, "journal_today": journal_today},
        flag_if=lambda v: not v["journal_today"],
        flag_reason="dagens journal mangler endnu",
    )

    return {"memory": surface, "added_today": added_today, "journal_today": journal_today}


@router.get("/runs")
async def get_runs(limit: int = 20) -> dict:
    """Projicér de seneste visible runs + absorbér en kompakt liveness-tæller.

    Owner-gated. Self-safe: producent-fejl → tom liste, stadig 200. Flagger hvis
    der er fejlede/afbrudte runs blandt de seneste.
    """
    require_central_owner()
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=max(limit, 1))
    except Exception:
        runs = []
    runs = runs or []
    failed = [
        r for r in runs
        if isinstance(r, dict) and str(r.get("status") or "") in ("failed", "cancelled")
    ]
    absorb(
        "run",
        "list",
        {"count": len(runs), "failed": len(failed)},
        flag_if=lambda v: v["failed"] > 0,
        flag_reason="fejlede/afbrudte runs",
    )
    return {"runs": runs, "count": len(runs), "failed_count": len(failed)}


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str) -> dict:
    """Projicér én run-detalje (opslag i de seneste 50) + absorbér fund/status.

    Owner-gated. Self-safe: producent-fejl → ikke-fundet, stadig 200.
    """
    require_central_owner()
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=50)
    except Exception:
        runs = []
    match = next(
        (
            r for r in (runs or [])
            if isinstance(r, dict) and str(r.get("run_id") or "") == str(run_id)
        ),
        None,
    )
    absorb(
        "run",
        "detail",
        {"found": bool(match), "status": (match or {}).get("status") if match else None},
    )
    return {"run": match, "found": bool(match)}


@router.get("/autonomy")
async def get_autonomy() -> dict:
    """Projicér autonomi-forslags-køen + absorbér den som nerve.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200.
    Flagger hvis der er ventende forslag (afventer godkendelse).
    """
    require_central_owner()

    try:
        from core.services.autonomy_proposal_queue import build_autonomy_proposal_surface
        surface = build_autonomy_proposal_surface(limit=20)
    except Exception:
        surface = {}

    proposals = (
        (surface.get("proposals") or surface.get("items") or [])
        if isinstance(surface, dict)
        else []
    )
    pending = [
        p for p in proposals
        if isinstance(p, dict) and str(p.get("status") or "") == "pending"
    ]

    absorb(
        "autonomy",
        "proposal",
        {"count": len(proposals), "pending": len(pending)},
        flag_if=lambda v: v["pending"] > 0,
        flag_reason="ventende autonomi-forslag",
    )

    return {
        "autonomy": surface if isinstance(surface, dict) else {},
        "proposals": proposals,
        "pending_count": len(pending),
        "count": len(proposals),
    }


@router.get("/attention")
async def get_attention() -> dict:
    """Projicér attention-budget-surfacen + absorbér liveness.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200.
    """
    require_central_owner()
    try:
        from core.services.attention_budget import build_attention_budget_surface
        s = build_attention_budget_surface()
    except Exception:
        s = {}
    s = s if isinstance(s, dict) else {}
    absorb("attention", "budget", {"active": bool(s)}, learn_key="attention:budget")
    return {"attention": s}


@router.get("/skills")
async def get_skills() -> dict:
    """Projicér skill-engine + skill-contract-registry + absorbér liveness.

    Owner-gated. Self-safe: hver producent-fejl → tomt surface, stadig 200.
    """
    require_central_owner()
    try:
        from core.services.skill_engine import build_skill_engine_surface
        eng = build_skill_engine_surface()
    except Exception:
        eng = {}
    try:
        from core.services.skill_contract_registry import (
            build_skill_contract_registry_surface,
        )
        reg = build_skill_contract_registry_surface()
    except Exception:
        reg = {}
    eng = eng if isinstance(eng, dict) else {}
    reg = reg if isinstance(reg, dict) else {}
    absorb("skill", "engine", {"active": bool(eng)}, learn_key="skill:engine")
    absorb("skill", "contracts", {"active": bool(reg)}, learn_key="skill:contracts")
    return {"engine": eng, "contracts": reg}


@router.get("/integrity")
async def get_integrity() -> dict:
    """Projicér self-deception-guard-surfacen + absorbér liveness.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200.
    """
    require_central_owner()
    try:
        from core.services.self_deception_guard import (
            build_self_deception_guard_surface,
        )
        s = build_self_deception_guard_surface()
    except Exception:
        s = {}
    s = s if isinstance(s, dict) else {}
    absorb(
        "integrity",
        "self_deception",
        {"active": bool(s)},
        learn_key="integrity:self_deception",
    )
    return {"integrity": s}


@router.get("/experiments")
async def get_experiments() -> dict:
    """Projicér cognitive-core-experiments-surfacen + absorbér liveness.

    Owner-gated. Self-safe: producent-fejl → tomt surface, stadig 200.
    """
    require_central_owner()
    try:
        from core.services.cognitive_core_experiments import (
            build_cognitive_core_experiments_surface,
        )
        s = build_cognitive_core_experiments_surface()
    except Exception:
        s = {}
    s = s if isinstance(s, dict) else {}
    absorb("experiment", "runner", {"active": bool(s)}, learn_key="experiment:runner")
    return {"experiments": s}


# Kun visible-execution-relevante flags projiceres — aldrig hele settings-dict'en
# (undgå secrets/støj). Whitelist dækker både de nominelle execution-flags og de
# faktisk-eksisterende visible-lane-nøgler; ikke-eksisterende nøgler springes over.
_EXECUTION_KEYS = (
    "visible_execution_mode",
    "generative_autonomy_enabled",
    "cheap_lane_enabled",
    "agenda_authoritative",
    "gut_consumer_mode",
    "lag4_adaptation",
    "visible_model_provider",
    "visible_model_name",
    "visible_auth_profile",
    "cheap_model_lane",
    "primary_model_lane",
)


@router.get("/execution")
async def get_execution() -> dict:
    """Projicér visible-execution-config (whitelisted flags) + absorbér liveness.

    Owner-gated. Self-safe: producent-fejl → tomt config, stadig 200. KUN
    whitelistede execution-flags returneres — aldrig hele settings-dict'en.
    """
    require_central_owner()
    try:
        from core.runtime.settings import load_settings
        st = load_settings()
        raw = st.to_dict() if hasattr(st, "to_dict") else st
    except Exception:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    cfg = {k: raw.get(k) for k in _EXECUTION_KEYS if k in raw}
    absorb("execution", "config", cfg, learn_key="execution:config")
    return {"execution": cfg}
