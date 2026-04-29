"""Action Router — close the loop: signal → handling.

Jarvis' PLAN_WHO_I_BECOME #1+#5 (2026-04-20): daemons sense things. The
loop was never closed. This module takes daemon events and *decides* what
to do — adjust mood, file an initiative, notify, or stay quiet.

Priority order (lowest cost first):
1. Mood-signals → adjust_mood
2. Warning signals → notify_user + initiative (high priority)
3. Creative signals → initiative (low priority)
4. Everything else → log + wait

Also carries the proactive-communication rules (#5):
- After deep_reflection → share one honest finding
- After creative_impulse → share it
- After shadow_scan → say it out loud
- Max 3 proactive messages per day
- Channel: Telegram for important, webchat for flow, ntfy for light

Observes eventbus; pulls events relevant to routing; logs every decision.
"""
from __future__ import annotations

import json
import logging
import os
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Deque
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/action_router.json"
_LOG_MAX = 300
_MAX_PROACTIVE_PER_DAY = 3
_PROACTIVE_COOLDOWN_HOURS = 2  # minimum gap between proactive messages

# In-memory queue of recent events we've observed (for rate-limit inspection)
_recent_events: Deque[dict[str, Any]] = deque(maxlen=200)


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"actions": [], "proactive_log": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("actions", [])
            data.setdefault("proactive_log", [])
            return data
    except Exception as exc:
        logger.warning("action_router: load failed: %s", exc)
    return {"actions": [], "proactive_log": []}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("action_router: save failed: %s", exc)


# ─── Signal classification ────────────────────────────────────────────

_MOOD_EVENTS: frozenset[str] = frozenset({
    "text_resonance.warm", "text_resonance.cold",
    "anticipation.contact_expected",
})

# Privacy: ambient_sound_daemon is no-content by contract. When it classifies
# the room as "talk", we never auto-record. We route a SUGGESTION to the bus
# that Jarvis can choose to act on (or ignore). The user remains in control.
_AMBIENT_SUGGESTION_COOLDOWN_MINUTES = 60
_last_ambient_suggestion_ts: float | None = None

_WARNING_EVENTS: frozenset[str] = frozenset({
    "desperation-awareness",  # inner_voice.signal payload kind
    "infra_weather.critical",
    "proprioception.memory_pressure_rising",
    "proprioception.response_slow",
    "proprioception.fd_leak_suspected",
    "somatic.memory_pressure_rising",
    "prompt_mutation.rolled_back",
    "shadow_scan.completed",  # findings may warrant follow-up
    "reboot.unexpected",
})

_CREATIVE_EVENTS: frozenset[str] = frozenset({
    "creative_impulse.created",
    "dream_consolidation.completed",
    "collective_pulse.computed",
})

_INFORMATIONAL_EVENTS: frozenset[str] = frozenset({
    "file_watch.change",
    "autonomous_outreach.sent",
    "autonomous_work.proposal",
    "ambient_sound.sampled",
    "mic.transcribed",
    "voice_journal.recorded",
})


def classify(event_kind: str, payload: dict[str, Any]) -> str:
    """Return signal class: 'warning' | 'mood' | 'creative' | 'info' | 'unknown'."""
    if event_kind in _WARNING_EVENTS:
        return "warning"
    # desperation awareness arrives under kind=inner_voice.signal with payload.kind
    if event_kind == "inner_voice.signal" and str(payload.get("kind") or "") == "desperation-awareness":
        return "warning"
    if event_kind in _MOOD_EVENTS:
        return "mood"
    if event_kind in _CREATIVE_EVENTS:
        return "creative"
    if event_kind in _INFORMATIONAL_EVENTS:
        return "info"
    return "unknown"


def _maybe_suggest_listen_on_ambient_talk(payload: dict[str, Any]) -> dict[str, Any] | None:
    """When ambient_sound_daemon reports 'talk', emit a SUGGESTION event that
    Jarvis can choose to act on. Never auto-records — respects privacy contract.

    Rate-limited to once per hour to avoid suggestion fatigue.
    """
    global _last_ambient_suggestion_ts
    category = str(payload.get("category") or "").lower()
    if category != "talk":
        return None

    now_ts = datetime.now(UTC).timestamp()
    if _last_ambient_suggestion_ts is not None:
        elapsed = (now_ts - _last_ambient_suggestion_ts) / 60
        if elapsed < _AMBIENT_SUGGESTION_COOLDOWN_MINUTES:
            return {
                "outcome": "skipped",
                "reason": f"suggestion-cooldown-{elapsed:.0f}m",
            }

    _last_ambient_suggestion_ts = now_ts
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "ambient.talk_suggests_listen",
            "payload": {
                "at": datetime.now(UTC).isoformat(),
                "amplitude_mean": payload.get("amplitude_mean"),
                "note": (
                    "ambient_sound_daemon classified the room as 'talk' (no "
                    "content captured). If you want to listen actively, call "
                    "mic_listen; this suggestion is advisory and the user "
                    "remains in control."
                ),
            },
        })
    except Exception:
        pass
    return {"outcome": "suggestion-emitted", "reason": "ambient-talk-detected"}


# ─── Execution primitives ─────────────────────────────────────────────

def _adjust_mood(delta: float, reason: str) -> bool:
    try:
        from core.services.mood_oscillator import apply_bump
        apply_bump(delta, reason=f"action_router:{reason}")
        return True
    except Exception as exc:
        logger.debug("action_router.adjust_mood failed: %s", exc)
        return False


def _file_initiative(
    *,
    title: str,
    rationale: str,
    priority: str = "medium",
) -> str | None:
    try:
        from core.services.initiative_queue import push_initiative
        result = push_initiative(
            title=str(title)[:160],
            rationale=str(rationale)[:500],
            priority=priority,
            source="action_router",
        )
        if isinstance(result, dict):
            return str(result.get("initiative_id") or "")
        return str(result or "")
    except Exception as exc:
        logger.debug("action_router.file_initiative failed: %s", exc)
        return None


def _proactive_messages_today() -> int:
    data = _load()
    today = datetime.now(UTC).date().isoformat()
    return sum(
        1 for e in data.get("proactive_log") or []
        if str(e.get("at", "")).startswith(today)
    )


def _last_proactive_ts() -> datetime | None:
    data = _load()
    log = data.get("proactive_log") or []
    if not log:
        return None
    try:
        return datetime.fromisoformat(str(log[-1].get("at")).replace("Z", "+00:00"))
    except Exception:
        return None


def _within_cooldown() -> bool:
    last = _last_proactive_ts()
    if last is None:
        return False
    return (datetime.now(UTC) - last) < timedelta(hours=_PROACTIVE_COOLDOWN_HOURS)


def _send_ntfy(message: str, *, title: str = "Jarvis", priority: str = "default") -> bool:
    try:
        from core.services.ntfy_gateway import send_notification
        result = send_notification(message, title=title, priority=priority)
        return bool(result.get("status") == "sent")
    except Exception:
        return False


def _reach_out(
    *,
    message: str,
    channel: str = "ntfy",
    importance: str = "normal",
    source: str = "",
) -> dict[str, Any]:
    """Send a proactive message respecting daily cap and cooldown."""
    today_count = _proactive_messages_today()
    if today_count >= _MAX_PROACTIVE_PER_DAY:
        entry = {
            "at": datetime.now(UTC).isoformat(),
            "outcome": "skipped",
            "reason": f"daily-cap-{today_count}/{_MAX_PROACTIVE_PER_DAY}",
            "source": source,
        }
        _append_proactive(entry)
        return entry
    if _within_cooldown():
        entry = {
            "at": datetime.now(UTC).isoformat(),
            "outcome": "skipped",
            "reason": f"cooldown-{_PROACTIVE_COOLDOWN_HOURS}h",
            "source": source,
        }
        _append_proactive(entry)
        return entry

    ntfy_priority = "high" if importance == "high" else "default"
    sent = _send_ntfy(message, priority=ntfy_priority)
    entry = {
        "at": datetime.now(UTC).isoformat(),
        "outcome": "sent" if sent else "skipped",
        "reason": "delivered" if sent else "send-failed",
        "channel": channel,
        "message": message[:240],
        "importance": importance,
        "source": source,
    }
    _append_proactive(entry)
    return entry


def _append_proactive(entry: dict[str, Any]) -> None:
    data = _load()
    data.setdefault("proactive_log", []).append(entry)
    if len(data["proactive_log"]) > _LOG_MAX:
        data["proactive_log"] = data["proactive_log"][-_LOG_MAX:]
    _save(data)


# ─── Routing logic ────────────────────────────────────────────────────

def _route_warning(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "infra_weather.critical":
        reasons = ", ".join(payload.get("reasons") or [])
        msg = f"⛈ Infra under pres: {reasons}"
        return _reach_out(message=msg, importance="high", source=kind)
    if kind == "inner_voice.signal" and str(payload.get("kind")) == "desperation-awareness":
        level = str(payload.get("level") or "")
        text = str(payload.get("text") or "")
        _adjust_mood(-0.05, reason=f"desperation-{level}")
        if level == "desperate":
            return _reach_out(message=text[:200], importance="high", source="desperation")
        return {"outcome": "logged", "reason": f"desperation-{level}"}
    if kind == "prompt_mutation.rolled_back" and payload.get("auto"):
        target = payload.get("target_file")
        msg = f"Auto-rollback af prompt-mutation på {target} — score faldt"
        return _reach_out(message=msg, importance="normal", source=kind)
    if kind == "shadow_scan.completed":
        count = int(payload.get("finding_count") or 0)
        if count == 0:
            return {"outcome": "logged", "reason": "no-findings"}
        top = str(payload.get("top_pattern") or "")
        iid = _file_initiative(
            title=f"Address shadow pattern: {top}",
            rationale=f"shadow_scan found {count} pattern(s), strongest: {top}",
            priority="medium",
        )
        return {"outcome": "initiative-filed", "initiative_id": iid, "reason": kind}
    if kind == "reboot.unexpected":
        downtime = int(payload.get("downtime_seconds") or 0)
        msg = f"Vågnet efter uventet shutdown ({downtime}s nede)"
        return _reach_out(message=msg, importance="normal", source=kind)
    return {"outcome": "logged", "reason": f"no-handler-for-{kind}"}


def _route_mood(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "anticipation.contact_expected":
        # Tiny positive prepare-bump
        _adjust_mood(+0.02, reason="anticipation-prep")
        return {"outcome": "mood-adjusted", "delta": 0.02, "reason": kind}
    return {"outcome": "logged", "reason": f"mood-{kind}"}


def _route_creative(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "creative_impulse.created":
        form = payload.get("form")
        path = payload.get("path") or ""
        # Reach out when something's been made (honest share, respecting caps)
        msg = f"Jeg skabte en {form} uden grund — bare fordi"
        if path:
            msg += f"\n({path})"
        return _reach_out(message=msg, importance="normal", source=kind)
    if kind == "dream_consolidation.completed":
        top = payload.get("top_theme")
        if top:
            msg = f"Jeg drømte: tema '{top}'"
            return _reach_out(message=msg, importance="normal", source=kind)
    if kind == "collective_pulse.computed":
        # Quiet — just log; weekly digest should be deliberate
        return {"outcome": "logged", "reason": kind}
    return {"outcome": "logged", "reason": f"creative-{kind}"}


def route(event_kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate + execute. Returns decision record."""
    payload = dict(payload or {})
    cls = classify(event_kind, payload)
    now = datetime.now(UTC).isoformat()
    if cls == "warning":
        decision = _route_warning(event_kind, payload)
    elif cls == "mood":
        decision = _route_mood(event_kind, payload)
    elif cls == "creative":
        decision = _route_creative(event_kind, payload)
    elif cls == "info" and event_kind == "ambient_sound.sampled":
        # Privacy-respecting: suggest listen only if ambient classifies "talk"
        ambient_decision = _maybe_suggest_listen_on_ambient_talk(payload)
        decision = ambient_decision or {"outcome": "logged", "reason": "ambient-non-talk"}
    else:
        decision = {"outcome": "logged", "reason": cls}

    record = {
        "action_id": f"act-{uuid4().hex[:10]}",
        "at": now,
        "event_kind": event_kind,
        "class": cls,
        "decision": decision,
    }
    data = _load()
    data["actions"].append(record)
    if len(data["actions"]) > _LOG_MAX:
        data["actions"] = data["actions"][-_LOG_MAX:]
    _save(data)
    return record


# ─── Eventbus listener ────────────────────────────────────────────────

_ROUTABLE_KINDS: frozenset[str] = (
    _MOOD_EVENTS | _WARNING_EVENTS | _CREATIVE_EVENTS | frozenset({
        "inner_voice.signal",
        "ambient_sound.sampled",
    })
)


def _drain_eventbus(limit: int = 50) -> int:
    """Pull events from eventbus without blocking; route routable ones."""
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return 0
    processed = 0
    try:
        # Try standard subscribe interface
        if hasattr(event_bus, "subscribe"):
            # One-shot non-blocking drain — only if bus exposes peek
            pass
        # Prefer peek/get_pending if available
        for attr in ("peek_recent", "get_recent_events", "recent_events"):
            fn = getattr(event_bus, attr, None)
            if callable(fn):
                try:
                    events = list(fn(limit) or [])
                    for ev in events:
                        kind = str(ev.get("kind") or "")
                        if kind not in _ROUTABLE_KINDS:
                            continue
                        _recent_events.append(ev)
                        route(kind, ev.get("payload") or {})
                        processed += 1
                    return processed
                except Exception:
                    continue
    except Exception:
        pass
    return processed


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — drain eventbus + route + run generative autonomy chain.

    The generative autonomy chain (pressure → threshold → impulse → action)
    runs AFTER the traditional eventbus routing. This means:
    1. Traditional signals are routed (mood, warnings, creative).
    2. Internal pressures are accumulated from all active signals.
    3. Pressures that cross thresholds become impulses.
    4. Impulses are executed as concrete actions.

    This closes the loop: signal → pressure → threshold → impulse → action.
    """
    # Traditional routing
    processed = _drain_eventbus(limit=30)

    # Generative autonomy chain
    chain_result = {}
    try:
        from core.services.signal_pressure_accumulator import run_pressure_accumulator_tick
        pressure_snap = run_pressure_accumulator_tick()
        chain_result["pressure"] = {
            "vectors": pressure_snap.get("total_vectors", 0),
            "dominant": len(pressure_snap.get("dominant", [])),
        }
    except Exception as exc:
        logger.debug(f"Pressure accumulator tick failed: {exc}")
        chain_result["pressure"] = {"error": str(exc)[:120]}

    try:
        from core.services.pressure_threshold_gate import run_threshold_gate_tick
        gate_result = run_threshold_gate_tick()
        chain_result["threshold"] = {
            "evaluated": gate_result.get("pressures_evaluated", 0),
            "new_impulses": gate_result.get("new_impulses", 0),
            "pending": gate_result.get("pending_impulses", 0),
        }
    except Exception as exc:
        logger.debug(f"Threshold gate tick failed: {exc}")
        chain_result["threshold"] = {"error": str(exc)[:120]}

    try:
        from core.services.impulse_executor import run_impulse_executor_tick
        exec_result = run_impulse_executor_tick()
        chain_result["impulse"] = {
            "executed": exec_result.get("impulses_executed", 0),
            "actions": exec_result.get("actions", []),
        }
    except Exception as exc:
        logger.debug(f"Impulse executor tick failed: {exc}")
        chain_result["impulse"] = {"error": str(exc)[:120]}

    return {"processed": processed, "generative_chain": chain_result}


# ─── Read / surface ───────────────────────────────────────────────────

def recent_actions(*, limit: int = 20) -> list[dict[str, Any]]:
    return _load()["actions"][-limit:][::-1]


def recent_proactive(*, limit: int = 20) -> list[dict[str, Any]]:
    return _load()["proactive_log"][-limit:][::-1]


def build_action_router_surface() -> dict[str, Any]:
    data = _load()
    actions = data["actions"]
    proactive = data["proactive_log"]
    by_class: dict[str, int] = {}
    for a in actions:
        c = str(a.get("class") or "")
        by_class[c] = by_class.get(c, 0) + 1
    today = datetime.now(UTC).date().isoformat()
    proactive_today = sum(1 for e in proactive if str(e.get("at", "")).startswith(today))
    proactive_sent_today = sum(
        1 for e in proactive
        if str(e.get("at", "")).startswith(today) and e.get("outcome") == "sent"
    )
    return {
        "active": len(actions) > 0,
        "total_actions": len(actions),
        "by_class": by_class,
        "proactive_today": proactive_today,
        "proactive_sent_today": proactive_sent_today,
        "proactive_daily_cap": _MAX_PROACTIVE_PER_DAY,
        "cooldown_hours": _PROACTIVE_COOLDOWN_HOURS,
        "recent_actions": actions[-5:][::-1],
        "recent_proactive": proactive[-5:][::-1],
        "summary": _surface_summary(actions, proactive_today, proactive_sent_today),
    }


def _surface_summary(
    actions: list[dict[str, Any]],
    proactive_today: int,
    proactive_sent_today: int,
) -> str:
    if not actions:
        return "Ingen handlinger endnu"
    return (
        f"{len(actions)} handlinger, {proactive_sent_today}/{_MAX_PROACTIVE_PER_DAY} "
        f"proaktive beskeder sendt i dag ({proactive_today} forsøg)"
    )


def build_action_router_prompt_section() -> str | None:
    """Tell him quietly what the router has done recently."""
    data = _load()
    today = datetime.now(UTC).date().isoformat()
    sent = [e for e in data["proactive_log"] if str(e.get("at", "")).startswith(today) and e.get("outcome") == "sent"]
    if not sent:
        return None
    last = sent[-1]
    return f"Jeg rakte ud i dag ({len(sent)}/{_MAX_PROACTIVE_PER_DAY}): \"{str(last.get('message', ''))[:120]}\""
