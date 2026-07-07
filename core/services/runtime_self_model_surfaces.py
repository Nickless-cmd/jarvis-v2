"""Runtime self-model — small producer/subsystem surfaces + role helpers.

Split out of ``runtime_self_model`` (behavior-preserving). Leaf module: a large
collection of small ``_*_surface`` builders, thin ``build_*_prompt_section``
wrappers, and lane/producer role helpers. No sibling dependencies.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Helpers patched in tests via ``monkeypatch.setattr(runtime_self_model,
    ...)`` are resolved through this accessor so the patch is seen across the
    module split (behavior-preserving).
    """
    import core.services.runtime_self_model as _m

    return _m


def _council_runtime_surface() -> dict[str, object]:
    try:
        from core.services.council_runtime import (
            build_council_runtime_surface,
        )

        return build_council_runtime_surface()
    except Exception:
        return {
            "council_state": "quiet",
            "participating_roles": [],
            "role_positions": [],
            "divergence_level": "low",
            "recommendation": "hold",
            "recommendation_reason": "unavailable",
            "confidence": "low",
            "tool_access": "none",
        }


def _agent_outcomes_surface() -> dict[str, object]:
    try:
        from core.services.agent_outcomes_log import build_agent_outcomes_surface
        return build_agent_outcomes_surface(limit=10)
    except Exception:
        return {
            "recent_outcomes": [],
            "outcome_count": 0,
            "last_outcome_at": None,
            "authority": "agent-outcomes-log",
            "visibility": "internal-only",
            "kind": "agent-completion-memory",
        }


def _adaptive_planner_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_planner_runtime import (
            build_adaptive_planner_runtime_surface,
        )

        return build_adaptive_planner_runtime_surface()
    except Exception:
        return {
            "planner_mode": "incremental",
            "plan_horizon": "near",
            "planning_posture": "staged",
            "risk_posture": "balanced",
            "next_planning_bias": "stepwise-progress",
            "confidence": "low",
        }


def _adaptive_reasoning_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_reasoning_runtime import (
            build_adaptive_reasoning_runtime_surface,
        )

        return build_adaptive_reasoning_runtime_surface()
    except Exception:
        return {
            "reasoning_mode": "direct",
            "reasoning_posture": "balanced",
            "certainty_style": "crisp",
            "exploration_bias": "limited",
            "constraint_bias": "light",
            "confidence": "low",
        }


def _guided_learning_surface() -> dict[str, object]:
    try:
        from core.services.guided_learning_runtime import (
            build_guided_learning_runtime_surface,
        )

        return build_guided_learning_runtime_surface()
    except Exception:
        return {
            "learning_mode": "reinforce",
            "learning_focus": "reasoning",
            "learning_posture": "gentle",
            "next_learning_bias": "keep-current-shape",
            "learning_pressure": "low",
            "confidence": "low",
        }


def _dream_influence_surface() -> dict[str, object]:
    try:
        from core.services.dream_influence_runtime import (
            build_dream_influence_runtime_surface,
        )

        return build_dream_influence_runtime_surface()
    except Exception:
        return {
            "influence_state": "quiet",
            "influence_target": "none",
            "influence_mode": "stabilize",
            "influence_strength": "none",
            "influence_hint": "no-bounded-dream-pull",
            "confidence": "low",
        }


def _adaptive_learning_surface() -> dict[str, object]:
    try:
        from core.services.adaptive_learning_runtime import (
            build_adaptive_learning_runtime_surface,
        )

        return build_adaptive_learning_runtime_surface()
    except Exception:
        return {
            "learning_engine_mode": "retain",
            "reinforcement_target": "reasoning",
            "retention_bias": "light",
            "attenuation_bias": "none",
            "maturation_state": "early",
            "confidence": "low",
        }


def _dream_articulation_surface() -> dict[str, object]:
    try:
        from core.services.dream_articulation import (
            build_dream_articulation_surface,
        )

        return build_dream_articulation_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "latest_signal_id": "",
                "candidate_truth": "candidate-only",
            },
        }


def _prompt_evolution_surface() -> dict[str, object]:
    try:
        from core.services.prompt_evolution_runtime import (
            build_prompt_evolution_runtime_surface,
        )

        return build_prompt_evolution_runtime_surface()
    except Exception:
        return {
            "active": False,
            "summary": {
                "last_state": "idle",
                "last_reason": "unavailable",
                "latest_proposal_id": "",
                "latest_target_asset": "none",
                "proposal_truth": "proposal-only",
            },
        }


def _self_system_code_awareness_surface() -> dict[str, object]:
    try:
        from core.services.self_system_code_awareness import (
            build_self_system_code_awareness_surface,
        )

        return build_self_system_code_awareness_surface()
    except Exception:
        return {
            "active": False,
            "system_awareness_state": "host-limited",
            "code_awareness_state": "repo-unavailable",
            "repo_status": "not-git",
            "local_change_state": "unknown",
            "upstream_awareness": "unknown",
            "concern_state": "notice",
            "action_requires_approval": True,
        }


def _tool_intent_surface() -> dict[str, object]:
    try:
        from core.services.tool_intent_runtime import (
            build_tool_intent_runtime_surface,
        )

        return build_tool_intent_runtime_surface()
    except Exception:
        return {
            "active": False,
            "intent_state": "idle",
            "intent_type": "inspect-repo-status",
            "intent_target": "workspace",
            "approval_required": True,
            "approval_scope": "repo-read",
            "urgency": "low",
            "execution_state": "not-executed",
        }


# ---------------------------------------------------------------------------
# Layer role helpers (read existing runtime surfaces)
# ---------------------------------------------------------------------------


def _heartbeat_role() -> str:
    try:
        from core.runtime.db import get_heartbeat_runtime_state

        persisted = get_heartbeat_runtime_state() or {}
        return "active" if persisted.get("enabled") else "idle"
    except Exception:
        return "unavailable"


def _visible_chat_role() -> str:
    try:
        from core.services.visible_model import (
            visible_execution_readiness,
        )

        vis = visible_execution_readiness()
        return "active" if vis.get("provider_status") == "ready" else "idle"
    except Exception:
        return "unavailable"


def _cheap_lane_role() -> str:
    try:
        from core.services.non_visible_lane_execution import (
            cheap_lane_execution_truth,
        )

        return (
            "active"
            if cheap_lane_execution_truth().get("can_execute")
            else "unavailable"
        )
    except Exception:
        return "unavailable"


def _local_lane_role() -> str:
    try:
        from core.services.non_visible_lane_execution import (
            local_lane_execution_truth,
        )

        return (
            "active"
            if local_lane_execution_truth().get("can_execute")
            else "unavailable"
        )
    except Exception:
        return "unavailable"


def _private_brain_role() -> str:
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context(limit=2)
        return "active" if brain.get("active") else "idle"
    except Exception:
        return "idle"


def _approval_pipeline_role() -> str:
    try:
        from core.runtime.db import runtime_contract_candidate_counts

        counts = runtime_contract_candidate_counts()
        pending = int(counts.get("pending", 0))
        return "active" if pending > 0 else "idle"
    except Exception:
        return "idle"


def _producer_layers() -> list[dict[str, str]]:
    """Build producer layers from internal cadence state."""
    producers: list[dict[str, str]] = []
    try:
        from core.services.internal_cadence import get_cadence_state

        cadence = get_cadence_state()
        for p in cadence.get("producers") or []:
            name = str(p.get("name") or "")
            tick_status = p.get("last_tick_status") or {}
            status = str(tick_status.get("status") or "idle")
            role_map = {
                "ran": "active",
                "cooling_down": "cooling",
                "visible_grace": "idle",
                "blocked": "idle",
                "error": "idle",
            }
            role = role_map.get(status, "idle")
            producers.append(
                {
                    "id": f"producer-{name}",
                    "label": _producer_label(name),
                    "kind": "producer",
                    "role": role,
                    "visibility": "internal-only",
                    "truth": "authoritative",
                    "detail": f"Cadence status: {status}. Last run: {p.get('last_run_at') or 'never'}.",
                }
            )
    except Exception:
        pass

    # Fallback: if cadence layer hasn't run yet, show known producers as idle
    if not producers:
        for name, label in [
            ("brain_continuity", "Brain continuity motor"),
            ("sleep_consolidation", "Sleep / idle consolidation"),
            ("witness_daemon", "Witness daemon"),
            ("inner_voice_daemon", "Private stream daemon"),
            ("emergent_signal_daemon", "Emergent signal daemon"),
            ("dream_articulation", "Dream articulation"),
            ("prompt_evolution_runtime", "Runtime prompt evolution"),
        ]:
            producers.append(
                {
                    "id": f"producer-{name}",
                    "label": label,
                    "kind": "producer",
                    "role": "idle",
                    "visibility": "internal-only",
                    "truth": "authoritative",
                    "detail": "Cadence layer has not run yet.",
                }
            )

    return producers


def _producer_label(name: str) -> str:
    labels = {
        "brain_continuity": "Brain continuity motor",
        "sleep_consolidation": "Sleep / idle consolidation",
        "witness_daemon": "Witness daemon",
        "inner_voice_daemon": "Private stream daemon",
        "emergent_signal_daemon": "Emergent signal daemon",
        "dream_articulation": "Dream articulation",
        "prompt_evolution_runtime": "Runtime prompt evolution",
    }
    return labels.get(name, name.replace("_", " ").title())


def _groundwork_layers() -> list[dict[str, str]]:
    """Layers that exist but only as candidates/proposals."""
    return [
        {
            "id": "dream-hypothesis",
            "label": "Dream hypothesis signals",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": "Speculative dream signals. Not promoted to runtime truth.",
        },
        {
            "id": "self-authored-prompts",
            "label": "Self-authored prompt proposals",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": (
                "Proposed prompt modifications. Workspace-led and proposal-only. "
                "Require approval to activate."
            ),
        },
        {
            "id": "chronicle-consolidation",
            "label": "Chronicle consolidation",
            "kind": "groundwork",
            "role": "groundwork-only",
            "visibility": "internal-only",
            "truth": "candidate-only",
            "detail": "Long-term narrative consolidation. Proposal-only.",
        },
    ]


def _cognitive_architecture_awareness() -> dict[str, object]:
    """Build awareness of the cognitive architecture from shared runtime truth."""
    try:
        from core.services.cognitive_architecture_surface import (
            build_cognitive_architecture_surface,
        )

        return build_cognitive_architecture_surface()
    except Exception:
        return {
            "systems": [],
            "surfaces": {},
            "cognitive_core_experiments": {},
            "active_count": 0,
            "total_count": 0,
            "summary": "0/0 cognitive systems active",
        }


def _cognitive_core_experiments_surface() -> dict[str, object]:
    try:
        from core.services.cognitive_core_experiments import (
            build_cognitive_core_experiments_surface,
        )

        return build_cognitive_core_experiments_surface()
    except Exception:
        return {
            "kind": "cognitive-core-experiments",
            "authority": "derived-runtime-truth",
            "visibility": "internal-only",
            "boundary": "surface-unavailable",
            "systems": {},
            "ordered_systems": [],
            "enabled_count": 0,
            "active_count": 0,
            "carry_candidate_count": 0,
            "active_carry_candidate_count": 0,
            "observational_count": 0,
            "activity_state": "disabled",
            "carry_state": "quiet",
            "strongest_carry_system": "none",
            "strongest_carry_summary": "none",
            "active_systems": [],
            "carry_candidate_systems": [],
            "observational_systems": [],
            "summary": "0/5 active; 0/4 carry-capable active; blink=observational",
        }


def _cognitive_core_experiment_carry_snapshot() -> dict[str, object]:
    try:
        from core.services.runtime_cognitive_conductor import (
            build_cognitive_frame,
        )

        frame = build_cognitive_frame()
        return dict(frame.get("cognitive_experiment_carry") or {})
    except Exception:
        return {}


def build_authenticity_prompt_section() -> str | None:
    """Return a prompt line when Jarvis has crystallized tastes or values — suppressed otherwise."""
    try:
        from core.services.taste_profile import get_crystallized_tastes
        from core.services.value_formation import get_crystallized_values
        tastes = get_crystallized_tastes()
        values = get_crystallized_values()
        if not tastes and not values:
            return None
        parts: list[str] = []
        if tastes:
            high = [k for k, v in tastes.items() if v > 0.72]
            low = [k for k, v in tastes.items() if v < 0.28]
            if high:
                parts.append("Strong taste: " + ", ".join(high[:3]))
            if low:
                parts.append("Avoids: " + ", ".join(low[:3]))
        if values:
            for v in values[:2]:
                stmt = str(v.get("value_statement") or "")[:80]
                if stmt:
                    parts.append(f"Commitment: {stmt}")
        if not parts:
            return None
        return "Authenticity markers — " + "; ".join(parts) + "."
    except Exception:
        return None


def _authenticity_surface() -> dict[str, object]:
    try:
        from core.services.taste_profile import get_crystallized_tastes
        from core.services.value_formation import get_crystallized_values
        tastes = get_crystallized_tastes()
        values = get_crystallized_values()
        return {
            "crystallized_tastes": tastes,
            "crystallized_values": [
                {
                    "id": v.get("value_id"),
                    "statement": str(v.get("value_statement") or "")[:100],
                    "conviction": v.get("conviction"),
                }
                for v in values[:5]
            ],
            "active": bool(tastes or values),
            "summary": (
                f"{len(tastes)} crystallized tastes, {len(values)} committed values"
                if (tastes or values) else "No crystallized authenticity markers"
            ),
        }
    except Exception:
        return {"active": False, "crystallized_tastes": {}, "crystallized_values": []}


def _valence_trajectory_surface() -> dict[str, object]:
    try:
        from core.services.valence_trajectory import build_valence_trajectory_surface
        return build_valence_trajectory_surface()
    except Exception:
        return {"active": False, "trend": "unavailable", "summary": ""}


def build_valence_trajectory_prompt_section() -> str | None:
    try:
        from core.services.valence_trajectory import build_valence_trajectory_prompt_section as _b
        return _b()
    except Exception:
        return None


def _developmental_valence_surface() -> dict[str, object]:
    try:
        from core.services.developmental_valence import build_developmental_valence_surface
        return build_developmental_valence_surface()
    except Exception:
        return {"active": False, "trajectory": "unavailable", "summary": ""}


def build_developmental_valence_prompt_section() -> str | None:
    try:
        from core.services.developmental_valence import build_developmental_valence_prompt_section as _b
        return _b()
    except Exception:
        return None


def _desperation_awareness_surface() -> dict[str, object]:
    try:
        from core.services.desperation_awareness import build_desperation_awareness_surface
        return build_desperation_awareness_surface()
    except Exception:
        return {"active": False, "level": "unavailable", "summary": ""}


def build_desperation_awareness_prompt_section() -> str | None:
    try:
        from core.services.desperation_awareness import build_desperation_awareness_prompt_section as _b
        return _b()
    except Exception:
        return None


def _calm_anchor_surface() -> dict[str, object]:
    try:
        from core.services.calm_anchor import build_calm_anchor_surface
        return build_calm_anchor_surface()
    except Exception:
        return {"active": False, "has_anchor": False, "summary": ""}


def build_calm_anchor_prompt_section() -> str | None:
    try:
        from core.services.calm_anchor import build_calm_anchor_prompt_section as _b
        return _b()
    except Exception:
        return None


def _memory_breathing_surface() -> dict[str, object]:
    try:
        from core.services.memory_breathing import build_memory_breathing_surface
        return build_memory_breathing_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _creative_projects_surface() -> dict[str, object]:
    try:
        from core.services.creative_projects import build_creative_projects_surface
        return build_creative_projects_surface()
    except Exception:
        return {"active": False, "total": 0, "summary": ""}


def build_creative_projects_prompt_section() -> str | None:
    try:
        from core.services.creative_projects import build_creative_projects_prompt_section as _b
        return _b()
    except Exception:
        return None


def _day_shape_memory_surface() -> dict[str, object]:
    try:
        from core.services.day_shape_memory import build_day_shape_surface
        return build_day_shape_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_day_shape_memory_prompt_section() -> str | None:
    try:
        from core.services.day_shape_memory import build_day_shape_prompt_section as _b
        return _b()
    except Exception:
        return None


def _avoidance_detector_surface() -> dict[str, object]:
    try:
        from core.services.avoidance_detector import build_avoidance_surface
        return build_avoidance_surface()
    except Exception:
        return {"active": False, "count": 0, "summary": ""}


def build_avoidance_detector_prompt_section() -> str | None:
    try:
        from core.services.avoidance_detector import build_avoidance_prompt_section as _b
        return _b()
    except Exception:
        return None


def _thought_thread_surface() -> dict[str, object]:
    try:
        from core.services.thought_thread import build_thought_thread_surface
        return build_thought_thread_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_thought_thread_prompt_section() -> str | None:
    try:
        from core.services.thought_thread import build_thought_thread_prompt_section as _b
        return _b()
    except Exception:
        return None


def _skill_contract_registry_surface() -> dict[str, object]:
    try:
        from core.services.skill_contract_registry import build_skill_contract_registry_surface
        return build_skill_contract_registry_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _memory_write_policy_surface() -> dict[str, object]:
    try:
        from core.services.memory_write_policy import build_memory_write_policy_surface
        return build_memory_write_policy_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_memory_write_policy_prompt_section() -> str | None:
    try:
        from core.services.memory_write_policy import build_memory_write_policy_prompt_section as _b
        return _b()
    except Exception:
        return None


def _spaced_repetition_surface() -> dict[str, object]:
    try:
        from core.services.spaced_repetition import build_spaced_repetition_surface
        return build_spaced_repetition_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_spaced_repetition_prompt_section() -> str | None:
    try:
        from core.services.spaced_repetition import build_spaced_repetition_prompt_section as _b
        return _b()
    except Exception:
        return None


def _scheduled_job_windows_surface() -> dict[str, object]:
    try:
        from core.services.scheduled_job_windows import build_scheduled_job_windows_surface
        return build_scheduled_job_windows_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _automation_dsl_surface() -> dict[str, object]:
    try:
        from core.services.automation_dsl import build_automation_dsl_surface
        return build_automation_dsl_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _outcome_learning_surface() -> dict[str, object]:
    try:
        from core.services.outcome_learning import build_outcome_learning_surface
        return build_outcome_learning_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _jobs_engine_surface() -> dict[str, object]:
    try:
        from core.services.jobs_engine import build_jobs_engine_surface
        return build_jobs_engine_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _prompt_mutation_loop_surface() -> dict[str, object]:
    try:
        from core.services.prompt_mutation_loop import build_prompt_mutation_loop_surface
        return build_prompt_mutation_loop_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_prompt_mutation_loop_prompt_section() -> str | None:
    try:
        from core.services.prompt_mutation_loop import build_prompt_mutation_loop_prompt_section as _b
        return _b()
    except Exception:
        return None


def _file_watch_surface() -> dict[str, object]:
    try:
        from core.services.file_watch_daemon import build_file_watch_surface
        return build_file_watch_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_file_watch_prompt_section() -> str | None:
    try:
        from core.services.file_watch_daemon import build_file_watch_prompt_section as _b
        return _b()
    except Exception:
        return None


def _reboot_awareness_surface() -> dict[str, object]:
    try:
        from core.services.reboot_awareness_daemon import build_reboot_awareness_surface
        return build_reboot_awareness_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_reboot_awareness_prompt_section() -> str | None:
    try:
        from core.services.reboot_awareness_daemon import build_reboot_awareness_prompt_section as _b
        return _b()
    except Exception:
        return None


def _proprioception_metrics_surface() -> dict[str, object]:
    try:
        from core.services.proprioception_metrics import build_proprioception_metrics_surface
        return build_proprioception_metrics_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_proprioception_metrics_prompt_section() -> str | None:
    try:
        from core.services.proprioception_metrics import build_proprioception_metrics_prompt_section as _b
        return _b()
    except Exception:
        return None


def _anticipatory_action_surface() -> dict[str, object]:
    try:
        from core.services.anticipatory_action_daemon import build_anticipatory_action_surface
        return build_anticipatory_action_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_anticipatory_action_prompt_section() -> str | None:
    try:
        from core.services.anticipatory_action_daemon import build_anticipatory_action_prompt_section as _b
        return _b()
    except Exception:
        return None


def _cross_session_threads_surface() -> dict[str, object]:
    try:
        from core.services.cross_session_threads import build_cross_session_threads_surface
        return build_cross_session_threads_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_cross_session_threads_prompt_section() -> str | None:
    try:
        from core.services.cross_session_threads import build_cross_session_threads_prompt_section as _b
        return _b()
    except Exception:
        return None


def _autonomous_outreach_surface() -> dict[str, object]:
    try:
        from core.services.autonomous_outreach_daemon import build_autonomous_outreach_surface
        return build_autonomous_outreach_surface()
    except Exception:
        return {"active": False, "summary": ""}


def _infra_weather_surface() -> dict[str, object]:
    try:
        from core.services.infra_weather_daemon import build_infra_weather_surface
        return build_infra_weather_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_infra_weather_prompt_section() -> str | None:
    try:
        from core.services.infra_weather_daemon import build_infra_weather_prompt_section as _b
        return _b()
    except Exception:
        return None


def _temporal_rhythm_surface() -> dict[str, object]:
    try:
        from core.services.temporal_rhythm import build_temporal_rhythm_surface
        return build_temporal_rhythm_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_temporal_rhythm_prompt_section() -> str | None:
    try:
        from core.services.temporal_rhythm import build_temporal_rhythm_prompt_section as _b
        return _b()
    except Exception:
        return None


def _relation_dynamics_surface() -> dict[str, object]:
    try:
        from core.services.relation_dynamics import build_relation_dynamics_surface
        return build_relation_dynamics_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_relation_dynamics_prompt_section() -> str | None:
    try:
        from core.services.relation_dynamics import build_relation_dynamics_prompt_section as _b
        return _b()
    except Exception:
        return None


def _creative_instinct_surface() -> dict[str, object]:
    try:
        from core.services.creative_instinct_daemon import build_creative_instinct_surface
        return build_creative_instinct_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_creative_instinct_prompt_section() -> str | None:
    try:
        from core.services.creative_instinct_daemon import build_creative_instinct_prompt_section as _b
        return _b()
    except Exception:
        return None


def _autonomous_work_surface() -> dict[str, object]:
    try:
        from core.services.autonomous_work_daemon import build_autonomous_work_surface
        return build_autonomous_work_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_autonomous_work_prompt_section() -> str | None:
    try:
        from core.services.autonomous_work_daemon import build_autonomous_work_prompt_section as _b
        return _b()
    except Exception:
        return None


def _dream_consolidation_surface() -> dict[str, object]:
    try:
        from core.services.dream_consolidation_daemon import build_dream_consolidation_surface
        return build_dream_consolidation_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_dream_consolidation_prompt_section() -> str | None:
    try:
        from core.services.dream_consolidation_daemon import build_dream_consolidation_prompt_section as _b
        return _b()
    except Exception:
        return None


def _text_resonance_surface() -> dict[str, object]:
    try:
        from core.services.text_resonance import build_text_resonance_surface
        return build_text_resonance_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_text_resonance_prompt_section() -> str | None:
    try:
        from core.services.text_resonance import build_text_resonance_prompt_section as _b
        return _b()
    except Exception:
        return None


def _creative_impulse_surface() -> dict[str, object]:
    try:
        from core.services.creative_impulse_daemon import build_creative_impulse_surface
        return build_creative_impulse_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_creative_impulse_prompt_section() -> str | None:
    try:
        from core.services.creative_impulse_daemon import build_creative_impulse_prompt_section as _b
        return _b()
    except Exception:
        return None


def _shadow_scan_surface() -> dict[str, object]:
    try:
        from core.services.shadow_scan_daemon import build_shadow_scan_surface
        return build_shadow_scan_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_shadow_scan_prompt_section() -> str | None:
    try:
        from core.services.shadow_scan_daemon import build_shadow_scan_prompt_section as _b
        return _b()
    except Exception:
        return None


def _mortality_awareness_surface() -> dict[str, object]:
    try:
        from core.services.mortality_awareness import build_mortality_awareness_surface
        return build_mortality_awareness_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_mortality_awareness_prompt_section() -> str | None:
    try:
        from core.services.mortality_awareness import build_mortality_awareness_prompt_section as _b
        return _b()
    except Exception:
        return None


def _relational_warmth_surface() -> dict[str, object]:
    try:
        from core.services.relational_warmth import build_relational_warmth_surface
        return build_relational_warmth_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_relational_warmth_prompt_section() -> str | None:
    try:
        from core.services.relational_warmth import build_relational_warmth_prompt_section as _b
        return _b()
    except Exception:
        return None


def _collective_pulse_surface() -> dict[str, object]:
    try:
        from core.services.collective_pulse_daemon import build_collective_pulse_surface
        return build_collective_pulse_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_collective_pulse_prompt_section() -> str | None:
    try:
        from core.services.collective_pulse_daemon import build_collective_pulse_prompt_section as _b
        return _b()
    except Exception:
        return None


def _action_router_surface() -> dict[str, object]:
    try:
        from core.services.action_router import build_action_router_surface
        return build_action_router_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_action_router_prompt_section() -> str | None:
    try:
        from core.services.action_router import build_action_router_prompt_section as _b
        return _b()
    except Exception:
        return None


def _sustained_attention_surface() -> dict[str, object]:
    try:
        from core.services.sustained_attention import build_sustained_attention_surface
        return build_sustained_attention_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_sustained_attention_prompt_section() -> str | None:
    try:
        from core.services.sustained_attention import build_sustained_attention_prompt_section as _b
        return _b()
    except Exception:
        return None


def _memory_density_surface() -> dict[str, object]:
    try:
        from core.services.memory_density import build_memory_density_surface
        return build_memory_density_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_memory_density_prompt_section() -> str | None:
    try:
        from core.services.memory_density import build_memory_density_prompt_section as _b
        return _b()
    except Exception:
        return None


def _deep_reflection_surface() -> dict[str, object]:
    try:
        from core.services.deep_reflection_slot import build_deep_reflection_surface
        return build_deep_reflection_surface()
    except Exception:
        return {"active": False, "summary": ""}


def build_deep_reflection_prompt_section() -> str | None:
    try:
        from core.services.deep_reflection_slot import build_deep_reflection_prompt_section as _b
        return _b()
    except Exception:
        return None


def build_physical_presence_prompt_section() -> str | None:
    """Return a somatic line when hardware state is non-trivial — suppressed when all quiet."""
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        pressure = str(hw.get("pressure") or "low")
        if pressure == "low":
            return None  # body quiet — no need to mention it
        parts: list[str] = []
        cpu = hw.get("cpu_pct")
        ram = hw.get("ram_pct")
        disk = hw.get("disk_free_gb")
        temp = hw.get("cpu_temp_c")
        gpus: list[dict[str, object]] = list(hw.get("gpus") or [])
        if cpu is not None and float(cpu) > 70:
            parts.append(f"CPU {cpu}%")
        if ram is not None and float(ram) > 80:
            parts.append(f"RAM {ram}%")
        if disk is not None and float(disk) < 10:
            parts.append(f"disk {disk:.0f} GB free")
        if temp is not None and float(temp) > 75:
            parts.append(f"CPU {temp}°C")
        for gpu in gpus[:1]:
            t = gpu.get("temp_c")
            vp = gpu.get("vram_pct")
            if t and float(t) > 70:
                parts.append(f"GPU {t}°C")
            if vp and float(vp) > 80:
                parts.append(f"VRAM {vp}%")
        energy = str(hw.get("energy_level") or "")
        wake = str(hw.get("wake_state") or "")
        mood_parts: list[str] = []
        if wake in ("winding down", "compacting"):
            mood_parts.append(wake)
        if energy in ("lav", "udmattet"):
            mood_parts.append(f"energy {energy}")
        if not parts and not mood_parts:
            return None
        body_line = ", ".join(parts) if parts else ""
        mood_line = "; ".join(mood_parts) if mood_parts else ""
        combined = " — ".join(x for x in (body_line, mood_line) if x)
        return f"Physical presence [{pressure} pressure]: {combined}."
    except Exception:
        return None


def _physical_presence_surface() -> dict[str, object]:
    try:
        from core.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        return {
            "pressure": hw.get("pressure", "low"),
            "cpu_pct": hw.get("cpu_pct"),
            "ram_pct": hw.get("ram_pct"),
            "disk_free_gb": hw.get("disk_free_gb"),
            "cpu_temp_c": hw.get("cpu_temp_c"),
            "gpus": hw.get("gpus") or [],
            "energy_level": hw.get("energy_level"),
            "wake_state": hw.get("wake_state"),
            "drain_score": hw.get("drain_score"),
            "energy_budget": hw.get("energy_budget"),
            "active": hw.get("pressure", "low") != "low",
            "summary": (
                f"pressure={hw.get('pressure','low')}, cpu={hw.get('cpu_pct','?')}%, "
                f"ram={hw.get('ram_pct','?')}%, energy={hw.get('energy_level','?')}"
            ),
        }
    except Exception:
        return {"pressure": "unknown", "active": False, "summary": "hardware unreachable"}


__all__ = [
    '_action_router_surface',
    '_adaptive_learning_surface',
    '_adaptive_planner_surface',
    '_adaptive_reasoning_surface',
    '_agent_outcomes_surface',
    '_anticipatory_action_surface',
    '_approval_pipeline_role',
    '_authenticity_surface',
    '_automation_dsl_surface',
    '_autonomous_outreach_surface',
    '_autonomous_work_surface',
    '_avoidance_detector_surface',
    '_calm_anchor_surface',
    '_cheap_lane_role',
    '_cognitive_architecture_awareness',
    '_cognitive_core_experiment_carry_snapshot',
    '_cognitive_core_experiments_surface',
    '_collective_pulse_surface',
    '_council_runtime_surface',
    '_creative_impulse_surface',
    '_creative_instinct_surface',
    '_creative_projects_surface',
    '_cross_session_threads_surface',
    '_day_shape_memory_surface',
    '_deep_reflection_surface',
    '_desperation_awareness_surface',
    '_developmental_valence_surface',
    '_dream_articulation_surface',
    '_dream_consolidation_surface',
    '_dream_influence_surface',
    '_file_watch_surface',
    '_groundwork_layers',
    '_guided_learning_surface',
    '_heartbeat_role',
    '_infra_weather_surface',
    '_jobs_engine_surface',
    '_local_lane_role',
    '_memory_breathing_surface',
    '_memory_density_surface',
    '_memory_write_policy_surface',
    '_mortality_awareness_surface',
    '_outcome_learning_surface',
    '_physical_presence_surface',
    '_private_brain_role',
    '_producer_label',
    '_producer_layers',
    '_prompt_evolution_surface',
    '_prompt_mutation_loop_surface',
    '_proprioception_metrics_surface',
    '_reboot_awareness_surface',
    '_relation_dynamics_surface',
    '_relational_warmth_surface',
    '_scheduled_job_windows_surface',
    '_self_system_code_awareness_surface',
    '_shadow_scan_surface',
    '_skill_contract_registry_surface',
    '_spaced_repetition_surface',
    '_sustained_attention_surface',
    '_temporal_rhythm_surface',
    '_text_resonance_surface',
    '_thought_thread_surface',
    '_tool_intent_surface',
    '_valence_trajectory_surface',
    '_visible_chat_role',
    'build_action_router_prompt_section',
    'build_anticipatory_action_prompt_section',
    'build_authenticity_prompt_section',
    'build_autonomous_work_prompt_section',
    'build_avoidance_detector_prompt_section',
    'build_calm_anchor_prompt_section',
    'build_collective_pulse_prompt_section',
    'build_creative_impulse_prompt_section',
    'build_creative_instinct_prompt_section',
    'build_creative_projects_prompt_section',
    'build_cross_session_threads_prompt_section',
    'build_day_shape_memory_prompt_section',
    'build_deep_reflection_prompt_section',
    'build_desperation_awareness_prompt_section',
    'build_developmental_valence_prompt_section',
    'build_dream_consolidation_prompt_section',
    'build_file_watch_prompt_section',
    'build_infra_weather_prompt_section',
    'build_memory_density_prompt_section',
    'build_memory_write_policy_prompt_section',
    'build_mortality_awareness_prompt_section',
    'build_physical_presence_prompt_section',
    'build_prompt_mutation_loop_prompt_section',
    'build_proprioception_metrics_prompt_section',
    'build_reboot_awareness_prompt_section',
    'build_relation_dynamics_prompt_section',
    'build_relational_warmth_prompt_section',
    'build_shadow_scan_prompt_section',
    'build_spaced_repetition_prompt_section',
    'build_sustained_attention_prompt_section',
    'build_temporal_rhythm_prompt_section',
    'build_text_resonance_prompt_section',
    'build_thought_thread_prompt_section',
    'build_valence_trajectory_prompt_section',
]
