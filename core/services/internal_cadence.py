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
        try:
            box["r"] = spec.run_fn(trigger=trigger, last_visible_at=last_visible_at)
        except BaseException as exc:  # noqa: BLE001 — videregiv til kalderen
            box["e"] = exc

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

    # Cognitive-state warmer (#2, 2026-06-30): pre-byg cognitive_state-cachen i
    # baggrunden hvert ~3 min, så den ENE dominante blokerende LLM-omkostning
    # (recall_for_message) betales HER i stedet for synkront under prompt assembly.
    # force=True → bygger frisk uden cache-gap (gammel cache serveres til ny er sat).
    # Visible-turen rammer så altid en varm cache (0 blokerende LLM). Den tilstands-
    # bevidste invalidering sikrer at den fanger ægte indre-liv-skift uafhængigt.
    def _run_cognitive_state_warm(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        warmed = 0
        try:
            from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
            for _compact in (False, True):
                try:
                    if build_cognitive_state_for_prompt(compact=_compact, force=True) is not None:
                        warmed += 1
                except Exception:
                    pass
        except Exception:
            pass
        return {"warmed": warmed}

    register_producer(ProducerSpec(
        name="cognitive_state_warm",
        cooldown_minutes=3,
        visible_grace_minutes=0,  # kører uanset visible — varm cache ER pointen (lokal lane, kolliderer ikke med deepseek-visible)
        run_fn=_run_cognitive_state_warm,
        priority=2,
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

    def _run_curiosity_consolidation_weekly(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from core.services.curiosity_consolidation import run_consolidation
        return run_consolidation(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="curiosity_consolidation_weekly",
        cooldown_minutes=10080,        # 7 dage
        visible_grace_minutes=60,
        run_fn=_run_curiosity_consolidation_weekly,
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

        out: dict[str, object] = {
            "rule_conclusions": "skipped", "cognitive_frame": "skipped",
            "cognitive_state": "skipped",
        }
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
        # cognitive_state (~5,5s, SQLite-cachet, TTL 120s) blev IKKE varmet før
        # — den var den dominerende kolde-cache-omkostning i den visible assembly
        # (Bjørn 2026-06-17). Varm den med compact=False (= visible owner-chat-nøglen)
        # så ingen tur betaler kold pris. Friskhed = warmer-kadence (~2 min), uændret.
        try:
            from core.services.cognitive_state_assembly import (
                invalidate_cognitive_state_cache, build_cognitive_state_for_prompt,
            )
            invalidate_cognitive_state_cache()
            _ = build_cognitive_state_for_prompt(compact=False)  # rebuild + cache
            out["cognitive_state"] = "warmed"
        except Exception as exc:
            out["cognitive_state"] = f"error: {exc}"
        logger.info(
            "prompt_assembly_cache_warmer: done rule_conclusions=%s cognitive_frame=%s cognitive_state=%s",
            out["rule_conclusions"], out["cognitive_frame"], out["cognitive_state"],
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

    def _run_counterfactual_predictions_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Counterfactuals Phase 1.5 (2026-05-14) — close the prediction
        resolution loop. Resolves counterfactual-bound predictions whose
        7-day horizon (+1d grace) has passed, marking as 'uncertain' with
        an audit note. Future Phase 2 will replace this with frequency-
        based supported/contradicted assignment."""
        from core.services.counterfactual_predictions import (
            sweep_expired_counterfactual_predictions,
        )
        return sweep_expired_counterfactual_predictions()

    register_producer(ProducerSpec(
        name="counterfactual_predictions_sweep",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_counterfactual_predictions_sweep,
        priority=35,
    ))

    def _run_shared_cache_cleanup(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Sweep expired rows from shared_cache (2026-05-14).

        shared_cache lazy-expires individual entries on read, but rows
        written and never read again would linger. Hourly cleanup keeps
        the table tight."""
        from core.services.shared_cache import cleanup_expired, stats
        deleted = cleanup_expired()
        return {"status": "ok", "deleted": deleted, **stats()}

    register_producer(ProducerSpec(
        name="shared_cache_cleanup",
        cooldown_minutes=60,  # hourly
        visible_grace_minutes=0,
        run_fn=_run_shared_cache_cleanup,
        priority=36,
    ))

    def _run_central_self_health(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """§1 (2026-06-22): Centralen prober SIG SELV hver time → observe + eskalér hvis
        decide/observe fejler, breakers er åbne, eller for mange uløste severe incidents."""
        from core.services.central_health import observe_and_escalate
        rep = observe_and_escalate()
        return {"status": "ok", "decide_ok": rep.get("decide_ok"),
                "observe_ok": rep.get("observe_ok"), "degraded": rep.get("degraded"),
                "open_breakers": len(rep.get("open_breakers") or [])}

    register_producer(ProducerSpec(
        name="central_self_health",
        cooldown_minutes=60,  # hver time — self-helbred skal fanges hurtigt
        visible_grace_minutes=0,
        run_fn=_run_central_self_health,
        priority=36,
    ))

    def _run_central_learning(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """#4 (2026-06-22): adaptiv læring pr. cluster fra incident-historikken → observe +
        flag degraderende clusters (trender mod nedbrud) + vurdér Jarvis' autonomi-modenhed.
        Deterministisk, read-only — akkumulerer over tid (fx overnight)."""
        from core.services.central_learning import observe_learning
        s = observe_learning()
        return {"status": "ok", "degrading": len(s.get("degrading") or []),
                "autonomy": (s.get("autonomy") or {}).get("verdict")}

    register_producer(ProducerSpec(
        name="central_learning",
        cooldown_minutes=60,  # hver time — lær kontinuerligt
        visible_grace_minutes=0,
        run_fn=_run_central_learning,
        priority=36,
    ))

    def _run_stream_stall_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Stream-cluster (audit 2026-06-23): stream_stall sweepede FØR kun opportunistisk
        ved næste note_start → en zombie-stream i en HELT stille periode (ingen nye streams)
        blev aldrig flagget. Denne producer kalder sweep() på kadence så zombier fanges også
        i stilhed. Read-only (flagger, dropper aldrig)."""
        from core.services import stream_sentinel
        live = stream_sentinel.sweep()
        return {"status": "ok", "live_streams": int(live)}

    register_producer(ProducerSpec(
        name="stream_stall_sweep",
        cooldown_minutes=5,  # hvert 5. min — zombie skal fanges selv uden ny aktivitet
        visible_grace_minutes=0,
        run_fn=_run_stream_stall_sweep,
        priority=37,
    ))

    def _run_config_drift(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """§7 (2026-06-22): config↔runtime-drift-check (port). Fanger 8010/8011-typen — settings
        siger én port, API'en svarer på en anden → observe + incident. Read-only probe."""
        from core.services.config_drift import observe_config_drift
        rep = observe_config_drift()
        return {"status": "ok", "declared_port": rep.get("declared_port"),
                "actual_port": rep.get("actual_port"), "drift": rep.get("drift")}

    register_producer(ProducerSpec(
        name="config_drift_check",
        cooldown_minutes=1440,  # daily — drift opstår kun ved deploy/config-skift
        visible_grace_minutes=0,
        run_fn=_run_config_drift,
        priority=36,
    ))

    def _run_instrument_scan(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Selv-instrumenterings-motor (2026-06-23): AST-scan af kodebasen for silent-failure-
        mønstre → score → observe → reviewbare proposals (score≥3). Incremental (kun ændrede
        filer). ALDRIG auto-merged, instrumenterer aldrig sig selv."""
        from core.services.central_instrument import run_instrument_scan
        rep = run_instrument_scan(trigger=trigger, changed_only=True)
        return {"status": "ok", "scanned": rep.get("scanned"), "changed": rep.get("changed"),
                "findings": rep.get("findings"), "new_proposals": rep.get("new_proposals")}

    register_producer(ProducerSpec(
        name="instrument_scan",
        cooldown_minutes=360,  # hver 6. time (Jarvis-spec); incremental → billigt
        visible_grace_minutes=0,
        run_fn=_run_instrument_scan,
        priority=38,
    ))

    def _run_provider_health(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """provider_health (2026-06-23, Jarvis-spec): proaktiv provider-ping → flag nede/
        degraderet/tør + model-drift. Bygger på config_drift-mekanik (observe+flag+auto-resolve).
        ALDRIG destruktiv — retter ikke config selv."""
        from core.services.provider_health_check import observe_and_flag
        rep = observe_and_flag()
        return {"status": "ok", "checked": rep.get("checked"), "down": rep.get("unreachable"),
                "degraded": rep.get("degraded"), "model_drift": rep.get("model_drift")}

    register_producer(ProducerSpec(
        name="provider_health_check",
        cooldown_minutes=5,  # hvert 5. min (Jarvis-spec) — proaktiv, fanger drift før kritisk
        visible_grace_minutes=0,
        run_fn=_run_provider_health,
        priority=37,
    ))

    def _run_db_health_scan(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """DB-cluster (2026-06-22): daglig table-census + vækst-flag via db_sentinel.observe.
        ALDRIG destruktiv — kun observe + flag (tom tabel = kandidat til review, ikke drop)."""
        from core.services.db_sentinel import observe
        report = observe()
        return {"status": "ok", "tables": report.get("tables"),
                "total_rows": report.get("total_rows"),
                "flagged_growth": len(report.get("flagged_growth") or []),
                "empty_candidates": len(report.get("empty") or [])}

    register_producer(ProducerSpec(
        name="db_health_scan",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_db_health_scan,
        priority=36,
    ))

    def _run_tool_usage_stats(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Tools-cluster Phase 2 (2026-06-22): daglig forbrugs-statistik via tool_usage_store
        → central.observe (mest/ofte/nogle-gange/sjældent/aldrig) + flag antal døde tools.
        Grundlag for at ordne kataloget (mest-brugt først, døde sidst). Observe-only."""
        from core.services.tool_usage_store import observe_stats
        try:
            from core.tools.simple_tools import _TOOL_HANDLERS
            registered = list(_TOOL_HANDLERS.keys())
        except Exception:
            registered = []
        summary = observe_stats(registered)
        return {"status": "ok", "tracked": summary.get("tracked"),
                "never": summary.get("never"), "registered": len(registered)}

    register_producer(ProducerSpec(
        name="tool_usage_stats",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_tool_usage_stats,
        priority=36,
    ))

    def _run_endpoint_usage_stats(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Tools-cluster (2026-06-22): daglig API-endpoint forbrugs-statistik → central.observe
        (mest/aldrig) + flag antal døde endpoints (registreret men aldrig kaldt). Observe-only."""
        from core.services.endpoint_usage_store import observe_stats
        summary = observe_stats()
        return {"status": "ok", "tracked": summary.get("tracked"),
                "registered": summary.get("registered"), "dead": summary.get("dead")}

    register_producer(ProducerSpec(
        name="endpoint_usage_stats",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_endpoint_usage_stats,
        priority=36,
    ))

    # Eventbus→Central KEYSTONE-bro (M0, spec §23.3 #1 / §24.1). Poll-bro, observe-only:
    # konverterer hvidlistede event-families til central().observe. Registreres via egen
    # modul-funktion (holder internal_cadence fri for bro-logikken).
    try:
        from core.services.eventbus_central_bridge import register_bridge_producer
        register_bridge_producer()
    except Exception:
        pass

    # Central-selv-observation (Fase 1, spec §23.3 #2 / §24.5). Måler Centralens EGEN
    # decide-latency-drift + breaker-frekvens — udløser-frit (ingen eskalering/heling).
    try:
        from core.services.central_self_observe import register_self_observe_producer
        register_self_observe_producer()
    except Exception:
        pass

    # Det aktive lag (§25). Vagten flagger+lærer+notificerer på de fodrede streams,
    # gated af støjfangeren. Ingen mutation (aktiv ændring kommer til sidst).
    try:
        from core.services.central_watch import register_watch_producer
        register_watch_producer()
    except Exception:
        pass

    # C (LivingNeuron-data): vækst-kapacitet — inner-drives egress-frit + semantic-indexer.
    try:
        from core.services.central_growth_observe import register_growth_observe_producer
        register_growth_observe_producer()
    except Exception:
        pass

    # Fase 1c: dækning + surface-count RUNTIME-MÅLT (ikke hardcodet) → tidsserie, plotbart.
    try:
        from core.services.central_coverage import register_coverage_producer
        register_coverage_producer()
    except Exception:
        pass

    # Fase 1d: causal-grafens tier-fordeling + precision (broen signal→hypotese) → tidsserie.
    try:
        from core.services.central_causal_quality import register_causal_quality_producer
        register_causal_quality_producer()
    except Exception:
        pass

    # Fase 1e: signal-korrekthed + hub meta-liveness (Centralen må ikke blive blind for sin blindhed).
    try:
        from core.services.central_signal_health import register_signal_health_producer
        register_signal_health_producer()
    except Exception:
        pass

    # Lag 3 v3: tvær-modal stance-aflæsning ("organer uenige i nuet") → tension-tidsserie.
    try:
        from core.services.central_stance import register_stance_producer
        register_stance_producer()
    except Exception:
        pass

    # Lag 3 (§11 Fase 2): governed hypotese-generator — OBSERVE-ONLY, routes gennem §8-dødsmekanismen.
    try:
        from core.services.central_hypothesis_generator import register_hypothesis_generator_producer
        register_hypothesis_generator_producer()
    except Exception:
        pass

    # Lag 3 loop-lukning: test aktive hypoteser mod virkeligheden → grounded samples (OBSERVE-ONLY).
    try:
        from core.services.central_hypothesis_sampler import register_hypothesis_sampler_producer
        register_hypothesis_sampler_producer()
    except Exception:
        pass

    # M1 SHADOW: reaktivt/prædiktivt lag — beregner hvad Centralen VILLE gøre, anvender
    # ALDRIG (ACTIVE_APPLY hardkodet False). Validér dømmekraft mod virkelighed før apply.
    try:
        from core.services.central_shadow import register_shadow_producer
        register_shadow_producer()
    except Exception:
        pass

    # INFRA-SANSNING: Centralen som husets nervesystem — reachability + PiHole + pfSense
    # read-only fra Jarvis-containeren. Miljø-modalitet til LivingNeuron.
    try:
        from core.services.infra_sense import register_infra_sense_producer
        register_infra_sense_producer()
    except Exception:
        pass


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
