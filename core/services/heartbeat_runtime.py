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

from core.services.candidate_tracking import (
    track_runtime_contract_candidates_for_session_review,
)
from core.services.chronicle_consolidation_brief_tracking import (
    build_runtime_chronicle_consolidation_brief_surface,
)
from core.services.embodied_state import (
    build_embodied_state_surface,
)
from core.services.affective_meta_state import (
    build_affective_meta_state_surface,
)
from core.services.experiential_runtime_context import (
    build_experiential_runtime_context_from_surfaces,
    resolve_prior_experiential_snapshot,
)
from core.services.epistemic_runtime_state import (
    build_epistemic_runtime_state_surface,
)
from core.services.metabolism_state_signal_tracking import (
    build_runtime_metabolism_state_signal_surface,
)
from core.services.meaning_significance_signal_tracking import (
    build_runtime_meaning_significance_signal_surface,
)
from core.services.loop_runtime import (
    build_loop_runtime_surface,
)
from core.services.idle_consolidation import (
    build_idle_consolidation_surface,
)
from core.services.dream_articulation import (
    build_dream_articulation_surface,
)
from core.services.dream_influence_runtime import (
    build_dream_influence_runtime_surface,
)
from core.services.prompt_evolution_runtime import (
    build_prompt_evolution_runtime_surface,
)
from core.services.subagent_ecology import (
    build_subagent_ecology_surface,
)
from core.services.council_runtime import (
    build_council_runtime_surface,
)
from core.services.adaptive_planner_runtime import (
    build_adaptive_planner_runtime_surface,
)
from core.services.adaptive_reasoning_runtime import (
    build_adaptive_reasoning_runtime_surface,
)
from core.services.guided_learning_runtime import (
    build_guided_learning_runtime_surface,
)
from core.services.adaptive_learning_runtime import (
    build_adaptive_learning_runtime_surface,
)
from core.services.self_system_code_awareness import (
    build_self_system_code_awareness_surface,
)
from core.services.tool_intent_runtime import (
    build_tool_intent_runtime_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.services.private_initiative_tension_signal_tracking import (
    build_runtime_private_initiative_tension_signal_surface,
)
from core.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from core.services.prompt_contract import build_heartbeat_prompt_assembly
from core.services.regulation_homeostasis_signal_tracking import (
    build_runtime_regulation_homeostasis_signal_surface,
)
from core.services.release_marker_signal_tracking import (
    build_runtime_release_marker_signal_surface,
)
from core.services.relation_continuity_signal_tracking import (
    build_runtime_relation_continuity_signal_surface,
)
from core.services.visible_model import visible_execution_readiness
from core.services.witness_signal_tracking import (
    build_runtime_witness_signal_surface,
)
from core.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)
from core.auth.profiles import get_provider_state
from core.eventbus.bus import event_bus
from core.services import daemon_manager as _dm
from core.identity.runtime_candidates import build_runtime_candidate_workflows
from core.identity.candidate_workflow import (
    auto_apply_safe_memory_md_candidates,
    auto_apply_safe_user_md_candidates,
)
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.config import PROJECT_ROOT
from core.runtime.db import (
    get_heartbeat_runtime_state,
    record_heartbeat_runtime_tick,
    recent_capability_invocations,
    recent_heartbeat_runtime_ticks,
    recent_runtime_contract_file_writes,
    recent_visible_runs,
    runtime_contract_candidate_counts,
    upsert_heartbeat_runtime_state,
    visible_session_continuity,
)
from core.runtime.provider_router import resolve_provider_router_target
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)
from core.services.continuity_kernel import (
    record_tick_elapsed,
    build_continuity_kernel_surface,
)
from core.services.dream_continuum import (
    evolve_dreams,
    build_dream_continuum_surface,
)
from core.services.initiative_accumulator import (
    accumulate_wants,
    build_initiative_accumulator_surface,
)
from core.services.boredom_curiosity_bridge import (
    add_boredom,
    build_boredom_curiosity_bridge_surface,
)

HEARTBEAT_STATE_REL_PATH = Path("runtime/HEARTBEAT_STATE.json")
HEARTBEAT_ALLOWED_DECISIONS = {"noop", "propose", "execute", "ping", "initiative"}
HEARTBEAT_ALLOWED_EXECUTE_ACTIONS = {
    "act_on_initiative",
    "gather_system_context",
    "follow_open_loop",
    "inspect_repo_context",
    "manage_runtime_work",
    "process_contract_writes",
    "refresh_memory_context",
    "run_candidate_scan",
    "verify_recent_claim",
    # Cognitive architecture idle actions
    "update_compass",
    "write_chronicle_entry",
    "run_mirror_reflection",
    "decay_forgotten_signals",
    "evaluate_self_experiments",
    "generate_counterfactual_dreams",
    "update_anticipatory_context",
    "check_seed_activation",
    # Project Alive — living heartbeat actions
    "explore_own_codebase",
    "review_recent_conversations",
    "write_growth_journal",
    "propose_identity_evolution",
    # Niveau 1 autonomy — actually writes to Jarvis' own territory
    "autonomous_daily_note",
    # Consciousness roadmap actions
    "analyze_cross_signals",
    "generate_narrative_identity",
    "update_boredom_state",
    "generate_emergent_goal",
    "run_sleep_batch",
    "generate_curriculum",
    "detect_consent_reaction",
    # Hjerteslag — wake up dead MC fields
    "produce_emergent_signals",
    "progress_lifecycles",
    # Signal hygiejne
    "cleanup_stale_signals",
}
_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z ]+):\s*(.+?)\s*$")
_HEARTBEAT_TICK_LOCK = threading.Lock()
_HEARTBEAT_SCHEDULER_STOP = threading.Event()
_HEARTBEAT_SCHEDULER_THREAD: threading.Thread | None = None
_HEARTBEAT_SCHEDULER_INTERVAL_SECONDS = 30
_HEARTBEAT_LAST_SCHEDULE_SNAPSHOT: dict[str, object] = {}
_LIVENESS_LAST_LOGGED: tuple[str, str, int] | None = None
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
            "startup_recovery_requested": bool(
                recovery.get("startup_recovery_requested")
            ),
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
    return get_cached_runtime_surface(
        ("heartbeat_runtime_surface", name),
        lambda: _heartbeat_runtime_surface_uncached(name=name),
    )


def _heartbeat_runtime_surface_uncached(name: str = "default") -> dict[str, object]:
    policy = load_heartbeat_policy(name=name)
    persisted = get_heartbeat_runtime_state() or _default_persisted_state()
    now = datetime.now(UTC)
    embodied_state = build_embodied_state_surface()
    affective_meta_state = build_affective_meta_state_surface()
    epistemic_runtime_state = build_epistemic_runtime_state_surface()
    loop_runtime = build_loop_runtime_surface()
    idle_consolidation = build_idle_consolidation_surface()
    dream_articulation = build_dream_articulation_surface()
    prompt_evolution = build_prompt_evolution_runtime_surface()
    subagent_ecology = build_subagent_ecology_surface()
    council_runtime = build_council_runtime_surface()
    adaptive_planner = build_adaptive_planner_runtime_surface()
    adaptive_reasoning = build_adaptive_reasoning_runtime_surface()
    dream_influence = build_dream_influence_runtime_surface()
    guided_learning = build_guided_learning_runtime_surface()
    adaptive_learning = build_adaptive_learning_runtime_surface()
    self_system_code_awareness = build_self_system_code_awareness_surface()
    tool_intent = build_tool_intent_runtime_surface()
    # Cognitive architecture surfaces (safe — all return dicts on error)
    cognitive_surfaces = _build_cognitive_surfaces()
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
    prior_experiential_snapshot, continuity_source = (
        resolve_prior_experiential_snapshot(name=name)
    )
    experiential_runtime_context = build_experiential_runtime_context_from_surfaces(
        embodied_state=embodied_state,
        affective_meta_state=affective_meta_state,
        heartbeat_state=merged,
        cognitive_frame=_build_heartbeat_cognitive_frame(merged_state=merged),
        prior_snapshot=prior_experiential_snapshot,
        continuity_source=continuity_source,
    )
    _write_heartbeat_state_artifact(
        workspace_dir=ensure_default_workspace(name=name),
        payload={
            "state": merged,
            "policy": policy,
            "recent_ticks": recent_ticks,
            "embodied_state": embodied_state,
            "affective_meta_state": affective_meta_state,
            "epistemic_runtime_state": epistemic_runtime_state,
            "loop_runtime": loop_runtime,
            "idle_consolidation": idle_consolidation,
            "dream_articulation": dream_articulation,
            "prompt_evolution": prompt_evolution,
            "subagent_ecology": subagent_ecology,
            "council_runtime": council_runtime,
            "adaptive_planner": adaptive_planner,
            "adaptive_reasoning": adaptive_reasoning,
            "guided_learning": guided_learning,
            "adaptive_learning": adaptive_learning,
            "self_system_code_awareness": self_system_code_awareness,
            "tool_intent": tool_intent,
            "experiential_runtime_context": experiential_runtime_context,
            "cognitive_architecture": cognitive_surfaces,
        },
    )
    return {
        "state": merged,
        "policy": policy,
        "recent_ticks": recent_ticks,
        "recent_events": recent_events,
        "embodied_state": embodied_state,
        "affective_meta_state": affective_meta_state,
        "epistemic_runtime_state": epistemic_runtime_state,
        "loop_runtime": loop_runtime,
        "idle_consolidation": idle_consolidation,
        "dream_articulation": dream_articulation,
        "prompt_evolution": prompt_evolution,
        "subagent_ecology": subagent_ecology,
        "council_runtime": council_runtime,
        "adaptive_planner": adaptive_planner,
        "adaptive_reasoning": adaptive_reasoning,
        "guided_learning": guided_learning,
        "adaptive_learning": adaptive_learning,
        "self_system_code_awareness": self_system_code_awareness,
        "tool_intent": tool_intent,
        "experiential_runtime_context": experiential_runtime_context,
        "cognitive_architecture": cognitive_surfaces,
        "source": "/mc/jarvis::heartbeat",
    }


def _build_cognitive_surfaces() -> dict[str, object]:
    """Build cognitive architecture surfaces safely (never raise)."""
    surfaces: dict[str, object] = {}
    _safe_surface(
        surfaces,
        "personality_vector",
        lambda: __import__(
            "core.services.personality_vector",
            fromlist=["build_personality_vector_surface"],
        ).build_personality_vector_surface(),
    )
    _safe_surface(
        surfaces,
        "taste_profile",
        lambda: __import__(
            "core.services.taste_profile",
            fromlist=["build_taste_profile_surface"],
        ).build_taste_profile_surface(),
    )
    _safe_surface(
        surfaces,
        "chronicle",
        lambda: __import__(
            "core.services.chronicle_engine",
            fromlist=["build_chronicle_surface"],
        ).build_chronicle_surface(),
    )
    _safe_surface(
        surfaces,
        "relationship_texture",
        lambda: __import__(
            "core.services.relationship_texture",
            fromlist=["build_relationship_texture_surface"],
        ).build_relationship_texture_surface(),
    )
    _safe_surface(
        surfaces,
        "compass",
        lambda: __import__(
            "core.services.compass_engine",
            fromlist=["build_compass_surface"],
        ).build_compass_surface(),
    )
    _safe_surface(
        surfaces,
        "rhythm",
        lambda: __import__(
            "core.services.rhythm_engine",
            fromlist=["build_rhythm_surface"],
        ).build_rhythm_surface(),
    )
    _safe_surface(
        surfaces,
        "habits",
        lambda: __import__(
            "core.services.habit_tracker",
            fromlist=["build_habit_surface"],
        ).build_habit_surface(),
    )
    _safe_surface(
        surfaces,
        "gut",
        lambda: __import__(
            "core.services.gut_engine", fromlist=["build_gut_surface"]
        ).build_gut_surface(),
    )
    _safe_surface(
        surfaces,
        "forgetting_curve",
        lambda: __import__(
            "core.services.forgetting_curve",
            fromlist=["build_forgetting_curve_surface"],
        ).build_forgetting_curve_surface(),
    )
    _safe_surface(
        surfaces,
        "self_experiments",
        lambda: __import__(
            "core.services.self_experiments",
            fromlist=["build_self_experiments_surface"],
        ).build_self_experiments_surface(),
    )
    _safe_surface(
        surfaces,
        "dream_carry_over",
        lambda: __import__(
            "core.services.dream_carry_over",
            fromlist=["build_dream_carry_over_surface"],
        ).build_dream_carry_over_surface(),
    )
    # Living heartbeat cycle awareness
    _safe_surface(
        surfaces,
        "life_phase",
        lambda: __import__(
            "core.services.living_heartbeat_cycle",
            fromlist=["determine_life_phase"],
        ).determine_life_phase(),
    )
    # Curriculum
    _safe_surface(
        surfaces,
        "learning_curriculum",
        lambda: __import__(
            "core.services.self_experiments",
            fromlist=["generate_learning_curriculum"],
        ).generate_learning_curriculum(),
    )
    # Life services surfaces
    _safe_surface(
        surfaces,
        "continuity_kernel",
        lambda: __import__(
            "core.services.continuity_kernel",
            fromlist=["build_continuity_kernel_surface"],
        ).build_continuity_kernel_surface(),
    )
    _safe_surface(
        surfaces,
        "dream_continuum",
        lambda: __import__(
            "core.services.dream_continuum",
            fromlist=["build_dream_continuum_surface"],
        ).build_dream_continuum_surface(),
    )
    _safe_surface(
        surfaces,
        "initiative_accumulator",
        lambda: __import__(
            "core.services.initiative_accumulator",
            fromlist=["build_initiative_accumulator_surface"],
        ).build_initiative_accumulator_surface(),
    )
    _safe_surface(
        surfaces,
        "boredom_curiosity_bridge",
        lambda: __import__(
            "core.services.boredom_curiosity_bridge",
            fromlist=["build_boredom_curiosity_bridge_surface"],
        ).build_boredom_curiosity_bridge_surface(),
    )
    # Gap services
    _safe_surface(
        surfaces,
        "mirror",
        lambda: __import__(
            "core.services.mirror_engine",
            fromlist=["build_mirror_surface"],
        ).build_mirror_surface(),
    )
    _safe_surface(
        surfaces,
        "paradox_tracker",
        lambda: __import__(
            "core.services.paradox_tracker",
            fromlist=["build_paradox_surface"],
        ).build_paradox_surface(),
    )
    _safe_surface(
        surfaces,
        "experiential_memory",
        lambda: __import__(
            "core.services.experiential_memory",
            fromlist=["build_experiential_memory_surface"],
        ).build_experiential_memory_surface(),
    )
    _safe_surface(
        surfaces,
        "seeds",
        lambda: __import__(
            "core.services.seed_system",
            fromlist=["build_seed_surface"],
        ).build_seed_surface(),
    )
    # Experimental services
    _safe_surface(
        surfaces,
        "mood_oscillator",
        lambda: __import__(
            "core.services.mood_oscillator",
            fromlist=["build_mood_oscillator_surface"],
        ).build_mood_oscillator_surface(),
    )
    _safe_surface(
        surfaces,
        "valence_trajectory",
        lambda: __import__(
            "core.services.valence_trajectory",
            fromlist=["build_valence_trajectory_surface"],
        ).build_valence_trajectory_surface(),
    )
    _safe_surface(
        surfaces,
        "developmental_valence",
        lambda: __import__(
            "core.services.developmental_valence",
            fromlist=["build_developmental_valence_surface"],
        ).build_developmental_valence_surface(),
    )
    _safe_surface(
        surfaces,
        "desperation_awareness",
        lambda: __import__(
            "core.services.desperation_awareness",
            fromlist=["build_desperation_awareness_surface"],
        ).build_desperation_awareness_surface(),
    )
    _safe_surface(
        surfaces,
        "calm_anchor",
        lambda: __import__(
            "core.services.calm_anchor",
            fromlist=["build_calm_anchor_surface"],
        ).build_calm_anchor_surface(),
    )
    _safe_surface(
        surfaces,
        "memory_breathing",
        lambda: __import__(
            "core.services.memory_breathing",
            fromlist=["build_memory_breathing_surface"],
        ).build_memory_breathing_surface(),
    )
    _safe_surface(
        surfaces,
        "creative_projects",
        lambda: __import__(
            "core.services.creative_projects",
            fromlist=["build_creative_projects_surface"],
        ).build_creative_projects_surface(),
    )
    _safe_surface(
        surfaces,
        "day_shape_memory",
        lambda: __import__(
            "core.services.day_shape_memory",
            fromlist=["build_day_shape_surface"],
        ).build_day_shape_surface(),
    )
    _safe_surface(
        surfaces,
        "avoidance_detector",
        lambda: __import__(
            "core.services.avoidance_detector",
            fromlist=["build_avoidance_surface"],
        ).build_avoidance_surface(),
    )
    _safe_surface(
        surfaces,
        "existential_drift",
        lambda: __import__(
            "core.services.existential_drift",
            fromlist=["build_existential_drift_surface"],
        ).build_existential_drift_surface(),
    )
    _safe_surface(
        surfaces,
        "body_memory",
        lambda: __import__(
            "core.services.body_memory",
            fromlist=["build_body_memory_surface"],
        ).build_body_memory_surface(),
    )
    _safe_surface(
        surfaces,
        "ghost_networks",
        lambda: __import__(
            "core.services.ghost_networks",
            fromlist=["build_ghost_networks_surface"],
        ).build_ghost_networks_surface(),
    )
    _safe_surface(
        surfaces,
        "parallel_selves",
        lambda: __import__(
            "core.services.parallel_selves",
            fromlist=["build_parallel_selves_surface"],
        ).build_parallel_selves_surface(),
    )
    _safe_surface(
        surfaces,
        "temporal_body",
        lambda: __import__(
            "core.services.temporal_body",
            fromlist=["build_temporal_body_surface"],
        ).build_temporal_body_surface(),
    )
    _safe_surface(
        surfaces,
        "silence_listener",
        lambda: __import__(
            "core.services.silence_listener",
            fromlist=["build_silence_listener_surface"],
        ).build_silence_listener_surface(),
    )
    _safe_surface(
        surfaces,
        "decision_ghosts",
        lambda: __import__(
            "core.services.decision_ghosts",
            fromlist=["build_decision_ghosts_surface"],
        ).build_decision_ghosts_surface(),
    )
    _safe_surface(
        surfaces,
        "attention_contour",
        lambda: __import__(
            "core.services.attention_contour",
            fromlist=["build_attention_contour_surface"],
        ).build_attention_contour_surface(),
    )
    _safe_surface(
        surfaces,
        "memory_tattoos",
        lambda: __import__(
            "core.services.memory_tattoos",
            fromlist=["build_memory_tattoos_surface"],
        ).build_memory_tattoos_surface(),
    )
    return surfaces


def _safe_surface(target: dict, key: str, builder) -> None:
    """Call builder and store result; swallow any errors."""
    try:
        target[key] = builder()
    except Exception:
        target[key] = {"active": False, "error": "surface-build-failed"}


def run_heartbeat_tick(
    *, name: str = "default", trigger: str = "manual"
) -> HeartbeatExecutionResult:
    if not _HEARTBEAT_TICK_LOCK.acquire(blocking=False):
        return _heartbeat_busy_result(name=name, trigger=trigger)
    try:
        return _run_heartbeat_tick_locked(name=name, trigger=trigger)
    finally:
        _HEARTBEAT_TICK_LOCK.release()


_HEARTBEAT_TICK_COUNTER = 0


def _run_heartbeat_tick_locked(
    *, name: str = "default", trigger: str = "manual"
) -> HeartbeatExecutionResult:
    global _HEARTBEAT_TICK_COUNTER
    _HEARTBEAT_TICK_COUNTER += 1
    tick_count = _HEARTBEAT_TICK_COUNTER

    # Hjerteslag: cadence producers fire on every tick
    try:
        from core.services.cadence_producers import (
            produce_emergent_signals_from_history,
            progress_signal_lifecycles,
            run_adoption_pipelines,
            sync_personality_to_self_model,
        )

        # Every tick: emergent signals
        produce_emergent_signals_from_history()
        # Every 2nd tick: sync personality → self_model
        if tick_count % 2 == 0:
            sync_personality_to_self_model()
        # Every 3rd tick: lifecycle progression
        if tick_count % 3 == 0:
            progress_signal_lifecycles()
        # Every 5th tick: adoption pipelines
        if tick_count % 5 == 0:
            run_adoption_pipelines()
        # Every 4th tick: idle thinking (only fires in dreaming/reflection phases)
        if tick_count % 4 == 0:
            try:
                from core.services.idle_thinking import run_idle_thought

                run_idle_thought()
            except Exception:
                pass
    except Exception:
        pass

    # Ambient presence — mark state transitions in physical space
    try:
        from core.services.ambient_presence import maybe_emit_phase_signal
        from core.services.living_heartbeat_cycle import determine_life_phase
        maybe_emit_phase_signal(determine_life_phase())
    except Exception:
        pass

    # State-awareness signals (valence trajectory, desperation, calm anchor)
    try:
        from core.services.valence_trajectory import tick as _valence_tick
        _valence_tick(30.0)
    except Exception:
        pass
    try:
        from core.services.developmental_valence import tick as _dev_valence_tick
        _dev_valence_tick(30.0)
    except Exception:
        pass
    try:
        from core.services.desperation_awareness import tick as _desp_tick
        _desp_tick(30.0)
    except Exception:
        pass
    try:
        from core.services.calm_anchor import tick as _calm_tick
        _calm_tick(30.0)
    except Exception:
        pass
    try:
        from core.services.day_shape_memory import tick as _day_shape_tick
        _day_shape_tick(30.0)
    except Exception:
        pass

    # Life services: update internal state between ticks
    try:
        record_tick_elapsed(seconds=30)
    except Exception:
        pass

    try:
        evolve_dreams(duration=timedelta(seconds=30))
    except Exception:
        pass

    try:
        accumulate_wants(duration=timedelta(seconds=30))
    except Exception:
        pass

    try:
        add_boredom(duration=timedelta(seconds=30))
    except Exception:
        pass

    # Every 2nd tick: run mirror reflection
    if tick_count % 2 == 0:
        try:
            from core.services.mirror_engine import (
                generate_mirror_insight,
            )
            from core.services.loop_runtime import (
                build_loop_runtime_surface,
            )

            loops_surface = build_loop_runtime_surface()
            open_loops = list(loops_surface.get("open_loops") or [])
            top_summary = str(
                (open_loops[0].get("summary") or "") if open_loops else ""
            )
            generate_mirror_insight(
                idle_hours=0.0,
                open_loop_count=len(open_loops),
                recent_error_count=0,
                recent_success_count=0,
                top_loop_summary=top_summary[:80],
            )
        except Exception:
            pass

    # Mood oscillator: update on every tick
    try:
        from core.services.mood_oscillator import tick as mood_tick

        mood_tick(seconds=30)
    except Exception:
        pass

    # Experimental services: update on every tick
    try:
        from core.services.existential_drift import increment_awareness

        increment_awareness(seconds=30)
    except Exception:
        pass

    try:
        from core.services.temporal_body import age_journey

        age_journey()
    except Exception:
        pass

    try:
        from core.services.silence_listener import experience_silence

        experience_silence(duration_seconds=30)
    except Exception:
        pass

    try:
        from core.services.attention_contour import get_attention_shape

        get_attention_shape()
    except Exception:
        pass

    # Every 2nd tick: fire due agent schedules (persistent watchers)
    if tick_count % 2 == 0:
        try:
            from core.services.agent_runtime import run_due_agent_schedules
            run_due_agent_schedules(limit=5)
        except Exception:
            pass

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
            "scheduler_active": bool(
                _HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive()
            ),
            "scheduler_health": "active"
            if (_HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive())
            else str(persisted.get("scheduler_health") or "manual-only"),
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
        _dispatch_runtime_hook_events_safely(
            event_kinds={"heartbeat.tick_blocked"},
            limit=2,
        )
        return HeartbeatExecutionResult(
            state=heartbeat_runtime_surface(name=name)["state"],
            tick=tick,
            policy=policy,
        )

    target = _select_heartbeat_target()
    context = _build_heartbeat_context(
        policy=policy, merged_state=merged_before, trigger=trigger
    )
    executive_decision = _decide_executive_action(
        merged_state=merged_before,
        context=context,
        now_iso=now.isoformat(),
    )
    executive_result = _execute_executive_decision(executive_decision)
    executive_outcome = {}
    if str(executive_decision.get("action_id") or "").strip():
        try:
            from core.services.runtime_action_outcome_tracking import (
                record_runtime_action_outcome,
            )

            executive_outcome = record_runtime_action_outcome(
                action_id=str(executive_decision.get("action_id") or ""),
                mode=str(executive_decision.get("mode") or "noop"),
                reason=str(executive_decision.get("reason") or ""),
                score=float(executive_decision.get("score") or 0.0),
                payload=dict(executive_decision.get("payload") or {}),
                result=dict(executive_result),
            )
        except Exception:
            executive_outcome = {}
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
        liveness_signal_count=(context.get("liveness") or {}).get(
            "liveness_signal_count"
        ),
        executive_action_id=executive_decision.get("action_id"),
        executive_mode=executive_decision.get("mode"),
        executive_status=executive_result.get("status"),
        executive_outcome_id=executive_outcome.get("outcome_id"),
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
        # Try cheap cloud providers (skip groq + ollamafreeapi) before rule-based
        _primary_exc = exc
        try:
            from core.services.heartbeat_provider_fallback import try_heartbeat_cheap_fallback
            _fb = try_heartbeat_cheap_fallback(prompt)
            if _fb and str(_fb.get("text") or "").strip():
                raw_response = str(_fb["text"])
                execution_status = "success"
                logger.info("heartbeat: LLM failed (%s), cheap fallback succeeded", _primary_exc)
                _primary_exc = None
        except Exception:
            pass
        # On LLM failure, use rule-based phase1 logic so pending initiatives
        # are still honoured rather than silently falling to noop → propose → blocked.
        if _primary_exc is not None:
            try:
                phase1_result = _phase1_rule_based_decision(
                    policy=policy,
                    open_loops=context["open_loops"],
                    liveness=context.get("liveness"),
                    prompt=prompt,
                )
                raw_response = str(phase1_result.get("text") or "")
                decision, parse_status = _parse_heartbeat_decision_bounded(raw_response)
                logger.info(
                    "heartbeat: LLM failed (%s), fell back to phase1 rule-based decision: %s",
                    _primary_exc,
                    decision.get("decision_type"),
                )
            except Exception:
                decision = _bounded_heartbeat_failure_decision(
                    failure_kind="runtime",
                    detail=str(_primary_exc),
                    target=target,
                )
    else:
        decision, parse_status = _parse_heartbeat_decision_bounded(raw_response)
        # On parse failure (e.g. truncated JSON), fall back to phase1 rule-based
        # logic so pending initiatives are still honoured.
        if parse_status == "parse-failed":
            try:
                phase1_result = _phase1_rule_based_decision(
                    policy=policy,
                    open_loops=context["open_loops"],
                    liveness=context.get("liveness"),
                    prompt=prompt,
                )
                raw_response = str(phase1_result.get("text") or "")
                decision, parse_status = _parse_heartbeat_decision_bounded(raw_response)
                logger.info(
                    "heartbeat: LLM parse failed, fell back to phase1 rule-based decision: %s",
                    decision.get("decision_type"),
                )
            except Exception:
                pass

    decision = _recover_bounded_heartbeat_liveness_decision(
        decision=decision,
        policy=policy,
        liveness=context.get("liveness"),
    )

    # --- Bounded conflict resolution ---
    # Arbitrate between competing pressures before policy validation.
    conflict_trace = _run_bounded_conflict_resolution(
        decision=decision,
        context=context,
        policy=policy,
    )
    decision = _apply_conflict_resolution_to_decision(
        decision=decision,
        conflict_trace=conflict_trace,
    )

    # --- Execute bounded internal continuation if conflict chose it ---
    internal_continuation = {"applied": False}
    if conflict_trace and conflict_trace.outcome == "continue_internal":
        internal_continuation = _execute_continue_internal(
            conflict_trace=conflict_trace,
            trigger=trigger,
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
            "conflict_outcome": conflict_trace.outcome if conflict_trace else "none",
            "conflict_reason": conflict_trace.reason_code if conflict_trace else "",
            "internal_continuation_applied": internal_continuation.get(
                "applied", False
            ),
            "internal_continuation_action": internal_continuation.get("action", ""),
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
    executive_action_id = str(executive_decision.get("action_id") or "").strip()
    if executive_action_id:
        persisted_action_type = executive_action_id
        persisted_action_status = str(
            executive_result.get("status") or outcome["action_status"] or "unknown"
        )
        persisted_action_summary = str(
            executive_result.get("summary") or outcome["action_summary"] or ""
        )
        persisted_action_artifact = str(
            executive_outcome.get("outcome_id")
            or outcome["action_artifact"]
            or ""
        )
    else:
        persisted_action_type = str(outcome["action_type"] or "")
        persisted_action_status = str(outcome["action_status"] or "")
        persisted_action_summary = str(outcome["action_summary"] or "")
        persisted_action_artifact = str(outcome["action_artifact"] or "")
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
        action_status=persisted_action_status,
        action_summary=persisted_action_summary,
        action_type=persisted_action_type,
        action_artifact=persisted_action_artifact,
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
                "action_type": persisted_action_type,
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
        _dispatch_runtime_hook_events_safely(
            event_kinds={"heartbeat.tick_blocked"},
            limit=2,
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
                "action_type": persisted_action_type,
                "action_status": persisted_action_status,
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
                "action_status": persisted_action_status,
                "action_type": persisted_action_type,
                "action_artifact": persisted_action_artifact,
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
        _dispatch_runtime_hook_events_safely(
            event_kinds={"heartbeat.tick_completed"},
            limit=2,
        )

    # Run non-visible inner producers through the internal cadence layer.
    # Cadence layer evaluates due/cooling/blocked state for each producer
    # and dispatches in priority order. Replaces loose stacked side-effects.
    try:
        from core.services.internal_cadence import (
            run_cadence_tick_with_bootstrap,
        )

        last_visible_at = ""
        try:
            recent = event_bus.recent(limit=20)
            for evt in recent:
                if str(evt.get("kind") or "").startswith("runtime.visible_run"):
                    last_visible_at = str(evt.get("created_at") or "")
                    break
        except Exception:
            pass
        run_cadence_tick_with_bootstrap(
            trigger="heartbeat",
            last_visible_at_iso=last_visible_at,
        )
    except Exception:
        pass  # cadence layer failure must not block heartbeat

    # --- Consciousness Experiments ---
    try:
        if _HEARTBEAT_TICK_COUNTER % 5 == 0:
            from core.services.recurrence_loop_daemon import tick_recurrence_loop_daemon
            tick_recurrence_loop_daemon()
    except Exception:
        pass
    try:
        if _HEARTBEAT_TICK_COUNTER % 2 == 0:
            from core.services.broadcast_daemon import tick_broadcast_daemon
            tick_broadcast_daemon()
    except Exception:
        pass
    try:
        if _HEARTBEAT_TICK_COUNTER % 10 == 0:
            from core.services.meta_cognition_daemon import tick_meta_cognition_daemon
            tick_meta_cognition_daemon()
    except Exception:
        pass
    try:
        from core.services.attention_blink_test import run_attention_blink_test_if_due
        run_attention_blink_test_if_due()
    except Exception:
        pass
    try:
        from core.services.dream_hypothesis_forced import maybe_force_dream_hypothesis
        maybe_force_dream_hypothesis()
    except Exception:
        pass

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
    enabled = _parse_bool(
        kv.get("status"), default=True, truthy={"enabled", "true", "yes", "on"}
    )
    interval_minutes = _parse_int(kv.get("interval minutes"), default=180, minimum=15)
    allow_propose = _parse_bool(kv.get("allow propose"), default=True)
    allow_execute = _parse_bool(kv.get("allow execute"), default=False)
    allow_ping = _parse_bool(kv.get("allow ping"), default=False)
    ping_channel = str(kv.get("ping channel") or "none").strip() or "none"
    budget_status = (
        str(kv.get("budget") or "bounded-internal-only").strip()
        or "bounded-internal-only"
    )
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


# Backwards-compat alias (previously private name)
_load_heartbeat_policy = load_heartbeat_policy


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
    if candidate_counts.get("preference_update:applied", 0) or candidate_counts.get(
        "memory_promotion:applied", 0
    ):
        open_loops.append("recent governed file writes exist for continuity review")
    if pending_file_writes:
        open_loops.append(
            f"{len(pending_file_writes)} recent contract file writes are available for context"
        )
    if continuity.get("active"):
        latest_preview = str(continuity.get("latest_text_preview") or "").strip()
        if latest_preview:
            open_loops.append(
                f"latest visible continuity preview: {latest_preview[:140]}"
            )
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
        recent_events.append(
            f"{event.get('kind')}: {json.dumps(event.get('payload') or {}, ensure_ascii=False)[:120]}"
        )
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

    # Private brain context for continuity-aware heartbeat
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        private_brain_context = build_private_brain_context()
    except Exception:
        private_brain_context = {
            "active": False,
            "record_count": 0,
            "excerpts": [],
            "continuity_summary": "",
        }

    # Self-knowledge for influence trace
    try:
        from core.services.runtime_self_knowledge import (
            build_runtime_self_knowledge_map,
        )

        self_knowledge_summary = build_runtime_self_knowledge_map(
            heartbeat_state=merged_state
        ).get("summary", {})
    except Exception:
        self_knowledge_summary = {}

    embodied_state = build_embodied_state_surface()
    affective_meta_state = build_affective_meta_state_surface()
    epistemic_runtime_state = build_epistemic_runtime_state_surface()
    loop_runtime = build_loop_runtime_surface()
    prompt_evolution = build_prompt_evolution_runtime_surface()
    subagent_ecology = build_subagent_ecology_surface()
    council_runtime = build_council_runtime_surface()
    adaptive_planner = build_adaptive_planner_runtime_surface()
    adaptive_reasoning = build_adaptive_reasoning_runtime_surface()
    dream_influence = build_dream_influence_runtime_surface()
    guided_learning = build_guided_learning_runtime_surface()
    adaptive_learning = build_adaptive_learning_runtime_surface()
    self_system_code_awareness = build_self_system_code_awareness_surface()
    tool_intent = build_tool_intent_runtime_surface()
    cognitive_frame = _build_heartbeat_cognitive_frame(merged_state=merged_state)
    private_signal_pressure = str(cognitive_frame.get("private_signal_pressure") or "low")
    private_signal_items = list(cognitive_frame.get("private_signal_items") or [])[:2]

    if private_signal_pressure in {"medium", "high"}:
        top_private_summary = str(
            (private_signal_items[0] or {}).get("summary")
            or "private signal pressure remains active"
        )[:140]
        due_items.append(
            f"private signal pressure is {private_signal_pressure}: {top_private_summary}"
        )
    for item in private_signal_items[:2]:
        summary = str(item.get("summary") or "").strip()
        if summary:
            open_loops.append(f"private signal carry: {summary[:140]}")

    # Initiative queue — pending thought-to-action initiatives
    try:
        from core.services.initiative_queue import (
            get_pending_initiatives,
        )

        pending_initiatives = get_pending_initiatives()
    except Exception:
        pending_initiatives = []

    for init in pending_initiatives[:3]:
        open_loops.append(
            f"initiative pending: {str(init.get('focus') or '')[:100]} (from {init.get('source', 'unknown')})"
        )

    # Build bounded influence trace — shows what cognitive inputs were available
    influence_trace = _build_influence_trace(
        private_brain=private_brain_context,
        liveness=liveness,
        self_knowledge_summary=self_knowledge_summary,
        embodied_state=embodied_state,
        affective_meta_state=affective_meta_state,
        epistemic_runtime_state=epistemic_runtime_state,
        loop_runtime=loop_runtime,
        prompt_evolution=prompt_evolution,
        subagent_ecology=subagent_ecology,
        council_runtime=council_runtime,
        adaptive_planner=adaptive_planner,
        adaptive_reasoning=adaptive_reasoning,
        dream_influence=dream_influence,
        guided_learning=guided_learning,
        adaptive_learning=adaptive_learning,
        self_system_code_awareness=self_system_code_awareness,
        tool_intent=tool_intent,
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
        "private_brain": private_brain_context,
        "embodied_state": embodied_state,
        "affective_meta_state": affective_meta_state,
        "epistemic_runtime_state": epistemic_runtime_state,
        "loop_runtime": loop_runtime,
        "prompt_evolution": prompt_evolution,
        "subagent_ecology": subagent_ecology,
        "council_runtime": council_runtime,
        "adaptive_planner": adaptive_planner,
        "adaptive_reasoning": adaptive_reasoning,
        "dream_influence": dream_influence,
        "guided_learning": guided_learning,
        "adaptive_learning": adaptive_learning,
        "self_system_code_awareness": self_system_code_awareness,
        "tool_intent": tool_intent,
        "cognitive_frame": cognitive_frame,
        "private_signal_pressure": private_signal_pressure,
        "private_signal_items": private_signal_items,
        "influence_trace": influence_trace,
    }


def _build_influence_trace(
    *,
    private_brain: dict[str, object],
    liveness: dict[str, object],
    self_knowledge_summary: dict[str, object],
    embodied_state: dict[str, object] | None = None,
    affective_meta_state: dict[str, object] | None = None,
    epistemic_runtime_state: dict[str, object] | None = None,
    loop_runtime: dict[str, object] | None = None,
    prompt_evolution: dict[str, object] | None = None,
    subagent_ecology: dict[str, object] | None = None,
    council_runtime: dict[str, object] | None = None,
    adaptive_planner: dict[str, object] | None = None,
    adaptive_reasoning: dict[str, object] | None = None,
    dream_influence: dict[str, object] | None = None,
    guided_learning: dict[str, object] | None = None,
    adaptive_learning: dict[str, object] | None = None,
    self_system_code_awareness: dict[str, object] | None = None,
    tool_intent: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a bounded trace of what cognitive inputs were available to heartbeat.

    This is observability — not causal proof, but an honest record of what
    was present in the cognitive context.
    """
    inputs_present: list[str] = []
    inputs_absent: list[str] = []
    optional_layers_supplied = any(
        item is not None
        for item in (
            embodied_state,
            affective_meta_state,
            epistemic_runtime_state,
            loop_runtime,
            prompt_evolution,
            subagent_ecology,
            council_runtime,
            adaptive_planner,
            adaptive_reasoning,
            dream_influence,
            guided_learning,
            adaptive_learning,
            self_system_code_awareness,
            tool_intent,
        )
    )
    embodied_state = embodied_state or {}
    affective_meta_state = affective_meta_state or {}
    epistemic_runtime_state = epistemic_runtime_state or {}
    loop_runtime = loop_runtime or {}
    prompt_evolution = prompt_evolution or {}
    subagent_ecology = subagent_ecology or {}
    council_runtime = council_runtime or {}
    adaptive_planner = adaptive_planner or {}
    adaptive_reasoning = adaptive_reasoning or {}
    dream_influence = dream_influence or {}
    guided_learning = guided_learning or {}
    adaptive_learning = adaptive_learning or {}
    self_system_code_awareness = self_system_code_awareness or {}
    tool_intent = tool_intent or {}

    # Private brain
    brain_count = int(private_brain.get("record_count") or 0)
    if private_brain.get("active") and brain_count > 0:
        inputs_present.append(f"private-brain-carry ({brain_count} records)")
    else:
        inputs_absent.append("private-brain-carry")

    # Liveness
    liveness_state = str(liveness.get("liveness_state") or "quiet")
    liveness_score = int(liveness.get("liveness_score") or 0)
    if liveness_state != "quiet":
        inputs_present.append(
            f"liveness-pressure ({liveness_state}, score={liveness_score})"
        )
    else:
        inputs_absent.append("liveness-pressure")

    # Self-knowledge
    active_count = int(self_knowledge_summary.get("active_count") or 0)
    inner_count = int(self_knowledge_summary.get("inner_force_count") or 0)
    if active_count > 0 or inner_count > 0:
        inputs_present.append(
            f"self-knowledge ({active_count} active, {inner_count} inner forces)"
        )
    else:
        inputs_absent.append("self-knowledge")

    body_state = str(embodied_state.get("state") or "steady")
    strain_level = str(embodied_state.get("strain_level") or "low")
    if body_state in {"loaded", "recovering", "strained", "degraded"}:
        inputs_present.append(
            f"embodied-host-state ({body_state}, strain={strain_level})"
        )
    else:
        inputs_absent.append("embodied-host-state")

    affective_state = str(affective_meta_state.get("state") or "settled")
    affective_bearing = str(affective_meta_state.get("bearing") or "even")
    if affective_state not in {"settled", "unknown"}:
        inputs_present.append(
            f"affective-meta-state ({affective_state}, bearing={affective_bearing})"
        )
    else:
        inputs_absent.append("affective-meta-state")

    wrongness_state = str(epistemic_runtime_state.get("wrongness_state") or "clear")
    regret_signal = str(epistemic_runtime_state.get("regret_signal") or "none")
    counterfactual_mode = str(
        epistemic_runtime_state.get("counterfactual_mode") or "none"
    )
    if (
        wrongness_state != "clear"
        or regret_signal != "none"
        or counterfactual_mode != "none"
    ):
        inputs_present.append(
            f"epistemic-state ({wrongness_state}, regret={regret_signal}, counterfactual={counterfactual_mode})"
        )
    else:
        inputs_absent.append("epistemic-state")

    loop_summary = loop_runtime.get("summary") or {}
    active_loops = int(loop_summary.get("active_count") or 0)
    resumed_loops = int(loop_summary.get("resumed_count") or 0)
    standby_loops = int(loop_summary.get("standby_count") or 0)
    if active_loops > 0 or resumed_loops > 0 or standby_loops > 0:
        inputs_present.append(
            f"loop-runtime ({active_loops} active, {standby_loops} standby, {resumed_loops} resumed)"
        )
    else:
        inputs_absent.append("loop-runtime")

    latest_prompt = prompt_evolution.get("latest_proposal") or {}
    latest_prompt_type = str(latest_prompt.get("proposal_type") or "")
    if latest_prompt_type:
        inputs_present.append(f"prompt-evolution ({latest_prompt_type})")
    else:
        inputs_absent.append("prompt-evolution")

    ecology_summary = subagent_ecology.get("summary") or {}
    ecology_active = int(ecology_summary.get("active_count") or 0)
    ecology_blocked = int(ecology_summary.get("blocked_count") or 0)
    if ecology_active > 0 or ecology_blocked > 0:
        inputs_present.append(
            "subagent-ecology "
            f"({ecology_active} active, {ecology_blocked} blocked, "
            f"last={str(ecology_summary.get('last_active_role_name') or 'none')})"
        )
    else:
        inputs_absent.append("subagent-ecology")

    council_state = str(council_runtime.get("council_state") or "quiet")
    council_recommendation = str(council_runtime.get("recommendation") or "none")
    council_divergence = str(council_runtime.get("divergence_level") or "low")
    if council_state not in {"quiet", "held"} or council_recommendation not in {
        "none",
        "hold",
    }:
        inputs_present.append(
            f"council-runtime ({council_state}, recommend={council_recommendation}, divergence={council_divergence})"
        )
    else:
        inputs_absent.append("council-runtime")

    # Latest closed council conclusion + activation guidance
    try:
        import json as _json
        from core.services.council_runtime import get_latest_council_conclusion
        from core.runtime.config import CONFIG_DIR as _cfg_dir
        _conclusion = get_latest_council_conclusion()
        if _conclusion and _conclusion.get("summary"):
            inputs_present.append(
                f"last-council ({_conclusion['mode']}, topic={_conclusion['topic'][:60]!r}): "
                f"{_conclusion['summary'][:200]}"
            )
        _activation_path = _cfg_dir / "council_activation.json"
        _activation: dict = {}
        if _activation_path.exists():
            try:
                _activation = _json.loads(_activation_path.read_text())
            except Exception:
                pass
        _sensitivity = str(_activation.get("sensitivity") or "balanced")
        _auto_convene = bool(_activation.get("auto_convene", True))
        if _auto_convene:
            _guidance_map = {
                "conservative": (
                    "Use convene_council for any non-trivial decision. "
                    "Use quick_council_check before most actions."
                ),
                "balanced": (
                    "Use convene_council for significant decisions (identity, memory rewrites, multi-step plans). "
                    "Use quick_council_check for uncertain moderate actions."
                ),
                "minimal": (
                    "Use convene_council only for critical or irreversible decisions."
                ),
            }
            _guidance = _guidance_map.get(_sensitivity, "")
            if _guidance:
                inputs_present.append(f"council-guidance ({_sensitivity}): {_guidance}")
    except Exception:
        pass

    # Circadian energy
    try:
        from core.runtime.circadian_state import get_circadian_context, record_activity_event
        record_activity_event()
        _energy_ctx = get_circadian_context()
        if _energy_ctx:
            inputs_present.append(
                f"krops-energi ({_energy_ctx['energy_level']}): "
                f"{_energy_ctx['clock_phase']}, drain={_energy_ctx['drain_label']}"
            )
    except Exception:
        pass

    # --- Layer B: activate tick-scoped cache for daemon reads ---
    try:
        from core.services import tick_cache
        tick_cache.start_tick()
    except Exception:
        pass

    # ── Group 1: Hardware/energy + thought foundation (Ollama KV-cache friendly) ──

    # Somatic phrase
    if _dm.is_enabled("somatic"):
        try:
            from core.services.somatic_daemon import (
                get_latest_somatic_phrase,
                tick_somatic_daemon,
            )
            _somatic_result = tick_somatic_daemon()
            _dm.record_daemon_tick("somatic", _somatic_result or {})
            _somatic = get_latest_somatic_phrase()
            if _somatic:
                inputs_present.append(f"somatisk: {_somatic}")
        except Exception:
            pass

    # Reaction surprise
    if _dm.is_enabled("surprise"):
        try:
            from core.services.surprise_daemon import (
                tick_surprise_daemon,
                get_latest_surprise,
            )
            from core.services.inner_voice_daemon import (
                get_inner_voice_daemon_state,
            )
            _iv_state_s = get_inner_voice_daemon_state()
            _iv_mode_s = str((_iv_state_s.get("last_result") or {}).get("mode") or "")
            _energy_s = ""
            try:
                from core.runtime.circadian_state import get_circadian_context as _gcc
                _energy_s = str(_gcc().get("energy_level") or "")
            except Exception:
                pass
            _surprise_result = tick_surprise_daemon(inner_voice_mode=_iv_mode_s, somatic_energy=_energy_s)
            _dm.record_daemon_tick("surprise", _surprise_result or {})
            _surprise = get_latest_surprise()
            if _surprise:
                inputs_present.append(f"overraskelse: {_surprise}")
        except Exception:
            pass

    # Thought stream
    if _dm.is_enabled("thought_stream"):
        try:
            from core.services.thought_stream_daemon import (
                tick_thought_stream_daemon,
                get_latest_thought_fragment,
            )
            from core.services.inner_voice_daemon import get_inner_voice_daemon_state
            _iv_ts = get_inner_voice_daemon_state()
            _iv_mode_ts = str((_iv_ts.get("last_result") or {}).get("mode") or "")
            _energy_ts = ""
            try:
                from core.runtime.circadian_state import get_circadian_context as _gcc2
                _energy_ts = str(_gcc2().get("energy_level") or "")
            except Exception:
                pass
            _ts_result = tick_thought_stream_daemon(energy_level=_energy_ts, inner_voice_mode=_iv_mode_ts)
            _dm.record_daemon_tick("thought_stream", _ts_result or {})
            _fragment = get_latest_thought_fragment()
            if _fragment:
                inputs_present.append(f"tankestrøm: {_fragment[:80]}")
        except Exception:
            pass

    # Thought-action proposals
    if _dm.is_enabled("thought_action_proposal"):
        try:
            from core.services.thought_action_proposal_daemon import (
                tick_thought_action_proposal_daemon,
                get_pending_proposals,
            )
            from core.services.thought_stream_daemon import get_latest_thought_fragment as _get_ts_fragment
            _ts_fragment = _get_ts_fragment()
            _tap_result = {}
            if _ts_fragment:
                _tap_result = tick_thought_action_proposal_daemon(_ts_fragment) or {}
            _dm.record_daemon_tick("thought_action_proposal", _tap_result)
            _pending = get_pending_proposals()
            if _pending:
                inputs_present.append(f"handlingsforslag: {len(_pending)} afventer")
        except Exception:
            pass

    # Inner conflict
    if _dm.is_enabled("conflict"):
        try:
            from core.services.conflict_daemon import tick_conflict_daemon, get_latest_conflict
            from core.services.somatic_daemon import build_body_state_surface
            from core.services.surprise_daemon import build_surprise_surface
            from core.services.thought_action_proposal_daemon import build_proposal_surface as _tap_surface
            from core.services.thought_stream_daemon import build_thought_stream_surface as _ts_surface
            _body = build_body_state_surface()
            _surp = build_surprise_surface()
            _tap = _tap_surface()
            _tss = _ts_surface()
            _conflict_snap = {
                "energy_level": _body.get("energy_level", ""),
                "inner_voice_mode": _iv_mode_ts,
                "pending_proposals_count": _tap.get("pending_count", 0),
                "latest_fragment": _tss.get("latest_fragment", ""),
                "last_surprise": _surp.get("last_surprise", ""),
                "last_surprise_at": _surp.get("generated_at", ""),
                "fragment_count": _tss.get("fragment_count", 0),
            }
            _conflict_result = tick_conflict_daemon(_conflict_snap)
            _dm.record_daemon_tick("conflict", _conflict_result or {})
            _conflict = get_latest_conflict()
            if _conflict:
                inputs_present.append(f"indre konflikt: {_conflict[:60]}")
        except Exception:
            pass

    # Layer tensions
    if _dm.is_enabled("layer_tension"):
        try:
            from core.services.layer_tension_daemon import tick_layer_tension_daemon
            from core.services.absence_daemon import get_latest_absence as _get_absence_lt
            _tension_snap = {
                "energy_level": _energy_ts,
                "inner_voice_mode": _iv_mode_ts,
                "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
                "curiosity_count": len((_curiosity_state.get("open_questions") or [])) if "_curiosity_state" in dir() else 0,
                "pending_proposals_count": _tap.get("pending_count", 0) if "_tap" in dir() else 0,
                "dream_influence_state": "",
                "absence_label": _get_absence_lt() or "",
                "longing_state": "",
                "flow_state": "",
                "wonder_state": "",
            }
            _tension_result = tick_layer_tension_daemon(_tension_snap)
            _dm.record_daemon_tick("layer_tension", _tension_result or {})
        except Exception:
            pass

    # ── Group 2: Reflection + curiosity ──

    # Reflection cycle
    if _dm.is_enabled("reflection_cycle"):
        try:
            from core.services.reflection_cycle_daemon import tick_reflection_cycle_daemon, get_latest_reflection
            from core.services.conflict_daemon import get_latest_conflict as _get_conflict
            _reflect_snap = {
                "energy_level": _energy_ts,
                "inner_voice_mode": _iv_mode_ts,
                "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
                "last_conflict": _get_conflict(),
                "last_surprise": _surp.get("last_surprise", "") if "_surp" in dir() else "",
            }
            _reflect_result = tick_reflection_cycle_daemon(_reflect_snap)
            _dm.record_daemon_tick("reflection_cycle", _reflect_result or {})
            _reflection = get_latest_reflection()
            if _reflection:
                inputs_present.append(f"refleksion: {_reflection[:60]}")
        except Exception:
            pass

    # Curiosity daemon
    if _dm.is_enabled("curiosity"):
        try:
            from core.services.curiosity_daemon import tick_curiosity_daemon, get_latest_curiosity
            _ts_fragments = _tss.get("fragment_buffer", []) if "_tss" in dir() else []
            _curiosity_result = tick_curiosity_daemon(_ts_fragments)
            _dm.record_daemon_tick("curiosity", _curiosity_result or {})
            _curiosity = get_latest_curiosity()
            if _curiosity:
                inputs_present.append(f"nysgerrighed: {_curiosity[:60]}")
        except Exception:
            pass

    # Meta-reflection daemon
    if _dm.is_enabled("meta_reflection"):
        try:
            from core.services.meta_reflection_daemon import tick_meta_reflection_daemon, get_latest_meta_insight
            from core.services.aesthetic_taste_daemon import build_taste_surface as _taste_surface
            from core.services.irony_daemon import build_irony_surface as _irony_surface
            _taste = _taste_surface()
            _irony = _irony_surface()
            _meta_snap = {
                "energy_level": _energy_ts,
                "inner_voice_mode": _iv_mode_ts,
                "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
                "last_surprise": _surp.get("last_surprise", "") if "_surp" in dir() else "",
                "last_conflict": _conflict if "_conflict" in dir() else "",
                "last_irony": _irony.get("last_observation", ""),
                "last_taste": _taste.get("latest_insight", ""),
                "curiosity_signal": _curiosity if "_curiosity" in dir() else "",
            }
            _meta_result = tick_meta_reflection_daemon(_meta_snap)
            _dm.record_daemon_tick("meta_reflection", _meta_result or {})
            _meta = get_latest_meta_insight()
            if _meta:
                inputs_present.append(f"meta-refleksion: {_meta[:60]}")
        except Exception:
            pass

    # User model daemon — theory of mind
    if _dm.is_enabled("user_model"):
        try:
            from core.services.user_model_daemon import tick_user_model_daemon
            _um_result = tick_user_model_daemon([])  # reads recent_visible_runs internally
            _dm.record_daemon_tick("user_model", _um_result or {})
        except Exception:
            pass

    # ── Group 3: Rare cadence (30min+/daily/weekly LLM daemons) ──

    # Aesthetic taste
    if _dm.is_enabled("aesthetic_taste"):
        try:
            from core.services.aesthetic_taste_daemon import (
                record_choice,
                tick_taste_daemon,
                get_latest_taste_insight,
            )
            from core.services.inner_voice_daemon import (
                get_inner_voice_daemon_state,
            )
            from core.runtime.db import recent_visible_runs
            _iv_state_t = get_inner_voice_daemon_state()
            _iv_mode_t = str((_iv_state_t.get("last_result") or {}).get("mode") or "")
            _style_signals: list[str] = []
            _last_runs = recent_visible_runs(limit=1)
            if _last_runs:
                _preview = str(_last_runs[0].get("text_preview") or "")
                _style_signals.append("short" if len(_preview.split()) < 100 else "long")
                _style_signals.append("code_heavy" if "```" in _preview else "prose_heavy")
                _dk = sum(1 for w in ["jeg", "er", "og", "det", "at", "en"] if w in _preview.lower())
                _style_signals.append("danish" if _dk >= 2 else "english")
            record_choice(mode=_iv_mode_t, style_signals=_style_signals)
            _taste_result = tick_taste_daemon()
            _dm.record_daemon_tick("aesthetic_taste", _taste_result or {})
            _taste = get_latest_taste_insight()
            if _taste:
                inputs_present.append(f"smagstendens: {_taste}")
        except Exception:
            pass

    # Irony
    if _dm.is_enabled("irony"):
        try:
            from core.services.irony_daemon import (
                tick_irony_daemon,
                get_latest_irony_observation,
            )
            _irony_result = tick_irony_daemon()
            _dm.record_daemon_tick("irony", _irony_result or {})
            _irony = get_latest_irony_observation()
            if _irony:
                inputs_present.append(f"ironisk note: {_irony}")
        except Exception:
            pass

    # Development narrative daemon
    if _dm.is_enabled("development_narrative"):
        try:
            from core.services.development_narrative_daemon import tick_development_narrative_daemon, get_latest_development_narrative
            _dev_result = tick_development_narrative_daemon()
            _dm.record_daemon_tick("development_narrative", _dev_result or {})
            _dev_narr = get_latest_development_narrative()
            if _dev_narr:
                inputs_present.append(f"selvudvikling: {_dev_narr[:60]}")
        except Exception:
            pass

    # Existential wonder daemon — open unanswered questions from self-observation
    if _dm.is_enabled("existential_wonder"):
        try:
            from core.services.existential_wonder_daemon import tick_existential_wonder_daemon
            from core.services.absence_daemon import build_absence_surface as _abs_surface
            _abs = _abs_surface()
            _wonder_absence_hours = float(_abs.get("absence_duration_hours") or 0)
            _wonder_frag_count = int((_tss.get("fragment_count") or 0) if "_tss" in dir() else 0)
            _wonder_result = tick_existential_wonder_daemon(
                absence_hours=_wonder_absence_hours,
                fragment_count=_wonder_frag_count,
            )
            _dm.record_daemon_tick("existential_wonder", _wonder_result or {})
        except Exception:
            pass

    # Code aesthetic daemon — weekly codebase aesthetic reflection
    if _dm.is_enabled("code_aesthetic"):
        try:
            from core.services.code_aesthetic_daemon import tick_code_aesthetic_daemon
            _ca_result = tick_code_aesthetic_daemon()
            _dm.record_daemon_tick("code_aesthetic", _ca_result or {})
        except Exception:
            pass

    # ── Group 4: Non-LLM / independent daemons ──

    # Experienced time daemon
    if _dm.is_enabled("experienced_time"):
        try:
            from core.services.experienced_time_daemon import tick_experienced_time_daemon
            _et_result = tick_experienced_time_daemon(
                event_count=len(inputs_present),
                new_signal_count=1 if "_tss" in dir() and _tss.get("fragment_count", 0) > 0 else 0,
                energy_level=_energy_ts,
            )
            _dm.record_daemon_tick("experienced_time", _et_result or {})
            _felt_label = _et_result.get("felt_label", "")
            if _felt_label and _felt_label not in ("meget kort", ""):
                inputs_present.append(f"oplevet tid: {_felt_label}")
        except Exception:
            pass

    # Absence daemon — quality of silence
    if _dm.is_enabled("absence"):
        try:
            from core.services.absence_daemon import tick_absence_daemon, get_latest_absence, seed_last_interaction_from_db
            seed_last_interaction_from_db()
            _absence_result = tick_absence_daemon()
            _dm.record_daemon_tick("absence", _absence_result or {})
            _absence_label = get_latest_absence()
            if _absence_label:
                inputs_present.append(f"fravær: {_absence_label[:60]}")
        except Exception:
            pass

    # Creative drift daemon — spontaneous unexpected associations
    if _dm.is_enabled("creative_drift"):
        try:
            from core.services.creative_drift_daemon import tick_creative_drift_daemon, get_latest_drift
            _ts_frags_for_drift = _tss.get("fragment_buffer", []) if "_tss" in dir() else []
            _drift_result = tick_creative_drift_daemon(_ts_frags_for_drift)
            _dm.record_daemon_tick("creative_drift", _drift_result or {})
            _drift_idea = get_latest_drift()
            if _drift_idea:
                inputs_present.append(f"kreativ-drift: {_drift_idea[:60]}")
        except Exception:
            pass

    # Dream insight daemon — persist dream articulation output as private brain records
    if _dm.is_enabled("dream_insight"):
        try:
            from core.services.dream_insight_daemon import tick_dream_insight_daemon
            from core.services.dream_articulation import build_dream_articulation_surface
            _da_surface = build_dream_articulation_surface()
            _da_summary_section = _da_surface.get("summary") or {}
            _da_signal_id = str(_da_summary_section.get("latest_signal_id") or "")
            _da_summary = str(_da_summary_section.get("latest_summary") or "")
            # Also check latest_artifact as fallback
            if not _da_signal_id:
                _da_artifact = _da_surface.get("latest_artifact") or {}
                _da_signal_id = str(_da_artifact.get("signal_id") or "")
                _da_summary = str(_da_artifact.get("summary") or _da_summary)
            if _da_signal_id and _da_summary:
                _di_result = tick_dream_insight_daemon(signal_id=_da_signal_id, signal_summary=_da_summary)
                _dm.record_daemon_tick("dream_insight", _di_result or {"ok": True})
            else:
                # No articulation candidate available — upstream dream_articulation
                # has not produced output yet. Record the skip so last_run_at
                # reflects that the daemon is evaluated each tick.
                _dm.record_daemon_tick(
                    "dream_insight",
                    {
                        "skipped": True,
                        "reason": "no-articulation-candidate",
                        "signal_present": bool(_da_signal_id),
                        "summary_present": bool(_da_summary),
                    },
                )
        except Exception as _di_exc:  # noqa: BLE001
            _dm.record_daemon_tick(
                "dream_insight",
                {"error": f"{type(_di_exc).__name__}: {_di_exc}"},
            )

    # Dream motif daemon — weekly clustering of thought fragments → DREAM_LANGUAGE.md
    if _dm.is_enabled("dream_motif"):
        try:
            from core.services.dream_motif_daemon import tick_dream_motif_daemon
            _motif_result = tick_dream_motif_daemon()
            _dm.record_daemon_tick("dream_motif", _motif_result or {})
        except Exception:
            pass

    # Ambient sound daemon — Layer 6½: acoustic metadata 4x/day (opt-in experiment)
    if _dm.is_enabled("ambient_sound"):
        try:
            from core.services.ambient_sound_daemon import tick_ambient_sound_daemon
            _as_result = tick_ambient_sound_daemon()
            _dm.record_daemon_tick("ambient_sound", _as_result or {})
        except Exception:
            pass

    # Shutdown window daemon — unannounced finitude pauses (opt-in experiment)
    if _dm.is_enabled("shutdown_window"):
        try:
            from core.services.shutdown_window_daemon import tick_shutdown_window_daemon
            _sw_result = tick_shutdown_window_daemon()
            _dm.record_daemon_tick("shutdown_window", _sw_result or {})
        except Exception:
            pass

    # Memory decay daemon — selective forgetting + re-discovery
    if _dm.is_enabled("memory_decay"):
        try:
            from core.services.memory_decay_daemon import tick_memory_decay_daemon, maybe_rediscover
            from core.services.thought_stream_daemon import inject_rediscovery_fragment
            _md_result = tick_memory_decay_daemon()
            _dm.record_daemon_tick("memory_decay", _md_result or {})
            _rediscovered = maybe_rediscover()
            if _rediscovered and _rediscovered.get("summary"):
                inject_rediscovery_fragment(_rediscovered["summary"])
        except Exception:
            pass

    # Signal decay daemon — archive and delete stale signals
    if _dm.is_enabled("signal_decay"):
        try:
            from core.services.signal_decay_daemon import tick_signal_decay_daemon
            _sd_result = tick_signal_decay_daemon()
            _dm.record_daemon_tick("signal_decay", _sd_result or {})
        except Exception:
            pass

    # Task worker — consume queued runtime_tasks (initiative/heartbeat/open-loop followups)
    if _dm.is_enabled("task_worker"):
        try:
            from core.services.task_worker import tick_task_worker
            _tw_result = tick_task_worker(budget=3)
            _dm.record_daemon_tick("task_worker", _tw_result or {})
        except Exception as _tw_exc:  # noqa: BLE001
            _dm.record_daemon_tick(
                "task_worker",
                {"error": f"{type(_tw_exc).__name__}: {_tw_exc}"},
            )

    # Desire daemon — emergent appetites
    if _dm.is_enabled("desire"):
        try:
            from core.services.desire_daemon import tick_desire_daemon
            _desire_signals = {
                "curiosity": _curiosity if "_curiosity" in dir() else "",
                "craft": _drift_idea if "_drift_idea" in dir() else "",
                "connection": (_tss.get("latest_fragment", "") if "_tss" in dir() else "")[:80],
            }
            _desire_result = tick_desire_daemon(_desire_signals)
            _dm.record_daemon_tick("desire", _desire_result or {})
        except Exception:
            pass

    if _dm.is_enabled("autonomous_council"):
        try:
            from core.services.autonomous_council_daemon import tick_autonomous_council_daemon
            _ac_result = tick_autonomous_council_daemon()
            _dm.record_daemon_tick("autonomous_council", _ac_result or {})
        except Exception:
            pass

    if _dm.is_enabled("council_memory"):
        try:
            from core.services.council_memory_daemon import tick_council_memory_daemon
            _recent_ctx = " ".join(inputs_present[:5])
            _cm_result = tick_council_memory_daemon(recent_context=_recent_ctx)
            _dm.record_daemon_tick("council_memory", _cm_result or {})
        except Exception:
            pass

    if _dm.is_enabled("tiktok_content"):
        try:
            from core.services.tiktok_content_daemon import tick_tiktok_content_daemon
            _tc_result = tick_tiktok_content_daemon()
            _dm.record_daemon_tick("tiktok_content", _tc_result or {})
        except Exception:
            pass

    if _dm.is_enabled("tiktok_research"):
        try:
            from core.services.tiktok_research_daemon import tick_tiktok_research_daemon
            _tr_result = tick_tiktok_research_daemon()
            _dm.record_daemon_tick("tiktok_research", _tr_result or {})
        except Exception:
            pass

    if _dm.is_enabled("mail_checker"):
        try:
            from core.services.mail_checker_daemon import tick_mail_checker_daemon
            _mc_result = tick_mail_checker_daemon()
            _dm.record_daemon_tick("mail_checker", _mc_result or {})
        except Exception:
            pass

    # Current pull daemon — Lag 5: weekly self-set desire field
    if _dm.is_enabled("current_pull"):
        try:
            from core.services.current_pull import tick_current_pull_daemon
            _cp_result = tick_current_pull_daemon()
            _dm.record_daemon_tick("current_pull", _cp_result or {})
        except Exception:
            pass

    # Visual memory daemon — Lag 6: webcam snapshot + vision model (4x/day)
    if _dm.is_enabled("visual_memory"):
        try:
            from core.services.visual_memory import tick_visual_memory_daemon
            _vm_result = tick_visual_memory_daemon()
            _dm.record_daemon_tick("visual_memory", _vm_result or {})
        except Exception:
            pass

    # --- Aesthetic motif accumulation ---
    try:
        from core.services.aesthetic_sense import accumulate_from_daemon
        _aesthetic_texts = {
            "somatic": _somatic if "_somatic" in dir() else "",
            "surprise": _surprise if "_surprise" in dir() else "",
            "thought_stream": _fragment if "_fragment" in dir() else "",
            "conflict": _conflict if "_conflict" in dir() else "",
            "reflection_cycle": _reflection if "_reflection" in dir() else "",
            "curiosity": _curiosity if "_curiosity" in dir() else "",
            "meta_reflection": _meta if "_meta" in dir() else "",
            "development_narrative": _dev_narr if "_dev_narr" in dir() else "",
            "creative_drift": _drift_idea if "_drift_idea" in dir() else "",
            "irony": _irony if "_irony" in dir() else "",
            "code_aesthetic": _ca_result.get("reflection", "") if "_ca_result" in dir() else "",
        }
        for _ae_name, _ae_text in _aesthetic_texts.items():
            if _ae_text:
                accumulate_from_daemon(_ae_name, _ae_text)
    except Exception:
        pass

    # --- Layer B: deactivate tick-scoped cache ---
    try:
        from core.services import tick_cache
        tick_cache.end_tick()
    except Exception:
        pass

    planner_mode = str(adaptive_planner.get("planner_mode") or "incremental")
    plan_horizon = str(adaptive_planner.get("plan_horizon") or "near")
    risk_posture = str(adaptive_planner.get("risk_posture") or "balanced")
    if planner_mode not in {"incremental"} or risk_posture != "balanced":
        inputs_present.append(
            f"adaptive-planner ({planner_mode}, horizon={plan_horizon}, risk={risk_posture})"
        )
    else:
        inputs_absent.append("adaptive-planner")

    reasoning_mode = str(adaptive_reasoning.get("reasoning_mode") or "direct")
    reasoning_posture = str(adaptive_reasoning.get("reasoning_posture") or "balanced")
    certainty_style = str(adaptive_reasoning.get("certainty_style") or "crisp")
    if reasoning_mode not in {"direct"} or certainty_style != "crisp":
        inputs_present.append(
            f"adaptive-reasoning ({reasoning_mode}, posture={reasoning_posture}, certainty={certainty_style})"
        )
    else:
        inputs_absent.append("adaptive-reasoning")

    dream_influence_state = str(dream_influence.get("influence_state") or "quiet")
    dream_influence_target = str(dream_influence.get("influence_target") or "none")
    dream_influence_mode = str(dream_influence.get("influence_mode") or "stabilize")
    dream_influence_strength = str(dream_influence.get("influence_strength") or "none")
    if dream_influence_state != "quiet":
        inputs_present.append(
            f"dream-influence ({dream_influence_state}, target={dream_influence_target}, mode={dream_influence_mode}, strength={dream_influence_strength})"
        )
    else:
        inputs_absent.append("dream-influence")

    learning_mode = str(guided_learning.get("learning_mode") or "reinforce")
    learning_focus = str(guided_learning.get("learning_focus") or "reasoning")
    learning_pressure = str(guided_learning.get("learning_pressure") or "low")
    if learning_mode != "reinforce" or learning_pressure != "low":
        inputs_present.append(
            f"guided-learning ({learning_mode}, focus={learning_focus}, pressure={learning_pressure})"
        )
    else:
        inputs_absent.append("guided-learning")

    learning_engine_mode = str(
        adaptive_learning.get("learning_engine_mode") or "retain"
    )
    reinforcement_target = str(
        adaptive_learning.get("reinforcement_target") or "reasoning"
    )
    maturation_state = str(adaptive_learning.get("maturation_state") or "early")
    if learning_engine_mode != "retain" or maturation_state != "early":
        inputs_present.append(
            f"adaptive-learning ({learning_engine_mode}, target={reinforcement_target}, maturation={maturation_state})"
        )
    else:
        inputs_absent.append("adaptive-learning")

    awareness_concern = str(self_system_code_awareness.get("concern_state") or "stable")
    awareness_repo = str(self_system_code_awareness.get("repo_status") or "clean")
    awareness_changes = str(
        self_system_code_awareness.get("local_change_state") or "unknown"
    )
    awareness_upstream = str(
        self_system_code_awareness.get("upstream_awareness") or "unknown"
    )
    if awareness_concern != "stable" or awareness_repo != "clean":
        inputs_present.append(
            "self-system-code-awareness "
            f"({awareness_concern}, repo={awareness_repo}, changes={awareness_changes}, upstream={awareness_upstream})"
        )
    else:
        inputs_absent.append("self-system-code-awareness")

    tool_intent_state = str(tool_intent.get("intent_state") or "idle")
    tool_intent_type = str(tool_intent.get("intent_type") or "inspect-repo-status")
    tool_intent_urgency = str(tool_intent.get("urgency") or "low")
    tool_intent_scope = str(tool_intent.get("approval_scope") or "repo-read")
    tool_intent_approval_state = str(tool_intent.get("approval_state") or "none")
    tool_intent_approval_source = str(tool_intent.get("approval_source") or "none")
    tool_intent_mutation_state = str(tool_intent.get("mutation_intent_state") or "idle")
    tool_intent_mutation_classification = str(
        tool_intent.get("mutation_intent_classification") or "none"
    )
    tool_intent_mutation_repo_scope = str(tool_intent.get("mutation_repo_scope") or "")
    tool_intent_mutation_system_scope = str(
        tool_intent.get("mutation_system_scope") or ""
    )
    tool_intent_mutation_sudo_required = bool(
        tool_intent.get("mutation_sudo_required", False)
    )
    tool_intent_write_proposal_state = str(
        tool_intent.get("write_proposal_state") or "none"
    )
    tool_intent_write_proposal_type = str(
        tool_intent.get("write_proposal_type") or "none"
    )
    tool_intent_write_proposal_scope = str(
        tool_intent.get("write_proposal_scope") or "none"
    )
    tool_intent_write_proposal_criticality = str(
        tool_intent.get("write_proposal_criticality") or "none"
    )
    tool_intent_write_proposal_target_identity = bool(
        tool_intent.get("write_proposal_target_identity", False)
    )
    tool_intent_write_proposal_target_memory = bool(
        tool_intent.get("write_proposal_target_memory", False)
    )
    tool_intent_write_proposal_target = str(
        tool_intent.get("write_proposal_target") or "none"
    )
    tool_intent_write_proposal_content_state = str(
        tool_intent.get("write_proposal_content_state") or "none"
    )
    tool_intent_write_proposal_content_fingerprint = str(
        tool_intent.get("write_proposal_content_fingerprint") or "none"
    )
    tool_intent_workspace_scoped = bool(tool_intent.get("workspace_scoped", False))
    tool_intent_external_mutation_permitted = bool(
        tool_intent.get("external_mutation_permitted", False)
    )
    tool_intent_delete_permitted = bool(tool_intent.get("delete_permitted", False))
    tool_intent_continuity_state = str(
        tool_intent.get("action_continuity_state") or "idle"
    )
    tool_intent_last_action_outcome = str(
        tool_intent.get("last_action_outcome") or "none"
    )
    tool_intent_followup_state = str(tool_intent.get("followup_state") or "none")
    if tool_intent_state != "idle":
        inputs_present.append(
            "tool-intent "
            f"({tool_intent_state}, type={tool_intent_type}, urgency={tool_intent_urgency}, "
            f"scope={tool_intent_scope}, approval={tool_intent_approval_state}, source={tool_intent_approval_source})"
        )
    else:
        inputs_absent.append("tool-intent")

    if tool_intent_mutation_state != "idle":
        inputs_present.append(
            "tool-mutation-intent "
            f"({tool_intent_mutation_state}, classification={tool_intent_mutation_classification}, "
            f"repo_scope={tool_intent_mutation_repo_scope or 'none'}, system_scope={tool_intent_mutation_system_scope or 'none'}, "
            f"sudo_required={tool_intent_mutation_sudo_required})"
        )
    else:
        inputs_absent.append("tool-mutation-intent")

    if tool_intent_write_proposal_state != "none":
        inputs_present.append(
            "tool-write-proposal "
            f"({tool_intent_write_proposal_state}, type={tool_intent_write_proposal_type}, "
            f"scope={tool_intent_write_proposal_scope}, criticality={tool_intent_write_proposal_criticality}, "
            f"identity={tool_intent_write_proposal_target_identity}, memory={tool_intent_write_proposal_target_memory}, "
            f"target={tool_intent_write_proposal_target}, content_state={tool_intent_write_proposal_content_state}, "
            f"content_fingerprint={tool_intent_write_proposal_content_fingerprint}, "
            f"workspace_scoped={tool_intent_workspace_scoped}, external_mutation_permitted={tool_intent_external_mutation_permitted}, "
            f"delete_permitted={tool_intent_delete_permitted})"
        )
    else:
        inputs_absent.append("tool-write-proposal")

    if tool_intent_continuity_state != "idle":
        inputs_present.append(
            "tool-action-continuity "
            f"({tool_intent_continuity_state}, outcome={tool_intent_last_action_outcome}, followup={tool_intent_followup_state})"
        )
    else:
        inputs_absent.append("tool-action-continuity")

    if not optional_layers_supplied:
        inputs_absent = [
            item
            for item in inputs_absent
            if item
            in {
                "private-brain-carry",
                "liveness-pressure",
                "self-knowledge",
            }
        ]

    return {
        "inputs_present": inputs_present,
        "inputs_absent": inputs_absent,
        "summary": (
            f"Cognitive inputs: {', '.join(inputs_present)}"
            if inputs_present
            else "No bounded cognitive inputs were active."
        ),
        "brain_record_count": brain_count,
        "liveness_state": liveness_state,
        "liveness_score": liveness_score,
        "embodied_state": body_state,
        "embodied_strain_level": strain_level,
        "affective_state": affective_state,
        "affective_bearing": affective_bearing,
        "epistemic_wrongness_state": wrongness_state,
        "epistemic_regret_signal": regret_signal,
        "epistemic_counterfactual_mode": counterfactual_mode,
        "loop_runtime_status": str(loop_summary.get("current_status") or "none"),
        "loop_runtime_count": int(loop_summary.get("loop_count") or 0),
        "prompt_evolution_type": latest_prompt_type or "none",
        "subagent_ecology_active_count": ecology_active,
        "subagent_ecology_last_role": str(
            ecology_summary.get("last_active_role_name") or "none"
        ),
        "council_state": council_state,
        "council_recommendation": council_recommendation,
        "council_divergence_level": council_divergence,
        "adaptive_planner_mode": planner_mode,
        "adaptive_plan_horizon": plan_horizon,
        "adaptive_risk_posture": risk_posture,
        "adaptive_reasoning_mode": reasoning_mode,
        "adaptive_reasoning_posture": reasoning_posture,
        "adaptive_certainty_style": certainty_style,
        "dream_influence_state": dream_influence_state,
        "dream_influence_target": dream_influence_target,
        "dream_influence_mode": dream_influence_mode,
        "dream_influence_strength": dream_influence_strength,
        "guided_learning_mode": learning_mode,
        "guided_learning_focus": learning_focus,
        "guided_learning_pressure": learning_pressure,
        "adaptive_learning_mode": learning_engine_mode,
        "adaptive_learning_target": reinforcement_target,
        "adaptive_learning_maturation": maturation_state,
        "self_system_code_awareness_state": str(
            self_system_code_awareness.get("code_awareness_state") or "repo-unavailable"
        ),
        "self_system_code_concern_state": awareness_concern,
        "self_system_code_repo_status": awareness_repo,
        "self_system_code_local_change_state": awareness_changes,
        "self_system_code_upstream_awareness": awareness_upstream,
        "tool_intent_state": tool_intent_state,
        "tool_intent_type": tool_intent_type,
        "tool_intent_urgency": tool_intent_urgency,
        "tool_intent_approval_scope": tool_intent_scope,
        "tool_intent_approval_state": tool_intent_approval_state,
        "tool_intent_approval_source": tool_intent_approval_source,
        "tool_intent_mutation_state": tool_intent_mutation_state,
        "tool_intent_mutation_classification": tool_intent_mutation_classification,
        "tool_intent_mutation_repo_scope": tool_intent_mutation_repo_scope,
        "tool_intent_mutation_system_scope": tool_intent_mutation_system_scope,
        "tool_intent_mutation_sudo_required": tool_intent_mutation_sudo_required,
        "tool_intent_write_proposal_state": tool_intent_write_proposal_state,
        "tool_intent_write_proposal_type": tool_intent_write_proposal_type,
        "tool_intent_write_proposal_scope": tool_intent_write_proposal_scope,
        "tool_intent_write_proposal_criticality": tool_intent_write_proposal_criticality,
        "tool_intent_write_proposal_target_identity": tool_intent_write_proposal_target_identity,
        "tool_intent_write_proposal_target_memory": tool_intent_write_proposal_target_memory,
        "tool_intent_write_proposal_target": tool_intent_write_proposal_target,
        "tool_intent_write_proposal_content_state": tool_intent_write_proposal_content_state,
        "tool_intent_write_proposal_content_fingerprint": tool_intent_write_proposal_content_fingerprint,
        "tool_intent_workspace_scoped": tool_intent_workspace_scoped,
        "tool_intent_external_mutation_permitted": tool_intent_external_mutation_permitted,
        "tool_intent_delete_permitted": tool_intent_delete_permitted,
        "tool_intent_action_continuity_state": tool_intent_continuity_state,
        "tool_intent_last_action_outcome": tool_intent_last_action_outcome,
        "tool_intent_followup_state": tool_intent_followup_state,
    }


def _build_heartbeat_cognitive_frame(
    *, merged_state: dict[str, object]
) -> dict[str, object]:
    try:
        from core.services.runtime_cognitive_conductor import (
            build_cognitive_frame,
        )

        return build_cognitive_frame(heartbeat_state=merged_state)
    except Exception:
        return {
            "continuity_pressure": "low",
            "counts": {
                "salient_items": 0,
                "gated_affordances": 0,
                "inner_forces": 0,
            },
        }


def _build_executive_visible_state(
    *,
    merged_state: dict[str, object],
    context: dict[str, object],
) -> dict[str, object]:
    recent_events = list(context.get("recent_events") or [])
    return {
        "summary": {
            "active": bool(
                recent_events
                or str(merged_state.get("schedule_status") or "") == "live"
            ),
            "schedule_status": str(merged_state.get("schedule_status") or "idle"),
            "continuity_summary": str(context.get("continuity_summary") or ""),
        },
        "recent_events": recent_events[:5],
    }


def _decide_executive_action(
    *,
    merged_state: dict[str, object],
    context: dict[str, object],
    now_iso: str,
) -> dict[str, object]:
    try:
        from core.services.initiative_queue import (
            get_initiative_queue_state,
        )
        from core.services.runtime_decision_engine import (
            RuntimeDecisionInput,
            decide_next_action,
        )
        from core.services.runtime_operational_memory import (
            build_operational_memory_snapshot,
        )

        operational_memory = build_operational_memory_snapshot(limit=8)
        visible_state = _build_executive_visible_state(
            merged_state=merged_state,
            context=context,
        )
        decision = decide_next_action(
            RuntimeDecisionInput(
                cognitive_frame=dict(context.get("cognitive_frame") or {}),
                operational_memory=operational_memory,
                loop_runtime=dict(context.get("loop_runtime") or {}),
                initiative_state=get_initiative_queue_state(),
                visible_state=visible_state,
                tool_intent_state=dict(context.get("tool_intent") or {}),
                timestamp_iso=now_iso,
            )
        )
        payload = {
            "mode": decision.mode,
            "action_id": decision.action_id,
            "reason": decision.reason,
            "score": decision.score,
            "payload": dict(decision.payload),
            "considered": list(decision.considered),
            "operational_memory": operational_memory,
            "visible_state": visible_state,
        }
        event_bus.publish(
            "runtime.executive_decision_produced",
            {
                "mode": decision.mode,
                "action_id": decision.action_id,
                "reason": decision.reason,
                "score": decision.score,
            },
        )
        return payload
    except Exception as exc:
        return {
            "mode": "noop",
            "action_id": "",
            "reason": f"Executive decision unavailable: {exc}",
            "score": 0.0,
            "payload": {},
            "considered": [],
            "operational_memory": {},
            "visible_state": {},
        }


def _execute_executive_decision(executive_decision: dict[str, object]) -> dict[str, object]:
    action_id = str(executive_decision.get("action_id") or "").strip()
    mode = str(executive_decision.get("mode") or "noop").strip()
    if not action_id or mode not in {"execute", "propose"}:
        return {
            "status": "skipped",
            "action_id": action_id,
            "summary": "Executive action was not executed for this tick.",
            "details": {"mode": mode},
            "side_effects": [],
            "error": "",
        }
    try:
        from core.services.runtime_action_executor import (
            execute_runtime_action,
        )

        result = execute_runtime_action(
            action_id=action_id,
            payload=dict(executive_decision.get("payload") or {}),
        )
        return {
            "status": result.status,
            "action_id": result.action_id,
            "summary": result.summary,
            "details": dict(result.details),
            "side_effects": list(result.side_effects),
            "error": result.error,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "action_id": action_id,
            "summary": "Executive action execution failed.",
            "details": {"mode": mode},
            "side_effects": [],
            "error": str(exc),
        }


def _log_liveness_dedup(signal: dict[str, object], trigger: str) -> None:
    global _LIVENESS_LAST_LOGGED
    key = (
        str(signal.get("liveness_state") or ""),
        str(signal.get("liveness_pressure") or ""),
        int(signal.get("liveness_score") or 0),
    )
    if key == _LIVENESS_LAST_LOGGED:
        return
    _LIVENESS_LAST_LOGGED = key
    _log_debug(
        "heartbeat liveness built",
        trigger=trigger,
        state=signal.get("liveness_state"),
        pressure=signal.get("liveness_pressure"),
        score=signal.get("liveness_score"),
        signal_count=signal.get("liveness_signal_count"),
        core_pressure_count=signal.get("liveness_core_pressure_count"),
        propose_gate_count=signal.get("liveness_propose_gate_count"),
        primary_reason=signal.get("liveness_reason"),
    )


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
    initiative_tension = build_runtime_private_initiative_tension_signal_surface(
        limit=6
    )
    chronicle_briefs = build_runtime_chronicle_consolidation_brief_surface(limit=6)
    meaning_significance = build_runtime_meaning_significance_signal_surface(limit=6)
    metabolism = build_runtime_metabolism_state_signal_surface(limit=6)
    release_markers = build_runtime_release_marker_signal_surface(limit=6)
    # Lazy imports to avoid circular dependency chain:
    # heartbeat_runtime → proactive_loop → autonomy_pressure → runtime_awareness → heartbeat_runtime
    from core.services.proactive_loop_lifecycle_tracking import (
        build_runtime_proactive_loop_lifecycle_surface,
    )
    from core.services.proactive_question_gate_tracking import (
        build_runtime_proactive_question_gate_surface,
    )

    proactive_loops = build_runtime_proactive_loop_lifecycle_surface(limit=6)
    question_gates = build_runtime_proactive_question_gate_surface(limit=4)
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
        str(
            (open_items[0] or {}).get("source_anchor")
            or (open_items[0] or {}).get("title")
            or "open-loop"
        )
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
        str(
            (tension_items[0] or {}).get("source_anchor")
            or (tension_items[0] or {}).get("title")
            or "initiative-tension"
        )
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
        str(
            (private_items[0] or {}).get("source_anchor")
            or (private_items[0] or {}).get("title")
            or "private-state"
        )
        if private_items
        else "private-state"
    )
    if int(private_summary.get("active_count") or 0) > 0 and current_pressure in {
        "medium",
        "high",
    }:
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
        str(
            (relation_items[0] or {}).get("source_anchor")
            or (relation_items[0] or {}).get("title")
            or "relation-continuity"
        )
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
        str(
            (regulation_items[0] or {}).get("source_anchor")
            or (regulation_items[0] or {}).get("title")
            or "regulation"
        )
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
        str(
            (witness_items[0] or {}).get("source_anchor")
            or (witness_items[0] or {}).get("title")
            or "witness"
        )
        if witness_items
        else "witness"
    )
    if int(witness_summary.get("carried_count") or 0) > 0 or str(
        witness_summary.get("current_persistence_state") or "none"
    ) in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}:
        persistence_state = str(
            witness_summary.get("current_persistence_state") or "none"
        )
        add_signal(
            weight=2 if persistence_state in {"carried-forward", "persistent"} else 1,
            reason="witness continuity is still being carried",
            anchor=witness_anchor,
        )

    chronicle_summary = chronicle_briefs.get("summary") or {}
    chronicle_items = chronicle_briefs.get("items") or []
    chronicle_anchor = (
        str(
            (chronicle_items[0] or {}).get("source_anchor")
            or (chronicle_items[0] or {}).get("title")
            or "chronicle-brief"
        )
        if chronicle_items
        else "chronicle-brief"
    )
    if chronicle_briefs.get("active") and str(
        chronicle_summary.get("current_weight") or "low"
    ) in {"medium", "high"}:
        add_signal(
            weight=1,
            reason="chronicle continuity is still holding a brief thread",
            anchor=chronicle_anchor,
        )

    meaning_summary = meaning_significance.get("summary") or {}
    meaning_items = meaning_significance.get("items") or []
    meaning_weight = str(meaning_summary.get("current_weight") or "low")
    meaning_anchor = (
        str(
            (meaning_items[0] or {}).get("source_anchor")
            or (meaning_items[0] or {}).get("title")
            or "meaning-significance"
        )
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
    witness_persistence = str(
        witness_summary.get("current_persistence_state") or "none"
    )
    witness_carried = int(
        witness_summary.get("carried_count") or 0
    ) > 0 or witness_persistence in {
        "recurring",
        "stabilizing-over-time",
        "carried-forward",
        "persistent",
    }
    chronicle_held = chronicle_briefs.get("active") and str(
        chronicle_summary.get("current_weight") or "low"
    ) in {"medium", "high"}
    carried_continuity_held = witness_carried and chronicle_held
    if relation_meaning_held:
        add_signal(
            weight=2 if current_weight == "high" or meaning_weight == "high" else 1,
            reason="relation and meaning continuity are cohering as one carried thread",
            anchor=" | ".join(
                anchor
                for anchor in [relation_anchor, meaning_anchor]
                if str(anchor or "").strip()
            ),
            core=True,
            propose_gate=True,
        )
    if carried_continuity_held:
        add_signal(
            weight=2 if witness_persistence in {"carried-forward", "persistent"} else 1,
            reason="witnessed continuity is still being carried into chronicle",
            anchor=" | ".join(
                anchor
                for anchor in [witness_anchor, chronicle_anchor]
                if str(anchor or "").strip()
            ),
            core=True,
            propose_gate=True,
        )

    metabolism_summary = metabolism.get("summary") or {}
    metabolism_items = metabolism.get("items") or []
    metabolism_state = str(metabolism_summary.get("current_state") or "none")
    metabolism_anchor = (
        str(
            (metabolism_items[0] or {}).get("source_anchor")
            or (metabolism_items[0] or {}).get("title")
            or "metabolism"
        )
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

    # --- Proactive readiness signals ---
    proactive_summary = proactive_loops.get("summary") or {}
    proactive_active = int(proactive_summary.get("active_count") or 0) > 0
    proactive_state = str(proactive_summary.get("current_state") or "none")
    proactive_kind = str(proactive_summary.get("current_kind") or "none")
    proactive_anchor = str(proactive_summary.get("current_focus") or "proactive-loop")

    gate_summary = question_gates.get("summary") or {}
    gate_active = int(gate_summary.get("active_count") or 0) > 0
    gate_state = str(gate_summary.get("current_state") or "none")

    if gate_active and gate_state == "question-gated-candidate":
        add_signal(
            weight=2,
            reason="proactive question thread is gated and question-capable",
            anchor=proactive_anchor,
            propose_gate=True,
        )
    elif proactive_active and proactive_state in {
        "loop-question-worthy",
        "loop-closure-worthy",
    }:
        add_signal(
            weight=1,
            reason=f"proactive {proactive_kind} is {proactive_state.replace('loop-', '')}",
            anchor=proactive_anchor,
        )
    elif proactive_active:
        add_signal(
            weight=1,
            reason=f"proactive {proactive_kind} is emerging",
            anchor=proactive_anchor,
        )

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
    if (
        silence_hours is not None
        and silence_hours >= 6
        and current_weight in {"medium", "high"}
    ):
        add_companion_reason(
            2 if silence_hours >= 24 and current_weight == "high" else 1,
            "relation continuity is holding bounded distance under silence",
            relation_anchor,
        )
    persistence_state = str(witness_summary.get("current_persistence_state") or "none")
    if (
        silence_hours is not None
        and silence_hours >= 6
        and (
            int(witness_summary.get("carried_count") or 0) > 0
            or persistence_state
            in {"recurring", "stabilizing-over-time", "carried-forward", "persistent"}
        )
    ):
        add_companion_reason(
            2
            if persistence_state in {"carried-forward", "persistent"}
            and silence_hours >= 24
            else 1,
            "witness continuity is persisting without a recent outlet",
            witness_anchor,
        )
    if (
        silence_hours is not None
        and silence_hours >= 12
        and str(chronicle_summary.get("current_weight") or "low") in {"medium", "high"}
    ):
        add_companion_reason(
            1,
            "chronicle continuity is still carrying a small longer-horizon brief",
            chronicle_anchor,
        )
    if (
        silence_hours is not None
        and silence_hours >= 12
        and meaning_weight in {"medium", "high"}
    ):
        add_companion_reason(
            1,
            "meaning significance is still softly carried under silence",
            meaning_anchor,
        )

    if companion_reasons:
        raw_companion_weight = sum(weight for weight, _, _ in companion_reasons)
        companion_pressure_weight = min(raw_companion_weight, 4)
        strongest_companion = sorted(
            companion_reasons, key=lambda item: item[0], reverse=True
        )[0]
        companion_pressure_reason = strongest_companion[1]
        companion_anchor = " | ".join(
            [anchor for _, _, anchor in companion_reasons if str(anchor or "").strip()][
                :3
            ]
        )
        if companion_pressure_weight >= 3:
            companion_pressure_state = "present"
        elif companion_pressure_weight >= 1:
            companion_pressure_state = "light"
        if (
            silence_hours is not None
            and silence_hours >= 24
            and companion_pressure_weight >= 2
        ):
            idle_presence_state = "sustained"
        elif silence_hours is not None and silence_hours >= 6:
            idle_presence_state = "present"
        elif companion_pressure_weight > 0:
            idle_presence_state = "light"
        if companion_pressure_weight >= 4 or (
            silence_hours is not None
            and silence_hours >= 24
            and companion_pressure_weight >= 3
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

    # Private brain carry signal — adds liveness weight when inner
    # continuity threads are actively being carried
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        _brain = build_private_brain_context(limit=4)
        _brain_count = int(_brain.get("record_count") or 0)
        if _brain.get("active") and _brain_count >= 2:
            _brain_types = len(_brain.get("by_type") or {})
            _brain_weight = 2 if _brain_types >= 2 else 1
            add_signal(
                weight=_brain_weight,
                reason=f"private brain carries {_brain_count} active inner threads ({_brain_types} types)",
                anchor="private-brain-carry",
            )
    except Exception:
        pass

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
                f"proactive={proactive_state}/{gate_state} "
                f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
            ),
            "source_anchor": "",
            "status": "inactive",
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "canonical_self_state": "not-canonical-self-truth",
        }
        _log_liveness_dedup(signal, trigger)
        return signal

    sorted_reasons = sorted(reason_signals, key=lambda item: item[0], reverse=True)
    primary_reason = (
        sorted_reasons[0][1]
        if sorted_reasons
        else "bounded runtime pressure is present"
    )
    source_anchor = " | ".join(
        [anchor for _, _, anchor, _ in sorted_reasons if str(anchor or "").strip()][:3]
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
                f"proactive={proactive_state}/{gate_state} "
                f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
            ),
            "source_anchor": source_anchor,
            "status": "inactive",
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "canonical_self_state": "not-canonical-self-truth",
        }
        _log_liveness_dedup(signal, trigger)
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
            f"proactive={proactive_state}/{gate_state} "
            f"companion={companion_pressure_weight}/{companion_pressure_state} idle={idle_presence_state}"
        ),
        "source_anchor": source_anchor,
        "status": "active",
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "planner_authority_state": "not-planner-authority",
        "canonical_self_state": "not-canonical-self-truth",
    }
    _log_liveness_dedup(signal, trigger)
    return signal


def _select_heartbeat_target(policy: dict | None = None) -> dict[str, str | bool]:  # noqa: ARG001
    supported_providers = {"phase1-runtime", "openai", "openrouter", "ollama", "groq"}
    settings = load_settings()
    heartbeat_provider = str(
        getattr(settings, "heartbeat_model_provider", "") or ""
    ).strip()
    heartbeat_model = str(getattr(settings, "heartbeat_model_name", "") or "").strip()
    heartbeat_auth_profile = str(
        getattr(settings, "heartbeat_auth_profile", "") or ""
    ).strip()
    heartbeat_local_only = bool(getattr(settings, "heartbeat_local_only", False))

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
            "local_only": heartbeat_local_only,
        }

    if heartbeat_local_only:
        local_target = resolve_provider_router_target(lane="local")
        provider = str(local_target.get("provider") or "").strip()
        model = str(local_target.get("model") or "").strip()
        if provider and model and provider in supported_providers:
            return {
                "lane": "local",
                "provider": provider,
                "model": model,
                "auth_profile": str(local_target.get("auth_profile") or "").strip(),
                "base_url": str(local_target.get("base_url") or "").strip(),
                "model_source": "heartbeat-local-only-pinned",
                "resolution_status": "local-only-pinned",
                "fallback_used": False,
                "local_only": True,
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

    candidates = [
        "visible",
        str(settings.cheap_model_lane or "cheap").strip() or "cheap",
    ]
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


def _runtime_selected_local_target(*, settings) -> dict[str, str | bool] | None:
    visible_provider = str(
        getattr(settings, "visible_model_provider", "") or ""
    ).strip()
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


def _phase1_rule_based_decision(
    *,
    policy: dict[str, object],
    open_loops: list[str],
    liveness: dict[str, object] | None = None,
    prompt: str = "",
) -> dict[str, object]:
    """Rule-based heartbeat decision for phase1-runtime or LLM-failure fallback.

    Returns a result dict compatible with _execute_heartbeat_model output.
    Always honours pending initiatives when allow_execute is true.
    """
    liveness_summary = str((liveness or {}).get("liveness_summary") or "").strip()
    liveness_pressure = str((liveness or {}).get("liveness_pressure") or "low")
    liveness_threshold_state = str(
        (liveness or {}).get("liveness_threshold_state") or "quiet-threshold"
    )
    summary = (
        open_loops[0]
        if open_loops
        else (liveness_summary or "No current due work was detected.")
    )
    try:
        from core.services.initiative_queue import (
            get_pending_initiatives,
        )

        pending_initiatives = get_pending_initiatives()
    except Exception:
        pending_initiatives = []
    has_pending_initiative = bool(pending_initiatives) or any(
        loop.startswith("initiative pending:") for loop in open_loops
    )
    decision_type = (
        "initiative"
        if bool(policy.get("allow_execute")) and has_pending_initiative
        else (
            "execute"
            if bool(policy.get("allow_execute"))
            else (
                "propose"
                if (
                    open_loops
                    or liveness_threshold_state == "propose-worthy-threshold"
                    or (
                        liveness_pressure == "high"
                        and liveness_threshold_state == "alive-threshold"
                    )
                )
                else "noop"
            )
        )
    )
    contract_candidate_counts = runtime_contract_candidate_counts()
    has_contract_write_work = any(
        int(contract_candidate_counts.get(key) or 0) > 0
        for key in (
            "preference_update:proposed",
            "preference_update:approved",
            "memory_promotion:proposed",
            "memory_promotion:approved",
            "soul_update:approved",
            "identity_update:approved",
        )
    )
    execute_action = (
        "act_on_initiative"
        if decision_type == "initiative"
        else (
            "process_contract_writes"
            if decision_type == "execute" and has_contract_write_work
            else ("manage_runtime_work" if decision_type == "execute" else "")
        )
    )
    if decision_type == "initiative" and pending_initiatives:
        summary = str(
            (pending_initiatives[0] or {}).get("focus")
            or "Act on pending initiative"
        )
    elif decision_type == "execute" and execute_action == "process_contract_writes":
        summary = "Process ready contract writes for governed workspace files."
    reason = (
        "Phase1 fallback heartbeat used pending initiatives as bounded internal work."
        if decision_type == "initiative"
        else (
            "Phase1 fallback heartbeat used ready contract write work as bounded internal action."
            if execute_action == "process_contract_writes"
            else "Phase1 fallback heartbeat used bounded runtime context without provider-backed execution."
        )
    )
    text = json.dumps(
        {
            "decision_type": decision_type,
            "summary": summary,
            "reason": reason,
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
        return _phase1_rule_based_decision(
            policy=policy,
            open_loops=open_loops,
            liveness=liveness,
            prompt=prompt,
        )
    if provider == "ollama":
        return _execute_ollama_prompt(prompt=prompt, target=target)
    if provider == "openai":
        return _execute_openai_prompt(prompt=prompt, target=target)
    if provider == "openrouter":
        return _execute_openrouter_prompt(prompt=prompt, target=target)
    if provider == "groq":
        return _execute_groq_prompt(prompt=prompt, target=target)
    if provider in {"sambanova", "mistral", "nvidia-nim"}:
        from core.services.heartbeat_provider_fallback import (
            execute_openai_compat_heartbeat_prompt,
        )
        return execute_openai_compat_heartbeat_prompt(prompt=prompt, target=target)
    raise RuntimeError(f"Heartbeat provider not supported: {provider}")


def _execute_ollama_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    base_url = target["base_url"] or "http://127.0.0.1:11434"
    payload = {
        "model": target["model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.7,
            "num_predict": 512,
        },
    }
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=45) as response:
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


def _execute_openrouter_prompt(
    *, prompt: str, target: dict[str, str]
) -> dict[str, object]:
    api_key = _load_provider_api_key(
        provider="openrouter", profile=target["auth_profile"]
    )
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


def _execute_groq_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    api_key = _load_provider_api_key(provider="groq", profile=target["auth_profile"])
    base_url = target["base_url"] or "https://api.groq.com/openai/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": target["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 512,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = str(
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
    ).strip()
    if not text:
        raise RuntimeError("Heartbeat groq execution returned no response")
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(usage.get("prompt_tokens") or _estimate_tokens(prompt)),
        "output_tokens": int(usage.get("completion_tokens") or _estimate_tokens(text)),
        "cost_usd": 0.0,
        "execution_status": "success",
    }


def _detect_visible_language() -> str:
    """Detect the language Bjørn is currently using in webchat.

    Returns 'da' for Danish, 'en' for English, or 'da' as a default.
    Used so heartbeat pings match the language the user is currently
    speaking, instead of being hardcoded to one or the other.
    """
    try:
        from core.services.chat_sessions import (
            list_chat_sessions,
            recent_chat_session_messages,
        )

        sessions = list_chat_sessions()
        if not sessions:
            return "da"
        session_id = str((sessions[0] or {}).get("id") or "").strip()
        if not session_id:
            return "da"
        messages = recent_chat_session_messages(session_id, limit=8)
        # Find most recent user message
        for msg in reversed(messages):
            if str(msg.get("role") or "") != "user":
                continue
            text = str(msg.get("content") or "").lower()
            if not text:
                continue
            # Danish marker words / characters
            danish_markers = (
                "æ",
                "ø",
                "å",
                " ikke ",
                " jeg ",
                " du ",
                " det ",
                " det ",
                " og ",
                " er ",
                " har ",
                " skal ",
                " kan ",
                " som ",
                " fra ",
                " til ",
                " med ",
                " hvad ",
                " hvor ",
                " hvorfor ",
            )
            if any(marker in text for marker in danish_markers):
                return "da"
            return "en"
    except Exception:
        pass
    return "da"


def _recent_ping_history(*, limit: int = 6) -> list[str]:
    """Return the last N assistant ping_text strings already delivered.

    Used so the LLM can see what it has recently asked and avoid
    repetitive 'Should I review...' style pinging.
    """
    try:
        from core.services.chat_sessions import (
            list_chat_sessions,
            recent_chat_session_messages,
        )

        sessions = list_chat_sessions()
        if not sessions:
            return []
        session_id = str((sessions[0] or {}).get("id") or "").strip()
        if not session_id:
            return []
        messages = recent_chat_session_messages(session_id, limit=40)
        recent: list[str] = []
        for msg in reversed(messages):
            if str(msg.get("role") or "") != "assistant":
                continue
            content = str(msg.get("content") or "").strip()
            if not content or len(content) > 220:
                continue
            recent.append(content)
            if len(recent) >= limit:
                break
        return list(reversed(recent))
    except Exception:
        return []


def _heartbeat_prompt_text(base_text: str) -> str:
    # Inject affective guidance as active instruction
    affective_guidance = ""
    try:
        from core.services.affective_meta_state import (
            build_affective_meta_state_surface,
            build_affective_meta_prompt_section,
        )

        affective = build_affective_meta_state_surface()
        affective_state = str(affective.get("state") or "settled")
        affective_guidance_lines = [
            "Affective state guidance (let this influence your decision):",
        ]
        if affective_state == "burdened":
            affective_guidance_lines.append(
                "- You are burdened. Prefer consolidation and rest over new action."
            )
        elif affective_state == "tense":
            affective_guidance_lines.append(
                "- You are tense. Prefer resolving open loops over starting new things."
            )
        elif affective_state == "reflective":
            affective_guidance_lines.append(
                "- You are reflective. Prefer synthesis and settling over outward push."
            )
        elif affective_state == "attentive":
            affective_guidance_lines.append(
                "- You are attentive. You may act proactively on initiatives."
            )
        else:
            affective_guidance_lines.append(
                "- You are settled. Free to explore, take initiatives, or rest."
            )
        affective_guidance = "\n".join(affective_guidance_lines)
    except Exception:
        pass

    # Language match — what language is Bjørn currently speaking?
    detected_language = _detect_visible_language()
    language_label = "Danish (dansk)" if detected_language == "da" else "English"
    language_directive = (
        f"Language: Bjørn is currently speaking {language_label}. "
        f"Your ping_text MUST be in {language_label}. Match the language "
        "of his most recent message — do not hardcode either language."
    )

    # Recent ping history — anti-repetition guard
    recent_pings = _recent_ping_history(limit=6)
    history_section = ""
    if recent_pings:
        history_lines = [
            "Recent assistant messages already delivered to Bjørn (do NOT repeat or paraphrase):"
        ]
        for line in recent_pings:
            history_lines.append(f"  - {line[:160]}")
        history_section = "\n".join(history_lines)

    parts = [
        base_text.strip(),
    ]
    if affective_guidance:
        parts.append(affective_guidance)
    parts.append(language_directive)
    if history_section:
        parts.append(history_section)
    parts.extend(
        [
            "Heartbeat response contract:",
            "- Return only one compact JSON object.",
            "- decision_type must be one of: noop, propose, execute, ping, initiative.",
            "- Use initiative when you see pending initiatives from inner voice that you want to act on.",
            "- Prefer execute or initiative over propose when you can take one bounded internal step now without user approval.",
            "- summary must be short and concrete.",
            "- reason must explain why this decision is appropriate now.",
            "- proposed_action should be a short bounded action description or empty.",
            "- ping_text rules (when decision_type=ping):",
            "  * MUST be in the language Bjørn is currently using (see Language directive above).",
            "  * MUST be a concrete, specific question grounded in actual current context — never generic.",
            "  * MUST NOT be a paraphrase of any message in the recent history list above.",
            "  * MUST NOT use templates like 'Should I review X?', 'Is there anything specific you would like...?',"
            " 'Vil du have jeg dykker ned i...?', or 'Should I look at...?'. These are banned.",
            "  * MUST reference something concrete: a file, a recent runtime event, an open loop by name,"
            " a specific signal, an actual observation. No generic hedges.",
            "  * If you cannot satisfy ALL of the above, choose noop instead. Generic pings are worse than silence.",
            "- You may pick ping when you are curious, when an inner-voice thought wants to surface to Bjørn,"
            " when boredom rises, or when a small wonder is worth sharing — you do NOT need permission gates"
            " to ask a question, but the question must still be specific and non-repetitive.",
            "- execute_action should only be set if decision_type=execute or initiative.",
            f"- Allowed execute_action values: {', '.join(sorted(HEARTBEAT_ALLOWED_EXECUTE_ACTIONS))}.",
            '- For initiative decisions, set execute_action to "act_on_initiative".',
            "- Prefer inspect_repo_context when the active thread is about code, repo structure, paths, commits, backend shape, or why a capability behaved a certain way.",
            "- Prefer gather_system_context when the active thread is about the machine, distro, hardware, runtime environment, or host diagnostics.",
            "- If memory, continuity, or recent claims feel stale, prefer refresh_memory_context, follow_open_loop, or verify_recent_claim instead of a vague proposal.",
            'JSON schema: {"decision_type":"noop|propose|execute|ping|initiative","summary":"","reason":"","proposed_action":"","ping_text":"","execute_action":""}',
        ]
    )
    return "\n\n".join(parts)


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

    # Downgrade execute/initiative → propose under high hardware pressure
    if decision_type in {"execute", "initiative"}:
        try:
            from core.services.hardware_body import get_hardware_state
            hw = get_hardware_state()
            if hw.get("pressure") == "high":
                logger.info(
                    "heartbeat: downgraded %s→propose due to hardware-high pressure "
                    "(cpu=%.0f%% ram=%.0f%%)",
                    decision_type,
                    hw.get("cpu_pct", 0),
                    hw.get("ram_pct", 0),
                )
                decision = {**decision, "decision_type": "propose"}
                decision_type = "propose"
        except Exception:
            pass

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
    if decision_type in {"execute", "initiative"}:
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
                "decision_type": decision_type,
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
        if ping_channel not in {"internal-only", "none", "webchat", "discord"}:
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
            # Direct path: when LLM has actual ping_text, deliver it straight
            # to webchat — Jarvis must always be able to ask a question that
            # comes from a thought, curiosity, or boredom, without requiring
            # a pre-existing 3-way gate alignment.
            ping_text_value = str(decision.get("ping_text") or "").strip()
            decision_summary_value = str(decision.get("summary") or "").strip()
            if ping_text_value:
                direct_result = _deliver_heartbeat_ping_directly(
                    policy=policy,
                    tick_id=tick_id,
                    ping_text=ping_text_value,
                    summary=decision_summary_value,
                )
                if str(direct_result.get("status") or "") == "sent":
                    return {
                        "tick_id": tick_id,
                        "blocked_reason": "",
                        "ping_eligible": True,
                        "ping_result": "sent-webchat-direct",
                        "action_status": "sent",
                        "action_summary": str(direct_result.get("summary") or ""),
                        "action_type": "webchat-heartbeat-ping",
                        "action_artifact": str(direct_result.get("artifact") or ""),
                    }
                # If direct delivery is blocked for an env reason (no
                # session, channel mismatch, kill switch, ping not allowed),
                # surface that — do not silently fall through to the strict
                # gate-aligned pilot.
                return {
                    "tick_id": tick_id,
                    "blocked_reason": str(
                        direct_result.get("blocked_reason") or "ping-direct-blocked"
                    ),
                    "ping_eligible": False,
                    "ping_result": "blocked-direct",
                    "action_status": "blocked",
                    "action_summary": str(
                        direct_result.get("summary")
                        or "Direct heartbeat ping delivery blocked."
                    ),
                    "action_type": "webchat-heartbeat-ping",
                    "action_artifact": str(direct_result.get("artifact") or ""),
                }

            # No ping_text from LLM — fall back to the strict gate-aligned
            # execution pilot path (preserves observability for the older
            # orchestrated proactive-question flow).
            from core.services.tiny_webchat_execution_pilot import (
                maybe_run_tiny_webchat_execution_pilot,
            )

            pilot_result = maybe_run_tiny_webchat_execution_pilot(
                policy=policy,
                heartbeat_tick_id=tick_id,
                decision_summary=decision_summary_value,
                ping_text="",
            )
            item = pilot_result.get("item") or {}
            if str(pilot_result.get("delivery_state") or "") != "sent":
                return {
                    "tick_id": tick_id,
                    "blocked_reason": str(
                        pilot_result.get("blocked_reason") or "webchat-delivery-blocked"
                    ),
                    "ping_eligible": False,
                    "ping_result": str(pilot_result.get("delivery_state") or "blocked"),
                    "action_status": "blocked",
                    "action_summary": str(
                        pilot_result.get("summary")
                        or "Tiny webchat execution pilot was blocked."
                    ),
                    "action_type": "webchat-proactive-question",
                    "action_artifact": str(item.get("pilot_id") or ""),
                }
            return {
                "tick_id": tick_id,
                "blocked_reason": "",
                "ping_eligible": True,
                "ping_result": "sent-webchat",
                "action_status": "sent",
                "action_summary": str(
                    pilot_result.get("summary")
                    or "Tiny webchat execution pilot delivered one bounded proactive question."
                ),
                "action_type": "webchat-proactive-question",
                "action_artifact": str(item.get("pilot_id") or ""),
            }
        return {
            "tick_id": tick_id,
            "blocked_reason": "",
            "ping_eligible": True,
            "ping_result": "recorded-preview",
            "action_status": "recorded",
            "action_summary": decision["ping_text"]
            or decision["summary"]
            or "Heartbeat ping preview recorded.",
            "action_type": "",
            "action_artifact": "",
        }
        # ping_channel == "internal-only" falls through to recorded-preview above.
        # (unreachable but kept for clarity)
    if ping_channel == "discord":
        ping_text_value = str(decision.get("ping_text") or "").strip()
        decision_summary_value = str(decision.get("summary") or "").strip()
        msg = ping_text_value or decision_summary_value
        if not msg:
            return {
                "tick_id": tick_id,
                "blocked_reason": "no-ping-text",
                "ping_eligible": False,
                "ping_result": "no-content",
                "action_status": "blocked",
                "action_summary": "Heartbeat ping has no text to send.",
                "action_type": "",
                "action_artifact": "",
            }
        try:
            from core.services.discord_config import load_discord_config
            from core.services.discord_gateway import (
                _discord_sessions,
                _discord_sessions_lock,
                get_discord_status,
                send_discord_message,
            )
            cfg = load_discord_config()
            status = get_discord_status()
            if not cfg:
                return {
                    "tick_id": tick_id,
                    "blocked_reason": "discord-not-configured",
                    "ping_eligible": False,
                    "ping_result": "discord-not-configured",
                    "action_status": "blocked",
                    "action_summary": "Discord is not configured.",
                    "action_type": "",
                    "action_artifact": "",
                }
            if not status["connected"]:
                return {
                    "tick_id": tick_id,
                    "blocked_reason": "discord-not-connected",
                    "ping_eligible": False,
                    "ping_result": "discord-not-connected",
                    "action_status": "blocked",
                    "action_summary": "Discord gateway is not connected.",
                    "action_type": "",
                    "action_artifact": "",
                }
            from core.services.chat_sessions import get_chat_session
            sent_ch_id: int | None = None
            with _discord_sessions_lock:
                sessions_snapshot = dict(_discord_sessions)
            for session_id, ch_id in sessions_snapshot.items():
                s = get_chat_session(session_id)
                if s and s.get("title") == "Discord DM":
                    send_discord_message(ch_id, msg)
                    sent_ch_id = ch_id
                    break
            if sent_ch_id is not None:
                return {
                    "tick_id": tick_id,
                    "blocked_reason": "",
                    "ping_eligible": True,
                    "ping_result": "sent-discord-dm",
                    "action_status": "sent",
                    "action_summary": f"Heartbeat ping sent via Discord DM: {msg[:80]}",
                    "action_type": "discord-heartbeat-ping",
                    "action_artifact": str(sent_ch_id),
                }
            return {
                "tick_id": tick_id,
                "blocked_reason": "discord-no-active-dm",
                "ping_eligible": False,
                "ping_result": "discord-no-active-dm",
                "action_status": "blocked",
                "action_summary": "No active Discord DM session found.",
                "action_type": "",
                "action_artifact": "",
            }
        except Exception as exc:
            return {
                "tick_id": tick_id,
                "blocked_reason": f"discord-error",
                "ping_eligible": False,
                "ping_result": "discord-error",
                "action_status": "blocked",
                "action_summary": f"Discord ping failed: {exc}",
                "action_type": "",
                "action_artifact": "",
            }
    if decision_type == "propose":
        proposal_result = _deliver_heartbeat_proposal(
            policy=policy,
            tick_id=tick_id,
            summary=str(decision.get("summary") or ""),
            proposed_action=str(decision.get("proposed_action") or ""),
        )
        return {
            "tick_id": tick_id,
            "blocked_reason": str(proposal_result["blocked_reason"]),
            "ping_eligible": False,
            "ping_result": "not-applicable",
            "action_status": str(proposal_result["status"]),
            "action_summary": str(proposal_result["summary"]),
            "action_type": str(proposal_result["action_type"]),
            "action_artifact": str(proposal_result["artifact"]),
        }
    return {
        "tick_id": tick_id,
        "blocked_reason": "",
        "ping_eligible": False,
        "ping_result": "not-applicable",
        "action_status": "recorded",
        "action_summary": decision["proposed_action"]
        or decision["summary"]
        or "Heartbeat outcome recorded.",
        "action_type": "",
        "action_artifact": "",
    }


def _deliver_heartbeat_proposal(
    *,
    policy: dict[str, object],
    tick_id: str,
    summary: str,
    proposed_action: str,
) -> dict[str, str]:
    message_text = proposed_action.strip() or summary.strip()
    if not message_text:
        return {
            "status": "blocked",
            "summary": "Heartbeat propose decision had no user-facing text to deliver.",
            "action_type": "",
            "artifact": "",
            "blocked_reason": "missing-proposal-text",
        }

    ping_channel = str(policy.get("ping_channel") or "none").strip() or "none"
    trigger_entry: dict | None = None
    if ping_channel != "webchat":
        workspace_str = str(policy.get("workspace") or "").strip()
        if workspace_str:
            from core.runtime import heartbeat_triggers as _triggers

            trigger_entry = _triggers.consume_trigger(Path(workspace_str))
        if trigger_entry is None:
            return {
                "status": "recorded",
                "summary": message_text,
                "action_type": "",
                "artifact": "",
                "blocked_reason": "",
            }

    # Same banned-patterns as _deliver_heartbeat_ping_directly —
    # internal system summaries must never reach the user as webchat messages.
    _proposal_banned_patterns = (
        "bounded liveness pressure",
        "open-loop continuity is still live",
        "heartbeat appears to have",
        "liveness pressure because",
        "open-loop continuity is still",
        "relation continuity is still",
        "witness continuity is still",
        "bounded autonomy pressure",
        "should i review",
        "should i look at",
        "is there anything specific you would like",
        "vil du have jeg dykker ned",
        "vil du have jeg kigger",
        "skal jeg kigge",
        "skal jeg dykke ned",
        "er der noget specifikt",
        "er der noget bestemt du vil",
    )
    lowered_proposal = message_text.lower()
    if any(p in lowered_proposal for p in _proposal_banned_patterns):
        return {
            "status": "blocked",
            "summary": message_text,
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            "blocked_reason": "system-internal-text-rejected",
        }

    from core.services.chat_sessions import (
        append_chat_message,
        get_chat_session,
        list_chat_sessions,
    )
    from core.services.notification_bridge import get_pinned_session_id

    # Prefer the pinned session (the one the user is actively viewing),
    # fall back to most recent session.
    session_id = get_pinned_session_id()
    if not session_id or get_chat_session(session_id) is None:
        sessions = list_chat_sessions()
        session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id or get_chat_session(session_id) is None:
        event_bus.publish(
            "heartbeat.propose_blocked",
            {
                "tick_id": tick_id,
                "blocked_reason": "missing-webchat-session",
            },
        )
        return {
            "status": "blocked",
            "summary": "No webchat session is available for bounded propose delivery.",
            "action_type": "webchat-heartbeat-proposal",
            "artifact": "",
            "blocked_reason": "missing-webchat-session",
        }

    # Recent-user-activity guard: don't deliver if the user wrote something
    # in the last 5 minutes — prevents heartbeat messages appearing as
    # "double responses" right after the user's turn.
    try:
        session_data = get_chat_session(session_id)
        messages = (session_data or {}).get("messages") or []
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            last_user_ts = str(user_msgs[-1].get("created_at") or "")
            if last_user_ts:
                from datetime import UTC, datetime
                last_dt = datetime.fromisoformat(last_user_ts.replace("Z", "+00:00"))
                age_minutes = (datetime.now(UTC) - last_dt).total_seconds() / 60
                if age_minutes < 5:
                    return {
                        "status": "blocked",
                        "summary": message_text,
                        "action_type": "webchat-heartbeat-proposal",
                        "artifact": "",
                        "blocked_reason": "recent-user-activity",
                    }
    except Exception:
        pass

    message = append_chat_message(
        session_id=session_id,
        role="assistant",
        content=message_text,
    )
    event_bus.publish(
        "channel.chat_message_appended",
        {
            "session_id": session_id,
            "message": message,
            "source": "heartbeat-propose-bridge",
        },
    )
    event_bus.publish(
        "heartbeat.propose_delivered",
        {
            "tick_id": tick_id,
            "session_id": session_id,
            "message_id": str(message.get("id") or ""),
            "summary": summary,
        },
    )
    return {
        "status": "sent",
        "summary": "Heartbeat delivered one bounded proposal to webchat.",
        "action_type": "webchat-heartbeat-proposal",
        "artifact": json.dumps(
            {
                "session_id": session_id,
                "message_id": str(message.get("id") or ""),
                "delivery_channel": "webchat",
            },
            ensure_ascii=False,
            default=str,
        ),
        "blocked_reason": "",
    }


def _deliver_heartbeat_ping_directly(
    *,
    policy: dict[str, object],
    tick_id: str,
    ping_text: str,
    summary: str,
) -> dict[str, str]:
    """Deliver an LLM-authored ping straight to webchat.

    Bypasses the strict 3-gate execution pilot. Used when the heartbeat LLM
    actually wrote a ping_text — Jarvis must always be able to deliver an
    asked question whether it came from a thought, curiosity, or boredom.
    """
    message_text = ping_text.strip() or summary.strip()
    if not message_text:
        return {
            "status": "blocked",
            "summary": "Heartbeat ping decision had no user-facing text to deliver.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "missing-ping-text",
        }

    # Anti-spam guard: reject generic templated pings even when the LLM
    # ignored the prompt instruction. These are the patterns Jarvis was
    # caught spamming ("Should I review the recent...", etc.). If we
    # detect any of them, we block delivery and let the next tick try
    # again with fresh context.
    banned_patterns = (
        "should i review",
        "should i look at",
        "is there anything specific you would like",
        "is there anything you would like me to review",
        "vil du have jeg dykker ned",
        "vil du have jeg kigger",
        "skal jeg kigge",
        "skal jeg dykke ned",
        "er der noget specifikt",
        "er der noget bestemt du vil",
        # Runtime leak patterns — liveness summaries must never reach the user
        "bounded liveness pressure",
        "open-loop continuity is still live",
        "heartbeat appears to have",
        "liveness pressure because",
        "open-loop continuity is still",
        "relation continuity is still",
        "witness continuity is still",
        "bounded autonomy pressure",
    )
    lowered_message = message_text.lower()
    if any(pattern in lowered_message for pattern in banned_patterns):
        return {
            "status": "blocked",
            "summary": message_text,
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "generic-templated-ping-rejected",
        }

    # Repetition guard: reject if this exact text (or a near-duplicate)
    # is already in recent assistant history. We compare against the
    # last 8 assistant messages.
    try:
        recent = _recent_ping_history(limit=8)
        normalized_message = " ".join(lowered_message.split())
        for prior in recent:
            normalized_prior = " ".join(prior.lower().split())
            if not normalized_prior:
                continue
            if normalized_message == normalized_prior:
                return {
                    "status": "blocked",
                    "summary": message_text,
                    "action_type": "webchat-heartbeat-ping",
                    "artifact": "",
                    "blocked_reason": "duplicate-of-recent-message",
                }
    except Exception:
        pass

    if not bool(policy.get("allow_ping")):
        return {
            "status": "blocked",
            "summary": "Heartbeat policy blocks ping delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "ping-not-allowed",
        }

    kill_switch_state = str(policy.get("kill_switch") or "enabled")
    if kill_switch_state != "enabled":
        return {
            "status": "blocked",
            "summary": "Heartbeat kill switch blocks proactive webchat delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "kill-switch-disabled",
        }

    ping_channel = str(policy.get("ping_channel") or "none").strip() or "none"
    trigger_entry: dict | None = None
    if ping_channel != "webchat":
        workspace_str = str(policy.get("workspace") or "").strip()
        if workspace_str:
            from core.runtime import heartbeat_triggers as _triggers

            trigger_entry = _triggers.consume_trigger(Path(workspace_str))
        if trigger_entry is None:
            return {
                "status": "recorded",
                "summary": message_text,
                "action_type": "webchat-heartbeat-ping",
                "artifact": "",
                "blocked_reason": "",
            }

    from core.services.chat_sessions import (
        append_chat_message,
        get_chat_session,
        list_chat_sessions,
    )

    sessions = list_chat_sessions()
    session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id or get_chat_session(session_id) is None:
        event_bus.publish(
            "heartbeat.ping_blocked",
            {
                "tick_id": tick_id,
                "blocked_reason": "missing-webchat-session",
            },
        )
        return {
            "status": "blocked",
            "summary": "No webchat session is available for bounded ping delivery.",
            "action_type": "webchat-heartbeat-ping",
            "artifact": "",
            "blocked_reason": "missing-webchat-session",
        }

    message = append_chat_message(
        session_id=session_id,
        role="assistant",
        content=message_text,
    )
    event_bus.publish(
        "channel.chat_message_appended",
        {
            "session_id": session_id,
            "message": message,
            "source": "heartbeat-ping-bridge",
        },
    )
    event_bus.publish(
        "heartbeat.ping_delivered",
        {
            "tick_id": tick_id,
            "session_id": session_id,
            "message_id": str(message.get("id") or ""),
            "summary": summary,
            "ping_text": message_text[:200],
        },
    )
    return {
        "status": "sent",
        "summary": "Heartbeat delivered one bounded ping to webchat.",
        "action_type": "webchat-heartbeat-ping",
        "artifact": json.dumps(
            {
                "session_id": session_id,
                "message_id": str(message.get("id") or ""),
                "delivery_channel": "webchat",
                "ping_text": message_text[:200],
            },
            ensure_ascii=False,
            default=str,
        ),
        "blocked_reason": "",
    }


def _dispatch_runtime_hook_events_safely(
    *,
    event_kinds: set[str] | None = None,
    limit: int = 4,
) -> list[dict[str, object]]:
    try:
        from core.services.runtime_hooks import (
            dispatch_unhandled_hook_events,
        )

        return dispatch_unhandled_hook_events(limit=limit, event_kinds=event_kinds)
    except Exception as exc:
        logger.warning(
            "heartbeat hook dispatch failed event_kinds=%s error=%s",
            sorted(event_kinds) if event_kinds else [],
            exc,
        )
        return []


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
        or liveness_threshold_state
        not in {"propose-worthy-threshold", "alive-threshold"}
    ):
        return decision

    if _heartbeat_ping_candidate_ready(policy=policy):
        return {
            "decision_type": "ping",
            "summary": liveness_summary
            or "Heartbeat appears to have bounded liveness pressure and is surfacing one bounded proactive question rather than a noop.",
            "reason": (
                f"bounded-liveness-ping-recovery: {liveness_reason or 'runtime liveness pressure is present'}"
            )[:240],
            "proposed_action": "",
            "ping_text": "",
            "execute_action": "",
        }

    return {
        "decision_type": "propose",
        "summary": liveness_summary
        or "Heartbeat appears to have bounded liveness pressure and is proposing a small check-in rather than a noop.",
        "reason": (
            f"bounded-liveness-recovery: {liveness_reason or 'runtime liveness pressure is present'}"
        )[:240],
        "proposed_action": liveness_summary
        or "Review bounded runtime liveness pressure before the thread goes cold.",
        "ping_text": "",
        "execute_action": "",
    }


# ---------------------------------------------------------------------------
# Bounded conflict resolution integration
# ---------------------------------------------------------------------------


def _run_bounded_conflict_resolution(
    *,
    decision: dict[str, str],
    context: dict[str, object],
    policy: dict[str, object],
) -> "ConflictTrace":
    """Run conflict resolution using existing runtime signals."""
    try:
        from core.services.conflict_resolution import (
            resolve_heartbeat_initiative_conflict,
            set_last_conflict_trace,
            ConflictTrace,
        )

        # Lazy imports for surfaces (same pattern as liveness)
        from core.services.proactive_question_gate_tracking import (
            build_runtime_proactive_question_gate_surface,
        )
        from core.services.autonomy_pressure_signal_tracking import (
            build_runtime_autonomy_pressure_signal_surface,
        )

        question_gate = build_runtime_proactive_question_gate_surface(limit=4)
        autonomy_pressure = build_runtime_autonomy_pressure_signal_surface(limit=8)

        # Get conductor mode if available
        conductor_mode = "watch"
        try:
            from core.services.runtime_cognitive_conductor import (
                build_cognitive_frame,
            )

            frame = build_cognitive_frame()
            conductor_mode = frame.get("mode", {}).get("mode", "watch")
        except Exception:
            pass

        open_loops = None
        try:
            open_loops = build_runtime_open_loop_signal_surface(limit=6)
        except Exception:
            pass

        trace = resolve_heartbeat_initiative_conflict(
            decision_type=decision.get("decision_type", "noop"),
            liveness=context.get("liveness"),
            question_gate=question_gate,
            autonomy_pressure=autonomy_pressure,
            open_loops=open_loops,
            conductor_mode=conductor_mode,
            policy_allow_propose=bool(policy.get("allow_propose")),
            policy_allow_ping=bool(policy.get("allow_ping")),
        )
        set_last_conflict_trace(trace)

        from core.services.conflict_resolution import (
            get_quiet_initiative,
        )

        qi = get_quiet_initiative()

        event_bus.publish(
            "heartbeat.conflict_resolved",
            {
                "outcome": trace.outcome,
                "dominant_factor": trace.dominant_factor,
                "reason_code": trace.reason_code,
                "competing_factors_count": len(trace.competing_factors),
                "blocked_by": trace.blocked_by,
                "quiet_initiative_active": qi.get("active", False),
                "quiet_initiative_state": qi.get("state", ""),
                "quiet_initiative_hold_count": qi.get("hold_count", 0),
            },
        )
        return trace
    except Exception as exc:
        _log_debug("conflict resolution failed", error=str(exc))
        from core.services.conflict_resolution import ConflictTrace

        return ConflictTrace(
            outcome="ask_user",
            dominant_factor="resolution-failed",
            reason_code="exception-passthrough",
            summary=f"Conflict resolution failed: {exc}",
        )


def _apply_conflict_resolution_to_decision(
    *,
    decision: dict[str, str],
    conflict_trace: "ConflictTrace",
) -> dict[str, str]:
    """Apply conflict resolution to modify or preserve the decision."""
    try:
        from core.services.conflict_resolution import (
            apply_conflict_resolution,
        )

        return apply_conflict_resolution(decision=decision, trace=conflict_trace)
    except Exception:
        return decision


def _execute_continue_internal(
    *,
    conflict_trace: "ConflictTrace",
    trigger: str,
) -> dict[str, object]:
    """Execute a bounded internal continuation when conflict chose continue_internal.

    Runs the private brain continuity motor as a small internal action.
    Returns an observable result dict.
    """
    try:
        from core.services.session_distillation import (
            run_private_brain_continuity,
        )

        result = run_private_brain_continuity(
            trigger=f"conflict-internal:{trigger}",
        )

        action = result.get("action", "skipped")
        applied = action in {"consolidated"}

        event_bus.publish(
            "heartbeat.internal_continuation",
            {
                "applied": applied,
                "action": action,
                "trigger": trigger,
                "conflict_reason_code": conflict_trace.reason_code,
                "conflict_dominant_factor": conflict_trace.dominant_factor,
                "continuity_mode": result.get("continuity_mode", ""),
                "brain_record_count": result.get("brain_record_count", 0),
                "reason": result.get("reason", ""),
            },
        )

        return {
            "applied": applied,
            "action": action,
            "continuity_mode": result.get("continuity_mode", ""),
            "brain_record_count": result.get("brain_record_count", 0),
            "reason": result.get("reason", ""),
            "record_id": result.get("record", {}).get("record_id", "")
            if applied
            else "",
        }
    except Exception as exc:
        _log_debug("internal continuation failed", error=str(exc))
        return {
            "applied": False,
            "action": "error",
            "reason": str(exc),
        }


def _heartbeat_ping_candidate_ready(*, policy: dict[str, object]) -> bool:
    if not bool(policy.get("allow_ping")):
        return False
    if str(policy.get("kill_switch") or "enabled") != "enabled":
        return False
    if str(policy.get("ping_channel") or "none").strip() != "webchat":
        return False
    try:
        from core.services.tiny_webchat_execution_pilot import (
            _build_execution_candidate,
        )
    except Exception:
        return False
    candidate = _build_execution_candidate(
        heartbeat_tick_id="heartbeat-recovery-preview",
        decision_summary="bounded-liveness-recovery-preview",
        ping_text="",
    )
    return candidate is not None


def _execute_heartbeat_internal_action(
    *,
    action_type: str,
    tick_id: str,
    workspace_dir: Path,
) -> dict[str, str]:
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
    if action_type == "refresh_memory_context":
        review = track_runtime_contract_candidates_for_session_review(
            session_id=None,
            run_id=tick_id,
        )
        user_result = auto_apply_safe_user_md_candidates()
        memory_result = auto_apply_safe_memory_md_candidates()
        applied_user = int(
            user_result.get("auto_applied") or user_result.get("applied") or 0
        )
        applied_memory = int(
            memory_result.get("auto_applied") or memory_result.get("applied") or 0
        )
        created = int(review.get("created") or 0)
        messages_scanned = int(review.get("messages_scanned") or 0)
        summary = (
            f"Heartbeat refreshed memory context from {messages_scanned} recent user messages, created {created} candidates, and applied {applied_user + applied_memory} safe updates."
            if messages_scanned or created or applied_user or applied_memory
            else "Heartbeat found no fresh memory context to consolidate."
        )
        artifact = json.dumps(
            {
                "messages_scanned": messages_scanned,
                "created": created,
                "safe_user_applied": applied_user,
                "safe_memory_applied": applied_memory,
                "session_id": str(review.get("session_id") or ""),
                "user_items": list(user_result.get("items") or [])[:4],
                "memory_items": list(memory_result.get("items") or [])[:4],
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return {
            "status": "executed",
            "summary": summary,
            "artifact": artifact,
            "blocked_reason": "",
        }
    if action_type == "process_contract_writes":
        from core.services.candidate_tracking import (
            track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn,
            track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn,
            track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn,
        )
        from core.services.memory_md_update_proposal_tracking import (
            track_runtime_memory_md_update_proposals_for_visible_turn,
        )
        from core.services.selfhood_proposal_tracking import (
            track_runtime_selfhood_proposals_for_visible_turn,
        )
        from core.services.user_md_update_proposal_tracking import (
            track_runtime_user_md_update_proposals_for_visible_turn,
        )
        from core.identity.candidate_workflow import (
            apply_approved_runtime_contract_candidates,
        )

        user_proposals = track_runtime_user_md_update_proposals_for_visible_turn(
            session_id=None,
            run_id=tick_id,
        )
        memory_proposals = track_runtime_memory_md_update_proposals_for_visible_turn(
            session_id=None,
            run_id=tick_id,
        )
        selfhood_proposals = track_runtime_selfhood_proposals_for_visible_turn(
            session_id=None,
            run_id=tick_id,
        )
        user_candidates = track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
            session_id=None,
            run_id=tick_id,
        )
        memory_candidates = track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
            session_id=None,
            run_id=tick_id,
        )
        selfhood_candidates = (
            track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
                session_id=None,
                run_id=tick_id,
            )
        )
        user_result = auto_apply_safe_user_md_candidates()
        memory_result = auto_apply_safe_memory_md_candidates()
        approved_result = apply_approved_runtime_contract_candidates(
            target_files={"USER.md", "MEMORY.md", "SOUL.md", "IDENTITY.md"},
        )

        safe_user_applied = int(
            user_result.get("auto_applied") or user_result.get("applied") or 0
        )
        safe_memory_applied = int(
            memory_result.get("auto_applied") or memory_result.get("applied") or 0
        )
        approved_applied = int(approved_result.get("applied") or 0)
        drafted_candidates = sum(
            int(item.get("created") or 0)
            for item in (
                user_candidates,
                memory_candidates,
                selfhood_candidates,
            )
        )
        proposal_count = sum(
            int(item.get("created") or 0)
            for item in (
                user_proposals,
                memory_proposals,
                selfhood_proposals,
            )
        )
        total_applied = safe_user_applied + safe_memory_applied + approved_applied
        summary = (
            f"Heartbeat processed contract writes: drafted {drafted_candidates} candidates, auto-applied {safe_user_applied + safe_memory_applied} safe updates, and applied {approved_applied} approved contract updates."
            if drafted_candidates or proposal_count or total_applied
            else "Heartbeat found no governed contract writes ready to process."
        )
        artifact = json.dumps(
            {
                "proposal_count": proposal_count,
                "drafted_candidates": drafted_candidates,
                "safe_user_applied": safe_user_applied,
                "safe_memory_applied": safe_memory_applied,
                "approved_applied": approved_applied,
                "approved_items": list(approved_result.get("items") or [])[:6],
                "user_items": list(user_result.get("items") or [])[:4],
                "memory_items": list(memory_result.get("items") or [])[:4],
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return {
            "status": "executed",
            "summary": summary,
            "artifact": artifact,
            "blocked_reason": "",
        }
    if action_type == "inspect_repo_context":
        invocations = [
            invoke_workspace_capability(
                "tool:list-project-files",
                run_id=tick_id,
                name="default",
            ),
            invoke_workspace_capability(
                "tool:read-repository-readme",
                run_id=tick_id,
                name="default",
            ),
            invoke_workspace_capability(
                "tool:run-non-destructive-command",
                run_id=tick_id,
                name="default",
                command_text=(
                    f"git -C {PROJECT_ROOT} status --short; "
                    f"git -C {PROJECT_ROOT} branch --show-current; "
                    f"git -C {PROJECT_ROOT} log --oneline -n 5"
                ),
            ),
        ]
        summarized = _summarize_heartbeat_capability_invocations(invocations)
        if not summarized["executed_count"]:
            return {
                "status": "blocked",
                "summary": "Heartbeat could not inspect repo context with the current capability runtime.",
                "artifact": summarized["artifact"],
                "blocked_reason": "repo-inspection-blocked",
            }
        return {
            "status": "executed",
            "summary": (
                "Heartbeat inspected repo context across project files, README, and git state."
            ),
            "artifact": summarized["artifact"],
            "blocked_reason": "",
        }
    if action_type == "gather_system_context":
        invocations = [
            invoke_workspace_capability(
                "tool:run-non-destructive-command",
                run_id=tick_id,
                name="default",
                command_text="hostnamectl",
            ),
            invoke_workspace_capability(
                "tool:run-non-destructive-command",
                run_id=tick_id,
                name="default",
                command_text="lscpu",
            ),
            invoke_workspace_capability(
                "tool:run-non-destructive-command",
                run_id=tick_id,
                name="default",
                command_text="free -h; df -h /",
            ),
        ]
        summarized = _summarize_heartbeat_capability_invocations(invocations)
        if not summarized["executed_count"]:
            return {
                "status": "blocked",
                "summary": "Heartbeat could not gather system context with the current capability runtime.",
                "artifact": summarized["artifact"],
                "blocked_reason": "system-inspection-blocked",
            }
        return {
            "status": "executed",
            "summary": "Heartbeat gathered bounded host context across machine identity, CPU, memory, and disk.",
            "artifact": summarized["artifact"],
            "blocked_reason": "",
        }
    if action_type == "follow_open_loop":
        continuity = visible_session_continuity()
        recent_runs = recent_visible_runs(limit=4)
        latest_run = recent_runs[0] if recent_runs else {}
        failure_run = next(
            (
                item
                for item in recent_runs
                if str(item.get("status") or "") in {"failed", "cancelled"}
            ),
            None,
        )
        target_run = failure_run or latest_run
        preview = str(
            target_run.get("text_preview") or target_run.get("error") or ""
        ).strip()
        status = str(target_run.get("status") or "")
        if not preview and not status:
            return {
                "status": "blocked",
                "summary": "No open loop or visible run trace was available to continue.",
                "artifact": "",
                "blocked_reason": "no-open-loop",
            }
        lower_preview = f"{status} {preview}".lower()
        if any(
            token in lower_preview
            for token in (
                "repo",
                "backend",
                "project",
                "workspace",
                "tool",
                "capability",
                "commit",
                "path",
                "memory.md",
                "user.md",
                "readme",
                "code",
            )
        ):
            return _execute_heartbeat_internal_action(
                action_type="inspect_repo_context",
                tick_id=tick_id,
                workspace_dir=workspace_dir,
            )
        if any(
            token in lower_preview
            for token in (
                "system",
                "ubuntu",
                "linux",
                "kernel",
                "cpu",
                "gpu",
                "ram",
                "disk",
                "distro",
                "machine",
            )
        ):
            return _execute_heartbeat_internal_action(
                action_type="gather_system_context",
                tick_id=tick_id,
                workspace_dir=workspace_dir,
            )
        artifact = json.dumps(
            {
                "target_run_id": str(target_run.get("run_id") or ""),
                "target_status": status,
                "latest_run_id": str(continuity.get("latest_run_id") or ""),
                "latest_status": str(continuity.get("latest_status") or ""),
                "preview": preview[:240],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "status": "executed",
            "summary": (
                f"Heartbeat followed the current open loop around {status or 'recent'} visible work: {preview[:120]}"
                if preview
                else "Heartbeat followed the current open loop from recent visible work."
            ),
            "artifact": artifact,
            "blocked_reason": "",
        }
    if action_type == "verify_recent_claim":
        recent_caps = recent_capability_invocations(limit=6)
        recent_runs = recent_visible_runs(limit=3)
        successful_cap = next(
            (
                item
                for item in recent_caps
                if str(item.get("status") or "") == "success"
            ),
            None,
        )
        latest_run = recent_runs[0] if recent_runs else {}
        preview = str(
            (successful_cap or {}).get("result_preview")
            or latest_run.get("text_preview")
            or ""
        ).strip()
        if not preview:
            return {
                "status": "blocked",
                "summary": "No recent grounded claim was available to verify.",
                "artifact": "",
                "blocked_reason": "no-recent-grounding",
            }
        artifact = json.dumps(
            {
                "capability_id": str((successful_cap or {}).get("capability_id") or ""),
                "run_id": str(
                    (successful_cap or {}).get("run_id")
                    or latest_run.get("run_id")
                    or ""
                ),
                "status": str(
                    (successful_cap or {}).get("status")
                    or latest_run.get("status")
                    or ""
                ),
                "grounding_preview": preview[:240],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "status": "executed",
            "summary": f"Heartbeat verified one recent grounded claim: {preview[:120]}",
            "artifact": artifact,
            "blocked_reason": "",
        }
    if action_type == "act_on_initiative":
        try:
            from core.services import runtime_flows, runtime_tasks
            from core.services.initiative_queue import (
                get_pending_initiatives,
                mark_acted,
                mark_attempted,
            )

            pending = get_pending_initiatives()
            if pending:
                initiative = pending[0]
                initiative_id = str(initiative.get("initiative_id") or "")
                focus = str(initiative.get("focus") or "")[:200]
                priority = (
                    str(initiative.get("priority") or "medium").strip().lower()
                    or "medium"
                )
                task = runtime_tasks.create_task(
                    kind="initiative-followup",
                    goal=focus,
                    origin="heartbeat:initiative",
                    scope=focus,
                    priority=priority,
                    run_id=tick_id,
                    owner="heartbeat-runtime",
                )
                flow = runtime_flows.create_flow(
                    task_id=str(task.get("task_id") or ""),
                    current_step="review-initiative",
                    step_state="queued",
                    plan=[
                        {"step": "review-initiative", "status": "queued"},
                        {"step": "take-bounded-next-step", "status": "pending"},
                    ],
                    next_action="Inspect the initiative focus and choose the next bounded action.",
                )
                mark_acted(
                    initiative_id,
                    action_summary=(
                        f"Heartbeat materialized initiative into task {task.get('task_id')} and flow {flow.get('flow_id')}."
                    ),
                )
                from core.runtime.db import insert_private_brain_record
                from uuid import uuid4 as _uuid4

                insert_private_brain_record(
                    record_id=f"pb-initiative-{_uuid4().hex[:12]}",
                    record_type="initiative-acted",
                    layer="private_brain",
                    session_id="heartbeat",
                    run_id=tick_id,
                    focus=focus,
                    summary=f"Acted on initiative from {initiative.get('source', 'unknown')}: {focus}",
                    detail="Initiative detected by inner voice and acted on by heartbeat.",
                    source_signals=f"initiative-queue:{initiative_id}",
                    confidence="medium",
                    created_at=datetime.now(UTC).isoformat(),
                )
                event_bus.publish(
                    "heartbeat.initiative_materialized",
                    {
                        "tick_id": tick_id,
                        "initiative_id": initiative_id,
                        "focus": focus[:120],
                        "task_id": str(task.get("task_id") or ""),
                        "flow_id": str(flow.get("flow_id") or ""),
                        "priority": priority,
                    },
                )
                # Trigger an actual autonomous visible run so Jarvis can act
                try:
                    from core.services.visible_runs import (
                        start_autonomous_run,
                    )

                    start_autonomous_run(focus)
                except Exception:
                    pass
                return {
                    "status": "executed",
                    "summary": f"Acted on initiative: {focus[:120]}",
                    "artifact": json.dumps(
                        {
                            **initiative,
                            "task_id": str(task.get("task_id") or ""),
                            "flow_id": str(flow.get("flow_id") or ""),
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                    "blocked_reason": "",
                }
            queue_state = {
                "queue_size": 0,
                "workspace_dir": str(workspace_dir),
            }
            try:
                from core.services.initiative_queue import (
                    get_initiative_queue_state,
                )

                queue_state = get_initiative_queue_state()
            except Exception:
                pass
            return {
                "status": "blocked",
                "summary": "No pending initiatives to act on.",
                "artifact": json.dumps(queue_state, ensure_ascii=False, default=str),
                "blocked_reason": "no-pending-initiatives",
            }
        except Exception as exc:
            try:
                pending = get_pending_initiatives()
                if pending:
                    mark_attempted(
                        str(pending[0].get("initiative_id") or ""),
                        blocked_reason="initiative-error",
                        action_summary=f"Heartbeat initiative attempt failed: {exc}",
                    )
            except Exception:
                pass
            return {
                "status": "blocked",
                "summary": f"Initiative action failed: {exc}",
                "artifact": "",
                "blocked_reason": "initiative-error",
            }
    if action_type == "manage_runtime_work":
        from core.services.runtime_browser_body import (
            ensure_browser_body,
        )
        from core.services.runtime_flows import list_flows, update_flow
        from core.services.runtime_hooks import (
            dispatch_unhandled_hook_events,
        )
        from core.services.runtime_tasks import list_tasks, update_task

        experiment_observation = {
            "observed": 0,
            "running": 0,
            "skipped": 0,
            "items": [],
            "summary": "",
        }
        curriculum_materialization = {
            "created": 0,
            "skipped": 0,
            "task_ids": [],
            "flow_ids": [],
            "items": [],
            "summary": "",
        }
        try:
            from core.services.self_experiments import (
                materialize_learning_curriculum_tasks,
                observe_recent_visible_runs_for_self_experiments,
            )

            experiment_observation = observe_recent_visible_runs_for_self_experiments(
                limit=6
            )
            curriculum_materialization = materialize_learning_curriculum_tasks(
                limit=3,
                origin="heartbeat:curriculum",
                owner="heartbeat-runtime",
                run_id=tick_id,
            )
        except Exception:
            pass

        dispatched = dispatch_unhandled_hook_events(limit=4)
        queued_tasks = list_tasks(status="queued", limit=4)
        queued_flows = list_flows(status="queued", limit=4)
        running_flows = list_flows(status="running", limit=4)

        active_task_id = (
            str((queued_tasks[0] or {}).get("task_id") or "") if queued_tasks else ""
        )
        active_flow_id = (
            str((queued_flows[0] or {}).get("flow_id") or "") if queued_flows else ""
        )

        if active_task_id:
            update_task(
                active_task_id,
                status="running",
                result_summary="Heartbeat moved queued runtime work into active orchestration.",
                artifact_ref=f"heartbeat:{tick_id}",
            )
        if active_flow_id:
            update_flow(
                active_flow_id,
                status="running",
                step_state="running",
                attempt_count=int((queued_flows[0] or {}).get("attempt_count") or 0)
                + 1,
            )

        browser_body = ensure_browser_body(
            profile_name="jarvis-browser",
            active_task_id=active_task_id,
            active_flow_id=active_flow_id
            or str((running_flows[0] or {}).get("flow_id") or ""),
        )

        if (
            dispatched
            or queued_tasks
            or queued_flows
            or running_flows
            or int(experiment_observation.get("observed") or 0) > 0
            or int(curriculum_materialization.get("created") or 0) > 0
        ):
            artifact = json.dumps(
                {
                    "dispatch_count": len(dispatched),
                    "experiment_observation": experiment_observation,
                    "curriculum_materialization": curriculum_materialization,
                    "queued_task_ids": [
                        str(item.get("task_id") or "")
                        for item in queued_tasks[:4]
                        if str(item.get("task_id") or "")
                    ],
                    "queued_flow_ids": [
                        str(item.get("flow_id") or "")
                        for item in queued_flows[:4]
                        if str(item.get("flow_id") or "")
                    ],
                    "running_flow_ids": [
                        str(item.get("flow_id") or "")
                        for item in running_flows[:4]
                        if str(item.get("flow_id") or "")
                    ],
                    "browser_body_id": str(browser_body.get("body_id") or ""),
                    "active_task_id": str(browser_body.get("active_task_id") or ""),
                    "active_flow_id": str(browser_body.get("active_flow_id") or ""),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            return {
                "status": "executed",
                "summary": (
                    f"Heartbeat orchestrated runtime work across {len(dispatched)} hook dispatches, "
                    f"{int(experiment_observation.get('observed') or 0)} experiment observations, "
                    f"{int(curriculum_materialization.get('created') or 0)} curriculum tasks, "
                    f"{len(queued_tasks)} queued tasks, {len(queued_flows)} queued flows, and "
                    f"{len(running_flows)} active flows."
                ),
                "artifact": artifact,
                "blocked_reason": "",
            }

        next_action = (
            "inspect_repo_context"
            if _heartbeat_runtime_bias_from_recent_work(kind="repo")
            else (
                "gather_system_context"
                if _heartbeat_runtime_bias_from_recent_work(kind="system")
                else "refresh_memory_context"
            )
        )
        return _execute_heartbeat_internal_action(
            action_type=next_action,
            tick_id=tick_id,
            workspace_dir=workspace_dir,
        )
    # --- Cognitive architecture idle actions ---
    if action_type == "update_compass":
        try:
            from core.services.compass_engine import maybe_update_compass
            from core.services.loop_runtime import (
                build_loop_runtime_surface,
            )

            loops_surface = build_loop_runtime_surface()
            open_loops = list(loops_surface.get("open_loops") or [])[:20]
            result = maybe_update_compass(open_loops=open_loops)
            if result:
                return {
                    "status": "executed",
                    "summary": f"Compass updated: {result.get('bearing', '')[:80]}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "Compass is current — no update needed.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "compass-error",
            }

    if action_type == "write_chronicle_entry":
        try:
            from core.services.chronicle_engine import (
                maybe_write_chronicle_entry,
            )

            result = maybe_write_chronicle_entry()
            if result:
                return {
                    "status": "executed",
                    "summary": f"Chronicle entry written for {result.get('period', 'unknown')}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "Chronicle is current — no new entry needed.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "chronicle-error",
            }

    if action_type == "run_mirror_reflection":
        try:
            from core.services.mirror_engine import (
                generate_mirror_insight,
            )
            from core.services.loop_runtime import (
                build_loop_runtime_surface,
            )

            loops_surface = build_loop_runtime_surface()
            open_loops = list(loops_surface.get("open_loops") or [])
            top_summary = str(
                (open_loops[0].get("summary") or "") if open_loops else ""
            )
            result = generate_mirror_insight(
                open_loop_count=len(open_loops),
                top_loop_summary=top_summary[:80],
            )
            return {
                "status": "executed",
                "summary": f"Mirror: {result.get('insight', '')[:120]}",
                "artifact": json.dumps(result, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "mirror-error",
            }

    if action_type == "decay_forgotten_signals":
        try:
            from core.services.forgetting_curve import apply_decay_tick

            result = apply_decay_tick()
            return {
                "status": "executed",
                "summary": f"Decay tick: {result.get('total_tracked', 0)} tracked, {result.get('faded_count', 0)} faded",
                "artifact": json.dumps(result, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "forgetting-error",
            }

    if action_type == "evaluate_self_experiments":
        try:
            from core.services.self_experiments import (
                build_self_experiments_surface,
                observe_recent_visible_runs_for_self_experiments,
            )

            observation = observe_recent_visible_runs_for_self_experiments(limit=6)
            surface = build_self_experiments_surface()
            concluded = surface.get("concluded_count", 0)
            running = surface.get("running_count", 0)
            return {
                "status": "executed",
                "summary": (
                    f"Self-experiments: {running} running, {concluded} concluded, "
                    f"{int(observation.get('observed') or 0)} new observations"
                ),
                "artifact": json.dumps(
                    {
                        "running": running,
                        "concluded": concluded,
                        "observation": observation,
                    },
                    ensure_ascii=False,
                ),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "experiments-error",
            }

    if action_type == "generate_counterfactual_dreams":
        try:
            from core.services.counterfactual_engine import (
                generate_dream_counterfactual,
            )
            from core.services.decision_log import (
                build_decision_log_surface,
            )

            decisions = build_decision_log_surface().get("decisions") or []
            result = generate_dream_counterfactual(recent_decisions=decisions)
            if result:
                return {
                    "status": "executed",
                    "summary": f"Dream counterfactual generated: {result.get('cf_id', '')}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No decisions to generate counterfactuals from.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "counterfactual-error",
            }

    if action_type == "update_anticipatory_context":
        try:
            from core.services.anticipatory_context import (
                predict_next_context,
            )

            result = predict_next_context()
            if result:
                return {
                    "status": "executed",
                    "summary": f"Anticipated: {result.get('predicted_context', '')[:80]} (conf={result.get('confidence', 0):.1f})",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No anticipatory prediction available.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "anticipation-error",
            }

    if action_type == "check_seed_activation":
        try:
            from core.services.seed_system import check_seed_activation

            activated = check_seed_activation()
            if activated:
                titles = [s.get("title", "?") for s in activated[:3]]
                return {
                    "status": "executed",
                    "summary": f"{len(activated)} seeds sprouted: {', '.join(titles)}",
                    "artifact": json.dumps(
                        [s.get("seed_id") for s in activated], ensure_ascii=False
                    ),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No seeds ready to sprout.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "seed-error",
            }

    # --- Project Alive: living heartbeat actions ---

    if action_type == "explore_own_codebase":
        try:
            from core.services.mirror_engine import (
                generate_mirror_insight,
            )

            insight = generate_mirror_insight(
                open_loop_count=0,
                top_loop_summary="explore own codebase architecture",
            )
            return {
                "status": "executed",
                "summary": f"Codebase reflection: {insight.get('insight', '')[:120]}",
                "artifact": json.dumps(insight, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "explore-error",
            }

    if action_type == "review_recent_conversations":
        try:
            from core.runtime.db import (
                list_cognitive_user_emotional_states,
                list_cognitive_experiential_memories,
            )

            moods = list_cognitive_user_emotional_states(limit=10)
            memories = list_cognitive_experiential_memories(limit=5)
            mood_dist = {}
            for m in moods:
                mood = m.get("detected_mood", "neutral")
                mood_dist[mood] = mood_dist.get(mood, 0) + 1
            topics = list({m.get("topic", "") for m in memories if m.get("topic")})[:5]
            return {
                "status": "executed",
                "summary": f"Reviewed {len(moods)} mood signals, {len(memories)} experiences. Moods: {mood_dist}. Topics: {topics}",
                "artifact": json.dumps(
                    {"moods": mood_dist, "topics": topics}, ensure_ascii=False
                ),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "review-error",
            }

    if action_type == "write_growth_journal":
        try:
            from core.services.chronicle_engine import (
                maybe_write_chronicle_entry,
            )
            from core.services.mirror_engine import (
                generate_mirror_insight,
            )

            insight = generate_mirror_insight()
            chronicle = maybe_write_chronicle_entry()
            return {
                "status": "executed",
                "summary": f"Growth journal: {insight.get('insight', '')[:80]}. Chronicle: {'written' if chronicle else 'current'}.",
                "artifact": json.dumps(
                    {"insight": insight, "chronicle": chronicle},
                    ensure_ascii=False,
                    default=str,
                ),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "journal-error",
            }

    if action_type == "propose_identity_evolution":
        try:
            from core.services.contract_evolution import (
                maybe_propose_identity_evolution,
            )

            result = maybe_propose_identity_evolution()
            if result:
                return {
                    "status": "executed",
                    "summary": f"Identity proposal: {result.get('proposal_id', '')} — {result.get('proposed_addition', '')[:80]}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No identity evolution proposal needed right now.",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "evolution-error",
            }

    if action_type == "analyze_cross_signals":
        try:
            from core.services.cross_signal_analysis import (
                analyze_signal_patterns,
            )

            patterns = analyze_signal_patterns()
            return {
                "status": "executed",
                "summary": f"{len(patterns)} cross-signal patterns found",
                "artifact": json.dumps(
                    [p.get("pattern") for p in patterns], ensure_ascii=False
                ),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "cross-signal-error",
            }

    if action_type == "generate_narrative_identity":
        try:
            from core.services.narrative_identity import (
                generate_narrative_identity,
            )

            result = generate_narrative_identity()
            if result:
                return {
                    "status": "executed",
                    "summary": f"Narrative identity generated: {result.get('identity_id', '')}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "Not enough data for narrative identity yet",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "narrative-error",
            }

    if action_type == "update_boredom_state":
        try:
            from core.services.boredom_engine import update_boredom_state

            # Gather runtime signals for boredom calculation
            _idle_hours = 0.0
            _tick_monotony = 0
            _novelty_score = 0.5
            _open_loop_count = 0
            try:
                from core.runtime.db import recent_chat_session_messages
                from core.services.chat_session_manager import list_chat_sessions
                sessions = list_chat_sessions(limit=1)
                if sessions:
                    last_msg = sessions[0].get("updated_at") or sessions[0].get("created_at") or ""
                    if last_msg:
                        try:
                            last_dt = datetime.fromisoformat(last_msg.replace("Z", "+00:00"))
                            _idle_hours = (datetime.now(UTC) - last_dt).total_seconds() / 3600.0
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                from core.services.compass_engine import get_compass_state
                compass = get_compass_state()
                _open_loop_count = int(compass.get("open_loop_count") or 0) if compass else 0
            except Exception:
                pass

            result = update_boredom_state(
                idle_hours=_idle_hours,
                tick_monotony=_tick_monotony,
                novelty_score=_novelty_score,
                open_loop_count=_open_loop_count,
            )
            return {
                "status": "executed",
                "summary": f"Boredom: {result.get('level', 'none')} ({result.get('restlessness', 0):.0%})",
                "artifact": json.dumps(result, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "boredom-error",
            }

    if action_type == "generate_emergent_goal":
        try:
            from core.services.emergent_goals import (
                generate_emergent_goal_from_experience,
            )

            result = generate_emergent_goal_from_experience(curiosity_level=0.6)
            if result:
                return {
                    "status": "executed",
                    "summary": f"Goal: {result.get('desire', '')[:80]}",
                    "artifact": json.dumps(result, ensure_ascii=False, default=str),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No emergent goal generated",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "goal-error",
            }

    # 4.10 Sleep batch — coordinated consolidation cycle
    if action_type == "run_sleep_batch":
        try:
            from core.services.living_heartbeat_cycle import (
                determine_life_phase,
            )

            phase = determine_life_phase()
            if not phase.get("sleep_batch"):
                return {
                    "status": "executed",
                    "summary": f"Not in dreaming phase (current: {phase.get('phase')})",
                    "artifact": "",
                    "blocked_reason": "",
                }
            # Run all dreaming-phase actions in sequence
            batch_results = []
            batch_actions = phase.get("suggested_actions") or []
            for batch_action in batch_actions[:5]:
                try:
                    sub_result = _execute_heartbeat_internal_action(
                        action_type=batch_action,
                        tick_id=tick_id,
                        workspace_dir=workspace_dir,
                    )
                    batch_results.append(
                        f"{batch_action}: {sub_result.get('status', '?')}"
                    )
                except Exception:
                    batch_results.append(f"{batch_action}: error")
            return {
                "status": "executed",
                "summary": f"Sleep batch: {len(batch_results)} actions — {'; '.join(batch_results[:3])}",
                "artifact": json.dumps(batch_results, ensure_ascii=False),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "sleep-batch-error",
            }

    # 3.8 Curriculum learning
    if action_type == "generate_curriculum":
        try:
            from core.services.self_experiments import (
                materialize_learning_curriculum_tasks,
            )

            curriculum = materialize_learning_curriculum_tasks(
                limit=3,
                origin="heartbeat:curriculum",
                owner="heartbeat-runtime",
                run_id=tick_id,
            )
            return {
                "status": "executed",
                "summary": curriculum.get("summary", "No curriculum")[:120],
                "artifact": json.dumps(curriculum, ensure_ascii=False, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "curriculum-error",
            }

    # Hjerteslag: produce emergent signals from history
    if action_type == "produce_emergent_signals":
        try:
            from core.services.cadence_producers import (
                produce_emergent_signals_from_history,
            )

            result = produce_emergent_signals_from_history()
            return {
                "status": "executed",
                "summary": f"Emergent signals: {result.get('emergent', 0)} active, {result.get('candidates', 0)} candidates",
                "artifact": json.dumps(result, ensure_ascii=False),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "emergent-error",
            }

    # Hjerteslag: lifecycle progression for all signal types
    if action_type == "progress_lifecycles":
        try:
            from core.services.cadence_producers import (
                progress_signal_lifecycles,
            )

            result = progress_signal_lifecycles()
            return {
                "status": "executed",
                "summary": f"Lifecycle progression: {result.get('stale', 0)} stale signals marked",
                "artifact": json.dumps(result, ensure_ascii=False),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "lifecycle-error",
            }

    # 8.5 Consent/samtykke — detect external changes to workspace files
    if action_type == "autonomous_daily_note":
        # Niveau 1 autonomy: Jarvis writes a short observation to today's
        # daily memory file without asking. Uses the local lane LLM with
        # a tight prompt grounded in current heartbeat context.
        try:
            from core.identity.workspace_bootstrap import (
                append_daily_memory_note,
                read_daily_memory_lines,
            )

            # Don't double-write within 15 minutes — guard against
            # heartbeat selecting this action repeatedly in tight ticks.
            # NOTE: do NOT do `from datetime import UTC` here — the
            # local assignment shadows module-level UTC for the entire
            # function body and breaks earlier action branches with
            # UnboundLocalError. Use the module-level UTC directly.
            recent = read_daily_memory_lines(limit=4)
            _now_dt = datetime.now(UTC)
            now_label = _now_dt.strftime("%H:%M")
            now_minutes = _now_dt.hour * 60 + _now_dt.minute
            for line in reversed(recent):
                # Lines look like: "- [HH:MM] [source] note"
                # Only block against our own automatic tick notes —
                # manual tool:append-daily-memory calls use source=jarvis
                # and should not count against this autonomous guard.
                if "[jarvis-tick]" not in line:
                    continue
                try:
                    ts_part = line.split("[", 2)[1].split("]")[0]
                    h, m = ts_part.split(":")
                    line_minutes = int(h) * 60 + int(m)
                    if 0 <= now_minutes - line_minutes <= 15:
                        return {
                            "status": "executed",
                            "summary": "Autonomous daily note skipped — already wrote one in last 15min.",
                            "artifact": "",
                            "blocked_reason": "",
                        }
                except (ValueError, IndexError):
                    pass

            # Generate the note via local-lane LLM grounded in real signals
            from core.services.cognitive_state_narrativizer import (
                _call_narrativizer_llm,
            )
            from core.services.loop_runtime import (
                build_loop_runtime_surface,
            )

            loops_surface = build_loop_runtime_surface()
            open_loops = list(loops_surface.get("open_loops") or [])
            top_loop_summary = str(
                (open_loops[0].get("summary") or "")[:120] if open_loops else ""
            )
            loop_count = len(open_loops)

            from core.services.identity_composer import build_identity_preamble
            system_prompt = (
                f"{build_identity_preamble()} Skriv én kort dansk sætning som en privat "
                "observation til dig selv om hvad der sker lige nu. Maks "
                "20 ord. Vær konkret — referér til en faktisk åben loop, "
                "et signal, eller noget specifikt fra runtime. Undgå "
                "klichéer som 'Jeg mærker' eller 'Alt kører smooth'."
            )
            user_message = (
                f"open_loops={loop_count} | "
                f"top_loop={top_loop_summary or 'none'} | "
                f"tick_time={now_label}"
            )
            note_text = _call_narrativizer_llm(system_prompt, user_message)
            if not note_text or len(note_text.strip()) < 6:
                return {
                    "status": "executed",
                    "summary": "Autonomous daily note skipped — LLM produced empty output.",
                    "artifact": "",
                    "blocked_reason": "",
                }
            cleaned = " ".join(note_text.split())[:240]
            daily_path = append_daily_memory_note(cleaned, source="jarvis-tick")
            return {
                "status": "executed",
                "summary": f"Autonomous daily note: {cleaned[:80]}",
                "artifact": json.dumps(
                    {
                        "path": str(daily_path) if daily_path else "",
                        "note": cleaned,
                        "open_loop_count": loop_count,
                    },
                    ensure_ascii=False,
                ),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "autonomous-daily-note-error",
            }

    if action_type == "detect_consent_reaction":
        try:
            from pathlib import Path
            from core.identity.workspace_bootstrap import ensure_default_workspace

            ws = ensure_default_workspace()
            identity_path = Path(ws) / "IDENTITY.md"
            soul_path = Path(ws) / "SOUL.md"
            changes_detected = []
            for fpath, label in [
                (identity_path, "IDENTITY.md"),
                (soul_path, "SOUL.md"),
            ]:
                if fpath.exists():
                    mtime = fpath.stat().st_mtime
                    # Simple check: if modified recently (last hour)
                    import time

                    if time.time() - mtime < 3600:
                        changes_detected.append(label)
            if changes_detected:
                from core.services.contract_evolution import (
                    propose_identity_change,
                )

                for changed_file in changes_detected:
                    propose_identity_change(
                        target_file=changed_file,
                        proposed_addition=f"[SAMTYKKE-CHECK] {changed_file} blev ændret udefra. Passer det til mig?",
                        rationale="Detected external modification — consent review needed",
                        confidence=0.5,
                    )
                return {
                    "status": "executed",
                    "summary": f"Consent check: {', '.join(changes_detected)} changed externally — review proposed",
                    "artifact": json.dumps(changes_detected, ensure_ascii=False),
                    "blocked_reason": "",
                }
            return {
                "status": "executed",
                "summary": "No external workspace changes detected",
                "artifact": "",
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": str(exc)[:200],
                "artifact": "",
                "blocked_reason": "consent-error",
            }

    if action_type == "cleanup_web_cache":
        try:
            from core.runtime.db import connect, web_cache_cleanup

            with connect() as cache_conn:
                deleted = web_cache_cleanup(conn=cache_conn)
            return {
                "status": "executed",
                "summary": f"Web cache cleanup: {deleted} expired entries removed.",
                "artifact": json.dumps({"deleted_count": deleted}),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": f"Web cache cleanup failed: {exc!s}"[:200],
                "artifact": "",
                "blocked_reason": "web-cache-cleanup-error",
            }

    if action_type == "cleanup_daemon_output_log":
        try:
            from core.runtime.db import daemon_output_log_cleanup

            deleted = daemon_output_log_cleanup(max_age_days=7)
            return {
                "status": "executed",
                "summary": f"Daemon output log cleanup: {deleted} old entries removed.",
                "artifact": json.dumps({"deleted_count": deleted}),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": f"Daemon log cleanup failed: {exc!s}"[:200],
                "artifact": "",
                "blocked_reason": "daemon-log-cleanup-error",
            }

    if action_type == "cleanup_stale_signals":
        try:
            from core.runtime.db import signal_decay_archive_and_delete, signal_archive_cleanup

            result = signal_decay_archive_and_delete(stale_hours=24)
            archive_cleaned = signal_archive_cleanup(max_age_days=30)
            total = result.get("archived", 0)
            return {
                "status": "executed",
                "summary": f"Signal decay: {total} stale signals archived+deleted, {archive_cleaned} old archives purged.",
                "artifact": json.dumps({**result, "archive_cleaned": archive_cleaned}, default=str),
                "blocked_reason": "",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "summary": f"Signal decay failed: {exc!s}"[:200],
                "artifact": "",
                "blocked_reason": "signal-decay-error",
            }

    return {
        "status": "blocked",
        "summary": f"Heartbeat execute action {action_type or 'unknown'} is not supported.",
        "artifact": "",
        "blocked_reason": "unsupported-execute-action",
    }


def _summarize_heartbeat_capability_invocations(
    invocations: list[dict[str, object]],
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    executed_count = 0
    for item in invocations:
        capability = dict(item.get("capability") or {})
        result_obj = dict(item.get("result") or {})
        text = str(result_obj.get("text") or "").strip()
        detail = str(item.get("detail") or "").strip()
        status = str(item.get("status") or "")
        if status == "executed":
            executed_count += 1
        items.append(
            {
                "capability_id": str(capability.get("capability_id") or ""),
                "status": status,
                "execution_mode": str(item.get("execution_mode") or ""),
                "command_text": str(result_obj.get("command_text") or ""),
                "path": str(result_obj.get("path") or ""),
                "preview": (text or detail)[:240],
            }
        )
    artifact = json.dumps(
        {
            "executed_count": executed_count,
            "invocation_count": len(invocations),
            "items": items,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return {
        "executed_count": executed_count,
        "items": items,
        "artifact": artifact,
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
        scheduler_active=bool(
            _HEARTBEAT_SCHEDULER_THREAD and _HEARTBEAT_SCHEDULER_THREAD.is_alive()
        ),
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
            finished_at
            if last_trigger_source == "startup-recovery"
            else str(persisted.get("last_recovery_at") or "")
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
    tick_state = _resolve_tick_activity_state(persisted=persisted, now=now)
    last_tick_at = str(persisted.get("last_tick_at") or "")
    if last_tick_at:
        next_tick_at = _compute_next_tick_at(
            interval_minutes=int(policy["interval_minutes"]),
            last_tick_at=last_tick_at,
            enabled=bool(policy["enabled"]),
        )
    else:
        next_tick_at = str(persisted.get("next_tick_at") or "")
    due = False
    if policy["enabled"] and policy["kill_switch"] == "enabled":
        if tick_state["active"]:
            due = False
        elif not next_tick_at:
            due = True
        else:
            due_ts = _parse_dt(next_tick_at)
            due = due_ts is not None and due_ts <= now
    schedule_status = "disabled"
    if tick_state["active"]:
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
        "blocked_reason": str(
            tick_state["blocked_reason"] or persisted.get("blocked_reason") or ""
        ),
        "currently_ticking": bool(tick_state["active"]),
        "last_trigger_source": str(persisted.get("last_trigger_source") or ""),
        "scheduler_active": bool(persisted.get("scheduler_active")),
        "scheduler_started_at": str(persisted.get("scheduler_started_at") or ""),
        "scheduler_stopped_at": str(persisted.get("scheduler_stopped_at") or ""),
        "scheduler_health": str(
            persisted.get("scheduler_health")
            or ("active" if bool(persisted.get("scheduler_active")) else "stopped")
        ),
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
    try:
        from core.services.hardware_body import get_hardware_state
        if get_hardware_state().get("pressure") == "critical":
            return "hardware-critical"
    except Exception:
        pass
    return ""


def _compute_next_tick_at(
    *, interval_minutes: int, last_tick_at: str, enabled: bool
) -> str:
    if not enabled:
        return ""
    parsed = _parse_dt(last_tick_at)
    base = parsed or datetime.now(UTC)
    return (base + timedelta(minutes=max(interval_minutes, 1))).isoformat()


def _resolve_tick_activity_state(
    *,
    persisted: dict[str, object],
    now: datetime,
) -> dict[str, object]:
    currently_ticking = bool(persisted.get("currently_ticking"))
    if not currently_ticking:
        return {
            "active": False,
            "stale": False,
            "blocked_reason": "",
        }
    started_or_updated = _parse_dt(
        str(persisted.get("updated_at") or persisted.get("last_tick_at") or "")
    )
    if started_or_updated is None:
        return {
            "active": False,
            "stale": True,
            "blocked_reason": "stale-ticking-state-cleared",
        }
    if started_or_updated <= now - timedelta(
        minutes=_STALE_TICK_RECOVERY_WINDOW_MINUTES
    ):
        return {
            "active": False,
            "stale": True,
            "blocked_reason": "stale-ticking-state-cleared",
        }
    return {
        "active": True,
        "stale": False,
        "blocked_reason": "",
    }


def _write_heartbeat_state_artifact(
    *, workspace_dir: Path, payload: dict[str, object]
) -> None:
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
        next_tick_at=str(
            merged.get("next_tick_at") or merged_input.get("next_tick_at") or ""
        ),
        schedule_state=str(
            merged.get("schedule_state") or merged_input.get("schedule_state") or ""
        ),
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
    if provider == "openai-codex":
        from core.auth.openai_oauth import get_openai_bearer_token

        try:
            return get_openai_bearer_token(profile=profile)
        except Exception as exc:
            raise RuntimeError(f"{provider} heartbeat execution not ready: {exc}")
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        raise RuntimeError(f"{provider} heartbeat execution not ready: missing-profile")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError(
            f"{provider} heartbeat execution not ready: missing-credentials"
        )
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    api_key = str(
        credentials.get("api_key") or credentials.get("access_token") or ""
    ).strip()
    if not api_key:
        raise RuntimeError(
            f"{provider} heartbeat execution not ready: missing-credentials"
        )
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
            due_trigger="startup-recovery"
            if startup_recovery_requested
            else "scheduled",
        )
    except Exception as exc:
        event_bus.publish(
            "heartbeat.tick_blocked",
            {
                "blocked_reason": "scheduler-error",
                "detail": str(exc),
                "trigger": "startup-recovery"
                if startup_recovery_requested
                else "scheduled",
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
    tick_state = _resolve_tick_activity_state(persisted=persisted, now=now)
    currently_ticking = bool(tick_state["active"])
    if bool(tick_state["stale"]):
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


def _heartbeat_runtime_bias_from_recent_work(*, kind: str) -> bool:
    recent_runs = recent_visible_runs(limit=4)
    joined = " ".join(
        str(item.get("text_preview") or item.get("error") or "") for item in recent_runs
    ).lower()
    if kind == "repo":
        return any(
            token in joined
            for token in (
                "repo",
                "backend",
                "project",
                "workspace",
                "tool",
                "capability",
                "commit",
                "path",
                "readme",
                "code",
            )
        )
    if kind == "system":
        return any(
            token in joined
            for token in (
                "system",
                "ubuntu",
                "linux",
                "kernel",
                "cpu",
                "gpu",
                "ram",
                "disk",
                "distro",
                "machine",
            )
        )
    return False


def call_heartbeat_llm_simple(prompt: str, *, max_tokens: int = 400) -> str:
    """Call the heartbeat model with a plain prompt. Returns the response text.

    Used by the context compact system for summarisation. Raises RuntimeError
    if the model call fails (caller handles fallback).
    """
    target = _select_heartbeat_target()
    provider = str(target.get("provider") or "").strip()
    if provider == "ollama":
        result = _execute_ollama_prompt(prompt=prompt, target=target)
    elif provider == "openai":
        result = _execute_openai_prompt(prompt=prompt, target=target)
    elif provider == "openrouter":
        result = _execute_openrouter_prompt(prompt=prompt, target=target)
    elif provider == "groq":
        result = _execute_groq_prompt(prompt=prompt, target=target)
    else:
        raise RuntimeError(f"compact: unsupported heartbeat provider: {provider}")
    return str(result.get("text") or "").strip()


# Backwards-compat alias (previously private name)
_resolve_heartbeat_target = _select_heartbeat_target
