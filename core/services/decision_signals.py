"""Decisions-as-signals: per-turn evaluation of behavioral decisions.

Triggers are code-defined functions registered by name at import time.
Each active behavioral_decision row may reference a trigger via its
`trigger_name` column. On every visible-chat turn, this module evaluates
all active triggers, applies per-decision cooldown, and produces the
`[FIRED_DECISIONS]` AWARENESS section.
"""
from __future__ import annotations

import contextvars
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Optional

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

logger = logging.getLogger(__name__)


@dataclass
class TriggerContext:
    """Snapshot of state available to a trigger function."""
    user_message: str
    session_id: Optional[str]
    run_id: Optional[str]
    consecutive_tool_only_rounds: int
    recent_tool_calls: list[dict]
    recent_assistant_text: str
    agentic_round_seq: int
    timestamp: str


@dataclass
class TriggerSpec:
    name: str
    fire_fn: Callable[[TriggerContext], bool]
    cooldown_seconds: int = 0
    cooldown_turns: int = 0


@dataclass
class FiredDecision:
    decision_id: str
    trigger_name: str
    context_summary: str = ""


_TRIGGER_REGISTRY: dict[str, TriggerSpec] = {}

# Bound by visible_runs.py before each prompt build
_current_trigger_context: contextvars.ContextVar[Optional[TriggerContext]] = (
    contextvars.ContextVar("_current_trigger_context", default=None)
)


def register(
    name: str,
    fire_fn: Callable[[TriggerContext], bool],
    *,
    cooldown_seconds: int = 0,
    cooldown_turns: int = 0,
) -> None:
    if name in _TRIGGER_REGISTRY:
        logger.warning("decision_signals: trigger %r is being overwritten", name)
    _TRIGGER_REGISTRY[name] = TriggerSpec(
        name=name,
        fire_fn=fire_fn,
        cooldown_seconds=int(cooldown_seconds),
        cooldown_turns=int(cooldown_turns),
    )


def _active_decisions_with_triggers() -> list[dict[str, Any]]:
    """Return active decisions that have a trigger_name set."""
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT decision_id, trigger_name FROM behavioral_decisions "
                "WHERE status = 'active' AND trigger_name IS NOT NULL "
                "AND trigger_name != ''"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("decision_signals: cannot query active decisions: %s", exc)
        return []


def _read_last_fired(decision_id: str) -> Optional[str]:
    try:
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_last_fired:{decision_id}",),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"] or "") or None
    except Exception:
        return None


def _read_last_fired_seq(decision_id: str) -> Optional[int]:
    try:
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_turn_seq:{decision_id}",),
            ).fetchone()
        if row is None or not row["value"]:
            return None
        return int(row["value"])
    except Exception:
        return None


def _write_last_fired(decision_id: str, iso_ts: str) -> None:
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO runtime_state_kv(key, value, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (f"decision_signal_last_fired:{decision_id}", iso_ts, iso_ts),
            )
            c.commit()
    except Exception as exc:
        logger.warning("decision_signals: cannot write last_fired: %s", exc)


def _write_last_fired_seq(decision_id: str, seq: int, iso_ts: str) -> None:
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO runtime_state_kv(key, value, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (f"decision_signal_turn_seq:{decision_id}", str(seq), iso_ts),
            )
            c.commit()
    except Exception:
        pass


def _cooldown_active(spec: TriggerSpec, decision_id: str, ctx: TriggerContext) -> bool:
    if spec.cooldown_seconds > 0:
        last_iso = _read_last_fired(decision_id)
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=UTC)
                elapsed = (datetime.now(UTC) - last_dt).total_seconds()
                if elapsed < spec.cooldown_seconds:
                    return True
            except Exception:
                pass
    if spec.cooldown_turns > 0:
        last_seq = _read_last_fired_seq(decision_id)
        if last_seq is not None:
            if (ctx.agentic_round_seq - last_seq) < spec.cooldown_turns:
                return True
    return False


def _publish_fired_event(*, decision_id: str, trigger_name: str, ctx: TriggerContext) -> None:
    try:
        event_bus.publish("decision_signal.fired", {
            "decision_id": decision_id,
            "trigger_name": trigger_name,
            "session_id": ctx.session_id,
            "run_id": ctx.run_id,
            "agentic_round_seq": ctx.agentic_round_seq,
            "consecutive_tool_only_rounds": ctx.consecutive_tool_only_rounds,
        })
    except Exception:
        pass


def evaluate_decision_triggers(ctx: TriggerContext) -> list[FiredDecision]:
    """Evaluate all active decisions with triggers; return those that fire.

    Sandboxed per-trigger: if one raises, others still run. Cooldown
    checked per-decision. Side effects (writing last_fired_at, publishing
    events) happen only for actual fires.
    """
    settings = RuntimeSettings()
    if not settings.decision_signals_enabled:
        return []

    fired: list[FiredDecision] = []
    decisions = _active_decisions_with_triggers()
    now_iso = datetime.now(UTC).isoformat()

    for d in decisions:
        decision_id = str(d.get("decision_id") or "")
        trigger_name = str(d.get("trigger_name") or "")
        if not decision_id or not trigger_name:
            continue

        spec = _TRIGGER_REGISTRY.get(trigger_name)
        if spec is None:
            logger.debug(
                "decision_signals: unknown_trigger %r for %s", trigger_name, decision_id
            )
            continue

        try:
            should_fire = bool(spec.fire_fn(ctx))
        except Exception as exc:
            logger.warning(
                "decision_signals: evaluate failed for %s (%s): %s",
                decision_id, trigger_name, exc,
            )
            continue

        if not should_fire:
            continue

        if _cooldown_active(spec, decision_id, ctx):
            continue

        # Build short context summary for the section text
        summary_bits = []
        if "loop_nudge" in trigger_name:
            summary_bits.append(f"round {ctx.consecutive_tool_only_rounds}")
        if "backend" in trigger_name:
            summary_bits.append("backend streak ≥3 unresolved")
        summary = ", ".join(summary_bits) or trigger_name

        _write_last_fired(decision_id, now_iso)
        if spec.cooldown_turns > 0:
            _write_last_fired_seq(decision_id, ctx.agentic_round_seq, now_iso)
        _publish_fired_event(decision_id=decision_id, trigger_name=trigger_name, ctx=ctx)

        fired.append(FiredDecision(
            decision_id=decision_id,
            trigger_name=trigger_name,
            context_summary=summary,
        ))
        logger.info("decision_signals.fired %s via %s", decision_id, trigger_name)

    return fired


def fired_decisions_section(ctx: TriggerContext) -> Optional[str]:
    """Build the [FIRED_DECISIONS] section text. None if nothing fired."""
    fired = evaluate_decision_triggers(ctx)
    if not fired:
        return None
    lines = ["🔔 fired decisions:"]
    for f in fired:
        lines.append(f"- decision:{f.decision_id} fired ({f.trigger_name}: {f.context_summary})")
    return "\n".join(lines)


def build_trigger_context(
    *,
    user_message: str = "",
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    consecutive_tool_only_rounds: int = 0,
    recent_tool_calls: Optional[list[dict]] = None,
    recent_assistant_text: str = "",
    agentic_round_seq: int = 0,
) -> TriggerContext:
    """Build a TriggerContext from explicit fields. Used in tests and as
    a fallback when the ContextVar is not bound."""
    return TriggerContext(
        user_message=str(user_message or ""),
        session_id=session_id,
        run_id=run_id,
        consecutive_tool_only_rounds=int(consecutive_tool_only_rounds or 0),
        recent_tool_calls=list(recent_tool_calls or []),
        recent_assistant_text=str(recent_assistant_text or ""),
        agentic_round_seq=int(agentic_round_seq or 0),
        timestamp=datetime.now(UTC).isoformat(),
    )


def get_current_trigger_context_or_build(
    *,
    user_message: str = "",
    session_id: Optional[str] = None,
) -> TriggerContext:
    """Return the bound ContextVar if set, else build a minimal fallback."""
    ctx = _current_trigger_context.get()
    if ctx is not None:
        return ctx
    return build_trigger_context(
        user_message=user_message,
        session_id=session_id,
    )


def bind_context(ctx: TriggerContext) -> contextvars.Token:
    """Bind the per-run TriggerContext. Caller must reset_token after use."""
    return _current_trigger_context.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    _current_trigger_context.reset(token)
