from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus

_MAX_ACTIVE_SIGNALS = 3
_SIGNAL_FADE_AFTER = timedelta(minutes=20)
_SIGNAL_RELEASE_AFTER = timedelta(minutes=45)


@dataclass(slots=True)
class EmergentSignal:
    id: str
    canonical_key: str
    signal_family: str
    signal_status: str
    lifecycle_state: str
    interpretation_state: str
    short_summary: str
    salience: float
    intensity: str
    source_hints: list[str] = field(default_factory=list)
    provenance: dict[str, object] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_grounded_at: str = ""
    fades_at: str = ""
    expires_at: str = ""
    influenced_layer: str = ""
    adopted_by: str = ""
    visibility: str = "internal-only"
    truth: str = "candidate-only"
    identity_boundary: str = "not-canonical-identity-truth"
    memory_boundary: str = "not-workspace-memory"
    action_boundary: str = "not-action"


_signals: dict[str, EmergentSignal] = {}
_released_history: list[dict[str, object]] = []
_last_daemon_run_at: str = ""
_last_daemon_result: dict[str, object] | None = None


def run_emergent_signal_daemon(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Produce a small bounded set of grounded candidate emergent signals.

    Signals are internal-only runtime support. They are never identity truth,
    workspace memory, or action authority.
    """
    global _last_daemon_run_at, _last_daemon_result

    now = datetime.now(UTC)
    now_iso = now.isoformat()
    candidates = _extract_grounded_candidates(now=now)
    grounded_keys: set[str] = set()
    created = 0
    strengthened = 0
    fading = 0
    released = 0

    for candidate in candidates[:_MAX_ACTIVE_SIGNALS]:
        grounded_keys.add(candidate["canonical_key"])
        existing = _signals.get(candidate["canonical_key"])
        if existing is None:
            signal = EmergentSignal(
                id=f"emergent-signal-{uuid4().hex}",
                canonical_key=str(candidate["canonical_key"]),
                signal_family=str(candidate["signal_family"]),
                signal_status="candidate",
                lifecycle_state="candidate",
                interpretation_state=str(candidate["interpretation_state"]),
                short_summary=str(candidate["short_summary"]),
                salience=float(candidate["salience"]),
                intensity=str(candidate["intensity"]),
                source_hints=list(candidate["source_hints"]),
                provenance=dict(candidate["provenance"]),
                created_at=now_iso,
                updated_at=now_iso,
                last_grounded_at=now_iso,
                fades_at=(now + _SIGNAL_FADE_AFTER).isoformat(),
                expires_at=(now + _SIGNAL_RELEASE_AFTER).isoformat(),
                influenced_layer=str(candidate.get("influenced_layer") or ""),
            )
            _signals[signal.canonical_key] = signal
            created += 1
            event_bus.publish(
                "runtime.emergent_signal_created",
                _event_payload(signal, trigger=trigger),
            )
            continue

        previous_lifecycle = existing.lifecycle_state
        previous_status = existing.signal_status
        existing.updated_at = now_iso
        existing.last_grounded_at = now_iso
        existing.fades_at = (now + _SIGNAL_FADE_AFTER).isoformat()
        existing.expires_at = (now + _SIGNAL_RELEASE_AFTER).isoformat()
        existing.short_summary = str(candidate["short_summary"])
        existing.salience = max(existing.salience, float(candidate["salience"]))
        existing.intensity = str(candidate["intensity"])
        existing.source_hints = list(candidate["source_hints"])
        existing.provenance = dict(candidate["provenance"])
        existing.influenced_layer = str(candidate.get("influenced_layer") or "")
        existing.lifecycle_state = "strengthening"
        if existing.salience >= 0.78:
            existing.signal_status = "emergent"
            existing.interpretation_state = "grounded-candidate"
        else:
            existing.signal_status = "candidate"
            existing.interpretation_state = str(candidate["interpretation_state"])
        if (
            previous_lifecycle != existing.lifecycle_state
            or previous_status != existing.signal_status
        ):
            strengthened += 1
            event_bus.publish(
                "runtime.emergent_signal_strengthened",
                _event_payload(existing, trigger=trigger),
            )

    for key, signal in list(_signals.items()):
        if key in grounded_keys:
            continue
        if signal.lifecycle_state == "released":
            continue
        last_grounded_at = _parse_dt(signal.last_grounded_at) or now
        if now - last_grounded_at >= _SIGNAL_RELEASE_AFTER:
            signal.lifecycle_state = "released"
            signal.updated_at = now_iso
            released += 1
            _released_history.insert(0, _serialize_signal(signal, now=now))
            _released_history[:] = _released_history[:8]
            event_bus.publish(
                "runtime.emergent_signal_released",
                _event_payload(signal, trigger=trigger),
            )
            continue
        if signal.lifecycle_state != "fading" and now - last_grounded_at >= _SIGNAL_FADE_AFTER:
            signal.lifecycle_state = "fading"
            signal.updated_at = now_iso
            fading += 1
            event_bus.publish(
                "runtime.emergent_signal_fading",
                _event_payload(signal, trigger=trigger),
            )

    _last_daemon_run_at = now_iso
    active_items = [
        item for item in _signals.values() if item.lifecycle_state != "released"
    ]
    _last_daemon_result = {
        "daemon_ran": True,
        "trigger": trigger,
        "last_visible_at": str(last_visible_at or ""),
        "created": created,
        "strengthened": strengthened,
        "fading": fading,
        "released": released,
        "grounded_candidates": len(candidates),
        "active_after_run": len(active_items),
    }
    event_bus.publish(
        "runtime.emergent_signal_daemon_ran",
        {
            "trigger": trigger,
            "created": created,
            "strengthened": strengthened,
            "fading": fading,
            "released": released,
            "grounded_candidates": len(candidates),
            "active_after_run": len(active_items),
        },
    )
    return dict(_last_daemon_result)


def build_runtime_emergent_signal_surface(*, limit: int = 8) -> dict[str, object]:
    now = datetime.now(UTC)
    items = [_serialize_signal(signal, now=now) for signal in _ordered_signals(limit)]
    active = [item for item in items if item["lifecycle_state"] != "released"]
    candidate = [item for item in active if item["signal_status"] == "candidate"]
    emergent = [item for item in active if item["signal_status"] == "emergent"]
    fading = [item for item in active if item["lifecycle_state"] == "fading"]
    latest = next(iter(active), None)
    return {
        "active": bool(active),
        "authority": "candidate-only",
        "layer_role": "runtime-support",
        "visibility": "internal-only",
        "identity_boundary": "not-canonical-identity-truth",
        "memory_boundary": "not-workspace-memory",
        "action_boundary": "not-action",
        "last_daemon_run_at": _last_daemon_run_at or None,
        "last_daemon_result": _last_daemon_result,
        "items": items,
        "recent_released": list(_released_history[: min(max(limit, 1), 5)]),
        "summary": {
            "active_count": len(active),
            "candidate_count": len(candidate),
            "emergent_count": len(emergent),
            "fading_count": len(fading),
            "released_count": len(_released_history),
            "current_signal": str((latest or {}).get("short_summary") or "No active emergent inner signal"),
            "current_status": str((latest or {}).get("signal_status") or "none"),
            "current_lifecycle_state": str((latest or {}).get("lifecycle_state") or "none"),
            "current_interpretation_state": str((latest or {}).get("interpretation_state") or "none"),
            "current_source_hints": list((latest or {}).get("source_hints") or []),
            "current_expiry_state": str((latest or {}).get("expiry_state") or "none"),
            "latest_emergent_signal": str((latest or {}).get("short_summary") or ""),
            "unknown_allowed_silent_disallowed": "runtime-observable",
            "authority": "candidate-only",
            "visibility": "internal-only",
            "identity_boundary": "not-canonical-identity-truth",
            "memory_boundary": "not-workspace-memory",
            "action_boundary": "not-action",
        },
    }


def get_emergent_signal_daemon_state() -> dict[str, object]:
    return {
        "last_run_at": _last_daemon_run_at or None,
        "last_result": _last_daemon_result,
        "tracked_signal_count": len(_signals),
        "released_history_count": len(_released_history),
    }


def _extract_grounded_candidates(*, now: datetime) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    witness = _safe_surface(
        "apps.api.jarvis_api.services.witness_signal_tracking",
        "build_runtime_witness_signal_surface",
    )
    tension = _safe_surface(
        "apps.api.jarvis_api.services.private_initiative_tension_signal_tracking",
        "build_runtime_private_initiative_tension_signal_surface",
    )
    development = _safe_surface(
        "apps.api.jarvis_api.services.development_focus_tracking",
        "build_runtime_development_focus_surface",
    )
    open_loops = _safe_surface(
        "apps.api.jarvis_api.services.open_loop_signal_tracking",
        "build_runtime_open_loop_signal_surface",
    )
    continuity = _safe_surface(
        "apps.api.jarvis_api.services.self_narrative_continuity_signal_tracking",
        "build_runtime_self_narrative_continuity_signal_surface",
    )

    inner_voice = _safe_daemon_state(
        "apps.api.jarvis_api.services.inner_voice_daemon",
        "get_inner_voice_daemon_state",
    )

    witness_title = _current_label(witness)
    tension_title = _current_label(tension)
    focus_title = _current_label(development)
    loop_title = _current_label(open_loops)
    continuity_title = _current_label(continuity)

    if witness.get("active") and tension.get("active"):
        candidates.append({
            "canonical_key": _signal_key("witness-tension", witness_title, tension_title),
            "signal_family": "witness-tension",
            "short_summary": "A small witnessed pressure may be cohering around an unresolved internal pull.",
            "salience": 0.78,
            "intensity": "medium",
            "interpretation_state": "grounded-candidate",
            "source_hints": [hint for hint in [witness_title, tension_title] if hint],
            "provenance": {
                "grounded_from": ["witness", "initiative-tension"],
                "witness_status": str((witness.get("summary") or {}).get("current_status") or "none"),
                "tension_status": str((tension.get("summary") or {}).get("current_status") or "none"),
            },
            "influenced_layer": "internal-attention",
        })

    if development.get("active") and open_loops.get("active"):
        candidates.append({
            "canonical_key": _signal_key("focus-recurrence", focus_title, loop_title),
            "signal_family": "focus-recurrence",
            "short_summary": "An internal line of work may be starting to pull harder than its named focus alone explains.",
            "salience": 0.72,
            "intensity": "medium",
            "interpretation_state": "weakly-grounded",
            "source_hints": [hint for hint in [focus_title, loop_title] if hint],
            "provenance": {
                "grounded_from": ["development-focus", "open-loop"],
                "focus_status": str((development.get("summary") or {}).get("current_status") or "none"),
                "loop_status": str((open_loops.get("summary") or {}).get("current_status") or "none"),
            },
            "influenced_layer": "open-loop-attention",
        })

    inner_voice_recent = _inner_voice_recent(inner_voice, now=now)
    if continuity.get("active") and inner_voice_recent:
        candidates.append({
            "canonical_key": _signal_key("continuity-carry", continuity_title, str(inner_voice_recent.get("focus") or "inner-voice")),
            "signal_family": "continuity-carry",
            "short_summary": "A continuity thread may be taking on a more specific internal pull without becoming identity truth.",
            "salience": 0.79,
            "intensity": "medium",
            "interpretation_state": "grounded-candidate",
            "source_hints": [
                hint
                for hint in [continuity_title, str(inner_voice_recent.get("focus") or "")]
                if hint
            ],
            "provenance": {
                "grounded_from": ["self-narrative-continuity", "inner-voice"],
                "continuity_status": str((continuity.get("summary") or {}).get("current_status") or "none"),
                "inner_voice_render_mode": str(inner_voice_recent.get("render_mode") or "unknown"),
            },
            "influenced_layer": "continuity-support",
        })

    candidates.sort(key=lambda item: float(item["salience"]), reverse=True)
    return candidates


def _ordered_signals(limit: int) -> list[EmergentSignal]:
    ordered = sorted(
        _signals.values(),
        key=lambda item: (
            1 if item.lifecycle_state == "strengthening" else 0,
            1 if item.signal_status == "emergent" else 0,
            item.updated_at,
        ),
        reverse=True,
    )
    return ordered[: max(limit, 1)]


def _serialize_signal(signal: EmergentSignal, *, now: datetime) -> dict[str, object]:
    payload = asdict(signal)
    payload["expiry_state"] = _expiry_state(signal, now=now)
    payload["authoritative"] = False
    return payload


def _event_payload(signal: EmergentSignal, *, trigger: str) -> dict[str, object]:
    return {
        "signal_id": signal.id,
        "canonical_key": signal.canonical_key,
        "signal_family": signal.signal_family,
        "signal_status": signal.signal_status,
        "lifecycle_state": signal.lifecycle_state,
        "interpretation_state": signal.interpretation_state,
        "summary": signal.short_summary,
        "source_hints": list(signal.source_hints),
        "trigger": trigger,
    }


def _expiry_state(signal: EmergentSignal, *, now: datetime) -> str:
    if signal.lifecycle_state == "released":
        return "released"
    expires_at = _parse_dt(signal.expires_at)
    fades_at = _parse_dt(signal.fades_at)
    if expires_at and now >= expires_at:
        return "expired"
    if fades_at and now >= fades_at:
        return "fading-window"
    return "live"


def _signal_key(family: str, *anchors: str) -> str:
    normalized = [anchor for anchor in (_slug(item) for item in anchors) if anchor]
    suffix = ":".join(normalized[:2]) or "unresolved"
    return f"emergent:{family}:{suffix}"


def _slug(value: str) -> str:
    return "-".join(
        part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in str(value or "")).split()[:6] if part
    )


def _current_label(surface: dict[str, object]) -> str:
    summary = surface.get("summary") or {}
    label = str(summary.get("current_signal") or "").strip()
    if label and not label.lower().startswith("no active") and label.lower() != "none":
        return label
    items = surface.get("items") or []
    if not items:
        return ""
    return str(items[0].get("title") or items[0].get("summary") or "").strip()


def _safe_surface(module_name: str, fn_name: str) -> dict[str, object]:
    try:
        module = __import__(module_name, fromlist=[fn_name])
        fn = getattr(module, fn_name)
        return dict(fn(limit=2))
    except Exception:
        return {"active": False, "items": [], "summary": {}}


def _safe_daemon_state(module_name: str, fn_name: str) -> dict[str, object]:
    try:
        module = __import__(module_name, fromlist=[fn_name])
        fn = getattr(module, fn_name)
        return dict(fn())
    except Exception:
        return {}


def _inner_voice_recent(state: dict[str, object], *, now: datetime) -> dict[str, object] | None:
    last_run_at = _parse_dt(state.get("last_run_at"))
    last_result = state.get("last_result") or {}
    if last_run_at is None or not last_result.get("inner_voice_created"):
        return None
    if now - last_run_at > timedelta(minutes=30):
        return None
    return {
        "focus": str(last_result.get("focus") or ""),
        "render_mode": str(last_result.get("render_mode") or ""),
    }


def _parse_dt(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)