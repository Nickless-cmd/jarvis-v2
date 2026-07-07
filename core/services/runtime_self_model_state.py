"""Runtime self-model — base state surfaces + temporal/mineness awareness.

Split out of ``runtime_self_model`` (behavior-preserving). Foundation layer:
base runtime-state surfaces plus subjective-temporal and mineness-ownership
awareness that the higher awareness/builder layers depend on.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.identity.workspace_bootstrap import workspace_memory_paths

def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Helpers patched in tests via ``monkeypatch.setattr(runtime_self_model,
    ...)`` are resolved through this accessor so the patch is seen across the
    module split (behavior-preserving).
    """
    import core.services.runtime_self_model as _m

    return _m


def _embodied_state_surface() -> dict[str, object]:
    try:
        from core.services.embodied_state import (
            build_embodied_state_surface,
        )

        return build_embodied_state_surface()
    except Exception:
        return {
            "state": "unknown",
            "strain_level": "unknown",
            "recovery_state": "steady",
            "freshness": {"state": "unknown"},
        }


def _loop_runtime_surface() -> dict[str, object]:
    try:
        from core.services.loop_runtime import (
            build_loop_runtime_surface,
        )

        return build_loop_runtime_surface()
    except Exception:
        return {
            "summary": {
                "current_status": "none",
                "active_count": 0,
                "standby_count": 0,
                "resumed_count": 0,
                "closed_count": 0,
            }
        }


def _runtime_task_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_tasks import list_tasks

        queued = list_tasks(status="queued", limit=12)
        running = list_tasks(status="running", limit=12)
        blocked = list_tasks(status="blocked", limit=12)
        latest = next(iter(running or queued or blocked), {})
        return {
            "queued_count": len(queued),
            "running_count": len(running),
            "blocked_count": len(blocked),
            "latest_goal": str(latest.get("goal") or "").strip(),
        }
    except Exception:
        return {
            "queued_count": 0,
            "running_count": 0,
            "blocked_count": 0,
            "latest_goal": "",
        }


def _runtime_flow_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_flows import list_flows

        queued = list_flows(status="queued", limit=12)
        running = list_flows(status="running", limit=12)
        blocked = list_flows(status="blocked", limit=12)
        latest = next(iter(running or queued or blocked), {})
        return {
            "queued_count": len(queued),
            "running_count": len(running),
            "blocked_count": len(blocked),
            "current_step": str(latest.get("current_step") or "").strip(),
        }
    except Exception:
        return {
            "queued_count": 0,
            "running_count": 0,
            "blocked_count": 0,
            "current_step": "",
        }


def _runtime_hook_state_surface() -> dict[str, object]:
    try:
        from core.eventbus.bus import event_bus
        from core.runtime.db import (
            get_runtime_hook_dispatch,
            list_runtime_hook_dispatches,
        )

        supported = {"heartbeat.initiative_pushed", "heartbeat.tick_completed"}
        recent_events = [
            item
            for item in event_bus.recent(limit=40)
            if str(item.get("kind") or "") in supported
        ]
        pending_count = sum(
            1
            for item in recent_events
            if get_runtime_hook_dispatch(int(item.get("id") or 0)) is None
        )
        dispatches = list_runtime_hook_dispatches(limit=12)
        latest = next(iter(dispatches), {})
        return {
            "pending_count": pending_count,
            "dispatched_count": len(dispatches),
            "latest_event_kind": str(latest.get("event_kind") or "").strip(),
        }
    except Exception:
        return {
            "pending_count": 0,
            "dispatched_count": 0,
            "latest_event_kind": "",
        }


def _browser_body_state_surface() -> dict[str, object]:
    try:
        from core.services.runtime_browser_body import (
            list_browser_bodies,
        )

        body = next(iter(list_browser_bodies(limit=1)), None)
        if body is None:
            return {
                "exists": False,
                "profile_name": "",
                "status": "",
                "tab_count": 0,
                "last_url": "",
            }
        return {
            "exists": True,
            "profile_name": str(body.get("profile_name") or "").strip(),
            "status": str(body.get("status") or "").strip(),
            "tab_count": len(body.get("tabs") or []),
            "last_url": str(body.get("last_url") or "").strip(),
        }
    except Exception:
        return {
            "exists": False,
            "profile_name": "",
            "status": "",
            "tab_count": 0,
            "last_url": "",
        }


def _standing_orders_state_surface() -> dict[str, object]:
    try:
        workspace_dir = workspace_memory_paths()["workspace_dir"]
        path = Path(workspace_dir) / "STANDING_ORDERS.md"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return {
            "exists": path.exists(),
            "loaded_by_default": True,
            "line_count": len(lines),
            "preview": (lines[0][:80] if lines else ""),
        }
    except Exception:
        return {
            "exists": False,
            "loaded_by_default": True,
            "line_count": 0,
            "preview": "",
        }


def _layered_memory_state_surface() -> dict[str, object]:
    try:
        paths = workspace_memory_paths()
        curated = paths["curated_memory"]
        daily = paths["daily_memory"]
        freshness = "fresh" if daily.exists() else "needs-daily-log"
        return {
            "daily_exists": daily.exists(),
            "curated_exists": curated.exists(),
            "daily_file": daily.name,
            "freshness": freshness,
        }
    except Exception:
        return {
            "daily_exists": False,
            "curated_exists": False,
            "daily_file": "",
            "freshness": "unknown",
        }


def _affective_meta_state_surface() -> dict[str, object]:
    try:
        from core.services.affective_meta_state import (
            build_affective_meta_state_surface,
        )

        return build_affective_meta_state_surface()
    except Exception:
        return {
            "state": "unknown",
            "bearing": "unknown",
            "monitoring_mode": "steady-check",
        }


def _experiential_runtime_context_surface() -> dict[str, object]:
    try:
        from core.services.experiential_runtime_context import (
            build_experiential_runtime_context_surface,
        )

        return build_experiential_runtime_context_surface()
    except Exception:
        return {
            "embodied_translation": {"state": "unknown", "narrative": "none"},
            "affective_translation": {"state": "unknown", "narrative": "none"},
            "intermittence_translation": {"state": "continuous", "narrative": "none"},
            "context_pressure_translation": {"state": "clear", "narrative": "none"},
        }


def _inner_voice_daemon_surface() -> dict[str, object]:
    """Read inner voice daemon state for self-model integration."""
    try:
        from core.services.inner_voice_daemon import (
            get_inner_voice_daemon_state,
        )

        return get_inner_voice_daemon_state()
    except Exception:
        return {
            "last_run_at": None,
            "last_result": None,
            "cooldown_minutes": 0,
        }


def _derive_support_stream_awareness(
    experiential: dict[str, object],
    inner_voice: dict[str, object],
) -> dict[str, object]:
    """Derive compact self-aware support stream state.

    Synthesizes experiential support carry-forward and private stream daemon
    truth into a small awareness snapshot that tells the self-model whether
    experiential support is actively shaping the inner stream.
    """
    support = experiential.get("experiential_support") or {}
    posture = str(support.get("support_posture") or "steadying")
    bias = str(support.get("support_bias") or "none")
    mode = str(support.get("support_mode") or "steady")

    last_result = inner_voice.get("last_result") or {}
    voice_created = bool(last_result.get("inner_voice_created"))
    voice_mode = str(last_result.get("mode") or "")

    # Stream is shaped when support is non-default and a private stream note was produced.
    active = posture != "steadying"
    shaped = active and voice_created and voice_mode != ""

    # Stream state mirrors support_mode when active, else baseline
    stream_state = mode if active else "baseline"

    # Compact self-awareness narrative
    narrative = ""
    if shaped:
        narrative = (
            f"Inner stream is {stream_state}. "
            f"Support ({posture}/{bias}) shaped private stream mode to {voice_mode}."
        )
    elif active:
        narrative = (
            f"Inner stream is {stream_state}. "
            f"Support active ({posture}/{bias}) but private stream not yet shaped."
        )
    appraisal = _runtime_self_appraisal_record(
        kind="support_stream_awareness",
        state={
            "stream_state": stream_state,
            "stream_shaped": shaped,
            "support_posture": posture if active else "none",
            "support_bias": bias if active else "none",
            "private_stream_mode": voice_mode if shaped else "",
        },
        evidence={
            "support_posture": posture,
            "support_bias": bias,
            "support_mode": mode,
            "private_stream_created": voice_created,
            "private_stream_mode": voice_mode,
        },
        confidence=0.86 if active else 0.7,
        allowed_effects=[
            "runtime_self_model_surface",
            "heartbeat_self_knowledge_context",
            "prompt_support_stream_line",
        ],
        ttl_minutes=20,
    )

    return {
        "stream_state": stream_state,
        "stream_shaped": shaped,
        "active_support_posture": posture if active else "none",
        "active_support_bias": bias if active else "none",
        "shaped_voice_mode": voice_mode if shaped else "",
        "narrative": narrative,
        "appraisal": appraisal,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "support-stream-awareness",
    }


def _runtime_self_appraisal_record(
    *,
    kind: str,
    state: dict[str, object],
    evidence: dict[str, object],
    confidence: float,
    allowed_effects: list[str],
    ttl_minutes: int,
) -> dict[str, object]:
    """Structured source-truth record for runtime self-model renderings."""
    now = datetime.now(UTC)
    return {
        "kind": kind,
        "state": state,
        "evidence": evidence,
        "confidence": round(max(0.0, min(1.0, float(confidence))), 3),
        "allowed_effects": allowed_effects,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (
            now + timedelta(minutes=max(1, int(ttl_minutes)))
        ).isoformat().replace("+00:00", "Z"),
        "rendering_contract": "narrative is derived display text; appraisal is source truth",
    }


def _derive_subjective_temporal_feel(
    experiential: dict[str, object],
    inner_voice: dict[str, object],
) -> dict[str, object]:
    """Derive a compact subjective temporal feel from existing runtime truth.

    Synthesises intermittence (gap/continuous), experiential continuity
    (stable/returning/lingering/…), experiential support posture, and
    inner-voice cadence into a small felt-time surface that expresses
    how the current moment sits in Jarvis' experienced timeline.

    Taxonomy for ``temporal_state``:
      immediate  — no gap, state stable, everything feels now
      recent     — brief gap but continuity holds
      lingering  — elevated state persists without shift
      returning  — came back after meaningful absence
      receding   — state is easing, pressure is lifting
      stretched  — elevated state with gap, time feels drawn out

    Taxonomy for ``felt_proximity``:
      close   — current thread feels near and carried
      held    — active support or influence holds it present
      fading  — easing or drifting, not yet gone
      resumed — returned after absence, reconnecting
    """
    intermittence = experiential.get("intermittence_translation") or {}
    continuity = experiential.get("experiential_continuity") or {}
    support = experiential.get("experiential_support") or {}
    pressure = experiential.get("context_pressure_translation") or {}

    gap_state = str(intermittence.get("state") or "continuous")
    gap_minutes = int(intermittence.get("gap_minutes") or 0)
    cont_state = str(continuity.get("continuity_state") or "initial")
    support_posture = str(support.get("support_posture") or "steadying")
    pressure_state = str(pressure.get("state") or "clear")

    voice_result = inner_voice.get("last_result") or {}
    voice_created = bool(voice_result.get("inner_voice_created"))

    # --- temporal_state ---
    if gap_state == "returned-after-gap":
        temporal_state = "returning"
    elif cont_state == "lingering":
        if gap_state == "brief-gap":
            temporal_state = "stretched"
        else:
            temporal_state = "lingering"
    elif cont_state == "easing":
        temporal_state = "receding"
    elif gap_state == "brief-gap":
        temporal_state = "recent"
    else:
        temporal_state = "immediate"

    # --- felt_proximity ---
    if temporal_state == "returning":
        felt_proximity = "resumed"
    elif temporal_state == "receding":
        felt_proximity = "fading"
    elif support_posture != "steadying" or voice_created:
        felt_proximity = "held"
    else:
        felt_proximity = "close"

    # --- return_signal ---
    return_signal = cont_state == "returning" or gap_state == "returned-after-gap"

    # --- persistence_feel ---
    if cont_state == "lingering" or cont_state == "escalating":
        persistence_feel = "persistent"
    elif cont_state == "easing":
        persistence_feel = "releasing"
    elif return_signal:
        persistence_feel = "reconnecting"
    elif pressure_state not in ("clear", "low"):
        persistence_feel = "pressing"
    else:
        persistence_feel = "settled"

    # --- narrative ---
    narrative = _temporal_narrative(
        temporal_state,
        felt_proximity,
        return_signal,
        persistence_feel,
        gap_minutes,
    )

    return {
        "temporal_state": temporal_state,
        "felt_proximity": felt_proximity,
        "return_signal": return_signal,
        "persistence_feel": persistence_feel,
        "gap_minutes": gap_minutes,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "subjective-temporal-feel",
    }


def _temporal_narrative(
    temporal_state: str,
    felt_proximity: str,
    return_signal: bool,
    persistence_feel: str,
    gap_minutes: int,
) -> str:
    """Compact self-awareness narrative for felt time."""
    if temporal_state == "returning":
        return f"After ~{gap_minutes}m gap; returning to prior context."
    if temporal_state == "stretched":
        return "Elevated state bridging a gap; time feels drawn out."
    if temporal_state == "lingering":
        return "Prior state still present; not yet at baseline."
    if temporal_state == "receding":
        return "Prior pressure receding; tension dropping."
    if temporal_state == "recent":
        return f"Brief ~{gap_minutes}m gap behind; continuity holds."
    # immediate
    if felt_proximity == "held":
        return "Immediate; actively held by support or private stream."
    return "Continuous; nothing pressing from the past."


# ---------------------------------------------------------------------------
# Mineness / ownership awareness
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth bridge for "what feels like mine in my current stream".
# This is not an identity engine and not a capability layer. It translates
# existing runtime signals (private brain carry, open loops, inner voice,
# experiential support shaping, subjective temporal feel) into a small,
# explainable ownership surface that the self-model and prompt can carry
# forward as bounded self-awareness.
#
# Taxonomy (load-bearing, not exhaustive):
#   ownership_state:
#     ambient          — signals are merely present, nothing is held as mine
#     held             — support / voice / temporal proximity holds something
#                        in the stream without it being an owned thread yet
#     owned            — a real thread is actively carried as mine
#                        (private brain carry + inner voice/open-loop carry)
#     returning-owned  — an owned thread feels like it is returning after gap
#
#   self_relevance:
#     merely-present     — signals exist but are not personally salient
#     actively-carried   — support is carrying something without full ownership
#     personally-salient — ownership is active and the thread is mine right now
#     resumed-own        — a previously-owned thread is re-entering experience
#
#   carried_thread_state:
#     none | single | multiple | returning
#
# The surface stays empty-narrative in the ambient default so prompt lines
# only emit when there is meaningful basis.


_MINENESS_CARRY_VOICE_MODES = {"carrying", "circling", "pulled"}


def _mineness_source_snapshot() -> dict[str, object]:
    """Gather the minimal runtime truth needed for mineness derivation.

    Consumes only existing seams (private brain context + open loop signal
    surface). All lookups are defensively wrapped so the self-model never
    fails because a downstream producer is unavailable.
    """
    brain_active = False
    brain_record_count = 0
    brain_top_focus = ""
    brain_continuity_summary = ""
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context()
        brain_active = bool(brain.get("active"))
        brain_record_count = int(brain.get("record_count") or 0)
        brain_continuity_summary = str(brain.get("continuity_summary") or "")[:160]
        excerpts = brain.get("excerpts") or []
        if excerpts:
            brain_top_focus = str(excerpts[0].get("focus") or "")[:120]
    except Exception:
        pass

    open_loop_open_count = 0
    open_loop_signal = ""
    try:
        from core.services.open_loop_signal_tracking import (
            build_runtime_open_loop_signal_surface,
        )

        loops = build_runtime_open_loop_signal_surface(limit=4)
        loop_summary = loops.get("summary") or {}
        open_loop_open_count = int(loop_summary.get("open_count") or 0)
        open_loop_signal = str(loop_summary.get("current_signal") or "")[:120]
    except Exception:
        pass

    return {
        "brain_active": brain_active,
        "brain_record_count": brain_record_count,
        "brain_top_focus": brain_top_focus,
        "brain_continuity_summary": brain_continuity_summary,
        "open_loop_open_count": open_loop_open_count,
        "open_loop_signal": open_loop_signal,
    }


def _derive_mineness_ownership(
    *,
    experiential: dict[str, object],
    inner_voice: dict[str, object],
    support_stream: dict[str, object],
    temporal_feel: dict[str, object],
    sources: dict[str, object],
) -> dict[str, object]:
    """Derive a bounded mineness/ownership surface from existing runtime truth.

    The ownership_state stays ``ambient`` (with empty narrative) whenever
    there is no meaningful basis, so downstream prompt lines only fire when
    something is actually being carried as mine.
    """
    last_voice = inner_voice.get("last_result") or {}
    voice_created = bool(last_voice.get("inner_voice_created"))
    voice_mode = str(last_voice.get("mode") or "")
    voice_carrying = voice_created and voice_mode in _MINENESS_CARRY_VOICE_MODES

    stream_shaped = bool(support_stream.get("stream_shaped"))
    support_posture = str(support_stream.get("active_support_posture") or "none")
    support_active = support_posture not in ("", "none")

    felt_proximity = str(temporal_feel.get("felt_proximity") or "close")
    temporal_return = bool(temporal_feel.get("return_signal"))
    felt_held = felt_proximity in ("held", "resumed")

    brain_active = bool(sources.get("brain_active"))
    brain_record_count = int(sources.get("brain_record_count") or 0)
    brain_carry = brain_active and brain_record_count > 0
    brain_top_focus = str(sources.get("brain_top_focus") or "")
    brain_continuity = str(sources.get("brain_continuity_summary") or "")
    open_loop_count = int(sources.get("open_loop_open_count") or 0)
    has_open_loops = open_loop_count > 0
    open_loop_signal = str(sources.get("open_loop_signal") or "")

    continuity = experiential.get("experiential_continuity") or {}
    continuity_state = str(continuity.get("continuity_state") or "initial")
    continuity_return = continuity_state == "returning"
    return_signal = temporal_return or continuity_return

    carried_thread_count = int(brain_carry) + int(has_open_loops) + int(voice_carrying)

    if return_signal and (brain_carry or has_open_loops or voice_carrying):
        carried_thread_state = "returning"
    elif carried_thread_count == 0:
        carried_thread_state = "none"
    elif carried_thread_count == 1:
        carried_thread_state = "single"
    else:
        carried_thread_state = "multiple"

    is_owned = brain_carry or (voice_carrying and (has_open_loops or stream_shaped))
    is_held_only = (not is_owned) and (
        voice_created or stream_shaped or felt_held or has_open_loops
    )
    is_returning_owned = is_owned and return_signal

    if is_returning_owned:
        ownership_state = "returning-owned"
    elif is_owned:
        ownership_state = "owned"
    elif is_held_only:
        ownership_state = "held"
    else:
        ownership_state = "ambient"

    self_relevance_map = {
        "returning-owned": "resumed-own",
        "owned": "personally-salient",
        "held": "actively-carried",
        "ambient": "merely-present",
    }
    self_relevance = self_relevance_map[ownership_state]

    return_ownership = ownership_state == "returning-owned"

    narrative = _mineness_narrative(
        ownership_state=ownership_state,
        carried_thread_state=carried_thread_state,
        carried_thread_count=carried_thread_count,
        brain_top_focus=brain_top_focus,
        brain_continuity=brain_continuity,
        open_loop_signal=open_loop_signal,
        voice_mode=voice_mode if voice_created else "",
        support_posture=support_posture if support_active else "",
        felt_proximity=felt_proximity,
    )

    return {
        "ownership_state": ownership_state,
        "self_relevance": self_relevance,
        "carried_thread_state": carried_thread_state,
        "carried_thread_count": carried_thread_count,
        "return_ownership": return_ownership,
        "narrative": narrative,
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "mineness-ownership",
    }


def _mineness_narrative(
    *,
    ownership_state: str,
    carried_thread_state: str,
    carried_thread_count: int,
    brain_top_focus: str,
    brain_continuity: str,
    open_loop_signal: str,
    voice_mode: str,
    support_posture: str,
    felt_proximity: str,
) -> str:
    """Compact mineness narrative. Empty in ambient default."""
    if ownership_state == "ambient":
        return ""

    anchor = (brain_top_focus or open_loop_signal or brain_continuity).strip()
    anchor_clause = f" around {anchor[:90]}" if anchor else ""

    if ownership_state == "returning-owned":
        return f"Returning strand{anchor_clause} feels like mine again."
    if ownership_state == "owned":
        if carried_thread_state == "multiple":
            return f"Several threads{anchor_clause} owned in current stream."
        return f"Thread{anchor_clause} owned in current stream."
    # held
    if voice_mode or support_posture:
        shaping = voice_mode or support_posture
        return f"Signals held by {shaping}; not yet owned."
    if felt_proximity == "held":
        return "Moment held present; no clear owned thread yet."
    return "Signals present; nothing owned yet."


def build_mineness_ownership_prompt_section() -> str | None:
    """Compact heartbeat-side prompt section for mineness/ownership.

    Returns ``None`` in the ambient default so nothing emits unless there
    is meaningful ownership basis in the current runtime stream.
    """
    try:
        experiential = _experiential_runtime_context_surface()
        inner_voice = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, inner_voice)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, inner_voice)
        sources = _mineness_source_snapshot()
        mineness = _facade()._derive_mineness_ownership(
            experiential=experiential,
            inner_voice=inner_voice,
            support_stream=support_stream,
            temporal_feel=temporal_feel,
            sources=sources,
        )
    except Exception:
        return None

    state = str(mineness.get("ownership_state") or "ambient")
    if state == "ambient":
        return None

    lines = [
        "Mineness / ownership (bounded runtime truth, internal-only):",
        (
            f"- ownership_state={state}"
            f" | self_relevance={mineness.get('self_relevance') or 'merely-present'}"
            f" | threads={mineness.get('carried_thread_state') or 'none'}"
            f" | count={mineness.get('carried_thread_count') or 0}"
            f" | returning={mineness.get('return_ownership', False)}"
        ),
    ]
    narrative = str(mineness.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- mineness_narrative={narrative}")
    return "\n".join(lines)


__all__ = [
    '_MINENESS_CARRY_VOICE_MODES',
    '_affective_meta_state_surface',
    '_browser_body_state_surface',
    '_derive_mineness_ownership',
    '_derive_subjective_temporal_feel',
    '_derive_support_stream_awareness',
    '_embodied_state_surface',
    '_experiential_runtime_context_surface',
    '_inner_voice_daemon_surface',
    '_layered_memory_state_surface',
    '_loop_runtime_surface',
    '_mineness_narrative',
    '_mineness_source_snapshot',
    '_runtime_flow_state_surface',
    '_runtime_hook_state_surface',
    '_runtime_self_appraisal_record',
    '_runtime_task_state_surface',
    '_standing_orders_state_surface',
    '_temporal_narrative',
    'build_mineness_ownership_prompt_section',
]
