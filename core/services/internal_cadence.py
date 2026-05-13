"""Internal cadence layer for non-visible inner producers.

Heartbeat remains the driver (motor).
This layer provides shared cadence evaluation and dispatch
for non-visible inner producers (witness daemon, inner voice daemon,
brain continuity motor).

Each producer is registered with:
- name: unique identifier
- cooldown_minutes: minimum interval between runs
- visible_grace_minutes: don't run if visible activity was this recent
- run_fn: callable that returns a result dict
- priority: lower = runs first within a tick
- depends_on: optional list of producer names that must run first

On each heartbeat tick, the cadence layer:
1. Finds the last visible activity timestamp
2. Evaluates each producer: due / cooling_down / visible_grace / blocked
3. Dispatches due producers in priority order
4. Returns observable cadence state

Design constraints:
- No scheduling of its own — heartbeat calls us
- No prompt/policy logic — pure cadence/orchestration
- Deterministic evaluation
- Observable in Mission Control
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Callable, Optional

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# Standalone scheduler — decoupled from heartbeat (2026-05-13).
# Cadence used to run inside heartbeat tick. Heartbeat blocked during
# active-chat-gate → cadence skipped → cache-warmer never fired →
# visible-chat assembly went cold every 3 min. Now runs in its own
# daemon thread, independent of heartbeat schedule.
_SCHEDULER_THREAD: Optional[threading.Thread] = None
_SCHEDULER_STOP = threading.Event()
_SCHEDULER_INTERVAL_S = 60  # tick once per minute; producers self-cool


# ---------------------------------------------------------------------------
# Producer registration
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProducerSpec:
    name: str
    cooldown_minutes: float
    visible_grace_minutes: float
    run_fn: Callable[..., dict[str, object]]
    priority: int = 10
    depends_on: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProducerTickResult:
    name: str
    status: str  # "ran" | "cooling_down" | "visible_grace" | "blocked" | "error" | "skipped"
    reason: str
    result: dict[str, object] | None = None


# Module-level state
_producers: dict[str, ProducerSpec] = {}
_last_run_at: dict[str, str] = {}
_last_tick_at: str = ""
_last_tick_results: list[ProducerTickResult] = []


def register_producer(spec: ProducerSpec) -> None:
    """Register a non-visible inner producer with the cadence layer."""
    _producers[spec.name] = spec


def deregister_producer(name: str) -> None:
    """Remove a producer from the cadence layer."""
    _producers.pop(name, None)


# ---------------------------------------------------------------------------
# Cadence evaluation (pure, deterministic)
# ---------------------------------------------------------------------------

def _evaluate_producer(
    spec: ProducerSpec,
    *,
    now: datetime,
    last_visible_at: datetime | None,
    ran_this_tick: set[str],
) -> tuple[str, str]:
    """Evaluate whether a producer is due.

    Returns (status, reason).
    """
    # Check dependencies
    for dep in spec.depends_on:
        if dep not in ran_this_tick:
            return "blocked", f"dependency-not-met:{dep}"

    # Cooldown check
    last_run_iso = _last_run_at.get(spec.name)
    if last_run_iso:
        try:
            last_run = datetime.fromisoformat(last_run_iso)
            elapsed = (now - last_run).total_seconds() / 60
            if elapsed < spec.cooldown_minutes:
                return "cooling_down", f"cooldown:{elapsed:.0f}m<{spec.cooldown_minutes:.0f}m"
        except (ValueError, TypeError):
            pass

    # Visible grace check
    if last_visible_at and spec.visible_grace_minutes > 0:
        visible_elapsed = (now - last_visible_at).total_seconds() / 60
        if visible_elapsed < spec.visible_grace_minutes:
            return "visible_grace", f"visible-too-recent:{visible_elapsed:.0f}m<{spec.visible_grace_minutes:.0f}m"

    return "due", "cadence-clear"


# ---------------------------------------------------------------------------
# Tick dispatch
# ---------------------------------------------------------------------------

def run_cadence_tick(
    *,
    trigger: str = "heartbeat",
    last_visible_at_iso: str = "",
) -> dict[str, object]:
    """Run one cadence tick: evaluate and dispatch all registered producers.

    Called by heartbeat after its own tick completes.
    Returns observable cadence state.
    """
    global _last_tick_at, _last_tick_results

    now = datetime.now(UTC)
    now_iso = now.isoformat()

    last_visible_at: datetime | None = None
    if last_visible_at_iso:
        try:
            last_visible_at = datetime.fromisoformat(last_visible_at_iso)
        except (ValueError, TypeError):
            pass

    # Sort producers by priority (lower first)
    ordered = sorted(_producers.values(), key=lambda p: p.priority)

    results: list[ProducerTickResult] = []
    ran_this_tick: set[str] = set()
    due_names: list[str] = []
    blocked_names: list[str] = []
    cooling_names: list[str] = []
    grace_names: list[str] = []
    ran_names: list[str] = []
    error_names: list[str] = []

    for spec in ordered:
        status, reason = _evaluate_producer(
            spec,
            now=now,
            last_visible_at=last_visible_at,
            ran_this_tick=ran_this_tick,
        )

        if status == "due":
            due_names.append(spec.name)
            # Dispatch
            try:
                result = spec.run_fn(trigger=trigger, last_visible_at=last_visible_at_iso)
                ran_this_tick.add(spec.name)
                _last_run_at[spec.name] = now_iso
                ran_names.append(spec.name)
                results.append(ProducerTickResult(
                    name=spec.name,
                    status="ran",
                    reason="cadence-dispatched",
                    result=result,
                ))
                # Mirror to daemon_manager so Mission Control sees the timestamp
                try:
                    from core.services import daemon_manager as _dm
                    if spec.name in _dm.get_daemon_names():
                        _dm.record_daemon_tick(spec.name, result if isinstance(result, dict) else {})
                except Exception:
                    pass
            except Exception as exc:
                error_names.append(spec.name)
                logger.warning("cadence producer %s failed: %s", spec.name, exc)
                results.append(ProducerTickResult(
                    name=spec.name,
                    status="error",
                    reason=f"dispatch-error:{type(exc).__name__}",
                ))
        elif status == "cooling_down":
            cooling_names.append(spec.name)
            results.append(ProducerTickResult(
                name=spec.name, status=status, reason=reason,
            ))
        elif status == "visible_grace":
            grace_names.append(spec.name)
            results.append(ProducerTickResult(
                name=spec.name, status=status, reason=reason,
            ))
        elif status == "blocked":
            blocked_names.append(spec.name)
            results.append(ProducerTickResult(
                name=spec.name, status=status, reason=reason,
            ))
        else:
            results.append(ProducerTickResult(
                name=spec.name, status="skipped", reason=reason,
            ))

    _last_tick_at = now_iso
    _last_tick_results = results

    # Observability event
    event_bus.publish(
        "heartbeat.cadence_tick",
        {
            "trigger": trigger,
            "tick_at": now_iso,
            "producer_count": len(ordered),
            "due": due_names,
            "ran": ran_names,
            "cooling_down": cooling_names,
            "visible_grace": grace_names,
            "blocked": blocked_names,
            "errors": error_names,
        },
    )

    return {
        "tick_at": now_iso,
        "trigger": trigger,
        "producer_count": len(ordered),
        "due": due_names,
        "ran": ran_names,
        "cooling_down": cooling_names,
        "visible_grace": grace_names,
        "blocked": blocked_names,
        "errors": error_names,
        "results": [
            {
                "name": r.name,
                "status": r.status,
                "reason": r.reason,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

def get_cadence_state() -> dict[str, object]:
    """Return current cadence layer state for MC observability."""
    producer_states: list[dict[str, object]] = []
    for name, spec in sorted(_producers.items(), key=lambda kv: kv[1].priority):
        last_run = _last_run_at.get(name)
        # Find last tick result for this producer
        last_result = None
        for r in reversed(_last_tick_results):
            if r.name == name:
                last_result = {"status": r.status, "reason": r.reason}
                break
        producer_states.append({
            "name": name,
            "cooldown_minutes": spec.cooldown_minutes,
            "visible_grace_minutes": spec.visible_grace_minutes,
            "priority": spec.priority,
            "depends_on": spec.depends_on,
            "last_run_at": last_run,
            "last_tick_status": last_result,
        })

    return {
        "last_tick_at": _last_tick_at or None,
        "producer_count": len(_producers),
        "producers": producer_states,
        "last_tick_summary": {
            "ran": [r.name for r in _last_tick_results if r.status == "ran"],
            "cooling_down": [r.name for r in _last_tick_results if r.status == "cooling_down"],
            "visible_grace": [r.name for r in _last_tick_results if r.status == "visible_grace"],
            "blocked": [r.name for r in _last_tick_results if r.status == "blocked"],
            "errors": [r.name for r in _last_tick_results if r.status == "error"],
        },
    }


# ---------------------------------------------------------------------------
# Bootstrap: register the known non-visible inner producers
# ---------------------------------------------------------------------------

def _ensure_producers_registered() -> None:
    """Register known producers if not already registered.

    Called lazily on first cadence tick.
    """
    if _producers:
        return

    # Brain continuity motor
    def _run_brain_continuity(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.session_distillation import (
            run_private_brain_continuity,
        )
        return run_private_brain_continuity(trigger=trigger)

    register_producer(ProducerSpec(
        name="brain_continuity",
        cooldown_minutes=5,
        visible_grace_minutes=0,  # brain continuity has no visible grace
        run_fn=_run_brain_continuity,
        priority=1,  # runs first — others may depend on its output
    ))

    def _run_sleep_consolidation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.idle_consolidation import (
            run_idle_consolidation,
        )
        return run_idle_consolidation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="sleep_consolidation",
        cooldown_minutes=15,
        visible_grace_minutes=5,
        run_fn=_run_sleep_consolidation,
        priority=3,
        depends_on=["brain_continuity"],
    ))

    # Witness daemon
    def _run_witness(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.witness_signal_tracking import (
            run_witness_daemon,
        )
        return run_witness_daemon(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="witness_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=1,
        run_fn=_run_witness,
        priority=5,
        depends_on=["brain_continuity"],
    ))

    # Inner voice daemon
    def _run_inner_voice(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.inner_voice_daemon import (
            run_inner_voice_daemon,
        )
        from core.services.witness_signal_tracking import (
            get_witness_daemon_state,
        )
        witness_state = get_witness_daemon_state()
        return run_inner_voice_daemon(
            trigger=trigger,
            last_visible_at=last_visible_at,
            witness_daemon_last_run_at=str(witness_state.get("last_run_at") or ""),
        )

    register_producer(ProducerSpec(
        name="inner_voice_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=2,
        run_fn=_run_inner_voice,
        priority=10,
        depends_on=["witness_daemon"],
    ))

    # Emergent inner signal daemon
    def _run_emergent_signals(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.emergent_signal_tracking import (
            run_emergent_signal_daemon,
        )

        return run_emergent_signal_daemon(
            trigger=trigger,
            last_visible_at=last_visible_at,
        )

    register_producer(ProducerSpec(
        name="emergent_signal_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=2,
        run_fn=_run_emergent_signals,
        priority=12,
        depends_on=["witness_daemon"],
    ))

    def _run_dream_articulation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.dream_articulation import (
            run_dream_articulation,
        )
        return run_dream_articulation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_articulation",
        cooldown_minutes=20,
        visible_grace_minutes=5,
        run_fn=_run_dream_articulation,
        priority=15,
        depends_on=["sleep_consolidation"],
    ))

    def _run_prompt_evolution_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.prompt_evolution_runtime import (
            run_prompt_evolution_runtime,
        )
        return run_prompt_evolution_runtime(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="prompt_evolution_runtime",
        cooldown_minutes=25,
        visible_grace_minutes=8,
        run_fn=_run_prompt_evolution_runtime,
        priority=18,
        depends_on=["dream_articulation"],
    ))

    def _run_self_critique_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.self_critique_runtime import (
            run_self_critique_cycle,
        )

        return run_self_critique_cycle(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="self_critique_runtime",
        cooldown_minutes=1440,
        visible_grace_minutes=15,
        run_fn=_run_self_critique_runtime,
        priority=20,
        depends_on=["prompt_evolution_runtime"],
    ))

    def _run_ontological_revision(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.self_critique_runtime import run_ontological_revision_check
        return run_ontological_revision_check()

    register_producer(ProducerSpec(
        name="ontological_revision",
        cooldown_minutes=1440,  # Check once/day — actual cadence is 90 days
        visible_grace_minutes=15,
        run_fn=_run_ontological_revision,
        priority=21,
        depends_on=["self_critique_runtime"],
    ))

    def _run_dream_distillation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.dream_distillation_daemon import (
            run_dream_distillation_daemon,
        )

        return run_dream_distillation_daemon(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_distillation_daemon",
        cooldown_minutes=180,
        visible_grace_minutes=30,
        run_fn=_run_dream_distillation,
        priority=22,
        depends_on=["self_critique_runtime"],
    ))

    def _run_creative_journal_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.creative_journal_runtime import (
            run_creative_journal_cycle,
        )

        return run_creative_journal_cycle(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="creative_journal_runtime",
        cooldown_minutes=10080,
        visible_grace_minutes=60,
        run_fn=_run_creative_journal_runtime,
        priority=24,
        depends_on=["dream_distillation_daemon"],
    ))

    def _run_finitude_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_finitude_ritual,
        )

        return run_finitude_ritual(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_runtime",
        cooldown_minutes=1440,
        visible_grace_minutes=60,
        run_fn=_run_finitude_runtime,
        priority=26,
        depends_on=["creative_journal_runtime"],
    ))

    def _run_finitude_monthly_reflection(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_monthly_finitude_reflection,
        )

        return run_monthly_finitude_reflection(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_monthly_reflection",
        cooldown_minutes=43200,  # 30 days
        visible_grace_minutes=60,
        run_fn=_run_finitude_monthly_reflection,
        priority=27,
        depends_on=["finitude_runtime"],
    ))

    def _run_world_model_ttl_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from core.services.world_model_signal_tracking import (
            _ttl_sweep_open_predictions,
        )
        return _ttl_sweep_open_predictions(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="world_model_ttl_sweeper",
        cooldown_minutes=1440,  # 1×/day
        visible_grace_minutes=60,
        run_fn=_run_world_model_ttl_sweep,
        priority=28,
        depends_on=[],
    ))

    def _run_curiosity_idle_window(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Curiosity-budget Phase 1 (2026-05-12) — idle-window opener.

        Cadence framework has already enforced `visible_grace_minutes=30`,
        so this fires only when visible chat has been quiet ≥30 min.
        We just check killswitch + budget, then flip the state_store flag.
        """
        from core.services.curiosity_budget import (
            curiosity_enabled,
            idle_window_open,
            open_idle_window,
            remaining_today,
        )
        if not curiosity_enabled():
            return {"status": "skipped", "reason": "killswitch"}
        if remaining_today() <= 0:
            return {"status": "skipped", "reason": "no_budget"}
        if idle_window_open():
            return {"status": "skipped", "reason": "already_open"}
        open_idle_window()
        return {"status": "ok", "window_opened": True,
                "remaining": remaining_today()}

    register_producer(ProducerSpec(
        name="curiosity_idle_window",
        cooldown_minutes=1,
        visible_grace_minutes=30,  # only fire after ≥30 min visible silence
        run_fn=_run_curiosity_idle_window,
        priority=29,
        depends_on=[],
    ))

    def _run_meta_learning_weekly(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Meta-læring Phase 1 (2026-05-12) — weekly retrospective."""
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from datetime import timedelta as _timedelta
        from core.services.meta_learning_retrospective import (
            _meta_learning_enabled,
            generate_weekly_retrospective,
        )
        from core.runtime.db import connect

        if not _meta_learning_enabled():
            return {"status": "skipped", "reason": "killswitch"}

        try:
            with connect() as conn:
                row = conn.execute(
                    "SELECT ts FROM learning_memos ORDER BY ts DESC LIMIT 1"
                ).fetchone()
            if row:
                last_ts = _datetime.fromisoformat(str(row["ts"]))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=_UTC)
                age = _datetime.now(_UTC) - last_ts
                if age < _timedelta(days=6, hours=12):
                    return {"status": "skipped", "reason": "recent memo exists (<6.5d)"}
        except Exception as exc:
            logger.debug("meta_learning producer: db check failed: %s", exc)

        return generate_weekly_retrospective(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="meta_learning_weekly_retrospective",
        cooldown_minutes=10080,        # 7 dage
        visible_grace_minutes=60,
        run_fn=_run_meta_learning_weekly,
        priority=30,
        depends_on=[],
    ))

    def _run_prompt_assembly_cache_warmer(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Refresh prompt-assembly section caches in background.

        Strategy: every 2 minutes, invalidate + rebuild both rule_conclusions
        and cognitive_frame caches. This way visible-chat turns always see
        ≤2 min stale data, AND never pay the cold-rebuild cost themselves —
        the heartbeat thread absorbs it.

        Without this: 180s TTL means a turn lands exactly when the cache
        expired pays the full 10s rebuild. With this: cache is always warm
        when visible chat needs it.

        Added 2026-05-12 after instrumentation identified rule_conclusions
        + cognitive_frame as the dominant assembly cost.
        """
        # Logger.info so we can SEE when this fires in journal.
        # Without this, the warmer is invisible because the producer
        # doesn't publish events to the DB. Cheap line, big diagnostic value.
        logger.info("prompt_assembly_cache_warmer: tick fired (trigger=%s)", trigger)

        out: dict[str, object] = {"rule_conclusions": "skipped", "cognitive_frame": "skipped"}
        try:
            from core.services.prompt_sections.rule_conclusions import (
                invalidate_section_cache, rule_conclusions_section,
            )
            invalidate_section_cache()
            _ = rule_conclusions_section()  # rebuild + cache
            out["rule_conclusions"] = "warmed"
        except Exception as exc:
            out["rule_conclusions"] = f"error: {exc}"
        try:
            from core.services.prompt_contract import (
                invalidate_cognitive_frame_cache, _cognitive_frame_section,
            )
            invalidate_cognitive_frame_cache()
            _ = _cognitive_frame_section()
            out["cognitive_frame"] = "warmed"
        except Exception as exc:
            out["cognitive_frame"] = f"error: {exc}"
        logger.info(
            "prompt_assembly_cache_warmer: done rule_conclusions=%s cognitive_frame=%s",
            out["rule_conclusions"], out["cognitive_frame"],
        )
        return {"status": "ok", **out}

    register_producer(ProducerSpec(
        name="prompt_assembly_cache_warmer",
        cooldown_minutes=2,            # refresh every 2 min (< 3 min TTL)
        visible_grace_minutes=0,       # always run — it's background pre-warm
        run_fn=_run_prompt_assembly_cache_warmer,
        priority=31,
        depends_on=[],
    ))

    def _run_life_projects_reassessment(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.life_projects import tick_life_projects_reassessment
        return tick_life_projects_reassessment(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="life_projects_reassessment",
        cooldown_minutes=1440,
        visible_grace_minutes=30,
        run_fn=_run_life_projects_reassessment,
        priority=28,
    ))

    def _run_relation_map_refresh(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.relation_map import tick_relation_map_refresh
        return tick_relation_map_refresh(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="relation_map_refresh",
        cooldown_minutes=720,
        visible_grace_minutes=0,
        run_fn=_run_relation_map_refresh,
        priority=30,
    ))

def run_cadence_tick_with_bootstrap(
    *,
    trigger: str = "heartbeat",
    last_visible_at_iso: str = "",
) -> dict[str, object]:
    """Bootstrap producers and run a cadence tick.

    Used by both the dedicated cadence scheduler (trigger='cadence-scheduler')
    and any external caller. Heartbeat used to call this too — that path is
    deprecated; cadence now runs independently of heartbeat via
    start_cadence_scheduler() below.
    """
    _ensure_producers_registered()
    return run_cadence_tick(
        trigger=trigger,
        last_visible_at_iso=last_visible_at_iso,
    )


# ---------------------------------------------------------------------------
# Standalone cadence scheduler (decoupled from heartbeat)
# ---------------------------------------------------------------------------

def _scheduler_loop() -> None:
    """Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds.

    Runs in a daemon thread, dies with the process. Catches exceptions
    per-tick so a single failure doesn't stop the loop.
    """
    logger.info("cadence scheduler loop starting (interval=%ds)", _SCHEDULER_INTERVAL_S)
    # Pull recent visible-chat timestamp on each tick from event_bus so
    # visible-grace logic still works (producers like curiosity_idle_window
    # use visible_grace_minutes to delay until chat has been quiet).
    while not _SCHEDULER_STOP.is_set():
        try:
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
                trigger="cadence-scheduler",
                last_visible_at_iso=last_visible_at,
            )
        except Exception as exc:
            logger.warning("cadence scheduler loop error: %s", exc)
        _SCHEDULER_STOP.wait(_SCHEDULER_INTERVAL_S)
    logger.info("cadence scheduler loop exited")


def start_cadence_scheduler() -> None:
    """Spawn the standalone cadence scheduler thread. Idempotent."""
    global _SCHEDULER_THREAD
    if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
        return
    _SCHEDULER_STOP.clear()
    _SCHEDULER_THREAD = threading.Thread(
        target=_scheduler_loop,
        name="cadence-scheduler",
        daemon=True,
    )
    _SCHEDULER_THREAD.start()
    logger.info("cadence-scheduler daemon started")


def stop_cadence_scheduler() -> None:
    """Signal the scheduler thread to exit. Best-effort; daemon dies with process."""
    _SCHEDULER_STOP.set()
