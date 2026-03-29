from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from apps.api.jarvis_api.services.candidate_tracking import (
    track_runtime_contract_candidates_for_session_review,
)
from apps.api.jarvis_api.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from apps.api.jarvis_api.services.metabolism_state_signal_tracking import (
    build_runtime_metabolism_state_signal_surface,
)
from apps.api.jarvis_api.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from apps.api.jarvis_api.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from apps.api.jarvis_api.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from apps.api.jarvis_api.services.prompt_contract import build_heartbeat_prompt_assembly
from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from apps.api.jarvis_api.services.release_marker_signal_tracking import (
    build_runtime_release_marker_signal_surface,
)
from apps.api.jarvis_api.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from apps.api.jarvis_api.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.auth.profiles import get_provider_state
from core.eventbus.bus import event_bus
from core.identity.runtime_candidates import build_runtime_candidate_workflows
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import (
    get_heartbeat_runtime_state,
    record_heartbeat_runtime_tick,
    recent_heartbeat_runtime_ticks,
    recent_runtime_contract_file_writes,
    recent_visible_runs,
    runtime_contract_candidate_counts,
    upsert_heartbeat_runtime_state,
    visible_session_continuity,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import load_workspace_capabilities

HEARTBEAT_STATE_REL_PATH = Path("runtime/HEARTBEAT_STATE.json")
HEARTBEAT_ALLOWED_DECISIONS = {"noop", "propose", "execute", "ping"}
HEARTBEAT_ALLOWED_EXECUTE_ACTIONS = {"run_candidate_scan"}
_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z ]+):\s*(.+?)\s*$")
_HEARTBEAT_TICK_LOCK = threading.Lock()
_HEARTBEAT_SCHEDULER_STOP = threading.Event()
_HEARTBEAT_SCHEDULER_THREAD: threading.Thread | None = None
_HEARTBEAT_SCHEDULER_INTERVAL_SECONDS = 30
_HEARTBEAT_LAST_SCHEDULE_SNAPSHOT: dict[str, object] = {}
_STALE_TICK_RECOVERY_WINDOW_MINUTES = 10
logger = logging.getLogger("uvicorn.error")


@dataclass(slots=True)
class HeartbeatExecutionResult:
    state: dict[str, object]
    tick: dict[str, object]
    policy: dict[str, object]


def _log_debug(message: str, **fields: object) -> None:
    detail = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False)}"
        for key, value in fields.items()
    )
    logger.debug("%s%s", message, f" | {detail}" if detail else "")


def _hours_since_iso(value: object) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - parsed.astimezone(UTC)
    return max(delta.total_seconds() / 3600.0, 0.0)


def start_heartbeat_scheduler(*, name: str = "default") -> None:
    global _HEARTBEAT_SCHEDULER_THREAD, _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT
    if _HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive():
        return
    recovery = _prepare_scheduler_startup(name=name)
    _HEARTBEAT_SCHEDULER_STOP.clear()
    thread = threading.Thread(
        target=_heartbeat_scheduler_loop,
        kwargs={
            "name": name,
            "startup_recovery_requested": bool(recovery.get("startup_recovery_requested")),
        },
        name="jarvis-heartbeat-scheduler",
        daemon=True,
    )
    thread.start()
    _HEARTBEAT_SCHEDULER_THREAD = thread
    _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT = {
        "schedule_state": str(recovery.get("schedule_state") or ""),
        "due": bool(recovery.get("due")),
    }
    logger.info(
        "heartbeat scheduler started name=%s due=%s schedule_state=%s recovery_status=%s",
        name,
        bool(recovery.get("due")),
        str(recovery.get("schedule_state") or "unknown"),
        str(recovery.get("recovery_status") or "idle"),
    )
    event_bus.publish(
        "heartbeat.scheduler_started",
        {
            "scheduler_active": True,
            "schedule_state": recovery.get("schedule_state"),
            "due": recovery.get("due"),
            "recovery_status": recovery.get("recovery_status"),
            "next_tick_at": recovery.get("next_tick_at"),
        },
    )


def stop_heartbeat_scheduler(*, name: str = "default") -> None:
    global _HEARTBEAT_SCHEDULER_THREAD, _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT
    _HEARTBEAT_SCHEDULER_STOP.set()
    thread = _HEARTBEAT_SCHEDULER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    _HEARTBEAT_SCHEDULER_THREAD = None
    _mark_scheduler_stopped(name=name)
    _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT = {}
    logger.info("heartbeat scheduler stopped name=%s", name)


def poll_heartbeat_schedule(*, name: str = "default") -> dict[str, object]:
    surface = heartbeat_runtime_surface(name=name)
    state = dict(surface["state"])
    _emit_schedule_transitions(state)
    _log_debug(
        "heartbeat schedule poll",
        name=name,
        schedule_state=state.get("schedule_state"),
        due=state.get("due"),
        next_tick_at=state.get("next_tick_at"),
        last_tick_at=state.get("last_tick_at"),
    )
    if state.get("schedule_state") == "due":
        run_heartbeat_tick(name=name, trigger="scheduled")
        return heartbeat_runtime_surface(name=name)
    return surface


def _poll_heartbeat_schedule_with_trigger(
    *,
    name: str,
    due_trigger: str,
) -> dict[str, object]:
    surface = heartbeat_runtime_surface(name=name)
    state = dict(surface["state"])
    _emit_schedule_transitions(state)
    _log_debug(
        "heartbeat startup poll",
        name=name,
        due_trigger=due_trigger,
        schedule_state=state.get("schedule_state"),
        due=state.get("due"),
        next_tick_at=state.get("next_tick_at"),
    )
    if state.get("schedule_state") == "due":
        if due_trigger == "startup-recovery":
            event_bus.publish(
                "heartbeat.startup_recovery_triggered",
                {
                    "schedule_state": state.get("schedule_state"),
                    "next_tick_at": state.get("next_tick_at"),
                    "last_tick_at": state.get("last_tick_at"),
                },
            )
        run_heartbeat_tick(name=name, trigger=due_trigger)
        return heartbeat_runtime_surface(name=name)
    return surface


def heartbeat_runtime_surface(name: str = "default") -> dict[str, object]:
    policy = load_heartbeat_policy(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    now = datetime.now(UTC)
    recent_ticks = recent_heartbeat_runtime_ticks(limit=8)
    recent_events = [
        item
        for item in event_bus.recent(limit=20)
        if str(item.get("family") or "") == "heartbeat"
    ][:8]
    merged = _merge_runtime_state(policy=policy, persisted=persisted, now=now)
    liveness = _build_heartbeat_liveness_signal(
        merged_state=merged,
        trigger="surface",
    )
    merged = {
        **merged,
        **liveness,
    }
    _write_heartbeat_state_artifact(
        workspace_dir=ensure_default_workspace(name=name),
        payload={
            "state": merged,
            "policy": policy,
            "recent_ticks": recent_ticks,
        },
    )
    return {
        "state": merged,
        "policy": policy,
        "recent_ticks": recent_ticks,
        "recent_events": recent_events,
        "source": "/mc/jarvis::heartbeat",
    }


def run_heartbeat_tick(*, name: str = "default", trigger: str = "manual") -> HeartbeatExecutionResult:
    if not _HEARTBEAT_TICK_LOCK.acquire(blocking=False):
        return _heartbeat_busy_result(name=name, trigger=trigger)
    try:
        return _run_heartbeat_tick_locked(name=name, trigger=trigger)
    finally:
        _HEARTBEAT_TICK_LOCK.release()


def _run_heartbeat_tick_locked(*, name: str = "default", trigger: str = "manual") -> HeartbeatExecutionResult:
    now = datetime.now(UTC)
    workspace_dir = ensure_default_workspace(name=name)
    policy = load_heartbeat_policy(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    merged_before = _merge_runtime_state(policy=policy, persisted=persisted, now=now)
    _persist_runtime_state(
        policy=policy,
        persisted=persisted,
        now=now,
        overrides={
            "blocked_reason": "",
            "currently_ticking": True,
            "last_trigger_source": trigger,
            "scheduler_active": bool(_HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive()),
            "scheduler_health": "active" if (_HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive()) else str(persisted.get("scheduler_health") or "manual-only"),
            "updated_at": now.isoformat(),
        },
    )

    event_bus.publish(
        "heartbeat.tick_started",
        {
            "trigger": trigger,
            "enabled": bool(merged_before["enabled"]),
            "schedule_state": merged_before["schedule_state"],
            "next_tick_at": merged_before["next_tick_at"],
        },
    )
    _log_debug(
        "heartbeat tick started",
        name=name,
        trigger=trigger,
        enabled=merged_before.get("enabled"),
        schedule_state=merged_before.get("schedule_state"),
        due=merged_before.get("due"),
        scheduler_health=merged_before.get("scheduler_health"),
    )

    blocked_reason = _tick_blocked_reason(merged_before)
    if blocked_reason:
        logger.warning(
            "heartbeat tick blocked trigger=%s blocked_reason=%s schedule_state=%s",
            trigger,
            blocked_reason,
            str(merged_before.get("schedule_state") or "unknown"),
        )
        tick = _record_heartbeat_outcome(
            policy=policy,
            persisted=persisted,
            tick_id=f"heartbeat-tick:{uuid.uuid4()}",
            trigger=trigger,
            tick_status="blocked",
            decision_type="noop",
            decision_summary="Heartbeat tick did not run.",
            decision_reason=blocked_reason,
            blocked_reason=blocked_reason,
            currently_ticking=False,
            last_trigger_source=trigger,
            provider="",
            model="",
            lane="",
            budget_status=str(merged_before["budget_status"]),
            ping_eligible=False,
            ping_result="not-checked",
            action_status="blocked",
            action_summary=blocked_reason,
            action_type="",
            action_artifact="",
            raw_response="",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            started_at=now.isoformat(),
            finished_at=datetime.now(UTC).isoformat(),
            workspace_dir=workspace_dir,
        )
        event_bus.publish(
            "heartbeat.tick_blocked",
            {
                "tick_id": tick["tick_id"],
                "blocked_reason": blocked_reason,
                "trigger": trigger,
            },
        )
        return HeartbeatExecutionResult(
            state=heartbeat_runtime_surface(name=name)["state"],
            tick=tick,
            policy=policy,
        )

    target = _select_heartbeat_target()
    context = _build_heartbeat_context(policy=policy, merged_state=merged_before, trigger=trigger)
    _log_debug(
        "heartbeat context built",
        trigger=trigger,
        target_provider=target.get("provider"),
        target_model=target.get("model"),
        target_lane=target.get("lane"),
        open_loop_count=len(context.get("open_loops") or []),
        due_count=len(context.get("due_items") or []),
        liveness_state=(context.get("liveness") or {}).get("liveness_state"),
        liveness_score=(context.get("liveness") or {}).get("liveness_score"),
        liveness_signal_count=(context.get("liveness") or {}).get("liveness_signal_count"),
    )
    assembly = build_heartbeat_prompt_assembly(heartbeat_context=context, name=name)
    prompt = _heartbeat_prompt_text(assembly.text or "")
    started_at = now.isoformat()
    execution_status = "not-run"
    parse_status = "not-run"
    raw_response = ""
    result = {
        "text": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
    }

    try:
        result = _execute_heartbeat_model(
            prompt=prompt,
            target=target,
            policy=policy,
            open_loops=context["open_loops"],
            liveness=context.get("liveness"),
        )
        raw_response = str(result.get("text") or "")
        execution_status = str(result.get("execution_status") or "success")
    except Exception as exc:
        execution_status = _classify_heartbeat_execution_exception(exc)
        decision = _bounded_heartbeat_failure_decision(
            failure_kind="runtime",
            detail=str(exc),
            target=target,
        )
    else:
        decision, parse_status = _parse_heartbeat_decision_bounded(raw_response)

    decision = _recover_bounded_heartbeat_liveness_decision(
        decision=decision,
        policy=policy,
        liveness=context.get("liveness"),
    )

    if execution_status == "success" and parse_status == "not-run":
        parse_status = "success"

    event_bus.publish(
        "heartbeat.decision_produced",
        {
            "decision_type": decision["decision_type"],
            "summary": decision["summary"],
            "trigger": trigger,
            "lane": target["lane"],
            "provider": target["provider"],
            "model": target["model"],
            "model_source": str(target.get("model_source") or ""),
            "resolution_status": str(target.get("resolution_status") or ""),
            "fallback_used": bool(target.get("fallback_used")),
            "execution_status": execution_status,
            "parse_status": parse_status,
        },
    )
    _log_debug(
        "heartbeat decision produced",
        trigger=trigger,
        execution_status=execution_status,
        parse_status=parse_status,
        decision_type=decision.get("decision_type"),
        reason=decision.get("reason"),
        summary=decision.get("summary"),
    )

    outcome = _validate_heartbeat_decision(
        decision=decision,
        policy=policy,
        workspace_dir=workspace_dir,
        tick_id=f"heartbeat-tick:{uuid.uuid4()}",
    )
    tick_status = "completed" if not outcome["blocked_reason"] else "blocked"
    finished_at = datetime.now(UTC).isoformat()
    tick = _record_heartbeat_outcome(
        policy=policy,
        persisted=persisted,
        tick_id=str(outcome["tick_id"]),
        trigger=trigger,
        tick_status=tick_status,
        decision_type=decision["decision_type"],
        decision_summary=decision["summary"],
        decision_reason=decision["reason"],
        blocked_reason=outcome["blocked_reason"],
        currently_ticking=False,
        last_trigger_source=trigger,
        provider=target["provider"],
        model=target["model"],
        lane=target["lane"],
        budget_status=str(policy["budget_status"]),
        model_source=str(target.get("model_source") or ""),
        resolution_status=str(target.get("resolution_status") or ""),
        fallback_used=bool(target.get("fallback_used")),
        execution_status=execution_status,
        parse_status=parse_status,
        ping_eligible=outcome["ping_eligible"],
        ping_result=outcome["ping_result"],
        action_status=outcome["action_status"],
        action_summary=outcome["action_summary"],
        action_type=outcome["action_type"],
        action_artifact=outcome["action_artifact"],
        raw_response=raw_response,
        input_tokens=int(result.get("input_tokens") or 0),
        output_tokens=int(result.get("output_tokens") or 0),
        cost_usd=float(result.get("cost_usd") or 0.0),
        started_at=started_at,
        finished_at=finished_at,
        workspace_dir=workspace_dir,
    )

    if outcome["blocked_reason"]:
        event_bus.publish(
            "heartbeat.tick_blocked",
            {
                "tick_id": tick["tick_id"],
                "decision_type": decision["decision_type"],
                "blocked_reason": outcome["blocked_reason"],
                "action_type": outcome["action_type"],
                "trigger": trigger,
                "lane": target["lane"],
                "provider": target["provider"],
                "model": target["model"],
                "model_source": str(target.get("model_source") or ""),
                "resolution_status": str(target.get("resolution_status") or ""),
                "fallback_used": bool(target.get("fallback_used")),
                "execution_status": execution_status,
                "parse_status": parse_status,
            },
        )
    else:
        event_bus.publish(
            "heartbeat.tick_completed",
            {
                "tick_id": tick["tick_id"],
                "trigger": trigger,
                "decision_type": decision["decision_type"],
                "tick_status": tick["tick_status"],
                "summary": tick["decision_summary"],
                "action_type": outcome["action_type"],
                "action_status": outcome["action_status"],
                "lane": target["lane"],
                "provider": target["provider"],
                "model": target["model"],
                "model_source": str(target.get("model_source") or ""),
                "resolution_status": str(target.get("resolution_status") or ""),
                "fallback_used": bool(target.get("fallback_used")),
                "execution_status": execution_status,
                "parse_status": parse_status,
            },
        )
        logger.info(
            "heartbeat tick completed trigger=%s decision_type=%s action_status=%s liveness_state=%s",
            trigger,
            str(decision.get("decision_type") or "unknown"),
            str(tick.get("action_status") or "unknown"),
            str((context.get("liveness") or {}).get("liveness_state") or "quiet"),
        )
        event_bus.publish(
            f"heartbeat.{decision['decision_type']}",
            {
                "tick_id": tick["tick_id"],
                "decision_type": decision["decision_type"],
                "summary": decision["summary"],
                "action_status": outcome["action_status"],
                "action_type": outcome["action_type"],
                "action_artifact": outcome["action_artifact"],
                "ping_result": outcome["ping_result"],
                "lane": target["lane"],
                "provider": target["provider"],
                "model": target["model"],
                "model_source": str(target.get("model_source") or ""),
                "resolution_status": str(target.get("resolution_status") or ""),
                "fallback_used": bool(target.get("fallback_used")),
                "execution_status": execution_status,
                "parse_status": parse_status,
            },
        )

    return HeartbeatExecutionResult(
        state=heartbeat_runtime_surface(name=name)["state"],
        tick=tick,
        policy=policy,
    )


def load_heartbeat_policy(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    heartbeat_path = workspace_dir / "HEARTBEAT.md"
    text = heartbeat_path.read_text(encoding="utf-8") if heartbeat_path.exists() else ""
    kv = _parse_heartbeat_key_values(text)
    enabled = _parse_bool(kv.get("status"), default=True, truthy={"enabled", "true", "yes", "on"})
    interval_minutes = _parse_int(kv.get("interval minutes"), default=180, minimum=15)
    allow_propose = _parse_bool(kv.get("allow propose"), default=True)
    allow_execute = _parse_bool(kv.get("allow execute"), default=False)
    allow_ping = _parse_bool(kv.get("allow ping"), default=False)
    ping_channel = str(kv.get("ping channel") or "none").strip() or "none"
    budget_status = str(kv.get("budget") or "bounded-internal-only").strip() or "bounded-internal-only"
    kill_switch = str(kv.get("kill switch") or "enabled").strip() or "enabled"
    summary_lines = [
        f"interval={interval_minutes}m",
        "propose=allowed" if allow_propose else "propose=blocked",
        "execute=allowed" if allow_execute else "execute=blocked",
        f"ping={'allowed' if allow_ping else 'blocked'}:{ping_channel}",
        f"budget={budget_status}",
    ]
    return {
        "workspace": str(workspace_dir),
        "heartbeat_file": str(heartbeat_path),
        "present": heartbeat_path.exists(),
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "allow_propose": allow_propose,
        "allow_execute": allow_execute,
        "allow_ping": allow_ping,
        "ping_channel": ping_channel,
        "budget_status": budget_status,
        "kill_switch": kill_switch,
        "summary": " | ".join(summary_lines),
        "source": "/mc/jarvis::heartbeat",
    }


def _build_heartbeat_context(
    *,
    policy: dict[str, object],
    merged_state: dict[str, object],
    trigger: str,
) -> dict[str, object]:
    workflows = build_runtime_candidate_workflows()
    candidate_counts = runtime_contract_candidate_counts()
    pending_file_writes = recent_runtime_contract_file_writes(limit=3)
    continuity = visible_session_continuity()
    recent_run_rows = recent_visible_runs(limit=3)
    capabilities = load_workspace_capabilities()
    visible_status = visible_execution_readiness()

    due_items: list[str] = []
    if trigger == "manual":
        due_items.append("manual-trigger requested from Mission Control")
    if merged_state["due"]:
        due_items.append("scheduled heartbeat interval is currently due")
    if capabilities.get("approval_required_count"):
        due_items.append(
            f"{capabilities['approval_required_count']} capabilities still require approval"
        )

    open_loops: list[str] = []
    for workflow in workflows.values():
        if workflow.get("pending_count"):
            open_loops.append(
                f"{workflow['label']} has {workflow['pending_count']} proposed items"
            )
        if workflow.get("approved_count"):
            open_loops.append(
                f"{workflow['label']} has {workflow['approved_count']} approved items awaiting apply"
            )
    if candidate_counts.get("preference_update:applied", 0) or candidate_counts.get("memory_promotion:applied", 0):
        open_loops.append("recent governed file writes exist for continuity review")
    if pending_file_writes:
        open_loops.append(
            f"{len(pending_file_writes)} recent contract file writes are available for context"
        )
    if continuity.get("active"):
        latest_preview = str(continuity.get("latest_text_preview") or "").strip()
        if latest_preview:
            open_loops.append(f"latest visible continuity preview: {latest_preview[:140]}")
    for item in recent_run_rows[:2]:
        status = str(item.get("status") or "unknown")
        if status in {"failed", "cancelled"}:
            preview = str(item.get("error") or item.get("text_preview") or "").strip()
            open_loops.append(f"recent visible run {status}: {preview[:140]}")

    recent_events = []
    for event in event_bus.recent(limit=12):
        family = str(event.get("family") or "")
        if family == "heartbeat":
            continue
        recent_events.append(f"{event.get('kind')}: {json.dumps(event.get('payload') or {}, ensure_ascii=False)[:120]}")
        if len(recent_events) >= 3:
            break

    allowed_capabilities = []
    if policy["allow_execute"]:
        allowed_capabilities.extend(sorted(HEARTBEAT_ALLOWED_EXECUTE_ACTIONS))

    continuity_summary = None
    if continuity.get("active"):
        continuity_summary = (
            f"latest_status={continuity.get('latest_status') or 'unknown'}"
            f" | latest_run_id={continuity.get('latest_run_id') or 'none'}"
            f" | visible_provider_status={visible_status.get('provider_status') or 'unknown'}"
        )
    liveness = _build_heartbeat_liveness_signal(
        merged_state=merged_state,
        trigger=trigger,
    )

    return {
        "schedule_status": str(merged_state["schedule_status"]),
        "budget_status": str(policy["budget_status"]),
        "kill_switch": str(policy["kill_switch"]),
        "due_items": due_items,
        "open_loops": open_loops[:5],
        "recent_events": recent_events,
        "allowed_capabilities": allowed_capabilities,
        "continuity_summary": continuity_summary,
        "liveness": liveness,
    }


def _build_heartbeat_liveness_signal(
    *,
    merged_state: dict[str, object],
    trigger: str,
) -> dict[str, object]:
    open_loops = build_runtime_open_loop_signal_surface(limit=6)
    relation_continuity = build_runtime_relation_continuity_signal_surface(limit=6)
    regulation = build_runtime_regulation_homeostasis_signal_surface(limit=6)
    witness = build_runtime_witness_signal_surface(limit=6)
    private_state = build_runtime_private_state_snapshot_surface(limit=6)
    initiative_tension = build_runtime_private_initiative_tension_signal_surface(limit=6)
    chronicle_briefs = build_runtime_chronicle_consolidation_brief_surface(limit=6)
    meaning_significance = build_runtime_meaning_significance_signal_surface(limit=6)
    metabolism = build_runtime_metabolism_state_signal_surface(limit=6)
    release_markers = build_runtime_release_marker_signal_surface(limit=6)
    continuity = visible_session_continuity()

    reason_signals: list[tuple[int, str, str, bool]] = []
    score = 0
    core_pressure_count = 0
    propose_gate_count = 0
    companion_pressure_weight = 0
    companion_pressure_state = "inactive"
    companion_pressure_reason = "no-bounded-companion-pressure"
    idle_presence_state = "inactive"
    checkin_worthiness = "low"

    def add_signal(
        *,
        weight: int,
        reason: str,
        anchor: str,
        core: bool = False,
        propose_gate: bool = False,
    ) -> None:
        nonlocal score, core_pressure_count, propose_gate_count
        score += weight
        reason_signals.append((weight, reason, anchor, core))
        if core:
            core_pressure_count += 1
        if propose_gate:
            propose_gate_count += 1

    open_summary = open_loops.get("summary") or {}
    open_items = open_loops.get("items") or []
    open_anchor = (
        str((open_items[0] or {}).get("source_anchor") or (open_items[0] or {}).get("title") or "open-loop")
        if open_items
        else "open-loop"
    )
    open_count = int(open_summary.get("open_count") or 0)
    softening_count = int(open_summary.get("softening_count") or 0)
    if open_loops.get("active") and open_count > 0:
        add_signal(
            weight=4,
            reason="open-loop continuity is still live",
            anchor=open_anchor,
            core=True,
            propose_gate=True,
        )
    elif open_loops.get("active") and softening_count > 0:
        add_signal(
            weight=2,
            reason="softening open-loop continuity is still present",
            anchor=open_anchor,
            core=True,
        )

    tension_summary = initiative_tension.get("summary") or {}
    tension_items = initiative_tension.get("items") or []
    tension_anchor = (
        str((tension_items[0] or {}).get("source_anchor") or (tension_items[0] or {}).get("title") or "initiative-tension")
        if tension_items
        else "initiative-tension"
    )
    tension_intensity = str(tension_summary.get("current_intensity") or "low")
    if int(tension_summary.get("active_count") or 0) > 0:
        tension_weight = 3 if tension_intensity == "medium" else 2
        add_signal(
            weight=tension_weight,
            reason="private initiative tension is still carrying bounded pull",
            anchor=tension_anchor,
            core=True,
            propose_gate=tension_intensity == "medium",
        )

    private_summary = private_state.get("summary") or {}
    private_items = private_state.get("items") or []
    current_pressure = str(private_summary.get("current_pressure") or "low")
    private_anchor = (
        str((private_items[0] or {}).get("source_anchor") or (private_items[0] or {}).get("title") or "private-state")
        if private_items
        else "private-state"
    )
    if int(private_summary.get("active_count") or 0) > 0 and current_pressure in {"medium", "high"}:
        add_signal(
            weight=3 if current_pressure == "high" else 2,
            reason="private state pressure is still present",
            anchor=private_anchor,
            core=True,
            propose_gate=current_pressure == "high",
        )

    relation_summary = relation_continuity.get("summary") or {}
    relation_items = relation_continuity.get("items") or []
    current_weight = str(relation_summary.get("current_weight") or "low")
    relation_anchor = (
        str((relation_items[0] or {}).get("source_anchor") or (relation_items[0] or {}).get("title") or "relation-continuity")
        if relation_items
        else "relation-continuity"
    )
    if relation_continuity.get("active") and current_weight in {"medium", "high"}:
        add_signal(
            weight=2 if current_weight == "high" else 1,
            reason="relation continuity is still holding weight",
            anchor=relation_anchor,
        )

    regulation_summary = regulation.get("summary") or {}
    regulation_items = regulation.get("items") or []
    regulation_pressure = str(regulation_summary.get("current_pressure") or "low")
    regulation_anchor = (
        str((regulation_items[0] or {}).get("source_anchor") or (regulation_items[0] or {}).get("title") or "regulation")
        if regulation_items
        else "regulation"
    )
    if regulation.get("active") and regulation_pressure in {"medium", "high"}:
        add_signal(
            weight=2 if regulation_pressure == "high" else 1,
            reason="regulation pressure is still elevated",
            anchor=regulation_anchor,
        )

    witness_summary = witness.get("summary") or {}
    witness_items = witness.get("items") or []
    witness_anchor = (
        str((witness_items[0] or {}).get("source_anchor") or (witness_items[0] or {}).get("title") or "witness")
        if witness_items
        else "witness"
    )
    if (
        int(witness_summary.get("carried_count") or 0) > 0
        or str(witness_summary.get("current_persistence_state") or "none")
        in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
    ):
        persistence_state = str(witness_summary.get("current_persistence_state") or "none")
        add_signal(
            weight=2 if persistence_state in {"carried-forward", "persistent"} else 1,
            reason="witness continuity is still being carried",
            anchor=witness_anchor,
        )

    chronicle_summary = chronicle_briefs.get("summary") or {}
    chronicle_items = chronicle_briefs.get("items") or []
    chronicle_anchor = (
        str((chronicle_items[0] or {}).get("source_anchor") or (chronicle_items[0] or {}).get("title") or "chronicle-brief")
        if chronicle_items
        else "chronicle-brief"
    )
    if chronicle_briefs.get("active") and str(chronicle_summary.get("current_weight") or "low") in {"medium", "high"}:
        add_signal(
            weight=1,
            reason="chronicle continuity is still holding a brief thread",
            anchor=chronicle_anchor,
        )

    meaning_summary = meaning_significance.get("summary") or {}
    meaning_items = meaning_significance.get("items") or []
    meaning_weight = str(meaning_summary.get("current_weight") or "low")
    meaning_anchor = (
        str((meaning_items[0] or {}).get("source_anchor") or (meaning_items[0] or {}).get("title") or "meaning-significance")
        if meaning_items
        else "meaning-significance"
    )
    if meaning_significance.get("active") and meaning_weight in {"medium", "high"}:
        add_signal(
            weight=1,
            reason="meaning significance is still softly carried",
            anchor=meaning_anchor,
        )

    relation_meaning_held = (
        relation_continuity.get("active")
        and meaning_significance.get("active")
        and current_weight in {"medium", "high"}
        and meaning_weight in {"medium", "high"}
    )
    witness_persistence = str(witness_summary.get("current_persistence_state") or "none")
    witness_carried = (
        int(witness_summary.get("carried_count") or 0) > 0
        or witness_persistence in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
    )
    chronicle_held = chronicle_briefs.get("active") and str(
        chronicle_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    carried_continuity_held = witness_carried and chronicle_held
    if relation_meaning_held:
        add_signal(
            weight=2 if current_weight == "high" or meaning_weight == "high" else 1,
            reason="relation and meaning continuity are cohering as one carried thread",
            anchor=" | ".join(anchor for anchor in [relation_anchor, meaning_anchor] if str(anchor or "").strip()),
            core=True,
            propose_gate=True,
        )
    if carried_continuity_held:
        add_signal(
            weight=2 if witness_persistence in {"carried-forward", "persistent"} else 1,
            reason="witnessed continuity is still being carried into chronicle",
            anchor=" | ".join(anchor for anchor in [witness_anchor, chronicle_anchor] if str(anchor or "").strip()),
            core=True,
            propose_gate=True,
        )

    metabolism_summary = metabolism.get("summary") or {}
    metabolism_items = metabolism.get("items") or []
    metabolism_state = str(metabolism_summary.get("current_state") or "none")
    metabolism_anchor = (
        str((metabolism_items[0] or {}).get("source_anchor") or (metabolism_items[0] or {}).get("title") or "metabolism")
        if metabolism_items
        else "metabolism"
    )
    if metabolism_state in {"active-retaining", "consolidating"}:
        add_signal(
            weight=1,
            reason="metabolism still reads as actively carrying shape",
            anchor=metabolism_anchor,
        )

    release_summary = release_markers.get("summary") or {}
    release_state = str(release_summary.get("current_state") or "none")
    if release_state == "release-ready":
        score -= 2
    elif release_state == "release-leaning":
        score -= 1

    silence_hours = _hours_since_iso(continuity.get("latest_finished_at"))
    companion_reasons: list[tuple[int, str, str]] = []

    def add_companion_reason(weight: int, reason: str, anchor: str) -> None:
        companion_reasons.append((weight, reason, anchor))

    if softening_count > 0:
        add_companion_reason(
            1,
            "older open-loop continuity is still carrying a light pull",
            open_anchor,
        )
    if silence_hours is not None and silence_hours >= 6 and current_weight in {"medium", "high"}:
        add_companion_reason(
            2 if silence_hours >= 24 and current_weight == "high" else 1,
            "relation continuity is holding bounded distance under silence",
            relation_anchor,
        )
    persistence_state = str(witness_summary.get("current_persistence_state") or "none")
    if silence_hours is not None and silence_hours >= 6 and (
        int(witness_summary.get("carried_count") or 0) > 0
        or persistence_state in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
    ):
        add_companion_reason(
            2 if persistence_state in {"carried-forward", "persistent"} and silence_hours >= 24 else 1,
            "witness continuity is persisting without a recent outlet",
            witness_anchor,
        )
    if silence_hours is not None and silence_hours >= 12 and str(chronicle_summary.get("current_weight") or "low") in {"medium", "high"}:
        add_companion_reason(
            1,
            "chronicle continuity is still carrying a small longer-horizon brief",
            chronicle_anchor,
        )
    if silence_hours is not None and silence_hours >= 12 and meaning_weight in {"medium", "high"}:
        add_companion_reason(
            1,
            "meaning significance is still softly carried under silence",
            meaning_anchor,
        )

    if companion_reasons:
        raw_companion_weight = sum(weight for weight, _, _ in companion_reasons)
        companion_pressure_weight = min(raw_companion_weight, 4)
        strongest_companion = sorted(companion_reasons, key=lambda item: item[0], reverse=True)[0]
        companion_pressure_reason = strongest_companion[1]
        companion_anchor = " | ".join(
            [
                anchor
                for _, _, anchor in companion_reasons
                if str(anchor or "").strip()
            ][:3]
        )
        if companion_pressure_weight >= 3:
            companion_pressure_state = "present"
        elif companion_pressure_weight >= 1:
            companion_pressure_state = "light"
        if silence_hours is not None and silence_hours >= 24 and companion_pressure_weight >= 2:
            idle_presence_state = "sustained"
        elif silence_hours is not None and silence_hours >= 6:
            idle_presence_state = "present"
        elif companion_pressure_weight > 0:
            idle_presence_state = "light"
        if companion_pressure_weight >= 4 or (
            silence_hours is not None and silence_hours >= 24 and companion_pressure_weight >= 3
        ):
            checkin_worthiness = "medium"
        elif companion_pressure_weight >= 2:
            checkin_worthiness = "low-present"
        add_signal(
            weight=companion_pressure_weight,
            reason=companion_pressure_reason,
            anchor=companion_anchor,
        )

    if trigger == "manual":
        add_signal(
            weight=1,
            reason="manual Mission Control trigger requested attention",
            anchor="manual-trigger",
        )
    if bool(merged_state.get("due")):
        add_signal(
            weight=1,
            reason="heartbeat cadence is currently due",
            anchor="heartbeat-cadence",
        )

    if score <= 0:
        signal = {
            "liveness_state": "quiet",
            "liveness_pressure": "low",
            "liveness_reason": "no-bounded-liveness-pressure",
            "liveness_summary": "No bounded liveness pressure is currently strong enough to pull heartbeat beyond quiet observation.",
            "liveness_confidence": "low",
            "liveness_threshold_state": "quiet-threshold",
            "liveness_score": 0,
            "liveness_signal_count": len(reason_signals),
            "liveness_core_pressure_count": core_pressure_count,
            "liveness_propose_gate_count": propose_gate_count,
            "companion_pressure_state": companion_pressure_state,
            "companion_pressure_reason": companion_pressure_reason,
            "companion_pressure_weight": companion_pressure_weight,
            "idle_presence_state": idle_presence_state,
            "checkin_worthiness": checkin_worthiness,
            "liveness_debug_summary": (
                "score=0 signals=0 core_pressure=0 propose_gates=0 "
                f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
            ),
            "source_anchor": "",
            "status": "inactive",
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "canonical_self_state": "not-canonical-self-truth",
        }
        _log_debug(
            "heartbeat liveness built",
            trigger=trigger,
            state=signal["liveness_state"],
            pressure=signal["liveness_pressure"],
            score=signal["liveness_score"],
            signal_count=signal["liveness_signal_count"],
            core_pressure_count=signal["liveness_core_pressure_count"],
            propose_gate_count=signal["liveness_propose_gate_count"],
        )
        return signal

    sorted_reasons = sorted(reason_signals, key=lambda item: item[0], reverse=True)
    primary_reason = (
        sorted_reasons[0][1]
        if sorted_reasons
        else "bounded runtime pressure is present"
    )
    source_anchor = " | ".join(
        [
            anchor
            for _, _, anchor, _ in sorted_reasons
            if str(anchor or "").strip()
        ][:3]
    )

    if score >= 8 and core_pressure_count >= 2 and propose_gate_count >= 1:
        liveness_pressure = "high"
        liveness_state = "propose-worthy"
        liveness_confidence = "high"
        liveness_threshold_state = "propose-worthy-threshold"
    elif score >= 5:
        liveness_pressure = "high"
        liveness_state = "alive-pressure"
        liveness_confidence = "high" if core_pressure_count >= 2 else "medium"
        liveness_threshold_state = "alive-threshold"
    elif score >= 2:
        liveness_pressure = "medium"
        liveness_state = "watchful"
        liveness_confidence = "medium"
        liveness_threshold_state = "watchful-threshold"
    else:
        liveness_pressure = "low"
        liveness_state = "quiet"
        liveness_confidence = "low"
        liveness_threshold_state = "quiet-threshold"

    if liveness_state == "quiet":
        signal = {
            "liveness_state": "quiet",
            "liveness_pressure": "low",
            "liveness_reason": primary_reason,
            "liveness_summary": (
                f"Heartbeat remains quiet because only light bounded liveness pressure is currently present."
            ),
            "liveness_confidence": liveness_confidence,
            "liveness_threshold_state": liveness_threshold_state,
            "liveness_score": score,
            "liveness_signal_count": len(reason_signals),
            "liveness_core_pressure_count": core_pressure_count,
            "liveness_propose_gate_count": propose_gate_count,
            "companion_pressure_state": companion_pressure_state,
            "companion_pressure_reason": companion_pressure_reason,
            "companion_pressure_weight": companion_pressure_weight,
            "idle_presence_state": idle_presence_state,
            "checkin_worthiness": checkin_worthiness,
            "liveness_debug_summary": (
                f"score={score} signals={len(reason_signals)} "
                f"core_pressure={core_pressure_count} propose_gates={propose_gate_count} "
                f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
            ),
            "source_anchor": source_anchor,
            "status": "inactive",
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "canonical_self_state": "not-canonical-self-truth",
        }
        _log_debug(
            "heartbeat liveness built",
            trigger=trigger,
            state=signal["liveness_state"],
            pressure=signal["liveness_pressure"],
            score=signal["liveness_score"],
            signal_count=signal["liveness_signal_count"],
            core_pressure_count=signal["liveness_core_pressure_count"],
            propose_gate_count=signal["liveness_propose_gate_count"],
            primary_reason=signal["liveness_reason"],
        )
        return signal

    signal = {
        "liveness_state": liveness_state,
        "liveness_pressure": liveness_pressure,
        "liveness_reason": primary_reason,
        "liveness_summary": (
            f"Heartbeat appears to have bounded liveness pressure because {primary_reason}."
        ),
        "liveness_confidence": liveness_confidence,
        "liveness_threshold_state": liveness_threshold_state,
        "liveness_score": score,
        "liveness_signal_count": len(reason_signals),
        "liveness_core_pressure_count": core_pressure_count,
        "liveness_propose_gate_count": propose_gate_count,
        "companion_pressure_state": companion_pressure_state,
        "companion_pressure_reason": companion_pressure_reason,
        "companion_pressure_weight": companion_pressure_weight,
        "idle_presence_state": idle_presence_state,
        "checkin_worthiness": checkin_worthiness,
        "liveness_debug_summary": (
            f"score={score} signals={len(reason_signals)} "
            f"core_pressure={core_pressure_count} propose_gates={propose_gate_count} "
            f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
        ),
        "source_anchor": source_anchor,
        "status": "active",
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "canonical_self_state": "not-canonical-self-truth",
    }
    _log_debug(
        "heartbeat liveness built",
        trigger=trigger,
        state=signal["liveness_state"],
        pressure=signal["liveness_pressure"],
        score=signal["liveness_score"],
        signal_count=signal["liveness_signal_count"],
        core_pressure_count=signal["liveness_core_pressure_count"],
        propose_gate_count=signal["liveness_propose_gate_count"],
        primary_reason=signal["liveness_reason"],
    )
    return signal


def _select_heartbeat_target() -> dict[str, str | bool]:
    supported_providers = {"phase1-runtime", "openai", "openrouter", "ollama"}
    settings = load_settings()
    heartbeat_provider = str(
        getattr(settings, "heartbeat_model_provider", "") or ""
    ).strip()
    heartbeat_model = str(getattr(settings, "heartbeat_model_name", "") or "").strip()
    heartbeat_auth_profile = str(
        getattr(settings, "heartbeat_auth_profile", "") or ""
    ).strip()
    if (
        heartbeat_provider
        and heartbeat_model
        and heartbeat_provider in supported_providers
    ):
        return {
            "lane": "heartbeat",
            "provider": heartbeat_provider,
            "model": heartbeat_model,
            "auth_profile": heartbeat_auth_profile,
            "base_url": "",
            "model_source": "runtime.settings.heartbeat_model",
            "resolution_status": "heartbeat-configured",
            "fallback_used": False,
        }

    runtime_selected_local = _runtime_selected_local_target(settings=settings)
    if runtime_selected_local is not None:
        return runtime_selected_local

    target = resolve_provider_router_target(lane="local")
    provider = str(target.get("provider") or "").strip()
    model = str(target.get("model") or "").strip()
    if provider and model and provider in supported_providers:
        return {
            "lane": "local",
            "provider": provider,
            "model": model,
            "auth_profile": str(target.get("auth_profile") or "").strip(),
            "base_url": str(target.get("base_url") or "").strip(),
            "model_source": "provider-router.local-lane-config",
            "resolution_status": "config-local",
            "fallback_used": False,
        }

    candidates = ["visible", str(settings.cheap_model_lane or "cheap").strip() or "cheap"]
    for lane in candidates:
        target = resolve_provider_router_target(lane=lane)
        provider = str(target.get("provider") or "").strip()
        model = str(target.get("model") or "").strip()
        if not provider or not model:
            continue
        if provider in supported_providers:
            return {
                "lane": lane,
                "provider": provider,
                "model": model,
                "auth_profile": str(target.get("auth_profile") or "").strip(),
                "base_url": str(target.get("base_url") or "").strip(),
                "model_source": f"provider-router.{lane}-lane-fallback",
                "resolution_status": "bounded-fallback",
                "fallback_used": True,
            }
    return {
        "lane": "visible",
        "provider": "phase1-runtime",
        "model": "visible-placeholder",
        "auth_profile": "",
        "base_url": "",
        "model_source": "heartbeat-fallback.visible-placeholder",
        "resolution_status": "bounded-fallback",
        "fallback_used": True,
    }


def _runtime_selected_local_target(
    *, settings
) -> dict[str, str | bool] | None:
    visible_provider = str(getattr(settings, "visible_model_provider", "") or "").strip()
    visible_model = str(getattr(settings, "visible_model_name", "") or "").strip()
    visible_auth_profile = str(
        getattr(settings, "visible_auth_profile", "") or ""
    ).strip()
    if visible_provider != "ollama" or not visible_model:
        return None
    target = resolve_provider_router_target(lane="visible")
    return {
        "lane": "local",
        "provider": "ollama",
        "model": visible_model,
        "auth_profile": visible_auth_profile,
        "base_url": str(target.get("base_url") or "").strip(),
        "model_source": "runtime.settings.visible_model_name",
        "resolution_status": "runtime-selected-local",
        "fallback_used": False,
    }


def _execute_heartbeat_model(
    *,
    prompt: str,
    target: dict[str, str],
    policy: dict[str, object],
    open_loops: list[str],
    liveness: dict[str, object] | None = None,
) -> dict[str, object]:
    provider = target["provider"]
    model = target["model"]
    if provider == "phase1-runtime":
        liveness_summary = str((liveness or {}).get("liveness_summary") or "").strip()
        liveness_pressure = str((liveness or {}).get("liveness_pressure") or "low")
        liveness_threshold_state = str(
            (liveness or {}).get("liveness_threshold_state") or "quiet-threshold"
        )
        summary = open_loops[0] if open_loops else (liveness_summary or "No current due work was detected.")
        decision_type = (
            "execute"
            if bool(policy.get("allow_execute"))
            else (
                "propose"
                if (
                    open_loops
                    or liveness_threshold_state == "propose-worthy-threshold"
                    or (liveness_pressure == "high" and liveness_threshold_state == "alive-threshold")
                )
                else "noop"
            )
        )
        execute_action = "run_candidate_scan" if decision_type == "execute" else ""
        text = json.dumps(
            {
                "decision_type": decision_type,
                "summary": summary,
                "reason": "Phase1 fallback heartbeat used bounded runtime context without provider-backed execution.",
                "proposed_action": summary if decision_type == "propose" else "",
                "ping_text": "",
                "execute_action": execute_action,
            },
            ensure_ascii=False,
        )
        return {
            "text": text,
            "input_tokens": _estimate_tokens(prompt),
            "output_tokens": _estimate_tokens(text),
            "cost_usd": 0.0,
        }
    if provider == "ollama":
        return _execute_ollama_prompt(prompt=prompt, target=target)
    if provider == "openai":
        return _execute_openai_prompt(prompt=prompt, target=target)
    if provider == "openrouter":
        return _execute_openrouter_prompt(prompt=prompt, target=target)
    raise RuntimeError(f"Heartbeat provider not supported: {provider}")


def _execute_ollama_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    base_url = target["base_url"] or "http://127.0.0.1:11434"
    payload = {
        "model": target["model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 160,
        },
    }
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = _http_error_detail(exc)
        raise RuntimeError(f"ollama-http-error:{exc.code}:{detail}") from exc
    except (urllib_error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("ollama-request-failed") from exc
    text = str(data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Heartbeat ollama execution returned no response")
    return {
        "text": text,
        "input_tokens": int(data.get("prompt_eval_count") or _estimate_tokens(prompt)),
        "output_tokens": int(data.get("eval_count") or _estimate_tokens(text)),
        "cost_usd": 0.0,
        "execution_status": "success",
    }


def _execute_openai_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    api_key = _load_provider_api_key(provider="openai", profile=target["auth_profile"])
    base_url = target["base_url"] or "https://api.openai.com/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/responses",
        data=json.dumps({"model": target["model"], "input": prompt}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = _extract_openai_text(data)
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(usage.get("input_tokens", _estimate_tokens(prompt))),
        "output_tokens": int(usage.get("output_tokens", _estimate_tokens(text))),
        "cost_usd": 0.0,
    }


def _execute_openrouter_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    api_key = _load_provider_api_key(provider="openrouter", profile=target["auth_profile"])
    base_url = target["base_url"] or "https://openrouter.ai/api/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": target["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = _extract_openrouter_text(data)
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or _estimate_tokens(prompt)
        ),
        "output_tokens": int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _estimate_tokens(text)
        ),
        "cost_usd": 0.0,
    }


def _heartbeat_prompt_text(base_text: str) -> str:
    return "\n\n".join(
        [
            base_text.strip(),
            "Heartbeat response contract:",
            "- Return only one compact JSON object.",
            "- decision_type must be one of: noop, propose, execute, ping.",
            "- summary must be short and concrete.",
            "- reason must explain why this decision is appropriate now.",
            "- proposed_action should be a short bounded action description or empty.",
            "- ping_text should only be set if decision_type=ping.",
            "- execute_action should only be set if decision_type=execute.",
            f"- Allowed execute_action values: {', '.join(sorted(HEARTBEAT_ALLOWED_EXECUTE_ACTIONS))}.",
            'JSON schema: {"decision_type":"noop|propose|execute|ping","summary":"","reason":"","proposed_action":"","ping_text":"","execute_action":""}',
        ]
    )


def _parse_heartbeat_decision(raw_text: str) -> dict[str, str]:
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.split("\n", 1)[-1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        data = json.loads(_extract_json_object(candidate))
    decision_type = str(data.get("decision_type") or "noop").strip().lower()
    if decision_type not in HEARTBEAT_ALLOWED_DECISIONS:
        decision_type = "noop"
    return {
        "decision_type": decision_type,
        "summary": str(data.get("summary") or "No heartbeat summary returned.").strip(),
        "reason": str(data.get("reason") or "").strip(),
        "proposed_action": str(data.get("proposed_action") or "").strip(),
        "ping_text": str(data.get("ping_text") or "").strip(),
        "execute_action": str(data.get("execute_action") or "").strip(),
    }


def _parse_heartbeat_decision_bounded(raw_text: str) -> tuple[dict[str, str], str]:
    try:
        return _parse_heartbeat_decision(raw_text), "success"
    except (json.JSONDecodeError, ValueError, TypeError):
        return (
            _bounded_heartbeat_failure_decision(
                failure_kind="parse",
                detail=raw_text[:240],
                target=None,
            ),
            "parse-failed",
        )


def _bounded_heartbeat_failure_decision(
    *,
    failure_kind: str,
    detail: str,
    target: dict[str, object] | None,
) -> dict[str, str]:
    if failure_kind == "runtime":
        model = str((target or {}).get("model") or "unknown-model").strip()
        return {
            "decision_type": "noop",
            "summary": "Heartbeat recorded a bounded runtime failure on the selected model.",
            "reason": f"runtime-failure on {model}: {detail[:200]}",
            "proposed_action": "",
            "ping_text": "",
            "execute_action": "",
        }
    return {
        "decision_type": "noop",
        "summary": "Heartbeat recorded a bounded parse failure from the selected model.",
        "reason": f"parse-failure: {detail[:200]}",
        "proposed_action": "",
        "ping_text": "",
        "execute_action": "",
    }


def _classify_heartbeat_execution_exception(exc: Exception) -> str:
    message = str(exc).strip().lower()
    if message.startswith("ollama-http-error"):
        return "http-error"
    if "request-failed" in message:
        return "request-failed"
    return "runtime-failed"


def _http_error_detail(exc: urllib_error.HTTPError) -> str:
    try:
        payload = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        payload = ""
    if not payload:
        return "no-body"
    return payload[:200]


def _validate_heartbeat_decision(
    *,
    decision: dict[str, str],
    policy: dict[str, object],
    workspace_dir: Path,
    tick_id: str,
) -> dict[str, object]:
    decision_type = decision["decision_type"]
    execute_action = str(decision.get("execute_action") or "").strip()
    if decision_type == "propose" and not bool(policy["allow_propose"]):
        return {
            "tick_id": tick_id,
            "blocked_reason": "propose-not-allowed",
            "ping_eligible": False,
            "ping_result": "not-allowed",
            "action_status": "blocked",
            "action_summary": "Heartbeat policy currently blocks propose outputs.",
            "action_type": "",
            "action_artifact": "",
        }
    if decision_type == "execute":
        if not bool(policy["allow_execute"]):
            return {
                "tick_id": tick_id,
                "blocked_reason": "execute-not-allowed",
                "ping_eligible": False,
                "ping_result": "not-allowed",
                "action_status": "blocked",
                "action_summary": "Heartbeat execute actions are disabled in the current policy.",
                "action_type": execute_action,
                "action_artifact": "",
            }
        event_bus.publish(
            "heartbeat.execute_requested",
            {
                "tick_id": tick_id,
                "action_type": execute_action,
                "summary": decision["summary"],
            },
        )
        if execute_action not in HEARTBEAT_ALLOWED_EXECUTE_ACTIONS:
            event_bus.publish(
                "heartbeat.execute_blocked",
                {
                    "tick_id": tick_id,
                    "action_type": execute_action,
                    "blocked_reason": "unsupported-execute-action",
                },
            )
            return {
                "tick_id": tick_id,
                "blocked_reason": "unsupported-execute-action",
                "ping_eligible": False,
                "ping_result": "not-applicable",
                "action_status": "blocked",
                "action_summary": f"Heartbeat execute action {execute_action or 'unknown'} is not in the bounded allowlist.",
                "action_type": execute_action,
                "action_artifact": "",
            }
        action_result = _execute_heartbeat_internal_action(
            action_type=execute_action,
            tick_id=tick_id,
            workspace_dir=workspace_dir,
        )
        if action_result["blocked_reason"]:
            event_bus.publish(
                "heartbeat.execute_blocked",
                {
                    "tick_id": tick_id,
                    "action_type": execute_action,
                    "blocked_reason": action_result["blocked_reason"],
                    "summary": action_result["summary"],
                },
            )
            return {
                "tick_id": tick_id,
                "blocked_reason": str(action_result["blocked_reason"]),
                "ping_eligible": False,
                "ping_result": "not-applicable",
                "action_status": str(action_result["status"]),
                "action_summary": str(action_result["summary"]),
                "action_type": execute_action,
                "action_artifact": str(action_result["artifact"]),
            }
        event_bus.publish(
            "heartbeat.execute_completed",
            {
                "tick_id": tick_id,
                "action_type": execute_action,
                "summary": action_result["summary"],
                "artifact": action_result["artifact"],
            },
        )
        return {
            "tick_id": tick_id,
            "blocked_reason": "",
            "ping_eligible": False,
            "ping_result": "not-applicable",
            "action_status": str(action_result["status"]),
            "action_summary": str(action_result["summary"]),
            "action_type": execute_action,
            "action_artifact": str(action_result["artifact"]),
        }
    if decision_type == "ping":
        if not bool(policy["allow_ping"]):
            return {
                "tick_id": tick_id,
                "blocked_reason": "ping-not-allowed",
                "ping_eligible": False,
                "ping_result": "not-allowed",
                "action_status": "blocked",
                "action_summary": "Heartbeat pings are disabled in the current policy.",
                "action_type": "",
                "action_artifact": "",
            }
        ping_channel = str(policy["ping_channel"])
        if ping_channel not in {"internal-only", "none", "webchat"}:
            return {
                "tick_id": tick_id,
                "blocked_reason": "unsupported-ping-channel",
                "ping_eligible": False,
                "ping_result": "unsupported-channel",
                "action_status": "blocked",
                "action_summary": f"Ping channel {ping_channel} is not supported in bounded heartbeat runtime.",
                "action_type": "",
                "action_artifact": "",
            }
        if ping_channel == "none":
            return {
                "tick_id": tick_id,
                "blocked_reason": "no-ping-channel",
                "ping_eligible": False,
                "ping_result": "missing-channel",
                "action_status": "blocked",
                "action_summary": "Ping is allowed in policy, but no usable bounded ping channel is configured.",
                "action_type": "",
                "action_artifact": "",
            }
        if ping_channel == "webchat":
            from apps.api.jarvis_api.services.tiny_webchat_execution_pilot import (
                maybe_run_tiny_webchat_execution_pilot,
            )

            pilot_result = maybe_run_tiny_webchat_execution_pilot(
                policy=policy,
                heartbeat_tick_id=tick_id,
                decision_summary=str(decision.get("summary") or ""),
                ping_text=str(decision.get("ping_text") or ""),
            )
            item = pilot_result.get("item") or {}
            if str(pilot_result.get("delivery_state") or "") != "sent":
                return {
                    "tick_id": tick_id,
                    "blocked_reason": str(pilot_result.get("blocked_reason") or "webchat-delivery-blocked"),
                    "ping_eligible": False,
                    "ping_result": str(pilot_result.get("delivery_state") or "blocked"),
                    "action_status": "blocked",
                    "action_summary": str(pilot_result.get("summary") or "Tiny webchat execution pilot was blocked."),
                    "action_type": "webchat-proactive-question",
                    "action_artifact": str(item.get("pilot_id") or ""),
                }
            return {
                "tick_id": tick_id,
                "blocked_reason": "",
                "ping_eligible": True,
                "ping_result": "sent-webchat",
                "action_status": "sent",
                "action_summary": str(pilot_result.get("summary") or "Tiny webchat execution pilot delivered one bounded proactive question."),
                "action_type": "webchat-proactive-question",
                "action_artifact": str(item.get("pilot_id") or ""),
            }
        return {
            "tick_id": tick_id,
            "blocked_reason": "",
            "ping_eligible": True,
            "ping_result": "recorded-preview",
            "action_status": "recorded",
            "action_summary": decision["ping_text"] or decision["summary"] or "Heartbeat ping preview recorded.",
            "action_type": "",
            "action_artifact": "",
        }
    return {
        "tick_id": tick_id,
        "blocked_reason": "",
        "ping_eligible": False,
        "ping_result": "not-applicable",
        "action_status": "recorded",
        "action_summary": decision["proposed_action"] or decision["summary"] or "Heartbeat outcome recorded.",
        "action_type": "",
        "action_artifact": "",
    }


def _recover_bounded_heartbeat_liveness_decision(
    *,
    decision: dict[str, str],
    policy: dict[str, object],
    liveness: dict[str, object] | None,
) -> dict[str, str]:
    if str(decision.get("decision_type") or "") != "noop":
        return decision
    if not bool(policy.get("allow_propose")):
        return decision

    liveness_state = str((liveness or {}).get("liveness_state") or "quiet")
    liveness_pressure = str((liveness or {}).get("liveness_pressure") or "low")
    liveness_threshold_state = str(
        (liveness or {}).get("liveness_threshold_state") or "quiet-threshold"
    )
    liveness_reason = str((liveness or {}).get("liveness_reason") or "").strip()
    liveness_summary = str((liveness or {}).get("liveness_summary") or "").strip()
    if (
        liveness_state == "quiet"
        or liveness_pressure not in {"medium", "high"}
        or liveness_threshold_state != "propose-worthy-threshold"
    ):
        return decision

    return {
        "decision_type": "propose",
        "summary": liveness_summary or "Heartbeat appears to have bounded liveness pressure and is proposing a small check-in rather than a noop.",
        "reason": (
            f"bounded-liveness-recovery: {liveness_reason or 'runtime liveness pressure is present'}"
        )[:240],
        "proposed_action": liveness_summary or "Review bounded runtime liveness pressure before the thread goes cold.",
        "ping_text": "",
        "execute_action": "",
    }


def _execute_heartbeat_internal_action(
    *,
    action_type: str,
    tick_id: str,
    workspace_dir: Path,
) -> dict[str, str]:
    del workspace_dir
    if action_type == "run_candidate_scan":
        review = track_runtime_contract_candidates_for_session_review(
            session_id=None,
            run_id=tick_id,
        )
        created = int(review.get("created") or 0)
        pref_count = int(review.get("preference_updates") or 0)
        memory_count = int(review.get("memory_promotions") or 0)
        messages_scanned = int(review.get("messages_scanned") or 0)
        session_id = str(review.get("session_id") or "")
        summary = (
            f"Heartbeat scanned {messages_scanned} recent user messages and proposed {created} candidates."
            if messages_scanned
            else "Heartbeat found no recent user messages to review."
        )
        artifact = json.dumps(
            {
                "session_id": session_id,
                "messages_scanned": messages_scanned,
                "created": created,
                "preference_updates": pref_count,
                "memory_promotions": memory_count,
                "candidate_ids": [
                    str(item.get("candidate_id") or "")
                    for item in list(review.get("items") or [])[:6]
                    if str(item.get("candidate_id") or "")
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "status": "executed",
            "summary": summary,
            "artifact": artifact,
            "blocked_reason": "",
        }
    return {
        "status": "blocked",
        "summary": f"Heartbeat execute action {action_type or 'unknown'} is not supported.",
        "artifact": "",
        "blocked_reason": "unsupported-execute-action",
    }


def _record_heartbeat_outcome(
    *,
    policy: dict[str, object],
    persisted: dict[str, object],
    tick_id: str,
    trigger: str,
    tick_status: str,
    decision_type: str,
    decision_summary: str,
    decision_reason: str,
    blocked_reason: str,
    currently_ticking: bool,
    last_trigger_source: str,
    provider: str,
    model: str,
    lane: str,
    budget_status: str,
    model_source: str = "",
    resolution_status: str = "",
    fallback_used: bool = False,
    execution_status: str = "",
    parse_status: str = "",
    ping_eligible: bool,
    ping_result: str,
    action_status: str,
    action_summary: str,
    action_type: str,
    action_artifact: str,
    raw_response: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    started_at: str,
    finished_at: str,
    workspace_dir: Path,
) -> dict[str, object]:
    tick = record_heartbeat_runtime_tick(
        tick_id=tick_id,
        trigger=trigger,
        tick_status=tick_status,
        decision_type=decision_type,
        decision_summary=decision_summary,
        decision_reason=decision_reason,
        blocked_reason=blocked_reason,
        provider=provider,
        model=model,
        lane=lane,
        model_source=model_source,
        resolution_status=resolution_status,
        fallback_used=fallback_used,
        execution_status=execution_status,
        parse_status=parse_status,
        budget_status=budget_status,
        ping_eligible=ping_eligible,
        ping_result=ping_result,
        action_status=action_status,
        action_summary=action_summary,
        action_type=action_type,
        action_artifact=action_artifact[:4000],
        raw_response=raw_response[:4000],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        started_at=started_at,
        finished_at=finished_at,
    )

    next_tick_at = _compute_next_tick_at(
        interval_minutes=int(policy["interval_minutes"]),
        last_tick_at=finished_at,
        enabled=bool(policy["enabled"]),
    )
    upsert_heartbeat_runtime_state(
        state_id=str(persisted.get("state_id") or "default"),
        last_tick_id=tick_id,
        last_tick_at=finished_at,
        next_tick_at=next_tick_at,
        schedule_state=_merge_runtime_state(
            policy=policy,
            persisted={
                **_default_persisted_state(),
                **persisted,
                "last_tick_id": tick_id,
                "last_tick_at": finished_at,
                "next_tick_at": next_tick_at,
                "last_decision_type": decision_type,
                "last_result": decision_summary or action_summary,
                "blocked_reason": blocked_reason,
                "currently_ticking": currently_ticking,
                "last_trigger_source": last_trigger_source,
                "provider": provider,
                "model": model,
                "lane": lane,
                "model_source": model_source,
                "resolution_status": resolution_status,
                "fallback_used": fallback_used,
                "execution_status": execution_status,
                "parse_status": parse_status,
                "budget_status": budget_status,
                "last_ping_eligible": ping_eligible,
                "last_ping_result": ping_result,
                "last_action_type": action_type,
                "last_action_status": action_status,
                "last_action_summary": action_summary,
                "last_action_artifact": action_artifact[:4000],
                "updated_at": finished_at,
            },
            now=datetime.now(UTC),
        )["schedule_state"],
        due=False,
        last_decision_type=decision_type,
        last_result=decision_summary or action_summary,
        blocked_reason=blocked_reason,
        currently_ticking=currently_ticking,
        last_trigger_source=last_trigger_source,
        scheduler_active=bool(_HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive()),
        scheduler_started_at=str(persisted.get("scheduler_started_at") or ""),
        scheduler_stopped_at=str(persisted.get("scheduler_stopped_at") or ""),
        scheduler_health=(
            "active"
            if (_HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive())
            else str(persisted.get("scheduler_health") or "manual-only")
        ),
        recovery_status=(
            "startup-recovery-completed"
            if last_trigger_source == "startup-recovery"
            else str(persisted.get("recovery_status") or "idle")
        ),
        last_recovery_at=(
            finished_at if last_trigger_source == "startup-recovery" else str(persisted.get("last_recovery_at") or "")
        ),
        provider=provider,
        model=model,
        lane=lane,
        model_source=model_source,
        resolution_status=resolution_status,
        fallback_used=fallback_used,
        execution_status=execution_status,
        parse_status=parse_status,
        budget_status=budget_status,
        last_ping_eligible=ping_eligible,
        last_ping_result=ping_result,
        last_action_type=action_type,
        last_action_status=action_status,
        last_action_summary=action_summary,
        last_action_artifact=action_artifact[:4000],
        updated_at=finished_at,
    )
    latest_state = get_heartbeat_runtime_state() or _default_persisted_state()
    _write_heartbeat_state_artifact(
        workspace_dir=workspace_dir,
        payload={
            "state": _merge_runtime_state(
                policy=policy,
                persisted=latest_state,
                now=datetime.now(UTC),
            ),
            "policy": policy,
            "recent_ticks": recent_heartbeat_runtime_ticks(limit=8),
        },
    )
    return tick


def _merge_runtime_state(
    *,
    policy: dict[str, object],
    persisted: dict[str, object],
    now: datetime,
) -> dict[str, object]:
    last_tick_at = str(persisted.get("last_tick_at") or "")
    next_tick_at = str(persisted.get("next_tick_at") or "") or _compute_next_tick_at(
        interval_minutes=int(policy["interval_minutes"]),
        last_tick_at=last_tick_at,
        enabled=bool(policy["enabled"]),
    )
    due = False
    if policy["enabled"] and policy["kill_switch"] == "enabled":
        if not next_tick_at:
            due = True
        else:
            due_ts = _parse_dt(next_tick_at)
            due = due_ts is not None and due_ts <= now
    schedule_status = "disabled"
    if bool(persisted.get("currently_ticking")):
        schedule_status = "ticking"
    elif policy["enabled"]:
        schedule_status = "due" if due else "scheduled"
    if policy["kill_switch"] != "enabled":
        schedule_status = "blocked"
    return {
        "enabled": bool(policy["enabled"]),
        "kill_switch": str(policy["kill_switch"]),
        "interval_minutes": int(policy["interval_minutes"]),
        "schedule_status": schedule_status,
        "schedule_state": schedule_status,
        "due": due,
        "last_tick_id": str(persisted.get("last_tick_id") or ""),
        "last_tick_at": last_tick_at,
        "next_tick_at": next_tick_at,
        "last_decision_type": str(persisted.get("last_decision_type") or ""),
        "last_result": str(persisted.get("last_result") or ""),
        "blocked_reason": str(persisted.get("blocked_reason") or ""),
        "currently_ticking": bool(persisted.get("currently_ticking")),
        "last_trigger_source": str(persisted.get("last_trigger_source") or ""),
        "scheduler_active": bool(persisted.get("scheduler_active")),
        "scheduler_started_at": str(persisted.get("scheduler_started_at") or ""),
        "scheduler_stopped_at": str(persisted.get("scheduler_stopped_at") or ""),
        "scheduler_health": str(persisted.get("scheduler_health") or ("active" if bool(persisted.get("scheduler_active")) else "stopped")),
        "recovery_status": str(persisted.get("recovery_status") or ""),
        "last_recovery_at": str(persisted.get("last_recovery_at") or ""),
        "provider": str(persisted.get("provider") or ""),
        "model": str(persisted.get("model") or ""),
        "lane": str(persisted.get("lane") or ""),
        "model_source": str(persisted.get("model_source") or ""),
        "resolution_status": str(persisted.get("resolution_status") or ""),
        "fallback_used": bool(persisted.get("fallback_used")),
        "execution_status": str(persisted.get("execution_status") or ""),
        "parse_status": str(persisted.get("parse_status") or ""),
        "budget_status": str(persisted.get("budget_status") or policy["budget_status"]),
        "policy_summary": str(policy["summary"]),
        "last_ping_eligible": bool(persisted.get("last_ping_eligible")),
        "last_ping_result": str(persisted.get("last_ping_result") or ""),
        "last_action_type": str(persisted.get("last_action_type") or ""),
        "last_action_status": str(persisted.get("last_action_status") or ""),
        "last_action_summary": str(persisted.get("last_action_summary") or ""),
        "last_action_artifact": str(persisted.get("last_action_artifact") or ""),
        "summary": _heartbeat_state_summary(
            enabled=bool(policy["enabled"]),
            schedule_status=schedule_status,
            last_decision_type=str(persisted.get("last_decision_type") or ""),
            last_result=str(persisted.get("last_result") or ""),
        ),
        "source": "/mc/jarvis::heartbeat",
        "state_file": str((Path(policy["workspace"]) / HEARTBEAT_STATE_REL_PATH)),
        "updated_at": str(persisted.get("updated_at") or ""),
    }


def _tick_blocked_reason(merged_state: dict[str, object]) -> str:
    if not bool(merged_state["enabled"]):
        return "disabled"
    if str(merged_state["kill_switch"]) != "enabled":
        return "kill-switch-disabled"
    return ""


def _compute_next_tick_at(*, interval_minutes: int, last_tick_at: str, enabled: bool) -> str:
    if not enabled:
        return ""
    parsed = _parse_dt(last_tick_at)
    base = parsed or datetime.now(UTC)
    return (base + timedelta(minutes=max(interval_minutes, 1))).isoformat()


def _write_heartbeat_state_artifact(*, workspace_dir: Path, payload: dict[str, object]) -> None:
    state_path = workspace_dir / HEARTBEAT_STATE_REL_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _default_persisted_state() -> dict[str, object]:
    return {
        "state_id": "default",
        "last_tick_id": "",
        "last_tick_at": "",
        "next_tick_at": "",
        "schedule_state": "",
        "due": False,
        "last_decision_type": "",
        "last_result": "",
        "blocked_reason": "",
        "currently_ticking": False,
        "last_trigger_source": "",
        "scheduler_active": False,
        "scheduler_started_at": "",
        "scheduler_stopped_at": "",
        "scheduler_health": "stopped",
        "recovery_status": "",
        "last_recovery_at": "",
        "provider": "",
        "model": "",
        "lane": "",
        "model_source": "",
        "resolution_status": "",
        "fallback_used": False,
        "execution_status": "",
        "parse_status": "",
        "budget_status": "",
        "last_ping_eligible": False,
        "last_ping_result": "",
        "last_action_type": "",
        "last_action_status": "",
        "last_action_summary": "",
        "last_action_artifact": "",
        "updated_at": "",
    }


def _heartbeat_state_summary(
    *, enabled: bool, schedule_status: str, last_decision_type: str, last_result: str
) -> str:
    if not enabled:
        return "Heartbeat is disabled by policy."
    if schedule_status == "ticking":
        return "Heartbeat tick is currently in progress."
    if schedule_status == "blocked":
        return "Heartbeat is blocked by kill switch."
    if last_decision_type and last_result:
        return f"{last_decision_type}: {last_result}"
    return "Heartbeat is configured and awaiting a bounded tick."


def _persist_runtime_state(
    *,
    policy: dict[str, object],
    persisted: dict[str, object],
    now: datetime,
    overrides: dict[str, object],
) -> dict[str, object]:
    merged_input = {
        **_default_persisted_state(),
        **persisted,
        **overrides,
    }
    merged = _merge_runtime_state(policy=policy, persisted=merged_input, now=now)
    return upsert_heartbeat_runtime_state(
        state_id=str(merged_input.get("state_id") or "default"),
        last_tick_id=str(merged_input.get("last_tick_id") or ""),
        last_tick_at=str(merged_input.get("last_tick_at") or ""),
        next_tick_at=str(merged.get("next_tick_at") or merged_input.get("next_tick_at") or ""),
        schedule_state=str(merged.get("schedule_state") or merged_input.get("schedule_state") or ""),
        due=bool(merged.get("due")),
        last_decision_type=str(merged_input.get("last_decision_type") or ""),
        last_result=str(merged_input.get("last_result") or ""),
        blocked_reason=str(merged_input.get("blocked_reason") or ""),
        currently_ticking=bool(merged_input.get("currently_ticking")),
        last_trigger_source=str(merged_input.get("last_trigger_source") or ""),
        scheduler_active=bool(merged_input.get("scheduler_active")),
        scheduler_started_at=str(merged_input.get("scheduler_started_at") or ""),
        scheduler_stopped_at=str(merged_input.get("scheduler_stopped_at") or ""),
        scheduler_health=str(merged_input.get("scheduler_health") or ""),
        recovery_status=str(merged_input.get("recovery_status") or ""),
        last_recovery_at=str(merged_input.get("last_recovery_at") or ""),
        provider=str(merged_input.get("provider") or ""),
        model=str(merged_input.get("model") or ""),
        lane=str(merged_input.get("lane") or ""),
        model_source=str(merged_input.get("model_source") or ""),
        resolution_status=str(merged_input.get("resolution_status") or ""),
        fallback_used=bool(merged_input.get("fallback_used")),
        execution_status=str(merged_input.get("execution_status") or ""),
        parse_status=str(merged_input.get("parse_status") or ""),
        budget_status=str(merged_input.get("budget_status") or policy["budget_status"]),
        last_ping_eligible=bool(merged_input.get("last_ping_eligible")),
        last_ping_result=str(merged_input.get("last_ping_result") or ""),
        last_action_type=str(merged_input.get("last_action_type") or ""),
        last_action_status=str(merged_input.get("last_action_status") or ""),
        last_action_summary=str(merged_input.get("last_action_summary") or ""),
        last_action_artifact=str(merged_input.get("last_action_artifact") or ""),
        updated_at=str(merged_input.get("updated_at") or now.isoformat()),
    )


def _parse_heartbeat_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = _KEY_LINE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        values[key] = value
    return values


def _parse_bool(
    value: str | None,
    *,
    default: bool,
    truthy: set[str] | None = None,
) -> bool:
    if value is None:
        return default
    lowered = str(value).strip().lower()
    if truthy is None:
        truthy = {"true", "yes", "1", "on", "enabled"}
    if lowered in truthy:
        return True
    if lowered in {"false", "no", "0", "off", "disabled"}:
        return False
    return default


def _parse_int(value: str | None, *, default: int, minimum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return default
    return max(parsed, minimum)


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    depth = 0
    for index, char in enumerate(text[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise json.JSONDecodeError("Unterminated JSON object", text, start)


def _extract_openai_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text":
                parts.append(str(content.get("text", "")))
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError("Heartbeat OpenAI execution returned no output_text")
    return text


def _extract_openrouter_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Heartbeat OpenRouter execution returned no choices")
    message = choices[0].get("message") or {}
    text = str(message.get("content") or "").strip()
    if not text:
        raise RuntimeError("Heartbeat OpenRouter execution returned no content")
    return text


def _load_provider_api_key(*, provider: str, profile: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        raise RuntimeError(f"{provider} heartbeat execution not ready: missing-profile")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError(f"{provider} heartbeat execution not ready: missing-credentials")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(credentials.get("api_key") or credentials.get("access_token") or "").strip()
    if not api_key:
        raise RuntimeError(f"{provider} heartbeat execution not ready: missing-credentials")
    return api_key


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _estimate_tokens(text: str) -> int:
    return max(1, len((text or "").split()))


def _heartbeat_busy_result(*, name: str, trigger: str) -> HeartbeatExecutionResult:
    policy = load_heartbeat_policy(name=name)
    workspace_dir = ensure_default_workspace(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    now = datetime.now(UTC).isoformat()
    tick = _record_heartbeat_outcome(
        policy=policy,
        persisted=persisted,
        tick_id=f"heartbeat-tick:{uuid.uuid4()}",
        trigger=trigger,
        tick_status="blocked",
        decision_type="noop",
        decision_summary="Heartbeat tick skipped because another tick is already running.",
        decision_reason="already-ticking",
        blocked_reason="already-ticking",
        currently_ticking=True,
        last_trigger_source=trigger,
        provider=str(persisted.get("provider") or ""),
        model=str(persisted.get("model") or ""),
        lane=str(persisted.get("lane") or ""),
        budget_status=str(persisted.get("budget_status") or policy["budget_status"]),
        ping_eligible=False,
        ping_result="not-checked",
        action_status="blocked",
        action_summary="Another heartbeat tick is already running.",
        action_type="",
        action_artifact="",
        raw_response="",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        started_at=now,
        finished_at=now,
        workspace_dir=workspace_dir,
    )
    event_bus.publish(
        "heartbeat.tick_blocked",
        {
            "tick_id": tick["tick_id"],
            "blocked_reason": "already-ticking",
            "trigger": trigger,
        },
    )
    return HeartbeatExecutionResult(
        state=heartbeat_runtime_surface(name=name)["state"],
        tick=tick,
        policy=policy,
    )


def _heartbeat_scheduler_loop(*, name: str, startup_recovery_requested: bool) -> None:
    logger.info(
        "heartbeat scheduler loop entered name=%s startup_recovery_requested=%s interval_seconds=%s",
        name,
        startup_recovery_requested,
        _HEARTBEAT_SCHEDULER_INTERVAL_SECONDS,
    )
    try:
        _poll_heartbeat_schedule_with_trigger(
            name=name,
            due_trigger="startup-recovery" if startup_recovery_requested else "scheduled",
        )
    except Exception as exc:
        event_bus.publish(
            "heartbeat.tick_blocked",
            {
                "blocked_reason": "scheduler-error",
                "detail": str(exc),
                "trigger": "startup-recovery" if startup_recovery_requested else "scheduled",
            },
        )
    while not _HEARTBEAT_SCHEDULER_STOP.wait(_HEARTBEAT_SCHEDULER_INTERVAL_SECONDS):
        try:
            _log_debug("heartbeat scheduler iteration", name=name)
            poll_heartbeat_schedule(name=name)
        except Exception as exc:
            logger.exception("heartbeat scheduler iteration failed name=%s", name)
            event_bus.publish(
                "heartbeat.tick_blocked",
                {
                    "blocked_reason": "scheduler-error",
                    "detail": str(exc),
                    "trigger": "scheduled",
                },
            )


def _prepare_scheduler_startup(*, name: str) -> dict[str, object]:
    policy = load_heartbeat_policy(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    now = datetime.now(UTC)
    recovery_status = "idle"
    blocked_reason = str(persisted.get("blocked_reason") or "")
    last_recovery_at = str(persisted.get("last_recovery_at") or "")
    currently_ticking = bool(persisted.get("currently_ticking"))
    if currently_ticking:
        stale_started = _parse_dt(str(persisted.get("updated_at") or persisted.get("last_tick_at") or ""))
        if stale_started is None or stale_started <= now - timedelta(minutes=_STALE_TICK_RECOVERY_WINDOW_MINUTES):
            currently_ticking = False
            blocked_reason = "stale-ticking-state-cleared"
            recovery_status = "stale-ticking-state-cleared"
            last_recovery_at = now.isoformat()

    startup_state = _persist_runtime_state(
        policy=policy,
        persisted=persisted,
        now=now,
        overrides={
            "blocked_reason": blocked_reason,
            "currently_ticking": currently_ticking,
            "scheduler_active": True,
            "scheduler_started_at": now.isoformat(),
            "scheduler_stopped_at": "",
            "scheduler_health": "active",
            "recovery_status": recovery_status,
            "last_recovery_at": last_recovery_at,
            "updated_at": now.isoformat(),
        },
    )
    next_tick_at = _parse_dt(str(startup_state.get("next_tick_at") or ""))
    should_trigger_recovery = bool(
        policy.get("enabled")
        and not startup_state.get("currently_ticking")
        and str(policy.get("kill_switch") or "enabled") == "enabled"
        and next_tick_at is not None
        and next_tick_at <= now
    )
    if should_trigger_recovery:
        event_bus.publish(
            "heartbeat.overdue_detected",
            {
                "schedule_state": startup_state.get("schedule_state"),
                "last_tick_at": startup_state.get("last_tick_at"),
                "next_tick_at": startup_state.get("next_tick_at"),
                "trigger": "startup",
            },
        )
        startup_state = _persist_runtime_state(
            policy=policy,
            persisted=get_heartbeat_runtime_state() or startup_state,
            now=now,
            overrides={
                "scheduler_active": True,
                "scheduler_started_at": now.isoformat(),
                "scheduler_stopped_at": "",
                "scheduler_health": "active",
                "recovery_status": "startup-recovery-pending",
                "last_recovery_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
        )
    _log_debug(
        "heartbeat scheduler startup prepared",
        name=name,
        schedule_state=startup_state.get("schedule_state"),
        due=startup_state.get("due"),
        startup_recovery_requested=should_trigger_recovery,
        blocked_reason=startup_state.get("blocked_reason"),
    )
    return {
        **startup_state,
        "startup_recovery_requested": should_trigger_recovery,
    }


def _mark_scheduler_stopped(*, name: str) -> None:
    policy = load_heartbeat_policy(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    now = datetime.now(UTC)
    stopped = _persist_runtime_state(
        policy=policy,
        persisted=persisted,
        now=now,
        overrides={
            "scheduler_active": False,
            "scheduler_stopped_at": now.isoformat(),
            "scheduler_health": "stopped",
            "updated_at": now.isoformat(),
        },
    )
    event_bus.publish(
        "heartbeat.scheduler_stopped",
        {
            "schedule_state": stopped.get("schedule_state"),
            "last_tick_at": stopped.get("last_tick_at"),
            "next_tick_at": stopped.get("next_tick_at"),
        },
    )


def _emit_schedule_transitions(state: dict[str, object]) -> None:
    global _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT
    previous_state = str(_HEARTBEAT_LAST_SCHEDULE_SNAPSHOT.get("schedule_state") or "")
    current_state = str(state.get("schedule_state") or "")
    previous_due = bool(_HEARTBEAT_LAST_SCHEDULE_SNAPSHOT.get("due"))
    current_due = bool(state.get("due"))

    if previous_state != current_state:
        event_bus.publish(
            "heartbeat.schedule_state_changed",
            {
                "previous_state": previous_state or "unknown",
                "schedule_state": current_state,
                "next_tick_at": state.get("next_tick_at"),
                "blocked_reason": state.get("blocked_reason") or "",
            },
        )
    if current_due and not previous_due:
        event_bus.publish(
            "heartbeat.became_due",
            {
                "schedule_state": current_state,
                "next_tick_at": state.get("next_tick_at"),
                "last_tick_at": state.get("last_tick_at"),
            },
        )
        event_bus.publish(
            "heartbeat.overdue_detected",
            {
                "schedule_state": current_state,
                "next_tick_at": state.get("next_tick_at"),
                "last_tick_at": state.get("last_tick_at"),
                "trigger": "scheduler",
            },
        )
    _HEARTBEAT_LAST_SCHEDULE_SNAPSHOT = {
        "schedule_state": current_state,
        "due": current_due,
    }
