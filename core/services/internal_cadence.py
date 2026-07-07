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
    tempo: float = 1.0,
) -> tuple[str, str]:
    """Evaluate whether a producer is due.

    Returns (status, reason).

    ``tempo`` (DIASTOLE-konsumtion, §28): multiplikator på den effektive cooldown
    for NON-exempt producers. Default 1.0 → ingen modulation (byte-identisk gammel
    adfærd; alle eksterne kaldere upåvirket). Infra/health/SECURITY undtages inde i
    effective_cooldown → altid rå cadence. tempo ∈ [0.5, 2.0] → 0.5×..2× base.
    """
    # Check dependencies
    for dep in spec.depends_on:
        if dep not in ran_this_tick:
            return "blocked", f"dependency-not-met:{dep}"

    # Cooldown check — moduleret af tempo for non-exempt producers (self-safe:
    # fejl i modulationen falder tilbage til rå cooldown = nuværende adfærd).
    try:
        from core.services.central_cadence_conductor import effective_cooldown
        _cooldown_min = effective_cooldown(spec.name, spec.cooldown_minutes, tempo)
    except Exception:
        _cooldown_min = spec.cooldown_minutes
    last_run_iso = _last_run_at.get(spec.name)
    if last_run_iso:
        try:
            last_run = datetime.fromisoformat(last_run_iso)
            elapsed = (now - last_run).total_seconds() / 60
            if elapsed < _cooldown_min:
                _mod = "" if _cooldown_min == spec.cooldown_minutes else f"~{_cooldown_min:.0f}m"
                return "cooling_down", f"cooldown:{elapsed:.0f}m<{spec.cooldown_minutes:.0f}m{_mod}"
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

def _run_producer_bounded(spec, *, trigger: str, last_visible_at: str, timeout_s: float):
    """Kør en producer i sin EGEN dæmon-tråd med en hård timeout.

    ROD-FIX (Bjørn 2026-06-17): producers kørte synkront i scheduler-tråden uden
    timeout. Én producer der hang i et LLM-kald (inner_voice/dreams/witness) frøs
    HELE cadence-loopet for evigt → warmer + alle private-lag-producers døde.
    Nu kan én hængende producer ikke vælte de andre — den timeout'er og loopet
    fortsætter. Den hængende tråd er daemon (dør med processen).
    """
    box: dict[str, object] = {}

    def _target() -> None:
        # Tag hvilken producer der kører NU, så cheap-lane-kald i run_fn (samme tråd) kan
        # attribueres til den (producer_novelty, observe-only). Self-safe.
        try:
            from core.services import producer_novelty as _pn
            _pn.set_producer(spec.name)
        except Exception:
            pass
        try:
            box["r"] = spec.run_fn(trigger=trigger, last_visible_at=last_visible_at)
        except BaseException as exc:  # noqa: BLE001 — videregiv til kalderen
            box["e"] = exc
        finally:
            try:
                from core.services import producer_novelty as _pn2
                _pn2.clear_producer()
            except Exception:
                pass

    t = threading.Thread(target=_target, name=f"cadence-prod-{spec.name}", daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        raise TimeoutError(f"producer '{spec.name}' overskred {timeout_s:.0f}s — sprunget over")
    if "e" in box:
        raise box["e"]  # type: ignore[misc]
    return box.get("r")


# Per-producer hård timeout. LLM-producers (inner_voice/dreams) tager ~10-20s;
# 75s giver rigeligt, men forhindrer en hængende én i at fryse hele cadencen.
_PRODUCER_TIMEOUT_S = 75.0


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

    # DIASTOLE-konsumtion (§28): sans tempoet ÉN gang pr. tick. Flag OFF eller
    # utilgængelig → 1.0 (byte-identisk nuværende adfærd). Loop-lag-dødemandsknap
    # sidder inde i current_tick_tempo → automatisk baseline under pres. Self-safe.
    try:
        from core.services.central_cadence_conductor import current_tick_tempo
        _cadence_tempo = current_tick_tempo()
    except Exception:
        _cadence_tempo = 1.0

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
            tempo=_cadence_tempo,
        )

        if status == "due":
            due_names.append(spec.name)
            # Dispatch — tidsbundet, så én hængende producer ikke fryser cadencen.
            try:
                _prod_t0 = time.monotonic()
                result = _run_producer_bounded(
                    spec, trigger=trigger, last_visible_at=last_visible_at_iso,
                    timeout_s=_PRODUCER_TIMEOUT_S,
                )
                _prod_dt = time.monotonic() - _prod_t0
                if _prod_dt > 10:
                    logger.warning("cadence producer '%s' tog %.1fs", spec.name, _prod_dt)
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
                # Fase 2 (§23.3 #3 / §24.4): ÉT hook → alle ~35 inner-life-daemons. Egress-frit,
                # kun aggregeret liveness. No-op for ikke-inner producers.
                try:
                    from core.services import central_private_observe as _cpo
                    _cpo.observe_cadence_liveness(spec.name, "ran", result)
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
                try:
                    from core.services import central_private_observe as _cpo
                    _cpo.observe_cadence_liveness(spec.name, "error", None)
                except Exception:
                    pass
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

    # Cross-proces (Bjørn 2026-06-23): daemons kører i runtime-processen; Central-terminalen
    # i api-processen. Publicér producer-snapshot til shared_cache så 'daemons'-kommandoen kan
    # se dem på tværs. Self-safe — en publish-fejl må aldrig røre cadence-tikket.
    try:
        from core.services import shared_cache as _sc
        _snap = {name: {"cooldown_minutes": s.cooldown_minutes, "priority": s.priority,
                        "last_run": _last_run_at.get(name, "")}
                 for name, s in _producers.items()}
        _sc.set("cadence:daemons", _snap, ttl_seconds=3600)
    except Exception:
        pass

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

    # Producer registrations are grouped by domain into sibling modules
    # (Boy Scout split, behavior-preserving). Each group registers its
    # producers via the shared register_producer in UNCHANGED order. Lazy
    # imports avoid a circular dependency (the group modules import
    # ProducerSpec from this module).
    from core.services.internal_cadence_core import register_core_producers
    from core.services.internal_cadence_matrix import register_matrix_producers
    from core.services.internal_cadence_inner_life import register_inner_life_producers
    from core.services.internal_cadence_maintenance import register_maintenance_producers
    from core.services.internal_cadence_central_wiring import (
        register_central_wiring_producers,
    )

    register_core_producers(register_producer)
    register_matrix_producers(register_producer)
    register_inner_life_producers(register_producer)
    register_maintenance_producers(register_producer)
    register_central_wiring_producers()


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

def _run_injection_refresh_tick() -> None:
    """Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path).
    Self-safe — en refresh-fejl må aldrig stoppe cadence-loopet."""
    try:
        from core.services import central_injection_units
        central_injection_units.register_default_units()   # idempotent
    except Exception:
        pass
    try:
        from core.services.central_injection_registry import refresh_dirty
        refresh_dirty()
    except Exception:
        pass


def _scheduler_loop() -> None:
    """Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds.

    Runs in a daemon thread, dies with the process. Catches exceptions
    per-tick so a single failure doesn't stop the loop.
    """
    logger.info("cadence scheduler loop starting (interval=%ds)", _SCHEDULER_INTERVAL_S)
    # Pull recent visible-chat timestamp on each tick from event_bus so
    # visible-grace logic still works (producers like curiosity_idle_window
    # use visible_grace_minutes to delay until chat has been quiet).
    _seam_primed = False
    while not _SCHEDULER_STOP.is_set():
        try:
            # STITCH prime (5. jul fix): mål boot-sømmen FØR vi skriver den første puls —
            # ellers overskriver pulsen forrige livs tidsstempel før _compute_boot_seam når
            # at læse det, og et ægte fravær maskeres til ~0s (reboot usynlig). Første-kald
            # cacher gap'et proces-lokalt, så resten af loopet er upåvirket.
            if not _seam_primed:
                try:
                    from core.services.central_self_state import _compute_boot_seam
                    _compute_boot_seam()
                except Exception:
                    pass
                _seam_primed = True
            _run_injection_refresh_tick()
            # STITCH liveness-puls: durabelt "jeg var i live nu" hvert tick → boot-sømmen
            # (central_self_state._compute_boot_seam) kan måle hvor længe Centralen var borte
            # efter en restart og sige "jeg vågnede for N siden". Billig, self-safe.
            try:
                from core.runtime.db_core import set_runtime_state_value as _sav
                from datetime import datetime as _dt, UTC as _UTC
                _sav("central_last_alive_ts", _dt.now(_UTC).isoformat())
            except Exception:
                pass
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
