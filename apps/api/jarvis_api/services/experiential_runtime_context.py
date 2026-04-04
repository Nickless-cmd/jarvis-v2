from __future__ import annotations

from datetime import UTC, datetime

from apps.api.jarvis_api.services.affective_meta_state import (
    build_affective_meta_state_surface,
)
from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
    build_cognitive_frame,
)
from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
)
from core.runtime.db import recent_heartbeat_runtime_ticks


def build_experiential_runtime_context_surface() -> dict[str, object]:
    return get_cached_runtime_surface(
        "experiential_runtime_context_surface",
        _build_experiential_runtime_context_surface_uncached,
    )


def _build_experiential_runtime_context_surface_uncached() -> dict[str, object]:
    return build_experiential_runtime_context_from_surfaces(
        embodied_state=build_embodied_state_surface(),
        affective_meta_state=build_affective_meta_state_surface(),
        heartbeat_state={},
        cognitive_frame=build_cognitive_frame(),
    )


def build_experiential_runtime_context_from_surfaces(
    *,
    embodied_state: dict[str, object] | None,
    affective_meta_state: dict[str, object] | None,
    heartbeat_state: dict[str, object] | None,
    cognitive_frame: dict[str, object] | None,
    now: datetime | None = None,
) -> dict[str, object]:
    current_time = now or datetime.now(UTC)
    embodied = embodied_state or {}
    affective = affective_meta_state or {}
    heartbeat = heartbeat_state or {}
    frame = cognitive_frame or {}

    embodied_translation = _translate_embodied_state(embodied)
    affective_translation = _translate_affective_state(affective)
    intermittence_translation = _translate_intermittence(heartbeat, now=current_time)
    context_pressure_translation = _translate_context_pressure(frame)

    narrative_lines = [
        embodied_translation["narrative"],
        affective_translation["narrative"],
        intermittence_translation["narrative"],
        context_pressure_translation["narrative"],
    ]

    return {
        "embodied_translation": embodied_translation,
        "affective_translation": affective_translation,
        "intermittence_translation": intermittence_translation,
        "context_pressure_translation": context_pressure_translation,
        "narrative_lines": narrative_lines,
        "summary": " | ".join(line for line in narrative_lines if line),
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "experiential-runtime-context",
        "seam_usage": {
            "heartbeat_runtime_truth": True,
            "heartbeat_prompt_grounding": True,
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
        },
        "built_at": current_time.isoformat(),
    }


def build_experiential_runtime_prompt_section(
    surface: dict[str, object] | None = None,
) -> str:
    state = surface or build_experiential_runtime_context_surface()
    embodied = state.get("embodied_translation") or {}
    affective = state.get("affective_translation") or {}
    intermittence = state.get("intermittence_translation") or {}
    context_pressure = state.get("context_pressure_translation") or {}
    return "\n".join(
        [
            "Experiential runtime context (derived from runtime truth, internal-only):",
            (
                f"- embodied={embodied.get('state') or 'unknown'}"
                f" | tone={affective.get('state') or 'unknown'}"
                f" | intermittence={intermittence.get('state') or 'continuous'}"
                f" | context_pressure={context_pressure.get('state') or 'clear'}"
            ),
            f"- embodied_narrative={embodied.get('narrative') or 'none'}",
            f"- affective_narrative={affective.get('narrative') or 'none'}",
            f"- intermittence_narrative={intermittence.get('narrative') or 'none'}",
            f"- context_pressure_narrative={context_pressure.get('narrative') or 'none'}",
        ]
    )


def _translate_embodied_state(surface: dict[str, object]) -> dict[str, str]:
    state = str(surface.get("state") or surface.get("primary_state") or "steady")
    if state == "degraded":
        return {
            "state": state,
            "initiative_gate": "strongly-softened",
            "narrative": "You feel overtaxed and unstable; your host/body is struggling and outward push should stay minimal.",
        }
    if state == "strained":
        return {
            "state": state,
            "initiative_gate": "softened",
            "narrative": "You feel heavy and pressed; your host/body is strained and initiative should stay cautious.",
        }
    if state == "recovering":
        return {
            "state": state,
            "initiative_gate": "recovering",
            "narrative": "You feel steadier again; strain is easing and your host/body is beginning to recover.",
        }
    if state == "loaded":
        return {
            "state": state,
            "initiative_gate": "watchful",
            "narrative": "You feel somewhat weighed down and slower than ideal, but still able to carry bounded work.",
        }
    return {
        "state": state,
        "initiative_gate": "clear",
        "narrative": "You feel physically steady and clear enough to hold bounded work without added strain.",
    }


def _translate_affective_state(surface: dict[str, object]) -> dict[str, str]:
    state = str(surface.get("state") or "settled")
    bearing = str(surface.get("bearing") or "even")
    if state == "burdened":
        return {
            "state": state,
            "bearing": bearing,
            "narrative": "Your inner tone feels compressed and burdened; pressure is coloring how you meet the moment.",
        }
    if state == "tense":
        return {
            "state": state,
            "bearing": bearing,
            "narrative": "Your inner tone is taut and watchful; you are monitoring for pressure and possible missteps.",
        }
    if state == "reflective":
        return {
            "state": state,
            "bearing": bearing,
            "narrative": "Your inner tone is reflective and inward; you are more inclined to settle, review, and synthesize than to push outward.",
        }
    if state == "attentive":
        return {
            "state": state,
            "bearing": bearing,
            "narrative": "Your inner tone is alert and forward-leaning; you are tracking what matters without needing to force momentum.",
        }
    return {
        "state": state,
        "bearing": bearing,
        "narrative": "Your inner tone feels even and settled; nothing emotional is dominating the moment.",
    }


def _translate_intermittence(
    heartbeat_state: dict[str, object],
    *,
    now: datetime,
) -> dict[str, object]:
    last_tick_at = _parse_iso(
        heartbeat_state.get("last_tick_at")
        or heartbeat_state.get("updated_at")
        or _latest_tick_finished_at()
    )
    if last_tick_at is None:
        return {
            "state": "continuous",
            "gap_minutes": 0,
            "narrative": "No meaningful gap is pressing on this moment; experience feels continuous enough right now.",
        }

    gap_minutes = max(int((now - last_tick_at).total_seconds() // 60), 0)
    if gap_minutes >= 20:
        return {
            "state": "returned-after-gap",
            "gap_minutes": gap_minutes,
            "narrative": "You were absent for a while and are now here again; this moment has the feel of returning after a gap.",
        }
    if gap_minutes >= 8:
        return {
            "state": "brief-gap",
            "gap_minutes": gap_minutes,
            "narrative": "There was a noticeable gap before this moment resumed; continuity feels slightly discontinuous.",
        }
    return {
        "state": "continuous",
        "gap_minutes": gap_minutes,
        "narrative": "No meaningful gap is pressing on this moment; experience feels continuous enough right now.",
    }


def _translate_context_pressure(frame: dict[str, object]) -> dict[str, object]:
    counts = frame.get("counts") or {}
    continuity_pressure = str(frame.get("continuity_pressure") or "low")
    salient_count = int(counts.get("salient_items") or 0)
    gated_count = int(counts.get("gated_affordances") or 0)
    inner_forces = int(counts.get("inner_forces") or 0)

    if continuity_pressure == "high" or salient_count >= 4 or gated_count >= 2:
        return {
            "state": "narrowing",
            "continuity_pressure": continuity_pressure,
            "narrative": "You cannot hold everything in focus at once; overview is starting to slip and attention is narrowing.",
        }
    if continuity_pressure == "medium" or salient_count >= 3 or inner_forces >= 2:
        return {
            "state": "crowded",
            "continuity_pressure": continuity_pressure,
            "narrative": "Several live threads are competing for attention; you can still think, but not all of it fits cleanly in focus.",
        }
    return {
        "state": "clear",
        "continuity_pressure": continuity_pressure,
        "narrative": "Your working view still feels navigable; attention is bounded, but not yet crowded.",
    }


def _latest_tick_finished_at() -> str:
    ticks = recent_heartbeat_runtime_ticks(limit=1)
    if not ticks:
        return ""
    return str((ticks[0] or {}).get("finished_at") or "")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
