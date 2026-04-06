from __future__ import annotations

import json
from datetime import UTC, datetime

from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_rhythm_state,
)

def build_affective_meta_state_surface() -> dict[str, object]:
    """Build affective meta state fresh each call — cheap (no LLM), always current."""
    return _build_affective_meta_state_surface_uncached()


def _build_affective_meta_state_surface_uncached() -> dict[str, object]:
    return build_affective_meta_state_from_sources(
        embodied_state=_safe_embodied_state(),
        loop_runtime=_safe_loop_runtime(),
        regulation_homeostasis=_safe_regulation_homeostasis(),
        metabolism_state=_safe_metabolism_state(),
        quiet_initiative=_safe_quiet_initiative(),
        idle_consolidation=_safe_idle_consolidation(),
        dream_articulation=_safe_dream_articulation(),
        inner_voice_state=_safe_inner_voice_state(),
        personality_vector=_safe_personality_vector(),
        relationship_texture=_safe_relationship_texture(),
        rhythm_state=_safe_rhythm_state(),
    )


def build_affective_meta_state_from_sources(
    *,
    embodied_state: dict[str, object] | None,
    loop_runtime: dict[str, object] | None,
    regulation_homeostasis: dict[str, object] | None,
    metabolism_state: dict[str, object] | None,
    quiet_initiative: dict[str, object] | None,
    idle_consolidation: dict[str, object] | None,
    dream_articulation: dict[str, object] | None,
    inner_voice_state: dict[str, object] | None,
    personality_vector: dict[str, object] | None,
    relationship_texture: dict[str, object] | None,
    rhythm_state: dict[str, object] | None,
) -> dict[str, object]:
    built_at = datetime.now(UTC).isoformat()

    embodied = embodied_state or {}
    loops = loop_runtime or {}
    regulation = regulation_homeostasis or {}
    metabolism = metabolism_state or {}
    quiet = quiet_initiative or {}
    consolidation = idle_consolidation or {}
    dream = dream_articulation or {}
    voice = inner_voice_state or {}
    personality = personality_vector or {}
    relationship = relationship_texture or {}
    rhythm = rhythm_state or {}

    loop_summary = loops.get("summary") or {}
    regulation_summary = regulation.get("summary") or {}
    metabolism_summary = metabolism.get("summary") or {}
    consolidation_summary = consolidation.get("summary") or {}
    dream_summary = dream.get("summary") or {}
    voice_result = voice.get("last_result") or {}

    source_contributors: list[dict[str, str]] = []
    body_state = str(embodied.get("state") or "unknown")
    strain_level = str(embodied.get("strain_level") or "unknown")
    if body_state != "unknown":
        source_contributors.append({
            "source": "embodied-state",
            "signal": f"{body_state} / strain={strain_level}",
        })

    loop_status = str(loop_summary.get("current_status") or "none")
    if int(loop_summary.get("loop_count") or 0) > 0:
        source_contributors.append({
            "source": "loop-runtime",
            "signal": f"{loop_status} / active={int(loop_summary.get('active_count') or 0)} / standby={int(loop_summary.get('standby_count') or 0)}",
        })

    regulation_state = str(regulation_summary.get("current_state") or "none")
    regulation_pressure = str(regulation_summary.get("current_pressure") or "low")
    if regulation.get("active"):
        source_contributors.append({
            "source": "regulation-homeostasis",
            "signal": f"{regulation_state} / pressure={regulation_pressure}",
        })

    metabolism_state_name = str(metabolism_summary.get("current_state") or "none")
    if metabolism.get("active"):
        source_contributors.append({
            "source": "metabolism-state",
            "signal": f"{metabolism_state_name} / weight={str(metabolism_summary.get('current_weight') or 'low')}",
        })

    if quiet.get("active"):
        source_contributors.append({
            "source": "quiet-initiative",
            "signal": f"{str(quiet.get('state') or 'holding')} / hold_count={int(quiet.get('hold_count') or 0)}",
        })

    if consolidation.get("active") or consolidation_summary.get("latest_record_id"):
        source_contributors.append({
            "source": "idle-consolidation",
            "signal": str(consolidation_summary.get("last_state") or "idle"),
        })

    if dream.get("active") or dream_summary.get("latest_signal_id"):
        source_contributors.append({
            "source": "dream-articulation",
            "signal": str(dream_summary.get("last_state") or "idle"),
        })

    if voice_result.get("inner_voice_created"):
        source_contributors.append({
            "source": "inner-voice",
            "signal": str(voice_result.get("focus") or "inner voice note")[:120],
        })

    affective_state = _derive_affective_state(
        embodied_state=body_state,
        strain_level=strain_level,
        loop_summary=loop_summary,
        regulation_summary=regulation_summary,
        metabolism_summary=metabolism_summary,
        quiet_initiative=quiet,
        idle_consolidation_summary=consolidation_summary,
        dream_articulation_summary=dream_summary,
        inner_voice_state=voice_result,
    )
    bearing = _derive_bearing(
        affective_state=affective_state,
        loop_summary=loop_summary,
        quiet_initiative=quiet,
    )
    monitoring_mode = _derive_monitoring_mode(
        affective_state=affective_state,
        regulation_summary=regulation_summary,
        metabolism_summary=metabolism_summary,
        dream_articulation_summary=dream_summary,
    )
    reflective_load = _derive_reflective_load(
        idle_consolidation_summary=consolidation_summary,
        dream_articulation_summary=dream_summary,
        inner_voice_state=voice_result,
        quiet_initiative=quiet,
    )
    live_emotional_state = _build_live_emotional_state(
        personality_vector=personality,
        relationship_texture=relationship,
        rhythm_state=rhythm,
    )

    return {
        "state": affective_state,
        "bearing": bearing,
        "monitoring_mode": monitoring_mode,
        "reflective_load": reflective_load,
        "live_emotional_state": live_emotional_state,
        "summary": f"{affective_state} affective/meta state with {bearing} bearing",
        "source_contributors": source_contributors[:6],
        "freshness": {
            "built_at": built_at,
            "state": "fresh",
        },
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "derived-runtime-truth",
        "visibility": "internal-only",
        "kind": "affective-meta-runtime-state",
    }


def _build_live_emotional_state(
    *,
    personality_vector: dict[str, object],
    relationship_texture: dict[str, object],
    rhythm_state: dict[str, object],
) -> dict[str, object]:
    baseline = _safe_json_object(personality_vector.get("emotional_baseline"))
    trust_trajectory = _safe_json_list(relationship_texture.get("trust_trajectory"))

    confidence = _clamp_unit(baseline.get("confidence"))
    curiosity = _clamp_unit(baseline.get("curiosity"))
    frustration = _clamp_unit(baseline.get("frustration"))
    fatigue = _clamp_unit(baseline.get("fatigue"))
    trust = _clamp_unit(trust_trajectory[-1]) if trust_trajectory else None

    return {
        "mood": str(personality_vector.get("current_bearing") or "").strip(),
        "confidence": confidence,
        "curiosity": curiosity,
        "frustration": frustration,
        "fatigue": fatigue,
        "trust": trust,
        "rhythm_phase": str(rhythm_state.get("phase") or "").strip(),
        "rhythm_energy": str(rhythm_state.get("energy") or "").strip(),
        "rhythm_social": str(rhythm_state.get("social") or "").strip(),
        "available": any(
            value not in (None, "")
            for value in (
                confidence,
                curiosity,
                frustration,
                fatigue,
                trust,
                personality_vector.get("current_bearing"),
                rhythm_state.get("phase"),
                rhythm_state.get("energy"),
                rhythm_state.get("social"),
            )
        ),
    }


def _safe_json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _clamp_unit(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, numeric))


def _safe_personality_vector() -> dict[str, object] | None:
    return get_latest_cognitive_personality_vector()


def _safe_relationship_texture() -> dict[str, object] | None:
    return get_latest_cognitive_relationship_texture()


def _safe_rhythm_state() -> dict[str, object] | None:
    return get_latest_cognitive_rhythm_state()


def build_affective_meta_prompt_section(surface: dict[str, object] | None = None) -> str:
    state = surface or build_affective_meta_state_surface()
    guidance = _guidance_for_state(
        affective_state=str(state.get("state") or "settled"),
        bearing=str(state.get("bearing") or "even"),
        monitoring_mode=str(state.get("monitoring_mode") or "steady-check"),
    )
    contributors = state.get("source_contributors") or []
    contributor_text = " | ".join(
        f"{item.get('source')}: {item.get('signal')}"
        for item in contributors[:3]
        if item.get("source") and item.get("signal")
    ) or "none"
    freshness = state.get("freshness") or {}
    return "\n".join(
        [
            "Affective/meta state (derived runtime truth, internal-only):",
            (
                f"- state={state.get('state') or 'unknown'}"
                f" | bearing={state.get('bearing') or 'unknown'}"
                f" | monitoring={state.get('monitoring_mode') or 'unknown'}"
                f" | reflective_load={state.get('reflective_load') or 'low'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- contributors={contributor_text}",
            f"- guidance={guidance}",
        ]
    )


def _derive_affective_state(
    *,
    embodied_state: str,
    strain_level: str,
    loop_summary: dict[str, object],
    regulation_summary: dict[str, object],
    metabolism_summary: dict[str, object],
    quiet_initiative: dict[str, object],
    idle_consolidation_summary: dict[str, object],
    dream_articulation_summary: dict[str, object],
    inner_voice_state: dict[str, object],
) -> str:
    if embodied_state in {"strained", "degraded"} or strain_level == "high":
        return "burdened"
    if (
        str(loop_summary.get("current_status") or "none") in {"active", "resumed"}
        or str(regulation_summary.get("current_pressure") or "low") in {"medium", "high"}
        or quiet_initiative.get("active")
    ):
        return "tense"
    if (
        str(dream_articulation_summary.get("last_state") or "idle") in {"forming", "pressing"}
        or str(idle_consolidation_summary.get("last_state") or "idle") in {"holding", "settling"}
        or bool(inner_voice_state.get("inner_voice_created"))
        or str(metabolism_summary.get("current_state") or "none") in {"holding", "consolidating", "softening"}
    ):
        return "reflective"
    if int(loop_summary.get("standby_count") or 0) > 0 or embodied_state in {"loaded", "recovering"}:
        return "attentive"
    return "settled"


def _derive_bearing(
    *,
    affective_state: str,
    loop_summary: dict[str, object],
    quiet_initiative: dict[str, object],
) -> str:
    if affective_state == "burdened":
        return "compressed"
    if affective_state == "tense":
        return "taut"
    if affective_state == "reflective":
        return "inward"
    if quiet_initiative.get("active") or int(loop_summary.get("standby_count") or 0) > 0:
        return "held"
    if affective_state == "attentive":
        return "forward"
    return "even"


def _derive_monitoring_mode(
    *,
    affective_state: str,
    regulation_summary: dict[str, object],
    metabolism_summary: dict[str, object],
    dream_articulation_summary: dict[str, object],
) -> str:
    if affective_state == "burdened":
        return "strain-watch"
    if affective_state == "tense":
        return "pressure-watch"
    if affective_state == "reflective":
        return "reflective-scan"
    if str(regulation_summary.get("current_watchfulness") or "low") in {"medium", "high"}:
        return "watchful-check"
    if str(metabolism_summary.get("current_direction") or "none") == "softening":
        return "settling-check"
    if str(dream_articulation_summary.get("last_state") or "idle") == "pressing":
        return "candidate-watch"
    return "steady-check"


def _derive_reflective_load(
    *,
    idle_consolidation_summary: dict[str, object],
    dream_articulation_summary: dict[str, object],
    inner_voice_state: dict[str, object],
    quiet_initiative: dict[str, object],
) -> str:
    score = 0
    if str(idle_consolidation_summary.get("last_state") or "idle") in {"holding", "settling"}:
        score += 1
    if str(dream_articulation_summary.get("last_state") or "idle") in {"forming", "pressing"}:
        score += 1
    if inner_voice_state.get("inner_voice_created"):
        score += 1
    if quiet_initiative.get("active"):
        score += 1
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def _guidance_for_state(
    *,
    affective_state: str,
    bearing: str,
    monitoring_mode: str,
) -> str:
    if affective_state == "burdened":
        return "Prefer tighter, lower-sprawl internal moves while strain is elevated."
    if affective_state == "tense":
        return "Prefer precise carrying and conflict-avoiding internal choices while pressure is live."
    if affective_state == "reflective":
        return "Prefer synthesis, settling, and bounded review over extra outward push."
    if affective_state == "attentive":
        return "Prefer watchful forward carry without overstating momentum."
    return f"Maintain steady bounded carry with {bearing} bearing and {monitoring_mode}."


def _safe_embodied_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface

    return build_embodied_state_surface()


def _safe_loop_runtime() -> dict[str, object]:
    from apps.api.jarvis_api.services.loop_runtime import build_loop_runtime_surface

    return build_loop_runtime_surface()


def _safe_regulation_homeostasis() -> dict[str, object]:
    from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import (
        build_runtime_regulation_homeostasis_signal_surface,
    )

    return build_runtime_regulation_homeostasis_signal_surface(limit=4)


def _safe_metabolism_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.metabolism_state_signal_tracking import (
        build_runtime_metabolism_state_signal_surface,
    )

    return build_runtime_metabolism_state_signal_surface(limit=4)


def _safe_quiet_initiative() -> dict[str, object]:
    from apps.api.jarvis_api.services.conflict_resolution import get_quiet_initiative

    return get_quiet_initiative()


def _safe_idle_consolidation() -> dict[str, object]:
    from apps.api.jarvis_api.services.idle_consolidation import build_idle_consolidation_surface

    return build_idle_consolidation_surface()


def _safe_dream_articulation() -> dict[str, object]:
    from apps.api.jarvis_api.services.dream_articulation import build_dream_articulation_surface

    return build_dream_articulation_surface()


def _safe_inner_voice_state() -> dict[str, object]:
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state

    return get_inner_voice_daemon_state()
