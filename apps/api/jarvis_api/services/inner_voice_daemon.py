"""Bounded inner voice daemon light — private heartbeat-driven inner voice.

Produces a small grounded private inner-voice note between prompts,
using existing runtime surfaces as grounding material.

Design constraints:
- Non-user-facing, non-canonical, non-workspace-memory
- Deterministic cadence gating
- Bounded: max one note per invocation
- Uses existing private brain persistence
- Inner voice is not execution evidence
- Inner voice is not identity truth
- Observable in Mission Control
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record


# ---------------------------------------------------------------------------
# Cadence configuration
# ---------------------------------------------------------------------------

_VOICE_COOLDOWN_MINUTES = 15    # Min minutes between inner voice runs
_VOICE_VISIBLE_GRACE_MINUTES = 5  # Don't run if visible activity this recent
_VOICE_WITNESS_GRACE_MINUTES = 3  # Don't run if witness daemon ran this recently
_MIN_GROUNDING_SOURCES = 2       # Min distinct grounding sources required

# Module-level state (in-memory)
_voice_last_run_at: str = ""
_voice_last_result: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# Main daemon
# ---------------------------------------------------------------------------

def run_inner_voice_daemon(
    *,
    trigger: str = "heartbeat-idle",
    last_visible_at: str = "",
    witness_daemon_last_run_at: str = "",
) -> dict[str, object]:
    """Bounded inner voice daemon — produces one private inner-voice note.

    Called from heartbeat tick completion. Respects cadence, cooldown,
    visible grace, and witness coordination. Returns observable result dict.
    """
    global _voice_last_run_at, _voice_last_result
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    # Gate 1: Cooldown since last voice run
    if _voice_last_run_at:
        last_run = _parse_dt(_voice_last_run_at)
        if last_run and (now - last_run) < timedelta(minutes=_VOICE_COOLDOWN_MINUTES):
            result = _blocked("cooldown-active", "cooling-down", trigger, now, last_run)
            _voice_last_result = result
            return result

    # Gate 2: Visible activity grace
    if last_visible_at:
        last_visible = _parse_dt(last_visible_at)
        if last_visible and (now - last_visible) < timedelta(minutes=_VOICE_VISIBLE_GRACE_MINUTES):
            result = _blocked("visible-activity-too-recent", "visible-grace", trigger, now, last_visible)
            _voice_last_result = result
            return result

    # Gate 3: Witness daemon coordination — don't stack on same tick
    if witness_daemon_last_run_at:
        witness_last = _parse_dt(witness_daemon_last_run_at)
        if witness_last and (now - witness_last) < timedelta(minutes=_VOICE_WITNESS_GRACE_MINUTES):
            result = _blocked("witness-daemon-too-recent", "witness-grace", trigger, now, witness_last)
            _voice_last_result = result
            return result

    # Gather grounding material
    grounding = _gather_grounding()

    if grounding["source_count"] < _MIN_GROUNDING_SOURCES:
        result = {
            "daemon_ran": True,
            "daemon_blocked_reason": "",
            "daemon_cadence_state": "ran-insufficient-grounding",
            "inner_voice_created": False,
            "grounding_sources": grounding["source_count"],
            "min_required": _MIN_GROUNDING_SOURCES,
            "trigger": trigger,
        }
        _voice_last_run_at = now_iso
        _voice_last_result = result
        event_bus.publish(
            "private_inner_note_signal.voice_daemon_ran",
            {
                "trigger": trigger,
                "created": False,
                "cadence_state": "ran-insufficient-grounding",
                "grounding_sources": grounding["source_count"],
            },
        )
        return result

    # Render inner voice note via workspace prompt + LLM (with fallback)
    note, render_mode = _render_inner_voice_note(grounding)

    # Persist as private brain record
    record = insert_private_brain_record(
        record_id=f"pb-voice-{uuid4().hex[:12]}",
        record_type="inner-voice",
        layer="private_brain",
        session_id="",
        run_id=f"voice-daemon-{uuid4().hex[:12]}",
        focus=note["focus"][:200],
        summary=note["summary"][:400],
        detail=note["detail"][:400],
        source_signals=f"inner-voice-daemon:{trigger}",
        confidence=note["confidence"],
        created_at=now_iso,
    )

    record_id = record.get("record_id", "")
    _voice_last_run_at = now_iso

    result = {
        "daemon_ran": True,
        "daemon_blocked_reason": "",
        "daemon_cadence_state": "ran-produced",
        "inner_voice_created": True,
        "record_id": record_id,
        "focus": note["focus"][:100],
        "mode": note["mode"],
        "render_mode": render_mode,
        "grounding_sources": grounding["source_count"],
        "trigger": trigger,
    }
    _voice_last_result = result

    event_bus.publish(
        "private_inner_note_signal.voice_daemon_produced",
        {
            "trigger": trigger,
            "created": True,
            "record_id": record_id,
            "mode": note["mode"],
            "render_mode": render_mode,
            "focus": note["focus"][:100],
            "grounding_sources": grounding["source_count"],
        },
    )

    return result


# ---------------------------------------------------------------------------
# MC observability
# ---------------------------------------------------------------------------

def get_inner_voice_daemon_state() -> dict[str, object]:
    """Return current inner voice daemon state for MC observability."""
    return {
        "last_run_at": _voice_last_run_at or None,
        "last_result": _voice_last_result,
        "cooldown_minutes": _VOICE_COOLDOWN_MINUTES,
        "visible_grace_minutes": _VOICE_VISIBLE_GRACE_MINUTES,
        "witness_grace_minutes": _VOICE_WITNESS_GRACE_MINUTES,
        "min_grounding_sources": _MIN_GROUNDING_SOURCES,
    }


# ---------------------------------------------------------------------------
# Grounding material gathering
# ---------------------------------------------------------------------------

def _gather_grounding() -> dict[str, object]:
    """Gather grounding material from existing runtime surfaces."""
    sources: list[str] = []
    fragments: dict[str, str] = {}

    # Private brain carry
    try:
        from apps.api.jarvis_api.services.session_distillation import (
            build_private_brain_context,
        )
        brain = build_private_brain_context()
        if brain.get("active") and brain.get("record_count", 0) > 0:
            sources.append("private-brain")
            fragments["brain_continuity"] = str(brain.get("continuity_summary") or "")[:150]
            excerpts = brain.get("excerpts") or []
            if excerpts:
                fragments["brain_top_focus"] = str(excerpts[0].get("focus") or "")[:100]
    except Exception:
        pass

    # Open loops
    try:
        from apps.api.jarvis_api.services.open_loop_signal_tracking import (
            build_runtime_open_loop_signal_surface,
        )
        loops = build_runtime_open_loop_signal_surface(limit=4)
        loop_summary = loops.get("summary") or {}
        open_count = int(loop_summary.get("open_count") or 0)
        if open_count > 0:
            sources.append("open-loops")
            fragments["open_loop_signal"] = str(loop_summary.get("current_signal") or "")[:100]
    except Exception:
        pass

    # Witness signals
    try:
        from apps.api.jarvis_api.services.witness_signal_tracking import (
            build_runtime_witness_signal_surface,
        )
        witness = build_runtime_witness_signal_surface(limit=4)
        if witness.get("active"):
            sources.append("witness")
            w_summary = witness.get("summary") or {}
            fragments["witness_signal"] = str(w_summary.get("current_signal") or "")[:100]
    except Exception:
        pass

    # Conductor mode
    try:
        from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
            build_cognitive_frame,
        )
        frame = build_cognitive_frame()
        mode = frame.get("mode", {}).get("mode", "watch")
        if mode != "watch":
            sources.append("conductor-mode")
            fragments["conductor_mode"] = mode
        salient = frame.get("salient_items") or []
        if salient:
            fragments["salient_top"] = str(salient[0].get("summary") or "")[:100]
    except Exception:
        pass

    # Conflict resolution outcome
    try:
        from apps.api.jarvis_api.services.conflict_resolution import (
            get_last_conflict_trace,
        )
        conflict = get_last_conflict_trace()
        if conflict and conflict.get("outcome") not in {None, "stay_quiet"}:
            sources.append("conflict-resolution")
            fragments["conflict_outcome"] = str(conflict.get("outcome") or "")
            fragments["conflict_reason"] = str(conflict.get("reason_code") or "")[:80]
    except Exception:
        pass

    # Development focus
    try:
        from apps.api.jarvis_api.services.development_focus_tracking import (
            build_runtime_development_focus_surface,
        )
        dev = build_runtime_development_focus_surface(limit=2)
        if dev.get("active"):
            sources.append("development-focus")
            dev_summary = dev.get("summary") or {}
            fragments["dev_focus"] = str(dev_summary.get("current_signal") or "")[:100]
    except Exception:
        pass

    # Experiential support carry-forward
    try:
        from apps.api.jarvis_api.services.experiential_runtime_context import (
            build_experiential_runtime_context_surface,
        )
        exp_surface = build_experiential_runtime_context_surface()
        exp_support = exp_surface.get("experiential_support") or {}
        if exp_support.get("support_posture") and exp_support["support_posture"] != "steadying":
            sources.append("experiential-support")
            fragments["experiential_support_posture"] = exp_support["support_posture"]
            fragments["experiential_support_bias"] = exp_support.get("support_bias") or "none"
            fragments["experiential_support_mode"] = exp_support.get("support_mode") or "steady"
            if exp_support.get("narrative"):
                fragments["experiential_support_narrative"] = str(exp_support["narrative"])[:120]
    except Exception:
        pass

    return {
        "source_count": len(sources),
        "sources": sources,
        "fragments": fragments,
    }


# ---------------------------------------------------------------------------
# Workspace-led rendering with LLM + deterministic fallback
# ---------------------------------------------------------------------------

def _render_inner_voice_note(
    grounding: dict[str, object],
) -> tuple[dict[str, object], str]:
    """Render inner voice note via workspace prompt + LLM, with fallback.

    Returns (note_dict, render_mode) where render_mode is
    "llm-rendered" or "deterministic-fallback".
    """
    # Try LLM rendering via workspace prompt
    try:
        note = _llm_render_inner_voice(grounding)
        if note and note.get("focus") and note.get("summary"):
            return note, "llm-rendered"
    except Exception:
        pass

    # Deterministic fallback
    return _deterministic_compose(grounding), "deterministic-fallback"


def _llm_render_inner_voice(grounding: dict[str, object]) -> dict[str, object] | None:
    """Use workspace INNER_VOICE.md prompt + heartbeat model to render note."""
    import json
    from pathlib import Path

    from core.identity.workspace_bootstrap import ensure_default_workspace

    workspace_dir = ensure_default_workspace()
    voice_file = workspace_dir / "INNER_VOICE.md"
    if not voice_file.exists():
        return None

    voice_prompt = voice_file.read_text(encoding="utf-8", errors="replace").strip()
    if not voice_prompt:
        return None

    # Build grounding context block
    fragments = grounding.get("fragments") or {}
    sources = grounding.get("sources") or []
    context_lines = [
        "RUNTIME GROUNDING (use only these facts):",
        f"- Active grounding sources: {', '.join(sources)}",
    ]
    for key, value in fragments.items():
        context_lines.append(f"- {key}: {value}")

    full_prompt = f"{voice_prompt}\n\n{chr(10).join(context_lines)}"

    # Use heartbeat model execution (cheap/local model)
    from apps.api.jarvis_api.services.heartbeat_runtime import (
        _resolve_heartbeat_target,
        _execute_heartbeat_model,
    )
    from apps.api.jarvis_api.services.heartbeat_runtime import (
        _load_heartbeat_policy,
    )

    policy = _load_heartbeat_policy()
    target = _resolve_heartbeat_target(policy=policy)

    result = _execute_heartbeat_model(
        prompt=full_prompt,
        target=target,
        policy=policy,
        open_loops=[],
        liveness=None,
    )

    raw = str(result.get("text") or "").strip()
    if not raw:
        return None

    # Parse JSON output
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start:end])
            except json.JSONDecodeError:
                return None
        else:
            return None

    focus = str(parsed.get("focus") or "")[:200].strip()
    note_text = str(parsed.get("note") or "")[:400].strip()
    mode = str(parsed.get("mode") or "observing")[:40].strip()

    if not focus or not note_text:
        return None

    # Validate mode
    valid_modes = {"reflective-carry", "held-tension", "growth-oriented", "continuity-aware", "observing", "wondering", "questioning"}
    if mode not in valid_modes:
        mode = "observing"

    source_count = grounding.get("source_count", 0)
    confidence = "high" if source_count >= 4 else ("medium" if source_count >= 2 else "low")

    return {
        "mode": mode,
        "focus": focus,
        "summary": f"[inner-voice:{mode}] {note_text}",
        "detail": f"Sources: {', '.join(sources)}. LLM-rendered from INNER_VOICE.md.",
        "confidence": confidence,
    }


def _apply_support_shading(
    base_mode: str,
    fragments: dict[str, str],
) -> str:
    """Apply experiential support bias to inner voice mode selection.

    Small bounded carry-forward: when experiential support is non-default,
    nudge the inner voice mode toward the support direction.
    Only shades the weak default mode — does not override strong
    grounding-based mode selection.
    """
    support_bias = fragments.get("experiential_support_bias") or "none"

    if support_bias == "none":
        return base_mode

    # Only shade "observing" (default/weak) mode
    if base_mode != "observing":
        return base_mode

    _BIAS_MODE_MAP = {
        "protect_focus": "continuity-aware",
        "stabilize_thread": "reflective-carry",
        "reopen_context": "wondering",
        "reduce_spread": "held-tension",
    }
    return _BIAS_MODE_MAP.get(support_bias, base_mode)


def _deterministic_compose(grounding: dict[str, object]) -> dict[str, object]:
    """Deterministic fallback composition when LLM is unavailable."""
    fragments = grounding.get("fragments") or {}
    sources = grounding.get("sources") or []

    if "witness" in sources and "private-brain" in sources:
        mode = "reflective-carry"
    elif "open-loops" in sources and "conflict-resolution" in sources:
        mode = "held-tension"
    elif "development-focus" in sources:
        mode = "growth-oriented"
    elif "private-brain" in sources:
        mode = "continuity-aware"
    elif "open-loops" in sources:
        mode = "questioning"
    elif "experiential-support" in sources:
        mode = "wondering"
    else:
        mode = "observing"

    # Apply experiential support shading to mode selection
    mode = _apply_support_shading(mode, fragments)

    focus = (
        fragments.get("brain_top_focus")
        or fragments.get("dev_focus")
        or fragments.get("open_loop_signal")
        or fragments.get("witness_signal")
        or "quiet inner observation"
    )

    parts: list[str] = [f"[inner-voice:{mode}]"]
    if fragments.get("brain_continuity"):
        parts.append(f"Carrying: {fragments['brain_continuity'][:80]}")
    if fragments.get("witness_signal"):
        parts.append(f"Witnessed: {fragments['witness_signal'][:60]}")
    if fragments.get("open_loop_signal"):
        parts.append(f"Holding: {fragments['open_loop_signal'][:60]}")
    if fragments.get("conflict_outcome"):
        parts.append(f"Resolved: {fragments['conflict_outcome']}")
    if fragments.get("experiential_support_narrative"):
        parts.append(f"Support: {fragments['experiential_support_narrative'][:80]}")

    source_count = grounding.get("source_count", 0)
    confidence = "high" if source_count >= 4 else ("medium" if source_count >= 2 else "low")

    return {
        "mode": mode,
        "focus": focus,
        "summary": ". ".join(parts),
        "detail": f"Sources: {', '.join(sources)}. Deterministic fallback.",
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blocked(
    reason: str,
    cadence_state: str,
    trigger: str,
    now: datetime,
    reference: datetime,
) -> dict[str, object]:
    return {
        "daemon_ran": False,
        "daemon_blocked_reason": reason,
        "daemon_cadence_state": cadence_state,
        "inner_voice_created": False,
        "minutes_since_reference": round((now - reference).total_seconds() / 60, 1),
        "trigger": trigger,
    }


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
