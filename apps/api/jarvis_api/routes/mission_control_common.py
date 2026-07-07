"""Shared foundation for Mission Control routes.

Kode flyttet uændret fra mission_control.py (god-fil-snit, behavior-preserving).
Indeholder import-flade (via mission_control_imports), konstanter, cache-primitiver,
_mc_runtime*-aggregatoren og alle _surface/-tool/-skill/-hardening/-lab hjælpere.
Route-moduler importerer herfra."""
from __future__ import annotations

import sys as _sys

from .mission_control_imports import *  # noqa: F401,F403 (re-eksport af fuld import-flade)

_MC_FACADE_MODULE = "apps.api.jarvis_api.routes.mission_control"


def _mc_facade(name: str):
    """Resolve ``name`` gennem aggregator-modulet ``mission_control`` hvis muligt.

    God-fil-snittet flyttede route/hjælpe-kroppe til undermoduler, men den samlede
    testsuite monkeypatch'er stadig symboler på ``mission_control`` (fx
    ``setattr(mission_control, "_mc_runtime_uncached", fake)``) og forventer at de
    virker. For at bevare den kontrakt slår call-sites for de patch-bare symboler
    op via dette facade: aggregator-modulets binding vinder, ellers falder vi
    tilbage til dette moduls egen binding (ren adfærd før patch).
    """
    module = _sys.modules.get(_MC_FACADE_MODULE)
    if module is not None:
        try:
            return getattr(module, name)
        except AttributeError:
            pass
    return globals()[name]

# ── konstanter + cache-primitiver (flyttet fra mission_control.py 472-770) ──
SUPPORTED_VISIBLE_PROVIDERS = (
    "phase1-runtime",
    "openai",
    "openai-codex",
    "github-copilot",
    "ollama",
)
VISIBLE_RUN_EVENT_KINDS = (
    "runtime.visible_run_started",
    "runtime.visible_run_completed",
    "runtime.visible_run_failed",
    "runtime.visible_run_cancelled",
)
CAPABILITY_INVOCATION_EVENT_KINDS = (
    "runtime.capability_invocation_started",
    "runtime.capability_invocation_completed",
)

_MC_ROUTE_CACHE_LOCK = threading.Lock()
_MC_ROUTE_CACHE: dict[str, tuple[float, object]] = {}
_PROTECTED_VOICE_PRIORITY_WINDOW = timedelta(minutes=15)
_PREFERRED_PROTECTED_VOICE_SOURCES = {"inner-voice-daemon"}
_TEMPLATE_PROTECTED_VOICE_SOURCE = (
    "private-state+private-self-model+private-development-state+"
    "private-reflective-selection"
)
_MC_ROUTE_BUILD_LOCKS: dict[str, threading.Lock] = {}


def _get_cached_mc_payload(cache_key: str, ttl_seconds: float) -> object | None:
    now = time.monotonic()
    with _MC_ROUTE_CACHE_LOCK:
        cached = _MC_ROUTE_CACHE.get(cache_key)
        if not cached or cached[0] <= now:
            return None
        return copy.deepcopy(cached[1])


def _store_cached_mc_payload(
    cache_key: str, ttl_seconds: float, payload: object
) -> object:
    expires_at = time.monotonic() + ttl_seconds
    with _MC_ROUTE_CACHE_LOCK:
        _MC_ROUTE_CACHE[cache_key] = (expires_at, copy.deepcopy(payload))
    return payload


def _get_or_build_cached_mc_payload(
    cache_key: str,
    ttl_seconds: float,
    builder,
) -> object:
    cached = _get_cached_mc_payload(cache_key, ttl_seconds)
    if cached is not None:
        return cached

    with _MC_ROUTE_CACHE_LOCK:
        lock = _MC_ROUTE_BUILD_LOCKS.setdefault(cache_key, threading.Lock())

    with lock:
        cached = _get_cached_mc_payload(cache_key, ttl_seconds)
        if cached is not None:
            return cached
        payload = builder()
        return _store_cached_mc_payload(cache_key, ttl_seconds, payload)


def _build_attention_budget_snapshot_uncached() -> dict[str, object]:
    from core.services.attention_budget import (
        get_attention_budget,
        build_micro_cognitive_frame,
    )

    profiles = {}
    for profile_name in ("visible_compact", "visible_full", "heartbeat"):
        budget = get_attention_budget(profile_name)
        section_budgets = {
            "cognitive_frame": budget.cognitive_frame,
            "private_brain": budget.private_brain,
            "self_knowledge": budget.self_knowledge,
            "self_report": budget.self_report,
            "support_signals": budget.support_signals,
            "inner_visible_bridge": budget.inner_visible_bridge,
            "continuity": budget.continuity,
            "liveness": budget.liveness,
            "capability_truth": budget.capability_truth,
        }
        profiles[profile_name] = {
            "total_char_target": budget.total_char_target,
            "sections": {
                name: {
                    "max_chars": sb.max_chars,
                    "max_items": sb.max_items,
                    "must_include": sb.must_include,
                    "priority": sb.priority,
                    "has_budget": sb.max_chars > 0,
                }
                for name, sb in sorted(
                    section_budgets.items(), key=lambda x: x[1].priority
                )
            },
        }

    micro_frame = build_micro_cognitive_frame()
    return {
        "profiles": profiles,
        "micro_cognitive_frame": micro_frame,
        "micro_frame_chars": len(micro_frame) if micro_frame else 0,
    }


def _mc_runtime_inspection_bundle_uncached() -> dict[str, object]:
    from core.services.runtime_self_model import build_runtime_self_model

    with runtime_surface_cache():
        return {
            "runtime_self_model": build_runtime_self_model(),
            "experiential_runtime_context": build_experiential_runtime_context_surface(),
            "attention_budget": _build_attention_budget_snapshot_uncached(),
        }


def _mc_runtime_inspection_bundle() -> dict[str, object]:
    payload = _get_or_build_cached_mc_payload(
        "runtime-inspection-bundle",
        10.0,
        _mc_facade("_mc_runtime_inspection_bundle_uncached"),
    )
    return payload  # type: ignore[return-value]


def _mc_runtime() -> dict:
    """Cached ``/mc/runtime`` payload (facade delt af mc_runtime-ruten samt af
    cross-modul-kaldere som mc_jarvis/mc_operations der før kaldte mc_runtime()
    direkte i samme fil)."""
    payload = _get_or_build_cached_mc_payload(
        "runtime",
        3.0,
        _mc_facade("_mc_runtime_uncached"),
    )
    return payload  # type: ignore[return-value]


def _mc_runtime_uncached() -> dict:
    with runtime_surface_cache():
        settings = _mc_facade("load_settings")()
        heartbeat = heartbeat_runtime_surface()
        from core.services.cognitive_architecture_surface import (
            build_cognitive_architecture_surface,
        )

        cognitive_architecture = build_cognitive_architecture_surface()
        payload = {
            "settings": _redact_mc_secrets(settings.to_dict()),
            "heartbeat_runtime": heartbeat,
            "cognitive_architecture": cognitive_architecture,
            "runtime_embodied_state": _mc_facade("build_embodied_state_surface")(),
            "runtime_affective_meta_state": _mc_facade("build_affective_meta_state_surface")(),
            "runtime_epistemic_state": _mc_facade("build_epistemic_runtime_state_surface")(),
            "runtime_subagent_ecology": _mc_facade("build_subagent_ecology_surface")(),
            "runtime_council_runtime": _mc_facade("build_council_runtime_surface")(),
            "runtime_adaptive_planner": _mc_facade("build_adaptive_planner_runtime_surface")(),
            "runtime_adaptive_reasoning": _mc_facade("build_adaptive_reasoning_runtime_surface")(),
            "runtime_guided_learning": _mc_facade("build_guided_learning_runtime_surface")(),
            "runtime_adaptive_learning": _mc_facade("build_adaptive_learning_runtime_surface")(),
            "runtime_self_system_code_awareness": _mc_facade("build_self_system_code_awareness_surface")(),
            "runtime_tool_intent": _mc_facade("build_tool_intent_runtime_surface")(),
            "runtime_loop_state": _mc_facade("build_loop_runtime_surface")(),
            "runtime_idle_consolidation": _mc_facade("build_idle_consolidation_surface")(),
            "runtime_dream_articulation": _mc_facade("build_dream_articulation_surface")(),
            "runtime_dream_influence": _mc_facade("build_dream_influence_runtime_surface")(),
            "runtime_prompt_evolution": _mc_facade("build_prompt_evolution_runtime_surface")(),
            "runtime_self_critique": _mc_facade("build_self_critique_surface")(),
            "runtime_creative_journal": _mc_facade("build_creative_journal_surface")(),
            "runtime_finitude": _mc_facade("build_finitude_surface")(),
            "runtime_modulator_witness": build_modulator_witness_surface(),
            "runtime_dream_distillation": _mc_facade("build_dream_distillation_surface")(),
            "runtime_unconscious_temperature_field": _mc_facade("build_unconscious_temperature_field_surface")(),
            "visible_execution": visible_execution_readiness(),
            "visible_identity": load_visible_identity_summary(),
            "visible_session_continuity": visible_session_continuity_summary(),
            "visible_continuity": visible_continuity_summary(),
            "visible_capability_continuity": visible_capability_continuity_summary(),
            "visible_work": _visible_work_surface(),
            "visible_work_surface": get_visible_work_surface(),
            "visible_selected_work_surface": get_visible_selected_work_surface(),
            "visible_selected_work_item": get_visible_selected_work_item(),
            "visible_selected_work_note": get_visible_selected_work_note(),
            "visible_run": _visible_run_surface(),
            "workspace_capabilities": load_workspace_capabilities(),
            "provider_router": provider_router_summary(),
            "cheap_lane_execution": cheap_lane_execution_truth(),
            "coding_lane_execution": coding_lane_execution_truth(),
            "local_lane_execution": local_lane_execution_truth(),
            "capability_invocation": _capability_invocation_surface(),
            "private_inner_note": _private_inner_note_surface(),
            "private_growth_note": _private_growth_note_surface(),
            "private_self_model": _private_self_model_surface(),
            "private_reflective_selection": _private_reflective_selection_surface(),
            "private_development_state": _private_development_state_surface(),
            "private_state": _private_state_surface(),
            "protected_inner_voice": _protected_inner_voice_surface(),
            "private_inner_interplay": _private_inner_interplay_surface(),
            "private_initiative_tension": _private_initiative_tension_surface(),
            "private_operational_preference": _private_operational_preference_surface(),
            "operational_preference_alignment": _operational_preference_alignment_surface(),
            "private_relation_state": _private_relation_state_surface(),
            "private_temporal_curiosity_state": _private_temporal_curiosity_state_surface(),
            "private_temporal_promotion_signal": _private_temporal_promotion_signal_surface(),
            "private_promotion_decision": _private_promotion_decision_surface(),
            "private_retained_memory_record": _private_retained_memory_record_surface(),
            "private_retained_memory_projection": _private_retained_memory_projection_surface(),
            "runtime_development_focuses": build_runtime_development_focus_surface(),
            "runtime_reflective_critics": build_runtime_reflective_critic_surface(),
            "runtime_self_model_signals": build_runtime_self_model_signal_surface(),
            "runtime_goal_signals": build_runtime_goal_signal_surface(),
            "runtime_reflection_signals": build_runtime_reflection_signal_surface(),
            "runtime_temporal_recurrence_signals": build_runtime_temporal_recurrence_signal_surface(),
            "runtime_witness_signals": build_runtime_witness_signal_surface(),
            "runtime_open_loop_signals": build_runtime_open_loop_signal_surface(),
            "runtime_open_loop_closure_proposals": build_runtime_open_loop_closure_proposal_surface(),
            "runtime_internal_opposition_signals": build_runtime_internal_opposition_signal_surface(),
            "runtime_self_review_signals": build_runtime_self_review_signal_surface(),
            "runtime_self_review_records": build_runtime_self_review_record_surface(),
            "runtime_self_review_runs": build_runtime_self_review_run_surface(),
            "runtime_self_review_outcomes": build_runtime_self_review_outcome_surface(),
            "runtime_self_review_cadence_signals": build_runtime_self_review_cadence_signal_surface(),
            "runtime_dream_hypothesis_signals": build_runtime_dream_hypothesis_signal_surface(),
            "runtime_dream_adoption_candidates": build_runtime_dream_adoption_candidate_surface(),
            "runtime_dream_influence_proposals": build_runtime_dream_influence_proposal_surface(),
            "runtime_self_authored_prompt_proposals": build_runtime_self_authored_prompt_proposal_surface(),
            "runtime_user_understanding_signals": build_runtime_user_understanding_signal_surface(),
            "runtime_remembered_fact_signals": build_runtime_remembered_fact_signal_surface(),
            "runtime_private_inner_note_signals": build_runtime_private_inner_note_signal_surface(),
            "runtime_private_initiative_tension_signals": build_runtime_private_initiative_tension_signal_surface(),
            "life_projects": _mc_facade("build_life_projects_surface")(),
            "runtime_private_inner_interplay_signals": build_runtime_private_inner_interplay_signal_surface(),
            "runtime_private_state_snapshots": build_runtime_private_state_snapshot_surface(),
            "runtime_diary_synthesis_signals": build_diary_synthesis_signal_surface(),
            "runtime_private_temporal_curiosity_states": build_runtime_private_temporal_curiosity_state_surface(),
            "runtime_inner_visible_support_signals": build_runtime_inner_visible_support_signal_surface(),
            "runtime_regulation_homeostasis_signals": build_runtime_regulation_homeostasis_signal_surface(),
            "runtime_relation_state_signals": build_runtime_relation_state_signal_surface(),
            "runtime_relation_continuity_signals": build_runtime_relation_continuity_signal_surface(),
            "runtime_meaning_significance_signals": build_runtime_meaning_significance_signal_surface(),
            "runtime_temperament_tendency_signals": build_runtime_temperament_tendency_signal_surface(),
            "runtime_self_narrative_continuity_signals": build_runtime_self_narrative_continuity_signal_surface(),
            "runtime_metabolism_state_signals": build_runtime_metabolism_state_signal_surface(),
            "runtime_release_marker_signals": build_runtime_release_marker_signal_surface(),
            "runtime_consolidation_target_signals": build_runtime_consolidation_target_signal_surface(),
            "runtime_selective_forgetting_candidates": build_runtime_selective_forgetting_candidate_surface(),
            "runtime_attachment_topology_signals": build_runtime_attachment_topology_signal_surface(),
            "runtime_loyalty_gradient_signals": build_runtime_loyalty_gradient_signal_surface(),
            "runtime_autonomy_pressure_signals": build_runtime_autonomy_pressure_signal_surface(),
            "runtime_proactive_loop_lifecycle_signals": build_runtime_proactive_loop_lifecycle_surface(),
            "runtime_proactive_question_gates": build_runtime_proactive_question_gate_surface(),
            "runtime_webchat_execution_pilot": build_runtime_webchat_execution_pilot_surface(),
            "runtime_self_narrative_self_model_review_bridge": build_runtime_self_narrative_self_model_review_bridge_surface(),
            "runtime_executive_contradiction_signals": build_runtime_executive_contradiction_signal_surface(),
            "runtime_private_temporal_promotion_signals": build_runtime_private_temporal_promotion_signal_surface(),
            "runtime_chronicle_consolidation_signals": build_runtime_chronicle_consolidation_signal_surface(),
            "runtime_chronicle_consolidation_briefs": build_runtime_chronicle_consolidation_brief_surface(),
            "runtime_chronicle_consolidation_proposals": build_runtime_chronicle_consolidation_proposal_surface(),
            "runtime_user_md_update_proposals": build_runtime_user_md_update_proposal_surface(),
            "runtime_memory_md_update_proposals": build_runtime_memory_md_update_proposal_surface(),
            "runtime_selfhood_proposals": build_runtime_selfhood_proposal_surface(),
            "runtime_world_model_signals": build_runtime_world_model_signal_surface(),
            "runtime_awareness_signals": build_runtime_awareness_signal_surface(),
            "runtime_emergent_signals": build_runtime_emergent_signal_surface(),
            "runtime_relevance_decisions": build_runtime_relevance_decision_surface(),
            "runtime_memory_selections": build_runtime_memory_selection_surface(),
            "runtime_inner_visible_prompt_bridges": build_runtime_inner_visible_prompt_bridge_surface(),
            "life_services": {
                "continuity_kernel": build_continuity_kernel_surface(),
                "dream_continuum": build_dream_continuum_surface(),
                "emergent_bridge": build_emergent_bridge_surface(),
                "initiative_accumulator": build_initiative_accumulator_surface(),
                "signal_network_visualizer": build_signal_network_visualizer_surface(),
                "temporal_narrative": build_temporal_narrative_surface(),
                "boredom_curiosity_bridge": build_boredom_curiosity_bridge_surface(),
                # GAP services
                "mirror": build_mirror_surface(),
                "paradox_tracker": build_paradox_surface(),
                "experiential_memory": build_experiential_memory_surface(),
                "seeds": build_seed_surface(),
                # Experimental services
                "mood_oscillator": build_mood_oscillator_surface(),
                "existential_drift": build_existential_drift_surface(),
                "body_memory": build_body_memory_surface(),
                "ghost_networks": build_ghost_networks_surface(),
                "parallel_selves": build_parallel_selves_surface(),
                "temporal_body": build_temporal_body_surface(),
                "silence_listener": build_silence_listener_surface(),
                "decision_ghosts": build_decision_ghosts_surface(),
                "attention_contour": build_attention_contour_surface(),
                "memory_tattoos": build_memory_tattoos_surface(),
            },
            "runtime_work": _runtime_work_surface(),
            "paths": {
                "config_dir": _path_state(CONFIG_DIR),
                "settings_file": _path_state(SETTINGS_FILE),
                "provider_router_file": _path_state(PROVIDER_ROUTER_FILE),
                "state_dir": _path_state(STATE_DIR),
                "log_dir": _path_state(LOG_DIR),
                "cache_dir": _path_state(CACHE_DIR),
                "auth_dir": _path_state(AUTH_DIR),
                "workspaces_dir": _path_state(WORKSPACES_DIR),
            },
        }
    return payload


# ── surface-hjælpere (flyttet fra mission_control.py 2634-3519) ──
def _latest_item(items: list[dict]) -> dict | None:
    return items[0] if items else None


def _with_private_lane_source_discipline(item: dict | None) -> dict | None:
    if not item:
        return item
    source = str(item.get("source") or "")
    grounded = "private-runtime-grounded" in source
    return {
        **item,
        "private_lane_source_state": (
            "private-runtime-grounded" if grounded else "legacy-source-unknown"
        ),
        "contamination_state": (
            "decontaminated-from-visible-reply"
            if grounded
            else "legacy-contamination-unknown"
        ),
    }


def _private_lane_surface_summary(item: dict | None) -> dict[str, str]:
    normalized = _with_private_lane_source_discipline(item)
    return {
        "current_source_state": str(
            (normalized or {}).get("private_lane_source_state")
            or "legacy-source-unknown"
        ),
        "current_contamination_state": str(
            (normalized or {}).get("contamination_state")
            or "legacy-contamination-unknown"
        ),
    }


def _path_state(path) -> dict[str, str | bool]:
    return {
        "path": str(path),
        "exists": path.exists(),
    }


_MC_SECRET_KEY_MARKERS = (
    "api_key",
    "secret",
    "password",
    "credential",
    "authorization",
    "bearer",
    "cookie",
    "oauth",
)

_MC_SECRET_EXACT_KEYS = {
    "app_id",
    "claim_code",
    "key",
    "token",
}


def _mc_key_is_secret(key: object) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    if not normalized:
        return False
    if any(marker in normalized for marker in _MC_SECRET_KEY_MARKERS):
        return True
    if normalized in _MC_SECRET_EXACT_KEYS:
        return True
    return normalized.endswith("_token") or normalized.endswith("_key")


def _redact_mc_secrets(value):
    """Return an MC-safe copy with configured secrets masked, not exposed."""
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if _mc_key_is_secret(key):
                redacted[key] = "***REDACTED***" if item not in (None, "") else item
            else:
                redacted[key] = _redact_mc_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_mc_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_mc_secrets(item) for item in value)
    return value


def _visible_execution_surface(settings) -> dict:
    return {
        "authority": {
            "visible_model_provider": settings.visible_model_provider,
            "visible_model_name": settings.visible_model_name,
            "visible_auth_profile": settings.visible_auth_profile,
        },
        "readiness": visible_execution_readiness(),
        "visible_identity": load_visible_identity_summary(),
        "visible_session_continuity": visible_session_continuity_summary(),
        "visible_continuity": visible_continuity_summary(),
        "visible_capability_continuity": visible_capability_continuity_summary(),
        "visible_work": _visible_work_surface(),
        "visible_work_surface": get_visible_work_surface(),
        "visible_selected_work_surface": get_visible_selected_work_surface(),
        "visible_selected_work_item": get_visible_selected_work_item(),
        "visible_selected_work_note": get_visible_selected_work_note(),
        "workspace_capabilities": load_workspace_capabilities(),
        "provider_router": provider_router_summary(),
        "cheap_lane_execution": cheap_lane_execution_truth(),
        "coding_lane_execution": coding_lane_execution_truth(),
        "local_lane_execution": local_lane_execution_truth(),
        "capability_invocation": _capability_invocation_surface(),
        "private_inner_note": _private_inner_note_surface(),
        "private_growth_note": _private_growth_note_surface(),
        "private_self_model": _private_self_model_surface(),
        "private_reflective_selection": _private_reflective_selection_surface(),
        "private_development_state": _private_development_state_surface(),
        "private_state": _private_state_surface(),
        "protected_inner_voice": _protected_inner_voice_surface(),
        "private_inner_interplay": _private_inner_interplay_surface(),
        "private_initiative_tension": _private_initiative_tension_surface(),
        "private_operational_preference": _private_operational_preference_surface(),
        "operational_preference_alignment": _operational_preference_alignment_surface(),
        "private_relation_state": _private_relation_state_surface(),
        "private_temporal_curiosity_state": _private_temporal_curiosity_state_surface(),
        "private_temporal_promotion_signal": _private_temporal_promotion_signal_surface(),
        "private_promotion_decision": _private_promotion_decision_surface(),
        "private_retained_memory_record": _private_retained_memory_record_surface(),
        "private_retained_memory_projection": _private_retained_memory_projection_surface(),
        "supported_providers": list(SUPPORTED_VISIBLE_PROVIDERS),
        "available_auth_profiles": _available_openai_profiles(),
        "visible_run": _visible_run_surface(),
    }


def _main_agent_selection_surface() -> dict:
    provider_router = provider_router_summary()
    return {
        "selection": provider_router.get("main_agent_selection"),
        "target": provider_router.get("main_agent_target"),
        "provider_router": provider_router,
        "readiness": visible_execution_readiness(),
        "ollama_models": available_ollama_models_for_visible_target(),
    }


def _maybe_configure_live_main_agent_target(
    *, provider: str, model: str, auth_profile: str
) -> bool:
    if not provider or not model:
        return False

    models_surface = _mc_facade("available_provider_models")(
        provider=provider,
        auth_profile=auth_profile,
    )
    available = {
        str(item.get("id") or "").strip()
        for item in models_surface.get("models", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if model not in available:
        return False

    configured_profile = str(auth_profile or models_surface.get("auth_profile") or "").strip()
    if provider == "ollama":
        local_target = resolve_provider_router_target(lane="local")
        configure_provider_router_entry(
            provider="ollama",
            model=model,
            auth_mode="none",
            auth_profile="",
            base_url=str(
                models_surface.get("base_url")
                or local_target.get("base_url")
                or "http://127.0.0.1:11434"
            ),
            api_key="",
            lane="local",
            set_visible=False,
        )
        return True

    if provider == "github-copilot":
        configure_provider_router_entry(
            provider="github-copilot",
            model=model,
            auth_mode="oauth",
            auth_profile=configured_profile or "copilot",
            base_url="",
            api_key="",
            lane="visible",
            set_visible=False,
        )
        return True

    return False


def _available_openai_profiles() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for profile in list_auth_profiles():
        name = str(profile.get("profile", "")).strip()
        if not name:
            continue
        state = get_provider_state(profile=name, provider="openai")
        items.append(
            {
                "profile": name,
                "auth_status": str(state.get("status", "missing"))
                if state
                else "missing",
            }
        )
    return items


def _visible_run_surface() -> dict:
    active = get_active_visible_run()
    last_outcome = get_last_visible_run_outcome()
    return {
        "active": bool(active),
        "active_run": active,
        "last_outcome": last_outcome,
        "last_capability_use": get_last_visible_capability_use(),
        "last_execution_trace": get_last_visible_execution_trace(),
        "persisted_recent_runs": recent_visible_runs(limit=5),
        "recent_events": _recent_visible_run_events(),
    }


def _visible_work_surface() -> dict:
    return {
        **get_visible_work(),
        "persisted_recent_units": recent_visible_work_units(limit=5),
        "persisted_recent_notes": recent_visible_work_notes(limit=5),
    }


def _capability_invocation_surface() -> dict:
    truth = get_capability_invocation_truth()
    return {
        **truth,
        "persisted_recent_invocations": recent_capability_invocations(limit=5),
        "recent_approval_requests": recent_capability_approval_requests(limit=5),
        "recent_events": _recent_capability_invocation_events(),
    }


def _private_inner_note_surface() -> dict:
    notes = recent_private_inner_notes(limit=5)
    return {
        "active": bool(notes),
        "recent_notes": notes,
    }


def _private_growth_note_surface() -> dict:
    notes = recent_private_growth_notes(limit=5)
    normalized_notes = [
        item
        for item in (_with_private_lane_source_discipline(note) for note in notes)
        if item
    ]
    return {
        "active": bool(normalized_notes),
        "recent_notes": normalized_notes,
        "summary": _private_lane_surface_summary(_latest_item(normalized_notes)),
    }


def _private_self_model_surface() -> dict:
    model = get_private_self_model()
    return {
        "active": bool(model),
        "current": model,
    }


def _private_reflective_selection_surface() -> dict:
    signals = recent_private_reflective_selections(limit=5)
    normalized_signals = [
        item
        for item in (_with_private_lane_source_discipline(signal) for signal in signals)
        if item
    ]
    return {
        "active": bool(normalized_signals),
        "recent_signals": normalized_signals,
        "summary": _private_lane_surface_summary(_latest_item(normalized_signals)),
    }


def _private_development_state_surface() -> dict:
    state = get_private_development_state()
    return {
        "active": bool(state),
        "current": state,
    }


def _private_state_surface() -> dict:
    state = get_private_state()
    return {
        "active": bool(state),
        "current": state,
    }


def _protected_inner_voice_surface() -> dict:
    voice = _current_protected_inner_voice()
    return {
        "active": bool(voice),
        "current": voice,
    }


def _current_protected_inner_voice() -> dict[str, object] | None:
    return _select_current_protected_inner_voice(
        list_recent_protected_inner_voices(limit=8)
    )


def _select_current_protected_inner_voice(
    voices: list[dict[str, object]],
) -> dict[str, object] | None:
    if not voices:
        return None
    latest = dict(voices[0])
    latest_created_at = _parse_runtime_iso_datetime(latest.get("created_at"))
    freshness_floor = (
        latest_created_at - _PROTECTED_VOICE_PRIORITY_WINDOW
        if latest_created_at is not None
        else None
    )
    best = latest
    best_score = _protected_inner_voice_priority(
        best,
        freshness_floor=freshness_floor,
    )
    for voice in voices[1:]:
        candidate = dict(voice)
        candidate_score = _protected_inner_voice_priority(
            candidate,
            freshness_floor=freshness_floor,
        )
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score
    return best


def _protected_inner_voice_priority(
    voice: dict[str, object],
    *,
    freshness_floor: datetime | None,
) -> tuple[int, int, int, str, int]:
    created_at = _parse_runtime_iso_datetime(voice.get("created_at"))
    is_fresh = (
        freshness_floor is None or created_at is None or created_at >= freshness_floor
    )
    source = str(voice.get("source") or "").strip()
    preferred = int(is_fresh and source in _PREFERRED_PROTECTED_VOICE_SOURCES)
    enriched = int(is_fresh and bool(voice.get("enriched")))
    freshness = int(is_fresh)
    generic_penalty = int(source == _TEMPLATE_PROTECTED_VOICE_SOURCE)
    created_sort = created_at.isoformat() if created_at is not None else ""
    identifier = int(voice.get("id") or 0)
    return (
        preferred,
        enriched,
        freshness,
        -generic_penalty,
        created_sort,
        identifier,
    )


def _parse_runtime_iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _private_inner_interplay_surface() -> dict:
    return _mc_facade("build_private_inner_interplay")(
        private_state=get_private_state(),
        protected_inner_voice=_current_protected_inner_voice(),
        private_development_state=get_private_development_state(),
        private_reflective_selection=_latest_item(
            recent_private_reflective_selections(limit=1)
        ),
    )


def _private_initiative_tension_surface() -> dict:
    return _mc_facade("build_private_initiative_tension")(
        private_state=get_private_state(),
        protected_inner_voice=_current_protected_inner_voice(),
        private_development_state=get_private_development_state(),
        private_reflective_selection=_latest_item(
            recent_private_reflective_selections(limit=1)
        ),
        private_temporal_promotion_signal=get_private_temporal_promotion_signal(),
        private_temporal_curiosity_state=_private_temporal_curiosity_state_surface().get(
            "current"
        ),
        private_retained_memory_projection=_private_retained_memory_projection_surface().get(
            "current"
        ),
    )


def _private_relation_state_surface() -> dict:
    return build_private_relation_state(
        visible_session_continuity=visible_session_continuity_summary(),
        visible_continuity=visible_continuity_summary(),
        visible_selected_work_item=get_visible_selected_work_item(),
        private_retained_memory_projection=_private_retained_memory_projection_surface().get(
            "current"
        ),
    )


def _private_operational_preference_surface() -> dict:
    return build_private_operational_preference(
        private_initiative_tension=_private_initiative_tension_surface().get("current"),
        private_temporal_curiosity_state=_private_temporal_curiosity_state_surface().get(
            "current"
        ),
        private_relation_state=_private_relation_state_surface().get("current"),
    )


def _operational_preference_alignment_surface() -> dict:
    provider_router = provider_router_summary()
    return build_operational_preference_alignment(
        private_operational_preference=_private_operational_preference_surface().get(
            "current"
        ),
        lane_targets=provider_router.get("lane_targets"),
    )


def _private_temporal_curiosity_state_surface() -> dict:
    return build_private_temporal_curiosity_state(
        private_state=get_private_state(),
        private_temporal_promotion_signal=get_private_temporal_promotion_signal(),
        private_development_state=get_private_development_state(),
    )


def _private_temporal_promotion_signal_surface() -> dict:
    signal = _with_private_lane_source_discipline(
        get_private_temporal_promotion_signal()
    )
    return {
        "active": bool(signal),
        "current": signal,
        "summary": _private_lane_surface_summary(signal),
    }


def _private_promotion_decision_surface() -> dict:
    decision = _with_private_lane_source_discipline(get_private_promotion_decision())
    return {
        "active": bool(decision),
        "current": decision,
        "summary": _private_lane_surface_summary(decision),
    }


def _private_retained_memory_record_surface() -> dict:
    record = _with_private_lane_source_discipline(get_private_retained_memory_record())
    recent_records = [
        item
        for item in (
            _with_private_lane_source_discipline(candidate)
            for candidate in recent_private_retained_memory_records(limit=5)
        )
        if item
    ]
    return {
        "active": bool(record),
        "current": record,
        "recent_records": recent_records,
        "summary": _private_lane_surface_summary(record),
    }


def _private_retained_memory_projection_surface() -> dict:
    record = _with_private_lane_source_discipline(get_private_retained_memory_record())
    recent_records = [
        item
        for item in (
            _with_private_lane_source_discipline(candidate)
            for candidate in recent_private_retained_memory_records(limit=5)
        )
        if item
    ]
    projection = build_private_retained_memory_projection(
        current_record=record,
        recent_records=recent_records,
    )
    normalized_projection = _with_private_lane_source_discipline(projection)
    if normalized_projection is None:
        return projection
    return {
        **normalized_projection,
        "current": _with_private_lane_source_discipline(
            normalized_projection.get("current")
            if isinstance(normalized_projection.get("current"), dict)
            else None
        ),
    }


def _recent_visible_run_events(limit: int = 5, scan_limit: int = 40) -> list[dict]:
    items = event_bus.recent(limit=max(scan_limit, limit))
    visible_items = [item for item in items if item["kind"] in VISIBLE_RUN_EVENT_KINDS]
    return visible_items[:limit]


def _recent_capability_invocation_events(
    limit: int = 5, scan_limit: int = 40
) -> list[dict]:
    items = event_bus.recent(limit=max(scan_limit, limit))
    capability_items = [
        item for item in items if item["kind"] in CAPABILITY_INVOCATION_EVENT_KINDS
    ]
    return capability_items[:limit]


def _jarvis_identity_summary(visible_identity: dict) -> dict[str, object]:
    files = list(visible_identity.get("source_files") or [])
    return {
        "active": bool(visible_identity.get("active")),
        "workspace": str(visible_identity.get("workspace") or ""),
        "source_files": files,
        "fingerprint": str(visible_identity.get("fingerprint") or ""),
        "line_count": int(visible_identity.get("extracted_line_count") or 0),
    }


def _jarvis_state_signal(
    protected_voice: dict, initiative_tension: dict, private_state: dict
) -> dict[str, str]:
    voice = protected_voice.get("current") or {}
    tension = initiative_tension.get("current") or {}
    state = private_state.get("current") or {}
    return {
        "mood_tone": str(voice.get("mood_tone") or "unknown"),
        "current_concern": _preview_text(
            str(voice.get("current_concern") or tension.get("reason") or "unknown"),
            limit=96,
        ),
        "current_pull": _preview_text(
            str(
                voice.get("current_pull") or tension.get("tension_target") or "unknown"
            ),
            limit=120,
        ),
        "confidence": str(
            state.get("confidence") or tension.get("confidence") or "unknown"
        ),
    }


def _jarvis_retained_summary(
    retained_projection: dict, retained_record: dict
) -> dict[str, str]:
    projection = retained_projection.get("current") or retained_projection or {}
    record = retained_record.get("current") or {}
    return {
        "focus": _preview_text(
            str(
                retained_projection.get("retained_focus")
                or projection.get("retained_value")
                or record.get("retained_value")
                or "none"
            ),
            limit=120,
        ),
        "kind": str(
            retained_projection.get("retained_kind")
            or projection.get("retained_kind")
            or record.get("retained_kind")
            or "unknown"
        ),
        "scope": str(
            retained_projection.get("retention_scope")
            or projection.get("retention_scope")
            or record.get("retention_scope")
            or "unknown"
        ),
        "confidence": str(
            retained_projection.get("confidence")
            or projection.get("confidence")
            or record.get("confidence")
            or "unknown"
        ),
    }


def _jarvis_development_summary(
    self_model: dict,
    development_state: dict,
    development_focuses: dict | None = None,
    reflective_critics: dict | None = None,
    self_model_signals: dict | None = None,
    goal_signals: dict | None = None,
    reflection_signals: dict | None = None,
) -> dict[str, str]:
    model = self_model.get("current") or {}
    state = development_state.get("current") or {}
    focus_summary = (development_focuses or {}).get("summary") or {}
    critic_summary = (reflective_critics or {}).get("summary") or {}
    self_signal_summary = (self_model_signals or {}).get("summary") or {}
    goal_summary = (goal_signals or {}).get("summary") or {}
    reflection_summary = (reflection_signals or {}).get("summary") or {}
    return {
        "direction": str(
            model.get("growth_direction")
            or state.get("preferred_direction")
            or "unknown"
        ),
        "identity_focus": str(
            model.get("identity_focus") or state.get("identity_thread") or "unknown"
        ),
        "work_mode": str(model.get("preferred_work_mode") or "unknown"),
        "tension": str(
            state.get("recurring_tension")
            or model.get("recurring_tension")
            or "unknown"
        ),
        "focus_count": str(focus_summary.get("active_count") or 0),
        "current_focus": str(
            focus_summary.get("current_focus") or "No active development focus"
        ),
        "critic_count": str(critic_summary.get("active_count") or 0),
        "current_critic": str(
            critic_summary.get("current_critic") or "No active critic signal"
        ),
        "self_model_signal_count": str(self_signal_summary.get("active_count") or 0),
        "current_self_model_signal": str(
            self_signal_summary.get("current_signal") or "No active self-model signal"
        ),
        "goal_count": str(
            (goal_summary.get("active_count") or 0)
            + (goal_summary.get("blocked_count") or 0)
        ),
        "current_goal": str(
            goal_summary.get("current_goal") or "No active goal signal"
        ),
        "reflection_signal_count": str(
            (reflection_summary.get("active_count") or 0)
            + (reflection_summary.get("integrating_count") or 0)
            + (reflection_summary.get("settled_count") or 0)
        ),
        "current_reflection_signal": str(
            reflection_summary.get("current_signal") or "No active reflection signal"
        ),
    }


def _jarvis_continuity_summary(
    relation_state: dict,
    visible_session: dict,
    promotion_signal: dict,
    world_model_signals: dict | None = None,
    runtime_awareness_signals: dict | None = None,
    runtime_work: dict | None = None,
) -> dict[str, str]:
    relation = relation_state.get("current") or {}
    signal = promotion_signal.get("current") or {}
    world_summary = (world_model_signals or {}).get("summary") or {}
    runtime_awareness_summary = (runtime_awareness_signals or {}).get("summary") or {}
    runtime_work_summary = (runtime_work or {}).get("summary") or {}
    return {
        "continuity_mode": str(
            relation.get("continuity_mode")
            or visible_session.get("latest_status")
            or "unknown"
        ),
        "interaction_mode": str(relation.get("interaction_mode") or "unknown"),
        "relation_pull": _preview_text(
            str(
                relation.get("relation_pull")
                or signal.get("promotion_target")
                or "unknown"
            ),
            limit=96,
        ),
        "session_status": str(visible_session.get("latest_status") or "unknown"),
        "world_model_count": str(world_summary.get("active_count") or 0),
        "current_world_model": str(
            world_summary.get("current_signal") or "No active world-model signal"
        ),
        "runtime_awareness_count": str(
            (runtime_awareness_summary.get("active_count") or 0)
            + (runtime_awareness_summary.get("constrained_count") or 0)
            + (runtime_awareness_summary.get("recovered_count") or 0)
        ),
        "current_runtime_awareness": str(
            runtime_awareness_summary.get("current_signal")
            or "No active runtime-awareness signal"
        ),
        "runtime_work_count": str(
            (runtime_work_summary.get("task_count") or 0)
            + (runtime_work_summary.get("flow_count") or 0)
        ),
        "current_runtime_work": str(
            runtime_work_summary.get("current_focus") or "No active runtime work"
        ),
    }


def _jarvis_heartbeat_summary(heartbeat: dict) -> dict[str, str]:
    state = heartbeat.get("state") or {}
    embodied = heartbeat.get("embodied_state") or {}
    idle_consolidation = heartbeat.get("idle_consolidation") or {}
    idle_summary = idle_consolidation.get("summary") or {}
    idle_last_result = idle_consolidation.get("last_result") or {}
    dream_articulation = heartbeat.get("dream_articulation") or {}
    dream_summary = dream_articulation.get("summary") or {}
    dream_last_result = dream_articulation.get("last_result") or {}
    return {
        "enabled": "enabled" if state.get("enabled") else "disabled",
        "status": str(
            state.get("schedule_state") or state.get("schedule_status") or "unknown"
        ),
        "decision": str(state.get("last_decision_type") or "none"),
        "result": _preview_text(
            str(
                state.get("last_result")
                or state.get("summary")
                or "No heartbeat result yet."
            ),
            limit=120,
        ),
        "next_tick_at": str(state.get("next_tick_at") or ""),
        "trigger": str(state.get("last_trigger_source") or "none"),
        "embodied_state": str(embodied.get("state") or "unknown"),
        "idle_consolidation": str(
            idle_summary.get("last_state")
            or idle_last_result.get("consolidation_state")
            or "idle"
        ),
        "idle_consolidation_reason": str(
            idle_last_result.get("reason")
            or idle_summary.get("last_reason")
            or "no-run-yet"
        ),
        "dream_articulation": str(
            dream_summary.get("last_state")
            or dream_last_result.get("candidate_state")
            or "idle"
        ),
        "dream_articulation_reason": str(
            dream_last_result.get("reason")
            or dream_summary.get("last_reason")
            or "no-run-yet"
        ),
    }


def _runtime_work_surface() -> dict[str, object]:
    queued_tasks = list_tasks(status="queued", limit=8)
    running_tasks = list_tasks(status="running", limit=8)
    blocked_tasks = list_tasks(status="blocked", limit=8)
    queued_flows = list_flows(status="queued", limit=8)
    running_flows = list_flows(status="running", limit=8)
    blocked_flows = list_flows(status="blocked", limit=8)
    browser_body = next(iter(list_browser_bodies(limit=2)), {})
    memory_paths = workspace_memory_paths()
    curated_exists = memory_paths["curated_memory"].exists()
    # Accept any daily file written within the last 7 days
    _today = datetime.now(UTC).date()
    _daily_dir = memory_paths["daily_dir"]
    daily_exists = any(
        (_daily_dir / f"{(_today - timedelta(days=d)).isoformat()}.md").exists()
        for d in range(8)
    )
    current_focus = (
        str(
            (running_tasks or queued_tasks or blocked_tasks or [{}])[0].get("goal")
            or ""
        ).strip()
        or str(
            (running_flows or queued_flows or blocked_flows or [{}])[0].get(
                "current_step"
            )
            or ""
        ).strip()
        or "No active runtime work"
    )
    return {
        "active": bool(
            queued_tasks
            or running_tasks
            or blocked_tasks
            or queued_flows
            or running_flows
            or blocked_flows
        ),
        "tasks": {
            "queued": queued_tasks,
            "running": running_tasks,
            "blocked": blocked_tasks,
        },
        "flows": {
            "queued": queued_flows,
            "running": running_flows,
            "blocked": blocked_flows,
        },
        "browser_body": browser_body,
        "layered_memory": {
            "daily_memory_path": str(memory_paths["daily_memory"]),
            "daily_memory_exists": daily_exists,
            "curated_memory_path": str(memory_paths["curated_memory"]),
            "curated_memory_exists": curated_exists,
        },
        "summary": {
            "task_count": len(queued_tasks) + len(running_tasks) + len(blocked_tasks),
            "flow_count": len(queued_flows) + len(running_flows) + len(blocked_flows),
            "browser_body_status": str(browser_body.get("status") or "absent"),
            "current_focus": current_focus,
            "daily_memory_state": "present" if daily_exists else "missing",
            "curated_memory_state": "present" if curated_exists else "missing",
        },
    }


def _jarvis_emergent_summary(emergent_signals: dict) -> dict[str, object]:
    summary = emergent_signals.get("summary") or {}
    return {
        "active_count": int(summary.get("active_count") or 0),
        "current_signal": str(
            summary.get("current_signal") or "No active emergent inner signal"
        ),
        "current_status": str(summary.get("current_status") or "none"),
        "current_lifecycle_state": str(
            summary.get("current_lifecycle_state") or "none"
        ),
        "authority": "candidate-only",
        "visibility": "internal-only",
    }


def _jarvis_emergent_summary(emergent_signals: dict) -> dict[str, object]:
    summary = emergent_signals.get("summary") or {}
    return {
        "active_count": int(summary.get("active_count") or 0),
        "current_signal": str(
            summary.get("current_signal") or "No active emergent inner signal"
        ),
        "current_status": str(summary.get("current_status") or "none"),
        "current_lifecycle_state": str(
            summary.get("current_lifecycle_state") or "none"
        ),
        "authority": "candidate-only",
        "visibility": "internal-only",
    }


def _preview_text(value: str, *, limit: int = 96) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:limit] + ("…" if len(text) > limit else "")


# ---------------------------------------------------------------------------
# Cognitive Architecture Endpoints
# ---------------------------------------------------------------------------


# tool/skill/hardening/lab-hjælpere bor i mission_control_helpers (holder begge
# filer < 1500 linjer). Re-eksportér dem her så den delte flade er komplet.
from .mission_control_helpers import *  # noqa: F401,F403
from .mission_control_helpers import (  # eksplicit: underscore-hjælpere (import * springer dem over)
    _get_all_tools,
    _skills_recent_invocations,
    _skills_calls_today,
    _hardening_approval_counts,
    _hardening_autonomy_level,
    _hardening_integrations,
    _hardening_recent_approvals,
    _lab_costs_today,
    _lab_providers_today,
    _lab_db_stats,
    _lab_recent_events,
)


# Eksportér ALT (inkl. underscore-hjælpere) så route-moduler kan bruge
# `from .mission_control_common import *` og få hele den delte flade.
__all__ = [__name for __name in dict(globals()) if not __name.startswith("__")]
