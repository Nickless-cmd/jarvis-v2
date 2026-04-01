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
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Callable

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


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
        from apps.api.jarvis_api.services.session_distillation import (
            run_private_brain_continuity,
        )
        return run_private_brain_continuity(trigger=trigger)

    register_producer(ProducerSpec(
        name="brain_continuity",
        cooldown_minutes=10,
        visible_grace_minutes=0,  # brain continuity has no visible grace
        run_fn=_run_brain_continuity,
        priority=1,  # runs first — others may depend on its output
    ))

    def _run_sleep_consolidation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from apps.api.jarvis_api.services.idle_consolidation import (
            run_idle_consolidation,
        )
        return run_idle_consolidation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="sleep_consolidation",
        cooldown_minutes=25,
        visible_grace_minutes=12,
        run_fn=_run_sleep_consolidation,
        priority=3,
        depends_on=["brain_continuity"],
    ))

    # Witness daemon
    def _run_witness(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from apps.api.jarvis_api.services.witness_signal_tracking import (
            run_witness_daemon,
        )
        return run_witness_daemon(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="witness_daemon",
        cooldown_minutes=10,
        visible_grace_minutes=3,
        run_fn=_run_witness,
        priority=5,
        depends_on=["brain_continuity"],
    ))

    # Inner voice daemon
    def _run_inner_voice(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from apps.api.jarvis_api.services.inner_voice_daemon import (
            run_inner_voice_daemon,
        )
        from apps.api.jarvis_api.services.witness_signal_tracking import (
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
        cooldown_minutes=15,
        visible_grace_minutes=5,
        run_fn=_run_inner_voice,
        priority=10,
        depends_on=["witness_daemon"],
    ))

    # Emergent inner signal daemon
    def _run_emergent_signals(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from apps.api.jarvis_api.services.emergent_signal_tracking import (
            run_emergent_signal_daemon,
        )

        return run_emergent_signal_daemon(
            trigger=trigger,
            last_visible_at=last_visible_at,
        )

    register_producer(ProducerSpec(
        name="emergent_signal_daemon",
        cooldown_minutes=10,
        visible_grace_minutes=5,
        run_fn=_run_emergent_signals,
        priority=12,
        depends_on=["witness_daemon"],
    ))

    def _run_dream_articulation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from apps.api.jarvis_api.services.dream_articulation import (
            run_dream_articulation,
        )
        return run_dream_articulation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_articulation",
        cooldown_minutes=35,
        visible_grace_minutes=14,
        run_fn=_run_dream_articulation,
        priority=15,
        depends_on=["sleep_consolidation"],
    ))

def run_cadence_tick_with_bootstrap(
    *,
    trigger: str = "heartbeat",
    last_visible_at_iso: str = "",
) -> dict[str, object]:
    """Bootstrap producers and run a cadence tick.

    This is the main entry point called by heartbeat.
    """
    _ensure_producers_registered()
    return run_cadence_tick(
        trigger=trigger,
        last_visible_at_iso=last_visible_at_iso,
    )
