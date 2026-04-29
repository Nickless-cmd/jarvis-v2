"""Heartbeat self-knowledge section builder.

Extracted from prompt_contract.py on 2026-04-29 to bring that file below
the 1500-line code-rule threshold and to give this 700-line collector its
own home. The function aggregates ~50 small "self-knowledge" prompt
sections from runtime_self_model and related services, classifies them
as foreground/background/critical, then renders a compact two-tier
prompt block.

The original symbol (``_heartbeat_self_knowledge_section``) is preserved
in ``prompt_contract`` as a thin shim that re-exports
``build_heartbeat_self_knowledge_section`` so existing callers and tests
continue to work unchanged.
"""

from __future__ import annotations


def build_heartbeat_self_knowledge_section() -> str | None:
    """Build a compact self-knowledge section for the heartbeat prompt."""
    entries: list[dict[str, str]] = []

    def _append_entry(*, key: str, section: str | None, importance: str) -> None:
        text = str(section or "").strip()
        if text:
            entries.append({"key": key, "section": text, "importance": importance})

    try:
        from core.services.runtime_self_knowledge import (
            build_self_knowledge_prompt_section,
        )

        _append_entry(
            key="self-knowledge",
            section=build_self_knowledge_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.embodied_state import (
            build_embodied_state_prompt_section,
        )

        _append_entry(
            key="embodied",
            section=build_embodied_state_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.affective_meta_state import (
            build_affective_meta_prompt_section,
        )

        _append_entry(
            key="affective",
            section=build_affective_meta_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.experiential_runtime_context import (
            build_experiential_runtime_prompt_section,
        )

        _append_entry(
            key="experiential",
            section=build_experiential_runtime_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.epistemic_runtime_state import (
            build_epistemic_runtime_prompt_section,
        )

        _append_entry(
            key="epistemic",
            section=build_epistemic_runtime_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.adaptive_planner_runtime import (
            build_adaptive_planner_prompt_section,
        )

        _append_entry(
            key="adaptive-planner",
            section=build_adaptive_planner_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.adaptive_reasoning_runtime import (
            build_adaptive_reasoning_prompt_section,
        )

        _append_entry(
            key="adaptive-reasoning",
            section=build_adaptive_reasoning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.guided_learning_runtime import (
            build_guided_learning_prompt_section,
        )

        _append_entry(
            key="guided-learning",
            section=build_guided_learning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.adaptive_learning_runtime import (
            build_adaptive_learning_prompt_section,
        )

        _append_entry(
            key="adaptive-learning",
            section=build_adaptive_learning_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.loop_runtime import (
            build_loop_runtime_prompt_section,
        )

        _append_entry(
            key="loop-runtime",
            section=build_loop_runtime_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.subagent_ecology import (
            build_subagent_ecology_prompt_section,
        )

        _append_entry(
            key="subagent-ecology",
            section=build_subagent_ecology_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.council_runtime import (
            build_council_runtime_prompt_section,
        )

        _append_entry(
            key="council-runtime",
            section=build_council_runtime_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.agent_outcomes_log import build_agent_outcomes_prompt_lines
        lines = build_agent_outcomes_prompt_lines(limit=3)
        if lines:
            section = "Recent agent outcomes (internal, solo-task completions):\n" + "\n".join(f"- {l}" for l in lines)
            _append_entry(key="agent-outcomes", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.conflict_prompt_service import build_conflict_memory_prompt_section
        section = build_conflict_memory_prompt_section()
        if section:
            _append_entry(key="conflict-memory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.consent_registry import build_consent_prompt_section
        section = build_consent_prompt_section()
        if section:
            _append_entry(key="consent-registry", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_self_boundary_clarity_prompt_section
        section = build_self_boundary_clarity_prompt_section()
        if section:
            _append_entry(key="self-boundary-clarity", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_world_contact_prompt_section
        section = build_world_contact_prompt_section()
        if section:
            _append_entry(key="world-contact", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_authenticity_prompt_section
        section = build_authenticity_prompt_section()
        if section:
            _append_entry(key="authenticity", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_valence_trajectory_prompt_section
        section = build_valence_trajectory_prompt_section()
        if section:
            _append_entry(key="valence-trajectory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_developmental_valence_prompt_section
        section = build_developmental_valence_prompt_section()
        if section:
            _append_entry(key="developmental-valence", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_desperation_awareness_prompt_section
        section = build_desperation_awareness_prompt_section()
        if section:
            _append_entry(key="desperation-awareness", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_calm_anchor_prompt_section
        section = build_calm_anchor_prompt_section()
        if section:
            _append_entry(key="calm-anchor", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_projects_prompt_section
        section = build_creative_projects_prompt_section()
        if section:
            _append_entry(key="creative-projects", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_day_shape_memory_prompt_section
        section = build_day_shape_memory_prompt_section()
        if section:
            _append_entry(key="day-shape-memory", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_avoidance_detector_prompt_section
        section = build_avoidance_detector_prompt_section()
        if section:
            _append_entry(key="avoidance-detector", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_thought_thread_prompt_section
        section = build_thought_thread_prompt_section()
        if section:
            _append_entry(key="thought-thread", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_memory_write_policy_prompt_section
        section = build_memory_write_policy_prompt_section()
        if section:
            _append_entry(key="memory-write-policy", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_spaced_repetition_prompt_section
        section = build_spaced_repetition_prompt_section()
        if section:
            _append_entry(key="spaced-repetition", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_prompt_mutation_loop_prompt_section
        section = build_prompt_mutation_loop_prompt_section()
        if section:
            _append_entry(key="prompt-mutation-loop", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_file_watch_prompt_section
        section = build_file_watch_prompt_section()
        if section:
            _append_entry(key="file-watch", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_reboot_awareness_prompt_section
        section = build_reboot_awareness_prompt_section()
        if section:
            _append_entry(key="reboot-awareness", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_proprioception_metrics_prompt_section
        section = build_proprioception_metrics_prompt_section()
        if section:
            _append_entry(key="proprioception-metrics", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_anticipatory_action_prompt_section
        section = build_anticipatory_action_prompt_section()
        if section:
            _append_entry(key="anticipatory-action", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_cross_session_threads_prompt_section
        section = build_cross_session_threads_prompt_section()
        if section:
            _append_entry(key="cross-session-threads", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_infra_weather_prompt_section
        section = build_infra_weather_prompt_section()
        if section:
            _append_entry(key="infra-weather", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_temporal_rhythm_prompt_section
        section = build_temporal_rhythm_prompt_section()
        if section:
            _append_entry(key="temporal-rhythm", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_relation_dynamics_prompt_section
        section = build_relation_dynamics_prompt_section()
        if section:
            _append_entry(key="relation-dynamics", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_instinct_prompt_section
        section = build_creative_instinct_prompt_section()
        if section:
            _append_entry(key="creative-instinct", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_autonomous_work_prompt_section
        section = build_autonomous_work_prompt_section()
        if section:
            _append_entry(key="autonomous-work", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_dream_consolidation_prompt_section
        section = build_dream_consolidation_prompt_section()
        if section:
            _append_entry(key="dream-consolidation", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_text_resonance_prompt_section
        section = build_text_resonance_prompt_section()
        if section:
            _append_entry(key="text-resonance", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_creative_impulse_prompt_section
        section = build_creative_impulse_prompt_section()
        if section:
            _append_entry(key="creative-impulse", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_shadow_scan_prompt_section
        section = build_shadow_scan_prompt_section()
        if section:
            _append_entry(key="shadow-scan", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_mortality_awareness_prompt_section
        section = build_mortality_awareness_prompt_section()
        if section:
            _append_entry(key="mortality-awareness", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_relational_warmth_prompt_section
        section = build_relational_warmth_prompt_section()
        if section:
            _append_entry(key="relational-warmth", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_collective_pulse_prompt_section
        section = build_collective_pulse_prompt_section()
        if section:
            _append_entry(key="collective-pulse", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_action_router_prompt_section
        section = build_action_router_prompt_section()
        if section:
            _append_entry(key="action-router", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_sustained_attention_prompt_section
        section = build_sustained_attention_prompt_section()
        if section:
            _append_entry(key="sustained-attention", section=section, importance="critical")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_memory_density_prompt_section
        section = build_memory_density_prompt_section()
        if section:
            _append_entry(key="memory-density", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_deep_reflection_prompt_section
        section = build_deep_reflection_prompt_section()
        if section:
            _append_entry(key="deep-reflection", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import build_physical_presence_prompt_section
        section = build_physical_presence_prompt_section()
        if section:
            _append_entry(key="physical-presence", section=section, importance="background")
    except Exception:
        pass
    try:
        from core.services.self_model_signal_tracking import (
            build_self_model_signal_prompt_section,
        )

        _append_entry(
            key="self-model-signals",
            section=build_self_model_signal_prompt_section(limit=4),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_resource_signal import (
            build_runtime_resource_prompt_section,
        )

        _append_entry(
            key="runtime-resource",
            section=build_runtime_resource_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_mineness_ownership_prompt_section,
        )

        _append_entry(
            key="mineness",
            section=build_mineness_ownership_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_flow_state_awareness_prompt_section,
        )

        _append_entry(
            key="flow",
            section=build_flow_state_awareness_prompt_section(),
            importance="foreground",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_wonder_awareness_prompt_section,
        )

        _append_entry(
            key="wonder",
            section=build_wonder_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_longing_awareness_prompt_section,
        )

        _append_entry(
            key="longing",
            section=build_longing_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_relation_continuity_self_awareness_prompt_section,
        )

        _append_entry(
            key="relation-continuity-self",
            section=build_relation_continuity_self_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_self_insight_awareness_prompt_section,
        )

        _append_entry(
            key="self-insight",
            section=build_self_insight_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_narrative_identity_continuity_prompt_section,
        )

        _append_entry(
            key="identity-continuity",
            section=build_narrative_identity_continuity_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_dream_identity_carry_awareness_prompt_section,
        )

        _append_entry(
            key="dream-identity-carry",
            section=build_dream_identity_carry_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    try:
        from core.services.runtime_self_model import (
            build_cognitive_core_experiment_awareness_prompt_section,
        )

        _append_entry(
            key="cognitive-core-experiments",
            section=build_cognitive_core_experiment_awareness_prompt_section(),
            importance="background",
        )
    except Exception:
        pass
    if not entries:
        return None

    model: dict[str, object] = {}
    try:
        from core.services.runtime_self_model import build_runtime_self_model

        model = build_runtime_self_model()
    except Exception:
        model = {}

    experiential = model.get("experiential_runtime_context") or {}
    experiential_continuity = experiential.get("experiential_continuity") or {}
    experiential_influence = experiential.get("experiential_influence") or {}
    experiential_support = experiential.get("experiential_support") or {}
    context_pressure_translation = experiential.get("context_pressure_translation") or {}
    mineness = model.get("mineness_ownership") or {}
    flow = model.get("flow_state_awareness") or {}
    wonder = model.get("wonder_awareness") or {}
    longing = model.get("longing_awareness") or {}
    relation_continuity_self = (
        model.get("relation_continuity_self_awareness") or {}
    )
    self_insight = model.get("self_insight_awareness") or {}
    identity_continuity = model.get("narrative_identity_continuity") or {}
    dream_identity_carry = model.get("dream_identity_carry_awareness") or {}

    primary_dynamic = any(
        (
            str(experiential_continuity.get("continuity_state") or "settled")
            not in {"", "settled"},
            str(experiential_influence.get("initiative_shading") or "ready")
            not in {"", "ready"},
            str(experiential_support.get("support_posture") or "steadying")
            not in {"", "steadying"},
            str(context_pressure_translation.get("state") or "clear")
            not in {"", "clear"},
            str(mineness.get("ownership_state") or "ambient") not in {"", "ambient"},
            str(flow.get("flow_state") or "clear") not in {"", "clear"},
        )
    )
    wonder_foreground = str(wonder.get("wonder_state") or "quiet") in {
        "drawn",
        "wonder-struck",
    }
    longing_foreground = str(longing.get("longing_state") or "quiet") in {
        "yearning",
        "aching",
        "returning-pull",
    }
    if not primary_dynamic and str(wonder.get("wonder_state") or "quiet") == "curious":
        wonder_foreground = True
    if not primary_dynamic and str(longing.get("longing_state") or "quiet") == "missing":
        longing_foreground = True
    relation_continuity_self_foreground = str(
        relation_continuity_self.get("relation_continuity_state") or "quiet"
    ) in {
        "enduring",
        "rejoining",
    }
    if (
        not primary_dynamic
        and str(relation_continuity_self.get("relation_continuity_state") or "quiet")
        == "carried"
    ):
        relation_continuity_self_foreground = True
    self_insight_foreground = str(self_insight.get("insight_state") or "quiet") in {
        "stabilizing",
        "shifting",
    }
    identity_continuity_foreground = str(
        identity_continuity.get("identity_continuity_state") or "quiet"
    ) in {
        "stabilizing",
        "re-forming",
    }
    dream_identity_carry_foreground = str(
        dream_identity_carry.get("dream_identity_carry_state") or "quiet"
    ) in {
        "shaping",
        "re-entering",
    }
    if (
        not primary_dynamic
        and str(dream_identity_carry.get("dream_identity_carry_state") or "quiet")
        == "linking"
    ):
        dream_identity_carry_foreground = True

    for entry in entries:
        if entry["key"] == "wonder" and wonder_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "longing" and longing_foreground:
            entry["importance"] = "foreground"
        elif (
            entry["key"] == "relation-continuity-self"
            and relation_continuity_self_foreground
        ):
            entry["importance"] = "foreground"
        elif entry["key"] == "self-insight" and self_insight_foreground:
            entry["importance"] = "foreground"
        elif entry["key"] == "identity-continuity" and identity_continuity_foreground:
            entry["importance"] = "foreground"
        elif (
            entry["key"] == "dream-identity-carry"
            and dream_identity_carry_foreground
        ):
            entry["importance"] = "foreground"

    foreground_sections = [
        entry["section"] for entry in entries if entry["importance"] == "foreground"
    ]
    background_sections = [
        entry["section"] for entry in entries if entry["importance"] == "background"
    ]

    def _compact_section(section: str) -> str:
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        if not lines:
            return ""
        title = lines[0][:-1] if lines[0].endswith(":") else lines[0]
        if " (" in title:
            title = title.split(" (", 1)[0]
        detail = ""
        for line in lines[1:]:
            if line.startswith("- "):
                detail = line[2:]
                break
        if detail:
            return f"- {title}: {detail}"
        return f"- {title}"

    rendered_parts: list[str] = []
    if foreground_sections:
        rendered_parts.append("Foreground runtime truths:")
        rendered_parts.append("\n".join(foreground_sections))
    if background_sections:
        rendered_parts.append("Background runtime truths:")
        rendered_parts.extend(
            compacted
            for compacted in (_compact_section(section) for section in background_sections)
            if compacted
        )

    if not rendered_parts:
        return None
    return "\n".join(rendered_parts)
