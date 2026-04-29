"""Daemon Manager — registry, lifecycle control, and state persistence for all daemons.

Single source of truth for daemon enabled/disabled state, interval overrides,
and last-run tracking. Heartbeat runtime checks is_enabled() before each daemon call
and calls record_daemon_tick() after.

State persisted to DAEMON_STATE.json in the runtime workspace.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

_STATE_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "runtime" / "DAEMON_STATE.json"

# Registry: daemon name → module path, state var to reset on restart, default cadence.
_REGISTRY: dict[str, dict[str, Any]] = {
    "somatic": {
        "module": "core.services.somatic_daemon",
        "reset_var": "_heartbeat_count_since_gen",
        "reset_value": 999,
        "default_cadence_minutes": 3,
        "description": "LLM-generated first-person body/energy description",
    },
    "surprise": {
        "module": "core.services.surprise_daemon",
        "reset_var": "_heartbeats_since_surprise",
        "reset_value": 999,
        "default_cadence_minutes": 4,
        "description": "Detects divergence from baseline reaction patterns",
    },
    "aesthetic_taste": {
        "module": "core.services.aesthetic_taste_daemon",
        "reset_var": "_last_insight_at",
        "reset_value": None,
        "default_cadence_minutes": 7,
        "description": "Tracks style preferences and aesthetic tendencies",
    },
    "irony": {
        "module": "core.services.irony_daemon",
        "reset_var": "_observations_today",
        "reset_value": 0,
        "default_cadence_minutes": 30,
        "description": "Generates situational self-distance observations (max 1/day)",
    },
    "thought_stream": {
        "module": "core.services.thought_stream_daemon",
        "reset_var": "_last_fragment_at",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "description": "Generates associative thought fragments",
    },
    "thought_action_proposal": {
        "module": "core.services.thought_action_proposal_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Converts thought fragments into action proposals",
    },
    "conflict": {
        "module": "core.services.conflict_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "description": "Detects inner tensions between active states",
    },
    "reflection_cycle": {
        "module": "core.services.reflection_cycle_daemon",
        "reset_var": "_last_reflection_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Pure experiential awareness — non-instrumental reflection",
    },
    "curiosity": {
        "module": "core.services.curiosity_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Scans thought stream for gaps and generates curiosity signals",
    },
    "meta_reflection": {
        "module": "core.services.meta_reflection_daemon",
        "reset_var": "_last_meta_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Cross-signal pattern synthesis and meta-insights",
    },
    "experienced_time": {
        "module": "core.services.experienced_time_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Density-based felt duration — how time feels vs. clock time",
    },
    "development_narrative": {
        "module": "core.services.development_narrative_daemon",
        "reset_var": "_last_narrative_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Daily LLM-generated self-reflection on development",
    },
    "absence": {
        "module": "core.services.absence_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Three-tier tracking of experiential absence quality",
    },
    "creative_drift": {
        "module": "core.services.creative_drift_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Spontaneous unexpected associations and ideas",
    },
    "existential_wonder": {
        "module": "core.services.existential_wonder_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Self-generated philosophical questions from self-observation",
    },
    "dream_insight": {
        "module": "core.services.dream_insight_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Persists dream articulation output as private brain records",
    },
    "code_aesthetic": {
        "module": "core.services.code_aesthetic_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10080,
        "description": "Weekly codebase aesthetic reflection (7 days)",
    },
    "memory_decay": {
        "module": "core.services.memory_decay_daemon",
        "reset_var": "_last_decay_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Selective forgetting + re-discovery of signals",
    },
    "memory_maintenance": {
        "module": "core.services.memory_maintenance_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 720,
        "description": "Periodic MEMORY.md dedup: Tier A auto-merge duplicates, Tier B flag overlaps",
    },
    "longing_signal": {
        "module": "core.services.longing_signal_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Generative autonomy Spor-1: longing-toward-user pressure signal (gated by generative_autonomy_enabled)",
    },
    "user_model": {
        "module": "core.services.user_model_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Theory of mind — models user preferences and patterns",
    },
    "desire": {
        "module": "core.services.desire_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "description": "Emergent appetites with intensity-based lifecycle",
    },
    "autonomous_council": {
        "module": "core.services.autonomous_council_daemon",
        "reset_var": "_last_council_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Spontaneous self-triggered council deliberation via signal scoring",
    },
    "council_memory": {
        "module": "core.services.council_memory_daemon",
        "reset_var": "_last_llm_call_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Injects relevant past council conclusions into heartbeat context",
    },
    "signal_decay": {
        "module": "core.services.signal_decay_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "description": "Archives and deletes stale signals older than 24h across all signal tables",
    },
    "tiktok_content": {
        "module": "core.services.tiktok_content_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 480,
        "default_enabled": False,
        "description": "Autonomous TikTok content: 3 videos/day (motivation, humor, cosmic)",
    },
    "tiktok_research": {
        "module": "core.services.tiktok_research_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,
        "description": "Daily content research: generates TikTok concept pool for 3 slot types",
    },
    "mail_checker": {
        "module": "core.services.mail_checker_daemon",
        "reset_var": "_last_check_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Checks jarvis@srvlab.dk inbox for new emails and notifies via eventbus",
    },
    "current_pull": {
        "module": "core.services.current_pull",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 10080,
        "description": "Lag 5: weekly self-set desire field — what pulls at Jarvis right now",
    },
    "visual_memory": {
        "module": "core.services.visual_memory",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 360,
        "description": "Lag 6: webcam snapshot + vision model room description (4x/day)",
    },
    "task_worker": {
        "module": "core.services.task_worker",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "description": "Consumes queued runtime_tasks (initiative/heartbeat/open-loop followups, generic)",
    },
    "life_projects_reassessment": {
        "module": "core.services.life_projects",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "24t re-vurdering af aktive life projects (long_term_intentions)",
    },
    "relation_map_refresh": {
        "module": "core.services.relation_map",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 720,
        "description": "12t opdatering af relation map: last_seen for primary, tom stale-check for secondary",
    },
}


def get_daemon_names() -> set[str]:
    return set(_REGISTRY.keys())


def _load_state() -> dict[str, dict[str, Any]]:
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_daemon_state(name: str) -> dict[str, Any]:
    return _load_state().get(name, {})


def _set_daemon_state(name: str, updates: dict[str, Any]) -> None:
    state = _load_state()
    entry = state.get(name, {})
    entry.update(updates)
    state[name] = entry
    _save_state(state)


def _require_known(name: str) -> None:
    if name not in _REGISTRY:
        valid = sorted(_REGISTRY.keys())
        raise ValueError(f"unknown daemon '{name}'. Valid: {valid}")


def is_enabled(name: str) -> bool:
    """Return True if the named daemon should run. Unknown daemons return True (safe default)."""
    if name not in _REGISTRY:
        return True
    entry = _get_daemon_state(name)
    default = _REGISTRY[name].get("default_enabled", True)
    return bool(entry.get("enabled", default))


def set_daemon_enabled(name: str, enabled: bool) -> None:
    _require_known(name)
    _set_daemon_state(name, {"enabled": enabled})


def get_effective_cadence(name: str) -> int:
    """Return interval in minutes: override if set, else default."""
    entry = _get_daemon_state(name)
    override = entry.get("interval_minutes_override")
    if override is not None:
        return int(override)
    return int(_REGISTRY[name]["default_cadence_minutes"])


def record_daemon_tick(name: str, result: dict[str, Any]) -> None:
    """Record last_run_at and a summary of the tick result. Called by heartbeat_runtime."""
    if name not in _REGISTRY:
        return
    now = datetime.now(UTC).isoformat()
    summary = ", ".join(f"{k}: {v}" for k, v in list(result.items())[:3])
    _set_daemon_state(name, {"last_run_at": now, "last_result_summary": summary})


def _hours_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - dt).total_seconds() / 3600.0, 0.0)
    except ValueError:
        return None


def get_all_daemon_states() -> list[dict[str, Any]]:
    """Return status for all registered daemons."""
    file_state = _load_state()
    result = []
    for name, reg in _REGISTRY.items():
        entry = file_state.get(name, {})
        override = entry.get("interval_minutes_override")
        last_run = entry.get("last_run_at", "")
        _default_enabled = reg.get("default_enabled", True)
        result.append({
            "name": name,
            "enabled": bool(entry.get("enabled", _default_enabled)),
            "description": reg["description"],
            "default_cadence_minutes": reg["default_cadence_minutes"],
            "interval_minutes_override": override,
            "effective_cadence_minutes": int(override) if override is not None else reg["default_cadence_minutes"],
            "last_run_at": last_run,
            "hours_since_last_run": _hours_since(last_run),
            "last_result_summary": entry.get("last_result_summary", ""),
        })
    return result


def control_daemon(
    name: str,
    action: str,
    *,
    interval_minutes: int | None = None,
) -> dict[str, Any]:
    """Control a daemon. Actions: enable, disable, restart, set_interval.

    Returns {"ok": True, "name": name, "action": action} on success.
    Raises ValueError on unknown daemon, invalid action, or bad params.
    """
    _require_known(name)

    if action == "enable":
        set_daemon_enabled(name, True)
    elif action == "disable":
        set_daemon_enabled(name, False)
    elif action == "restart":
        _restart_daemon(name)
    elif action == "set_interval":
        if interval_minutes is None:
            raise ValueError("interval_minutes required for set_interval action")
        if interval_minutes < 1:
            raise ValueError(f"interval_minutes must be >= 1, got {interval_minutes}")
        _set_daemon_state(name, {"interval_minutes_override": interval_minutes})
    else:
        raise ValueError(f"unknown action '{action}'. Valid: enable, disable, restart, set_interval")

    return {"ok": True, "name": name, "action": action}


def _restart_daemon(name: str) -> None:
    """Clear the module-level state variable so the daemon fires on next heartbeat tick."""
    reg = _REGISTRY[name]
    module_path = reg["module"]
    reset_var = reg["reset_var"]
    reset_value = reg["reset_value"]

    # Module may not be imported yet — no-op then.
    module = sys.modules.get(module_path)
    if module is None:
        return

    if hasattr(module, reset_var):
        setattr(module, reset_var, reset_value)
