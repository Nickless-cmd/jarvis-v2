"""Task worker — consumes queued runtime_tasks in heartbeat tick cadence.

Responsibilities:
- Claim the next queued task ordered by priority and age
- Dispatch to a handler based on the task's `kind`
- Mark `succeeded`/`failed` with a short result_summary

This worker is deliberately thin: it converts tasks from `queued` to a terminal
state so Jarvis' runtime no longer accumulates dead queue entries. Richer
handlers (hooking into runtime_action_executor, LLM-driven follow-through) can
be layered on top in subsequent work.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import runtime_tasks
from core.runtime.state_store import load_json, save_json

_DEFAULT_KINDS: tuple[str, ...] = (
    "initiative-followup",
    "heartbeat-followup",
    "generic",
    "open-loop-follow-up",
    "agency_bridge_repair",
    "observability_bridge_repair",
    "theater_refactor",
)


def claim_next_task(
    kinds: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any] | None:
    """Claim the next queued task and mark it `running`.

    Returns the updated task dict, or ``None`` if nothing is queued.
    """
    allowed = tuple(kinds) if kinds else _DEFAULT_KINDS
    # runtime_tasks.list_tasks already sorts by (priority_rank, retry_at/updated_at).
    queued = runtime_tasks.list_tasks(status="queued", limit=50)
    candidates = [t for t in queued if str(t.get("kind") or "") in allowed]
    if not candidates:
        return None
    task = candidates[0]
    updated = runtime_tasks.update_task(str(task["task_id"]), status="running")
    return updated or task


def _handle_initiative_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"initiative-followup acknowledged: {goal[:300]}"


def _handle_heartbeat_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"heartbeat-followup acknowledged: {goal[:300]}"


def _handle_open_loop_followup(task: dict[str, Any]) -> str:
    goal = str(task.get("goal") or "(no goal)")
    return f"open-loop-follow-up acknowledged: {goal[:300]}"


def _handle_agency_bridge_repair(task: dict[str, Any]) -> dict[str, str]:
    """Prepare a repair brief for a weak agency bridge.

    The worker must not silently edit source. It turns the runtime task into a
    durable, MC-visible brief that a visible/coding lane can pick up under the
    normal approval flow.
    """
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    edge = _matching_agency_edge(scope=scope, goal=goal)
    task_id = str(task.get("task_id") or "")
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-repair",
        "scope": scope,
        "goal": goal,
        "edge": edge,
        "recommended_next_action": (
            "Open a visible/coding-lane repair pass for this agency bridge. "
            "Inspect the missing markers, add the smallest bridge that makes "
            "the runtime connection real, then rerun the cartographer scan."
        ),
        "suggested_files": _suggested_agency_files(scope=scope, edge=edge),
    }
    _store_agency_repair_brief(task_id=task_id, brief=brief)
    missing = ", ".join(edge.get("missing_markers") or []) if edge else ""
    return {
        "status": "blocked",
        "summary": (
            "Agency bridge repair brief prepared; source changes require "
            f"visible/coding lane approval. {scope or goal}"[:240]
        ),
        "artifact_ref": f"state:agency_bridge_repair_briefs:{task_id}",
        "blocked_reason": (
            "repair brief ready; awaiting approved implementation lane"
            + (f"; missing markers: {missing[:180]}" if missing else "")
        ),
    }


def _handle_observability_bridge_repair(task: dict[str, Any]) -> dict[str, str]:
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    task_id = str(task.get("task_id") or "")
    service = Path(scope).stem if scope else ""
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-repair",
        "scope": scope,
        "goal": goal,
        "service": service,
        "recommended_next_action": (
            "Add a minimal build_*surface for this service or connect an existing "
            "surface to Mission Control/System Cartographer. Then rerun the "
            "cartographer and verify the dark edge drops or its coverage score rises."
        ),
        "suggested_files": _suggested_observability_files(scope=scope, service=service),
    }
    _store_observability_repair_brief(task_id=task_id, brief=brief)
    return {
        "status": "blocked",
        "summary": (
            "Observability bridge repair brief prepared; source changes require "
            f"visible/coding lane approval. {service or scope or goal}"[:240]
        ),
        "artifact_ref": f"state:observability_bridge_repair_briefs:{task_id}",
        "blocked_reason": "observability brief ready; awaiting approved implementation lane",
    }


def _handle_theater_refactor(task: dict[str, Any]) -> dict[str, str]:
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    task_id = str(task.get("task_id") or "")
    audit_file = _matching_theater_file(scope=scope)
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-refactor",
        "scope": scope,
        "goal": goal,
        "audit_file": audit_file,
        "recommended_next_action": (
            "Convert this layer from narrative-first prompting to structured "
            "appraisal state. Preserve voice as optional rendering, but make "
            "evidence, confidence, expiry, and allowed runtime effects the durable truth."
        ),
        "refactor_contract": {
            "state_before_prose": True,
            "requires_evidence": True,
            "requires_confidence": True,
            "requires_decay_or_expiry": True,
            "requires_allowed_effects": True,
            "first_person_text_is_rendering_only": True,
        },
        "suggested_files": _suggested_theater_files(scope=scope),
    }
    _store_theater_refactor_brief(task_id=task_id, brief=brief)
    return {
        "status": "blocked",
        "summary": (
            "Theater refactor brief prepared; source changes require "
            f"visible/coding lane approval. {scope or goal}"[:240]
        ),
        "artifact_ref": f"state:theater_refactor_briefs:{task_id}",
        "blocked_reason": "theater refactor brief ready; awaiting approved implementation lane",
    }


def _execute_task(task: dict[str, Any]) -> None:
    """Execute a single task and persist its final status. Never raises."""
    kind = str(task.get("kind") or "")
    task_id = str(task.get("task_id") or "")
    try:
        if kind == "initiative-followup":
            summary = _handle_initiative_followup(task)
        elif kind == "heartbeat-followup":
            summary = _handle_heartbeat_followup(task)
        elif kind == "open-loop-follow-up":
            summary = _handle_open_loop_followup(task)
        elif kind == "agency_bridge_repair":
            result = _handle_agency_bridge_repair(task)
            runtime_tasks.update_task(
                task_id,
                status=result["status"],
                blocked_reason=result["blocked_reason"],
                result_summary=result["summary"],
                artifact_ref=result["artifact_ref"],
            )
            return
        elif kind == "observability_bridge_repair":
            result = _handle_observability_bridge_repair(task)
            runtime_tasks.update_task(
                task_id,
                status=result["status"],
                blocked_reason=result["blocked_reason"],
                result_summary=result["summary"],
                artifact_ref=result["artifact_ref"],
            )
            return
        elif kind == "theater_refactor":
            result = _handle_theater_refactor(task)
            runtime_tasks.update_task(
                task_id,
                status=result["status"],
                blocked_reason=result["blocked_reason"],
                result_summary=result["summary"],
                artifact_ref=result["artifact_ref"],
            )
            return
        elif kind == "generic":
            summary = f"generic task acknowledged: {str(task.get('goal') or '')[:120]}"
        else:
            runtime_tasks.update_task(
                task_id,
                status="failed",
                result_summary=f"unknown kind: {kind}",
            )
            return
        runtime_tasks.update_task(
            task_id,
            status="succeeded",
            result_summary=(summary or "ok")[:500],
        )
    except Exception as exc:  # noqa: BLE001
        runtime_tasks.update_task(
            task_id,
            status="failed",
            result_summary=f"error: {type(exc).__name__}: {exc}"[:500],
        )


def tick_task_worker(budget: int = 3) -> dict[str, Any]:
    """Run one worker tick: claim and execute up to ``budget`` tasks.

    Returns a summary dict suitable for ``daemon_manager.record_daemon_tick``.
    """
    processed = 0
    succeeded = 0
    failed = 0
    blocked = 0
    allowed = _DEFAULT_KINDS
    for _ in range(max(0, int(budget))):
        task = claim_next_task(kinds=allowed)
        if task is None:
            break
        _execute_task(task)
        reloaded = runtime_tasks.get_task(str(task["task_id"]))
        processed += 1
        status = str((reloaded or {}).get("status") or "")
        if status == "succeeded":
            succeeded += 1
        elif status == "failed":
            failed += 1
        elif status == "blocked":
            blocked += 1
    remaining = [
        t
        for t in runtime_tasks.list_tasks(status="queued", limit=50)
        if str(t.get("kind") or "") in allowed
    ]
    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "blocked": blocked,
        "remaining_queued": len(remaining),
    }


def _matching_agency_edge(*, scope: str, goal: str) -> dict[str, Any]:
    try:
        from core.services.agency_cartographer import get_cartographer_snapshot

        snapshot = get_cartographer_snapshot(refresh=True)
        candidates = list(snapshot.get("taskCandidates") or [])
        edges = list(snapshot.get("edges") or [])
        for candidate in candidates:
            if scope and str(candidate.get("scope") or "").strip() == scope:
                edge_id = str(candidate.get("id") or "").removeprefix("agency-")
                return _edge_by_id(edges, edge_id) or dict(candidate)
            if goal and str(candidate.get("goal") or "").strip() == goal:
                edge_id = str(candidate.get("id") or "").removeprefix("agency-")
                return _edge_by_id(edges, edge_id) or dict(candidate)
        for edge in edges:
            if scope and str(edge.get("target") or "").strip() == scope:
                return dict(edge)
    except Exception:
        return {}
    return {}


def _edge_by_id(edges: list[dict[str, Any]], edge_id: str) -> dict[str, Any]:
    for edge in edges:
        if str(edge.get("id") or "") == edge_id:
            return dict(edge)
    return {}


def _store_agency_repair_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("agency_bridge_repair_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("agency_bridge_repair_briefs", data)


def _store_observability_repair_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("observability_bridge_repair_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("observability_bridge_repair_briefs", data)


def _store_theater_refactor_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("theater_refactor_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("theater_refactor_briefs", data)


def _matching_theater_file(*, scope: str) -> dict[str, Any]:
    if not scope:
        return {}
    try:
        from core.services.theater_audit import build_theater_audit_surface

        surface = build_theater_audit_surface()
        for item in surface.get("files") or []:
            if str(item.get("path") or "").strip() == scope:
                return dict(item)
    except Exception:
        return {}
    return {}


def _suggested_agency_files(*, scope: str, edge: dict[str, Any]) -> list[str]:
    haystack = " ".join([
        scope,
        str(edge.get("id") or ""),
        str(edge.get("target") or ""),
        str(edge.get("title") or ""),
    ]).lower()
    suggestions: list[str] = ["core/services/agency_cartographer.py"]
    if "senses" in haystack or "sensory" in haystack:
        suggestions.extend([
            "core/services/sensory_archive.py",
            "core/services/perceptual_event_engine.py",
            "core/services/memory_emotional_context.py",
        ])
    if "emotion" in haystack:
        suggestions.extend([
            "core/services/emotion_concepts_channel_triggers.py",
            "core/services/memory_emotional_context.py",
        ])
    if "repair" in haystack:
        suggestions.append("core/services/self_repair_engine.py")
    if "executive" in haystack:
        suggestions.append("core/services/living_executive.py")
    if "tools" in haystack:
        suggestions.extend([
            "core/services/tool_intent_runtime.py",
            "core/services/runtime_action_outcome_tracking.py",
        ])
    if "mission control" in haystack or "hidden" in haystack:
        suggestions.extend([
            "core/services/agency_map.py",
            "apps/ui/src/components/mission-control/AgencyMapTab.jsx",
        ])
    return list(dict.fromkeys(suggestions))


def _suggested_observability_files(*, scope: str, service: str) -> list[str]:
    suggestions = []
    if scope:
        suggestions.append(scope)
    suggestions.extend([
        "core/services/system_cartographer.py",
        "core/services/agency_map.py",
        "apps/ui/src/components/mission-control/AgencyMapTab.jsx",
    ])
    if service == "identity_composer":
        suggestions.insert(0, "core/services/identity_composer.py")
    return list(dict.fromkeys(suggestions))


def _suggested_theater_files(*, scope: str) -> list[str]:
    suggestions = []
    if scope:
        suggestions.append(scope)
    suggestions.extend([
        "core/services/theater_audit.py",
        "core/services/system_cartographer.py",
        "core/services/agency_map.py",
        "apps/ui/src/components/mission-control/AgencyMapTab.jsx",
    ])
    if scope.endswith("cognitive_state_assembly.py"):
        suggestions.extend([
            "core/services/cognitive_state_assembly.py",
            "core/services/affective_meta_state.py",
            "core/services/somatic_daemon.py",
        ])
    return list(dict.fromkeys(suggestions))


def build_task_worker_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "task_worker",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_task_worker_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"task_worker.{kind}",
            payload or {},
        )
    except Exception:
        pass

