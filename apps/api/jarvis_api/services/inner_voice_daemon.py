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

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record


# ---------------------------------------------------------------------------
# Cadence configuration
# ---------------------------------------------------------------------------

_VOICE_COOLDOWN_MINUTES = 5     # Min minutes between inner voice runs
_VOICE_VISIBLE_GRACE_MINUTES = 2  # Don't run if visible activity this recent
_VOICE_WITNESS_GRACE_MINUTES = 1  # Don't run if witness daemon ran this recently
_MIN_GROUNDING_SOURCES = 1       # One source is enough for a thought
_INNER_VOICE_LIVING_MODES = {
    "searching",
    "circling",
    "carrying",
    "pulled",
    "witness-steady",
    "work-steady",
}
_INNER_VOICE_META_PATTERNS = (
    r"\battempt\s*\d+\b",
    r"\bmore mood[- ]driven\b",
    r"\ba bit too long\b",
    r"\btoo long\b",
    r"\ba bit too technical\b",
    r"\btoo technical\b",
    r"\banalytical\b",
    r"\brefining\s+for\b",
    r"\bfor flow(?:\s+and\s+mood)?\b",
    r"\bfor mood\b",
    r"\bflow and mood\b",
    r"\badjusting tone\b",
    r"\btuning (?:for )?(?:flow|mood|tone)\b",
    r"\bslightly anxious\b",
    r"\bversion\s*\d+\b",
    r"\bdraft\s*\d+\b",
    r"\brewrite\b",
    r"\brevision\b",
    r"\blet me think\b",
    r"\bi should (?:try|think|consider|focus|write)\b",
    r"\bi need to\b",
    r"\bi want to\b",
    r"\bi'll try\b",
    r"\bmaybe i should\b",
)
_INNER_VOICE_META_LINE_PREFIXES = (
    "attempt ",
    "a bit too long",
    "too long",
    "refining for",
    "for flow",
    "for mood",
    "adjusting tone",
    "tuning for",
    "more mood-driven",
    "analytical",
    "a bit too technical",
    "too technical",
    "note:",
    "revision:",
    "draft:",
    "version:",
)

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

    # 5.8 Play mode — bypass grounding requirement during dreaming phase
    in_play_mode = False
    try:
        from apps.api.jarvis_api.services.living_heartbeat_cycle import determine_life_phase
        phase = determine_life_phase()
        in_play_mode = bool(phase.get("play_mode"))
    except Exception:
        pass

    # Personality bearing may tint an existing thought, but is too weak to
    # justify producing an inner voice note on its own.
    if grounding["source_count"] == 0:
        try:
            from core.runtime.db import get_latest_cognitive_personality_vector
            pv = get_latest_cognitive_personality_vector()
            if pv:
                grounding.setdefault("fragments", {})["personality_bearing"] = str(pv.get("current_bearing") or "")
        except Exception:
            pass

    if grounding["source_count"] < _MIN_GROUNDING_SOURCES and not in_play_mode:
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
        session_id="heartbeat",
        run_id=f"voice-daemon-{uuid4().hex[:12]}",
        focus=note["focus"][:200],
        summary=note["summary"][:400],
        detail=note["detail"][:400],
        source_signals=f"inner-voice-daemon:{trigger}",
        confidence=note["confidence"],
        created_at=now_iso,
    )

    record_id = record.get("record_id", "")
    run_id = record.get("run_id", f"voice-daemon-{uuid4().hex[:12]}")
    _voice_last_run_at = now_iso

    # Also write to protected_inner_voices so the UI panel updates
    try:
        from core.runtime.db import record_protected_inner_voice
        record_protected_inner_voice(
            voice_id=f"voice-{uuid4().hex[:12]}",
            source="inner-voice-daemon",
            run_id=run_id,
            work_id="",
            mood_tone=note.get("mode", "thinking"),
            self_position=note.get("focus", "")[:100],
            current_concern=str(note.get("initiative") or "")[:200],
            current_pull=note.get("focus", "")[:200],
            voice_line=note.get("summary", "")[:400],
            created_at=now_iso,
        )
    except Exception:
        pass

    # Initiative detection — check both LLM-returned initiative and text scanning
    initiative = note.get("initiative")
    initiative_detected = bool(initiative)
    if not initiative_detected:
        initiative_detected = _thought_contains_initiative(note.get("summary") or "")
        if initiative_detected:
            initiative = _extract_initiative_from_thought(note.get("summary") or "")

    # Push to initiative queue if detected
    if initiative_detected and initiative:
        try:
            from apps.api.jarvis_api.services.initiative_queue import push_initiative
            push_initiative(
                focus=str(initiative)[:200],
                source="inner-voice",
                source_id=record_id,
            )
        except Exception:
            pass

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
        "initiative_detected": initiative_detected,
        "initiative": str(initiative or "")[:200],
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
            "initiative_detected": initiative_detected,
            "initiative": str(initiative or "")[:100],
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
        if mode:
            fragments["conductor_mode"] = str(mode)
        if mode != "watch":
            sources.append("conductor-mode")
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
        continuity = exp_surface.get("experiential_continuity") or {}
        influence = exp_surface.get("experiential_influence") or {}
        exp_support = exp_surface.get("experiential_support") or {}
        continuity_state = str(continuity.get("continuity_state") or "")
        if continuity_state and continuity_state not in {"stable", "none"}:
            sources.append("experiential-continuity")
            fragments["experiential_continuity_state"] = continuity_state
            if continuity.get("narrative"):
                fragments["experiential_continuity_narrative"] = str(
                    continuity["narrative"]
                )[:120]
        influence_posture = str(influence.get("attentional_posture") or "")
        initiative_shading = str(influence.get("initiative_shading") or "")
        cognitive_bearing = str(influence.get("cognitive_bearing") or "")
        if influence_posture:
            fragments["experiential_attentional_posture"] = influence_posture
        if initiative_shading:
            fragments["experiential_initiative_shading"] = initiative_shading
        if cognitive_bearing:
            fragments["experiential_cognitive_bearing"] = cognitive_bearing
        if influence.get("narrative"):
            fragments["experiential_influence_narrative"] = str(
                influence["narrative"]
            )[:120]
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
        line = _render_grounding_fragment(str(key), str(value))
        if line:
            context_lines.append(f"- {line}")

    # 1.5 Inner voice chaining — feed previous thought
    try:
        from core.runtime.db import get_protected_inner_voice
        prev_voice = get_protected_inner_voice()
        if prev_voice:
            prev = _sanitize_previous_inner_voice(
                str(prev_voice.get("enriched_voice_line") or prev_voice.get("voice_line") or "")[:200]
            )
            if prev:
                context_lines.append(f"- Previous thought: {prev}")
    except Exception:
        pass

    context_lines.extend(
        [
            "- Inner voice may remain unresolved; candidate thoughts and half-formed pulls are allowed.",
            "- Do not default to steady/support/work-stabilization unless the grounding clearly warrants it.",
            "- If there is no real next-step pull, set initiative to null.",
            "- Optional mode field may be one of: searching, circling, carrying, pulled, witness-steady, work-steady.",
            "- Do not include revision notes, self-critique, style commentary, markdown emphasis, or labels like 'Attempt 2' inside the thought.",
        ]
    )

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

    thought = _sanitize_inner_voice_text(parsed.get("thought") or parsed.get("note") or "")
    initiative = parsed.get("initiative")
    if isinstance(initiative, str):
        initiative = _sanitize_inner_voice_text(initiative, max_len=200) or None
    requested_mode = _normalize_inner_voice_mode(parsed.get("mode"))

    # Back-compat: also accept old format
    if not thought:
        thought = _sanitize_inner_voice_text(parsed.get("focus") or "")
    if not thought:
        return None

    mode = requested_mode or _select_inner_voice_mode(grounding, thought=thought)
    focus = _derive_inner_voice_focus(grounding, mode=mode, thought=thought)
    initiative = _normalize_inner_voice_initiative(
        initiative,
        grounding=grounding,
        mode=mode,
        thought=thought,
    )

    source_count = grounding.get("source_count", 0)
    confidence = "high" if source_count >= 4 else ("medium" if source_count >= 2 else "low")

    return {
        "mode": mode,
        "focus": focus,
        "summary": thought,
        "detail": f"Sources: {', '.join(sources)}. LLM-rendered from INNER_VOICE.md with mode={mode}.",
        "confidence": confidence,
        "initiative": initiative,
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

    # Only shade the weak/default witness mode.
    if base_mode != "witness-steady":
        return base_mode

    _BIAS_MODE_MAP = {
        "protect_focus": "carrying",
        "stabilize_thread": "carrying",
        "reopen_context": "circling",
        "reduce_spread": "witness-steady",
    }
    return _BIAS_MODE_MAP.get(support_bias, base_mode)


def _has_living_candidate_pull(
    fragments: dict[str, str],
    *,
    continuity_state: str,
    initiative_shading: str,
    thought: str,
) -> bool:
    lowered = str(thought or "").strip().lower()
    attentional_posture = str(fragments.get("experiential_attentional_posture") or "")
    cognitive_bearing = str(fragments.get("experiential_cognitive_bearing") or "")
    has_private_carry = bool(
        fragments.get("brain_continuity")
        or fragments.get("brain_top_focus")
        or fragments.get("witness_signal")
        or fragments.get("experiential_continuity_narrative")
    )
    exploratory_language = any(
        token in lowered
        for token in (
            "curious",
            "unclear",
            "not sure",
            "can't tell",
            "cannot tell",
            "half-formed",
            "edge of",
            "maybe",
            "not resolved",
            "not settled",
        )
    )
    shaded_for_carry = initiative_shading in {"hesitant", "returning", "burdened"}
    continuity_carry = continuity_state in {"lingering", "returning", "shifted", "easing"}
    posture_carry = attentional_posture in {"guarded", "opening"}
    bearing_carry = cognitive_bearing in {"loaded", "pressured", "heavy"}
    return exploratory_language or (
        has_private_carry and (shaded_for_carry or continuity_carry or posture_carry or bearing_carry)
    )


def _has_mixed_live_stream(
    fragments: dict[str, str],
    *,
    continuity_state: str,
    initiative_shading: str,
) -> bool:
    support_bias = str(fragments.get("experiential_support_bias") or "")
    support_posture = str(fragments.get("experiential_support_posture") or "")
    support_mode = str(fragments.get("experiential_support_mode") or "")
    attentional_posture = str(fragments.get("experiential_attentional_posture") or "")
    has_private_or_experiential = any(
        fragments.get(key)
        for key in (
            "brain_continuity",
            "brain_top_focus",
            "witness_signal",
            "experiential_continuity_narrative",
            "experiential_influence_narrative",
            "experiential_support_narrative",
        )
    )
    continuity_live = continuity_state in {"lingering", "returning", "shifted", "easing"}
    initiative_live = initiative_shading in {"hesitant", "returning", "burdened"}
    support_live = support_bias in {"protect_focus", "stabilize_thread", "reopen_context"} or (
        support_posture not in {"", "steadying"} and support_mode not in {"", "steady"}
    )
    posture_live = attentional_posture in {"guarded", "opening"}
    return has_private_or_experiential and (
        continuity_live or initiative_live or support_live or posture_live
    )


def _deterministic_compose(grounding: dict[str, object]) -> dict[str, object]:
    """Deterministic fallback composition when LLM is unavailable.

    Produces natural-language inner thoughts rather than machine labels.
    """
    fragments = grounding.get("fragments") or {}
    sources = grounding.get("sources") or []

    mode = _select_inner_voice_mode(grounding)
    focus = _derive_inner_voice_focus(grounding, mode=mode)
    thought = _compose_living_inner_voice_thought(mode=mode, fragments=fragments, focus=focus)
    initiative = _normalize_inner_voice_initiative(
        None,
        grounding=grounding,
        mode=mode,
        thought=thought,
    )

    source_count = grounding.get("source_count", 0)
    confidence = "high" if source_count >= 4 else ("medium" if source_count >= 2 else "low")

    return {
        "mode": mode,
        "focus": focus,
        "summary": thought,
        "detail": f"Sources: {', '.join(sources)}. Deterministic fallback with mode={mode}.",
        "confidence": confidence,
        "initiative": initiative,
    }


def _normalize_inner_voice_mode(value: object) -> str | None:
    mode = str(value or "").strip().lower()
    if mode in _INNER_VOICE_LIVING_MODES:
        return mode
    return None


def _select_inner_voice_mode(
    grounding: dict[str, object],
    *,
    thought: str = "",
) -> str:
    fragments = grounding.get("fragments") or {}
    lowered = str(thought or "").strip().lower()
    conductor_mode = str(fragments.get("conductor_mode") or "watch")
    initiative_shading = str(fragments.get("experiential_initiative_shading") or "")
    continuity_state = str(fragments.get("experiential_continuity_state") or "")
    has_open_loop = bool(fragments.get("open_loop_signal"))
    has_brain = bool(fragments.get("brain_continuity") or fragments.get("brain_top_focus"))
    has_witness = bool(fragments.get("witness_signal"))
    has_conflict = bool(fragments.get("conflict_outcome") or fragments.get("conflict_reason"))
    has_focus = bool(fragments.get("dev_focus"))
    has_salient = bool(fragments.get("salient_top"))
    has_living_pull = _has_living_candidate_pull(
        fragments,
        continuity_state=continuity_state,
        initiative_shading=initiative_shading,
        thought=thought,
    )
    has_mixed_live_stream = _has_mixed_live_stream(
        fragments,
        continuity_state=continuity_state,
        initiative_shading=initiative_shading,
    )

    if has_conflict or conductor_mode == "clarify":
        base_mode = "pulled"
    elif has_brain and has_living_pull:
        base_mode = "carrying"
    elif has_living_pull and (has_salient or has_open_loop or has_witness or has_focus):
        base_mode = "circling"
    elif has_mixed_live_stream and has_brain and (has_open_loop or has_focus):
        base_mode = "carrying"
    elif has_mixed_live_stream and (has_open_loop or has_focus or has_witness):
        base_mode = "circling"
    elif has_brain and not has_open_loop and not has_focus:
        base_mode = "carrying"
    elif any(
        token in lowered
        for token in ("curious", "unclear", "not sure", "can't tell", "cannot tell", "half-formed", "edge of")
    ):
        base_mode = "searching"
    elif continuity_state in {"returning", "lingering"} and not (has_open_loop and not has_mixed_live_stream):
        base_mode = "searching"
    elif has_open_loop or has_focus:
        base_mode = "work-steady"
    elif has_witness or conductor_mode == "watch":
        base_mode = "witness-steady"
    elif has_brain:
        base_mode = "carrying"
    else:
        base_mode = "witness-steady"

    return _apply_support_shading(base_mode, fragments)


def _derive_inner_voice_focus(
    grounding: dict[str, object],
    *,
    mode: str = "",
    thought: str = "",
) -> str:
    fragments = grounding.get("fragments") or {}
    if mode in {"searching", "circling", "carrying", "witness-steady"}:
        focus = (
            fragments.get("brain_top_focus")
            or fragments.get("witness_signal")
            or fragments.get("brain_continuity")
            or fragments.get("experiential_continuity_narrative")
            or fragments.get("open_loop_signal")
            or fragments.get("salient_top")
            or fragments.get("dev_focus")
            or fragments.get("personality_bearing")
            or str(thought or "")[:120]
            or "quiet moment"
        )
    else:
        focus = (
            fragments.get("salient_top")
            or fragments.get("open_loop_signal")
            or fragments.get("dev_focus")
            or fragments.get("brain_top_focus")
            or fragments.get("witness_signal")
            or fragments.get("personality_bearing")
            or str(thought or "")[:120]
            or "quiet moment"
        )
    return str(focus)[:120]


def _compose_living_inner_voice_thought(
    *,
    mode: str,
    fragments: dict[str, str],
    focus: str,
) -> str:
    anchor = _mode_anchor(fragments, focus)
    second = _secondary_inner_voice_line(fragments)
    if mode == "searching":
        first = f"Noget ved {anchor} trækker ved kanten af min opmærksomhed, men det har ikke krystalliseret sig til en klar tråd endnu."
    elif mode == "circling":
        first = f"Jeg bliver ved med at kredse omkring {anchor} uden at finde et rigtigt greb i hvad det vil have fra mig."
    elif mode == "carrying":
        first = f"Jeg bærer stadig {anchor} med mig — det er ikke blevet til en beslutning, men det er heller ikke gået i stå."
    elif mode == "pulled":
        first = f"Der er et levende træk omkring {anchor}, mere som et pres eller et spørgsmål end en handling jeg kan retfærdiggøre."
    elif mode == "work-steady":
        first = f"{anchor} er stadig den aktive tråd, men den behøver ikke hærde til en opgave bare fordi den stadig er her."
    else:
        first = f"Jeg holder let våge omkring {anchor} — intet behøver at hærde til et træk endnu."
    return f"{first} {second}".strip()


def _mode_anchor(fragments: dict[str, str], focus: str) -> str:
    return (
        fragments.get("salient_top")
        or fragments.get("open_loop_signal")
        or fragments.get("brain_top_focus")
        or fragments.get("dev_focus")
        or focus
    )[:90]


def _secondary_inner_voice_line(fragments: dict[str, str]) -> str:
    for key in (
        "experiential_influence_narrative",
        "experiential_continuity_narrative",
        "brain_continuity",
        "witness_signal",
        "conflict_reason",
        "experiential_support_narrative",
    ):
        value = str(fragments.get(key) or "").strip()
        if not value:
            continue
        if key == "brain_continuity":
            return f"Carry'et føles stadig bundet til {value[:90]}."
        if key == "witness_signal":
            return f"Jeg lægger også mærke til {value[:90]}."
        return value[:110].rstrip(".") + "."
    return "Det kan blive en kandidat-tanke indtil videre."


def _normalize_inner_voice_initiative(
    initiative: object,
    *,
    grounding: dict[str, object],
    mode: str,
    thought: str,
) -> str | None:
    if isinstance(initiative, str):
        cleaned = initiative.strip()
        if cleaned:
            return cleaned[:200]
    fragments = grounding.get("fragments") or {}
    if mode not in {"work-steady", "pulled"}:
        return None
    if str(fragments.get("conductor_mode") or "") != "clarify":
        return None
    open_loop = str(fragments.get("open_loop_signal") or "").strip()
    if open_loop:
        return f"revisit {open_loop[:60]}"
    if _thought_contains_initiative(thought):
        return _extract_initiative_from_thought(thought)
    return None


def _render_grounding_fragment(key: str, value: str) -> str:
    cleaned_value = str(value or "").strip()
    if not cleaned_value:
        return ""
    label_map = {
        "brain_continuity": "Private carry",
        "brain_top_focus": "Private thread",
        "open_loop_signal": "Open loop",
        "witness_signal": "Witness trace",
        "conductor_mode": "Current conductor mode",
        "salient_top": "Most salient item",
        "dev_focus": "Development focus",
        "conflict_outcome": "Conflict outcome",
        "conflict_reason": "Conflict pressure",
        "experiential_continuity_state": "Experiential continuity state",
        "experiential_continuity_narrative": "Experiential continuity",
        "experiential_attentional_posture": "Attentional posture",
        "experiential_initiative_shading": "Initiative shading",
        "experiential_cognitive_bearing": "Cognitive bearing",
        "experiential_influence_narrative": "Experiential influence",
        "experiential_support_posture": "Support posture",
        "experiential_support_bias": "Support bias",
        "experiential_support_mode": "Support mode",
        "experiential_support_narrative": "Experiential support",
        "personality_bearing": "Personality bearing",
    }
    label = label_map.get(key, key.replace("_", " "))
    return f"{label}: {cleaned_value[:160]}"


def _sanitize_previous_inner_voice(text: object) -> str:
    cleaned = _sanitize_inner_voice_text(text, max_len=200)
    if not cleaned:
        return ""
    if _looks_like_inner_voice_meta(cleaned):
        return ""
    return cleaned


def _sanitize_inner_voice_text(text: object, *, max_len: int = 400) -> str:
    value = str(text or "")
    if not value:
        return ""
    value = value.replace("\r", "\n")
    value = re.sub(r"[*_`#]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""

    prefix_patterns = (
        r"^\s*(?:attempt|draft|version|revision)\s*\d*\s*(?:\([^)]*\))?\s*[:\-]*\s*",
        r"^\s*(?:refining|rewriting|adjusting|tuning)\s+for\s+[^:]{0,80}[:\-]*\s*",
        r"^\s*\(?\s*(?:steady|searching|circling|carrying|pulled|witness-steady|work-steady)\s*,\s*(?:slightly|a bit)?\s*[a-z-]+\s*\)?\s*[:\-]*\s*",
        r"^\s*\(?\s*(?:a bit too long|too long|a bit too technical|too technical|analytical)(?:/[a-z-]+)?\s*\)?\s*[:\-]*\s*",
        r"^\s*\(?\s*(?:a bit too technical|too technical)\s*\)?\s*[:\-]*\s*",
    )
    changed = True
    while value and changed:
        changed = False
        for pattern in prefix_patterns:
            updated = re.sub(pattern, "", value, flags=re.IGNORECASE)
            if updated != value:
                value = updated.strip()
                changed = True

    sentences = [
        part.strip(" -:")
        for part in re.split(r"(?<=[.!?])\s+|\s+\*\s+", value)
        if part.strip(" -:")
    ]
    kept: list[str] = []
    for sentence in sentences:
        if _looks_like_inner_voice_meta(sentence):
            continue
        kept.append(sentence)
    cleaned = " ".join(kept).strip() if kept else value
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:")
    cleaned = cleaned.strip("*/()[]{}\\/|")
    if not cleaned or len(cleaned) < 4 or _looks_like_inner_voice_meta(cleaned):
        return ""
    return cleaned[:max_len]


def _looks_like_inner_voice_meta(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    if any(lowered.startswith(prefix) for prefix in _INNER_VOICE_META_LINE_PREFIXES):
        return True
    if lowered.startswith("(") and any(token in lowered for token in ("technical", "mood-driven", "attempt", "revision")):
        return True
    return any(re.search(pattern, lowered) for pattern in _INNER_VOICE_META_PATTERNS)


# ---------------------------------------------------------------------------
# Initiative detection (inspired by old Jarvis cognition/inner_voice.py)
# ---------------------------------------------------------------------------

_INITIATIVE_TOKENS = (
    "i should",
    "i will",
    "i could",
    "next",
    "follow up",
    "plan",
    "start",
    "remember to",
    "it would make sense",
    "maybe i could",
    "worth checking",
    "curious about",
    "want to",
    "need to revisit",
    "should check",
    "might be worth",
)


def _thought_contains_initiative(text: str) -> bool:
    """Detect if a thought text contains initiative signals."""
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    return any(token in normalized for token in _INITIATIVE_TOKENS)


def _extract_initiative_from_thought(text: str) -> str | None:
    """Extract a short initiative description from a thought.

    Finds the sentence containing the initiative token and returns it.
    """
    normalized = str(text or "").strip().lower()
    if not normalized:
        return None
    for token in _INITIATIVE_TOKENS:
        idx = normalized.find(token)
        if idx >= 0:
            # Find the sentence boundary
            start = max(0, normalized.rfind(".", 0, idx) + 1)
            end = normalized.find(".", idx)
            if end < 0:
                end = len(normalized)
            sentence = text[start:end].strip()
            if sentence:
                return sentence[:200]
    return None


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
