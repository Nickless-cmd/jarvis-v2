"""Mission Control routes: runs, overview, events, costs, approvals, memory-pipeline, autonomy, initiatives, operations

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/liveness")
def mc_liveness(table: str = "") -> dict:
    """Liveness-sandheds-flade (Stage 2, anti-konfabulation): klassificér en tabel
    (active/replaced/manual_only/orphaned/wired) eller få det aggregerede overblik.
    Så Mission Control viser 'afløst af X' i stedet for 'tom/død'."""
    from core.services.liveness_registry import classify_table, liveness_summary
    if table:
        return classify_table(table)
    return liveness_summary()


@router.get("/overview")
def mc_overview() -> dict:
    with connect() as conn:
        event_count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    costs = telemetry_summary()
    latest_event = _latest_item(event_bus.recent(limit=1))
    latest_cost = _latest_item(recent_costs(limit=1))
    settings = load_settings()
    visible = visible_execution_readiness()

    return {
        "ok": True,
        "events": int(event_count),
        "cost_rows": costs["cost_rows"],
        "input_tokens": costs["input_tokens"],
        "output_tokens": costs["output_tokens"],
        "total_cost_usd": costs["total_cost_usd"],
        "runtime": {
            "app": settings.app_name,
            "environment": settings.environment,
            "host": settings.host,
            "port": settings.port,
            "settings_path": str(SETTINGS_FILE),
            "state_dir": str(STATE_DIR),
            "workspaces_dir": str(WORKSPACES_DIR),
        },
        "visible_execution": visible,
        "visible_run": _visible_run_surface(),
        "capability_invocation": _capability_invocation_surface(),
        "latest_event": latest_event,
        "latest_cost": latest_cost,
    }


@router.get("/events")
def mc_events(limit: int = 50, family: str | None = None) -> dict:
    items = event_bus.recent(limit=max(limit, 1))
    if family:
        items = [item for item in items if item["family"] == family]
        items = items[:limit]
    return {
        "items": items,
        "meta": {
            "limit": limit,
            "family": family,
            "returned": len(items),
        },
    }


@router.get("/costs")
def mc_costs(limit: int = 50) -> dict:
    return {
        "summary": telemetry_summary(),
        "items": recent_costs(limit=limit),
    }


@router.get("/runs")
def mc_runs(limit: int = 20) -> dict:
    surface = _visible_run_surface()
    work = _visible_work_surface()
    recent_runs = list(surface.get("persisted_recent_runs") or [])[: max(limit, 1)]
    failed_runs = [
        item
        for item in recent_runs
        if str(item.get("status") or "") in {"failed", "cancelled"}
    ]
    return {
        "active_run": surface.get("active_run"),
        "last_outcome": surface.get("last_outcome"),
        "last_capability_use": surface.get("last_capability_use"),
        "recent_runs": recent_runs,
        "recent_events": list(surface.get("recent_events") or []),
        "recent_work_units": list(work.get("persisted_recent_units") or [])[:8],
        "recent_work_notes": list(work.get("persisted_recent_notes") or [])[:8],
        "summary": {
            "active": bool(surface.get("active")),
            "recent_count": len(recent_runs),
            "failed_count": len(failed_runs),
        },
    }


@router.get("/approvals")
def mc_approvals(limit: int = 20) -> dict:
    surface = _capability_invocation_surface()
    requests = list(surface.get("recent_approval_requests") or [])[: max(limit, 1)]
    pending = [item for item in requests if str(item.get("status") or "") == "pending"]
    approved = [
        item for item in requests if str(item.get("status") or "") == "approved"
    ]
    return {
        "requests": requests,
        "recent_invocations": list(surface.get("persisted_recent_invocations") or [])[
            : max(limit, 1)
        ],
        "recent_events": list(surface.get("recent_events") or []),
        "summary": {
            "pending_count": len(pending),
            "approved_count": len(approved),
            "request_count": len(requests),
        },
    }


@router.get("/memory-pipeline")
def mc_memory_pipeline(limit: int = 10) -> dict:
    """Memory-pipeline status surface (added 2026-06-09).

    Read-only diagnostisk view over de fire memory-pipes:
      1. runtime_contract_candidates → MEMORY.md (pending + recent applied)
      2. auto_remember_subscriber → jarvis_brain (entries today)
      3. daily_journal daemon (today's journal status)
      4. jarvis_brain totals (file counts per kind)

    Bruges af Mission Control til at vise om pipen er live, og af Bjørn
    til at se hvad der står og venter på at blive applied.
    """
    import os
    import sqlite3
    from datetime import UTC, datetime
    from pathlib import Path

    jarvis_home = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
    db_path = jarvis_home / "state" / "jarvis.db"
    today = datetime.now(UTC).date().isoformat()
    n = max(int(limit), 1)

    # ── 1. MEMORY.md candidate pipeline ───────────────────────────────────
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        pending = conn.execute(
            """SELECT canonical_key, summary, confidence, evidence_class,
                      created_at, updated_at
               FROM runtime_contract_candidates
               WHERE target_file='MEMORY.md' AND status='proposed'
               ORDER BY updated_at DESC LIMIT ?""",
            (n,),
        ).fetchall()
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM runtime_contract_candidates "
            "WHERE target_file='MEMORY.md' AND status='proposed'"
        ).fetchone()[0]
        applied_count_total = conn.execute(
            "SELECT COUNT(*) FROM runtime_contract_candidates "
            "WHERE target_file='MEMORY.md' AND status='applied'"
        ).fetchone()[0]
        applied_today = conn.execute(
            "SELECT COUNT(*) FROM runtime_contract_candidates "
            "WHERE target_file='MEMORY.md' AND status='applied' "
            "AND date(updated_at) = ?",
            (today,),
        ).fetchone()[0]
        recent_applied = conn.execute(
            """SELECT canonical_key, summary, updated_at
               FROM runtime_contract_candidates
               WHERE target_file='MEMORY.md' AND status='applied'
               ORDER BY updated_at DESC LIMIT ?""",
            (n,),
        ).fetchall()
        last_write = conn.execute(
            """SELECT target_file, write_status, created_at
               FROM runtime_contract_file_writes
               WHERE target_file='MEMORY.md'
               ORDER BY created_at DESC LIMIT 1"""
        ).fetchone()
        conn.close()
        contract_pipeline = {
            "pending_count": int(pending_count),
            "applied_count_total": int(applied_count_total),
            "applied_today": int(applied_today),
            "pending_sample": [
                {
                    "canonical_key": str(r["canonical_key"]),
                    "summary": str(r["summary"] or "")[:200],
                    "confidence": str(r["confidence"]),
                    "evidence_class": str(r["evidence_class"]),
                    "updated_at": str(r["updated_at"]),
                }
                for r in pending
            ],
            "recent_applied": [
                {
                    "canonical_key": str(r["canonical_key"]),
                    "summary": str(r["summary"] or "")[:200],
                    "applied_at": str(r["updated_at"]),
                }
                for r in recent_applied
            ],
            "last_write": (
                {
                    "target_file": str(last_write["target_file"]),
                    "write_status": str(last_write["write_status"]),
                    "created_at": str(last_write["created_at"]),
                }
                if last_write else None
            ),
        }
    except Exception as exc:
        contract_pipeline = {"error": str(exc)}

    # ── 2. jarvis_brain auto-remember activity ────────────────────────────
    brain_dir = jarvis_home / "shared" / "jarvis_brain"
    brain_kinds = {}
    brain_today_count = 0
    brain_recent: list[dict] = []
    try:
        if brain_dir.exists():
            for kind in ("fakta", "indsigt", "observation", "reference"):
                kdir = brain_dir / kind
                if not kdir.exists():
                    brain_kinds[kind] = 0
                    continue
                files = list(kdir.glob("*.md"))
                brain_kinds[kind] = len(files)
                for f in files:
                    if f.name.startswith(today):
                        brain_today_count += 1
                        brain_recent.append({
                            "kind": kind,
                            "name": f.name,
                            "size_bytes": f.stat().st_size,
                        })
            brain_recent.sort(key=lambda x: x["name"], reverse=True)
            brain_recent = brain_recent[:n]
    except Exception as exc:
        brain_kinds = {"error": str(exc)}

    # ── 3. Daily journal status ───────────────────────────────────────────
    try:
        from core.services.daily_journal import journal_exists_for
        from datetime import date as _date
        today_date = _date.fromisoformat(today)
        journal_today = journal_exists_for(today_date)
        journal_obs_dir = jarvis_home / "shared" / "jarvis_brain" / "observation"
        recent_journals = []
        if journal_obs_dir.exists():
            for f in sorted(journal_obs_dir.glob("*-daily.md"), reverse=True)[:5]:
                recent_journals.append({
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                })
    except Exception as exc:
        journal_today = False
        recent_journals = []

    return {
        "active": True,
        "as_of": datetime.now(UTC).isoformat(),
        "memory_md_pipeline": contract_pipeline,
        "jarvis_brain": {
            "total_by_kind": brain_kinds,
            "added_today": brain_today_count,
            "recent_today": brain_recent,
        },
        "daily_journal": {
            "today_exists": bool(journal_today),
            "today_date": today,
            "recent": recent_journals,
        },
    }


@router.get("/autonomy/proposals")
def mc_autonomy_proposals(limit: int = 30) -> dict:
    """MC surface for Niveau 2 autonomy proposal queue.

    Returns pending proposals awaiting Bjørn approval plus recent
    resolved history.
    """
    from core.services.autonomy_proposal_queue import (
        build_autonomy_proposal_surface,
    )

    return build_autonomy_proposal_surface(limit=max(int(limit), 1))


@router.post("/autonomy/proposals/{proposal_id}/approve")
def mc_approve_autonomy_proposal(proposal_id: str, note: str = "") -> dict:
    from core.services.autonomy_proposal_queue import (
        approve_proposal,
    )

    return approve_proposal(proposal_id, resolution_note=note)


@router.post("/autonomy/proposals/{proposal_id}/reject")
def mc_reject_autonomy_proposal(proposal_id: str, note: str = "") -> dict:
    from core.services.autonomy_proposal_queue import (
        reject_proposal,
    )

    return reject_proposal(proposal_id, resolution_note=note)


@router.get("/initiatives")
def mc_initiatives(limit: int = 20) -> dict:
    """MC surface for the persistent initiative queue — pending, acted, approved, rejected."""
    from core.services.initiative_queue import get_initiative_queue_state
    state = get_initiative_queue_state()
    # Honour the limit on the full item list
    all_items = (state.get("pending") or []) + (state.get("recent_acted") or [])
    return {
        **state,
        "items": all_items[: max(int(limit), 1)],
    }


@router.post("/initiatives/{initiative_id}/approve")
def mc_approve_initiative(initiative_id: str, note: str = "") -> dict:
    """Approve a pending initiative so the heartbeat may act on it."""
    from core.services.initiative_queue import approve_initiative
    result = approve_initiative(initiative_id, note=note)
    if result is None:
        return {"ok": False, "error": f"initiative {initiative_id!r} not found"}
    return {"ok": True, "initiative": result}


@router.post("/initiatives/{initiative_id}/reject")
def mc_reject_initiative(initiative_id: str, note: str = "") -> dict:
    """Reject and expire a pending initiative."""
    from core.services.initiative_queue import reject_initiative
    result = reject_initiative(initiative_id, note=note)
    if result is None:
        return {"ok": False, "error": f"initiative {initiative_id!r} not found"}
    return {"ok": True, "initiative": result}


@router.get("/life-projects")
def mc_life_projects() -> dict:
    """Mission Control surface for Jarvis-owned long-term intentions."""
    return _mc_facade("build_life_projects_surface")()


@router.post("/life-projects/{initiative_id}/abandon")
def mc_abandon_life_project(initiative_id: str, note: str = "") -> dict:
    """Abandon a long-term intention without deleting its record."""
    result = abandon_life_project(initiative_id, note=note)
    if result.get("status") != "ok":
        return {"ok": False, "error": result.get("error", "unknown error")}
    return {"ok": True, "life_project": result.get("life_project") or {}}


@router.get("/operations")
def mc_operations(limit: int = 20) -> dict:
    cache_key = f"operations:{limit}"
    cached = _get_cached_mc_payload(cache_key, 3.0)
    if cached is not None:
        return cached  # type: ignore[return-value]

    runs = _mc_facade("mc_runs")(limit=limit)
    approvals = _mc_facade("mc_approvals")(limit=limit)
    with runtime_surface_cache():
        runtime = _mc_facade("mc_runtime")()  # mc_runtime-ruten bor i mission_control_runtime_config
    tool_intent = dict(runtime.get("runtime_tool_intent") or {})
    sessions = {"items": _mc_facade("list_chat_sessions")()}
    payload = {
        "runtime": runtime,
        "tool_intent": tool_intent,
        "runs": runs,
        "approvals": approvals,
        "sessions": sessions,
        "summary": {
            "active_run": bool(runs.get("active_run")),
            "approval_request_count": int(
                (approvals.get("summary") or {}).get("request_count") or 0
            ),
            "session_count": len(sessions["items"]),
            "tool_intent_active": bool(tool_intent.get("active")),
            "tool_intent_approval_state": str(
                tool_intent.get("approval_state") or "none"
            ),
            "tool_intent_execution_state": str(
                tool_intent.get("execution_state") or "not-executed"
            ),
            "tool_intent_execution_mode": str(
                tool_intent.get("execution_mode") or "read-only"
            ),
            "tool_intent_execution_command": str(
                tool_intent.get("execution_command") or "none"
            ),
            "tool_intent_mutation_permitted": bool(
                tool_intent.get("mutation_permitted", False)
            ),
            "tool_intent_sudo_permitted": bool(
                tool_intent.get("sudo_permitted", False)
            ),
            "tool_intent_workspace_scoped": bool(
                tool_intent.get("workspace_scoped", False)
            ),
            "tool_intent_external_mutation_permitted": bool(
                tool_intent.get("external_mutation_permitted", False)
            ),
            "tool_intent_delete_permitted": bool(
                tool_intent.get("delete_permitted", False)
            ),
            "tool_intent_mutation_intent_state": str(
                tool_intent.get("mutation_intent_state") or "idle"
            ),
            "tool_intent_mutation_classification": str(
                tool_intent.get("mutation_intent_classification") or "none"
            ),
            "tool_intent_mutation_repo_scope": str(
                tool_intent.get("mutation_repo_scope") or ""
            ),
            "tool_intent_mutation_system_scope": str(
                tool_intent.get("mutation_system_scope") or ""
            ),
            "tool_intent_mutation_sudo_required": bool(
                tool_intent.get("mutation_sudo_required", False)
            ),
            "tool_intent_write_proposal_state": str(
                tool_intent.get("write_proposal_state") or "none"
            ),
            "tool_intent_write_proposal_type": str(
                tool_intent.get("write_proposal_type") or "none"
            ),
            "tool_intent_write_proposal_scope": str(
                tool_intent.get("write_proposal_scope") or "none"
            ),
            "tool_intent_write_proposal_criticality": str(
                tool_intent.get("write_proposal_criticality") or "none"
            ),
            "tool_intent_write_proposal_target_identity": bool(
                tool_intent.get("write_proposal_target_identity", False)
            ),
            "tool_intent_write_proposal_target_memory": bool(
                tool_intent.get("write_proposal_target_memory", False)
            ),
            "tool_intent_write_proposal_target": str(
                tool_intent.get("write_proposal_target") or "none"
            ),
            "tool_intent_write_proposal_content_state": str(
                tool_intent.get("write_proposal_content_state") or "none"
            ),
            "tool_intent_write_proposal_content_fingerprint": str(
                tool_intent.get("write_proposal_content_fingerprint") or "none"
            ),
            "tool_intent_mutating_exec_proposal_state": str(
                tool_intent.get("mutating_exec_proposal_state") or "none"
            ),
            "tool_intent_mutating_exec_proposal_scope": str(
                tool_intent.get("mutating_exec_proposal_scope") or "none"
            ),
            "tool_intent_mutating_exec_git_mutation_class": str(
                tool_intent.get("mutating_exec_git_mutation_class") or "none"
            ),
            "tool_intent_mutating_exec_repo_stewardship_domain": str(
                tool_intent.get("mutating_exec_repo_stewardship_domain") or "none"
            ),
            "tool_intent_mutating_exec_requires_sudo": bool(
                tool_intent.get("mutating_exec_requires_sudo", False)
            ),
            "tool_intent_mutating_exec_criticality": str(
                tool_intent.get("mutating_exec_criticality") or "none"
            ),
            "tool_intent_sudo_exec_proposal_state": str(
                tool_intent.get("sudo_exec_proposal_state") or "none"
            ),
            "tool_intent_sudo_exec_proposal_scope": str(
                tool_intent.get("sudo_exec_proposal_scope") or "none"
            ),
            "tool_intent_sudo_exec_requires_sudo": bool(
                tool_intent.get("sudo_exec_requires_sudo", False)
            ),
            "tool_intent_sudo_exec_criticality": str(
                tool_intent.get("sudo_exec_criticality") or "none"
            ),
            "tool_intent_sudo_approval_window_state": str(
                tool_intent.get("sudo_approval_window_state") or "none"
            ),
            "tool_intent_sudo_approval_window_scope": str(
                tool_intent.get("sudo_approval_window_scope") or "none"
            ),
            "tool_intent_sudo_approval_window_expires_at": str(
                tool_intent.get("sudo_approval_window_expires_at") or ""
            ),
            "tool_intent_sudo_approval_window_remaining_seconds": int(
                tool_intent.get("sudo_approval_window_remaining_seconds") or 0
            ),
            "tool_intent_sudo_approval_window_reusable": bool(
                tool_intent.get("sudo_approval_window_reusable", False)
            ),
            "tool_intent_action_continuity_state": str(
                tool_intent.get("action_continuity_state") or "idle"
            ),
            "tool_intent_last_action_outcome": str(
                tool_intent.get("last_action_outcome") or "none"
            ),
            "tool_intent_last_action_at": str(tool_intent.get("last_action_at") or ""),
            "tool_intent_followup_state": str(
                tool_intent.get("followup_state") or "none"
            ),
        },
    }
    return _store_cached_mc_payload(cache_key, 3.0, payload)  # type: ignore[return-value]


