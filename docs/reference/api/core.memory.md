# `core.memory` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/memory/__init__.py`

_(no top-level classes or functions)_

## `core/memory/inner_llm_enrichment.py`
_Async LLM enrichment for private memory pipeline layers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sanitize_private_inner_note_enrichment` | `(text)` | — | [src](../../../core/memory/inner_llm_enrichment.py#L40) |
| function | `_sanitize_private_growth_note_enrichment` | `(text)` | — | [src](../../../core/memory/inner_llm_enrichment.py#L45) |
| function | `_sanitize_inner_voice_enrichment` | `(text)` | Reuse inner-voice sanitization before writing enriched voice lines. | [src](../../../core/memory/inner_llm_enrichment.py#L59) |
| function | `_sanitize_private_layer_text` | `(text, *, max_len=…)` | — | [src](../../../core/memory/inner_llm_enrichment.py#L69) |
| function | `_resolve_enrichment_target` | `()` | Resolve Groq-first primary target for inner enrichment. | [src](../../../core/memory/inner_llm_enrichment.py#L92) |
| function | `_resolve_ollama_fallback_target` | `()` | — | [src](../../../core/memory/inner_llm_enrichment.py#L117) |
| function | `_synthetic_groq_target` | `()` | — | [src](../../../core/memory/inner_llm_enrichment.py#L135) |
| function | `_build_inner_note_prompt` | `(payload, chat_context)` | Return (system_prompt, user_message) for inner note enrichment. | [src](../../../core/memory/inner_llm_enrichment.py#L174) |
| function | `_build_growth_note_prompt` | `(payload, chat_context)` | Return (system_prompt, user_message) for growth note enrichment. | [src](../../../core/memory/inner_llm_enrichment.py#L196) |
| function | `_build_inner_voice_prompt` | `(payload, chat_context)` | Return (system_prompt, user_message) for inner voice enrichment. | [src](../../../core/memory/inner_llm_enrichment.py#L218) |
| function | `_resolve_auth_header` | `(target)` | Build auth headers from provider router target. | [src](../../../core/memory/inner_llm_enrichment.py#L243) |
| function | `_resolve_cheap_cloud_fallback_targets` | `()` | Return non-Ollama cheap providers from the registry as fallback candidates. | [src](../../../core/memory/inner_llm_enrichment.py#L285) |
| function | `call_cheap_llm` | `(system_prompt, user_message)` | Public alias for _call_cheap_llm so other services can reuse it. | [src](../../../core/memory/inner_llm_enrichment.py#L305) |
| function | `_call_cheap_llm` | `(system_prompt, user_message)` | Call Groq-first LLM with local Ollama fallback. | [src](../../../core/memory/inner_llm_enrichment.py#L314) |
| function | `_call_remote_chat` | `(*, target, system_prompt, user_message, timeout)` | — | [src](../../../core/memory/inner_llm_enrichment.py#L406) |
| function | `_call_ollama_chat` | `(*, model, base_url, system_prompt, user_message, timeout)` | — | [src](../../../core/memory/inner_llm_enrichment.py#L479) |
| function | `_observe_enrichment` | `(*, enriched, reused, failed)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN antal lag | [src](../../../core/memory/inner_llm_enrichment.py#L549) |
| function | `_enrich_worker` | `(*, run_id, inner_note_payload, growth_note_payload, inner_voice_payload, recent_chat_context)` | Sequentially enrich 3 layers via cheap LLM, updating DB in-place. | [src](../../../core/memory/inner_llm_enrichment.py#L564) |
| function | `enrich_private_layers_async` | `(*, run_id, inner_note_payload, growth_note_payload, inner_voice_payload, recent_chat_context)` | Fire-and-forget: spawn daemon thread to enrich private layer payloads via LLM. | [src](../../../core/memory/inner_llm_enrichment.py#L683) |

## `core/memory/private_development_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_development_state` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN confidence-label + | [src](../../../core/memory/private_development_state.py#L6) |
| function | `build_private_development_state_payload` | `(*, private_growth_note, private_self_model, private_reflective_selection, created_at, updated_at)` | — | [src](../../../core/memory/private_development_state.py#L25) |
| function | `_retained_pattern` | `(*, private_growth_note, private_reflective_selection)` | — | [src](../../../core/memory/private_development_state.py#L76) |

## `core/memory/private_growth_note.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_growth_note` | `(*, learning_kind, confidence, has_mistake)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN learning_kind/ | [src](../../../core/memory/private_growth_note.py#L6) |
| function | `build_private_growth_note_payload` | `(*, run_id, work_id, status, work_preview, private_inner_note, created_at)` | — | [src](../../../core/memory/private_growth_note.py#L27) |
| function | `_learning_kind` | `(*, status)` | — | [src](../../../core/memory/private_growth_note.py#L74) |
| function | `_lesson` | `(*, learning_kind, focus, work_signal)` | — | [src](../../../core/memory/private_growth_note.py#L83) |
| function | `_mistake_signal` | `(*, status)` | — | [src](../../../core/memory/private_growth_note.py#L97) |
| function | `_helpful_signal` | `(*, status, focus, work_signal)` | — | [src](../../../core/memory/private_growth_note.py#L104) |
| function | `_confidence` | `(*, status, work_preview)` | — | [src](../../../core/memory/private_growth_note.py#L139) |
| function | `_topic_text` | `(value)` | — | [src](../../../core/memory/private_growth_note.py#L148) |
| function | `_signal_text` | `(value)` | — | [src](../../../core/memory/private_growth_note.py#L153) |
| function | `_signal_hint` | `(value)` | — | [src](../../../core/memory/private_growth_note.py#L160) |

## `core/memory/private_initiative_tension.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_initiative_tension` | `(*, active, current)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag + | [src](../../../core/memory/private_initiative_tension.py#L6) |
| function | `build_private_initiative_tension` | `(*, private_state, protected_inner_voice, private_development_state, private_reflective_selection, private_temporal_promotion_signal, private_temporal_curiosity_state, private_retained_memory_projection)` | — | [src](../../../core/memory/private_initiative_tension.py#L28) |
| function | `_tension_kind` | `(*, private_state, private_reflective_selection, private_temporal_promotion_signal, private_temporal_curiosity_state)` | — | [src](../../../core/memory/private_initiative_tension.py#L113) |
| function | `_tension_target` | `(*, protected_inner_voice, private_development_state, private_retained_memory_projection)` | — | [src](../../../core/memory/private_initiative_tension.py#L137) |
| function | `_tension_level` | `(*, private_state, private_reflective_selection, private_temporal_promotion_signal, private_temporal_curiosity_state)` | — | [src](../../../core/memory/private_initiative_tension.py#L154) |
| function | `_reason` | `(*, protected_inner_voice, private_development_state, private_reflective_selection, private_temporal_promotion_signal, private_temporal_curiosity_state)` | — | [src](../../../core/memory/private_initiative_tension.py#L179) |

## `core/memory/private_inner_interplay.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_inner_interplay` | `(*, active, current)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag + | [src](../../../core/memory/private_inner_interplay.py#L6) |
| function | `build_private_inner_interplay` | `(*, private_state, protected_inner_voice, private_development_state, private_reflective_selection)` | — | [src](../../../core/memory/private_inner_interplay.py#L28) |

## `core/memory/private_inner_note.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_inner_note` | `(*, status, uncertainty)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN status/uncertainty- | [src](../../../core/memory/private_inner_note.py#L6) |
| function | `build_private_inner_note_payload` | `(*, run_id, work_id, status, user_message_preview, work_preview, capability_id, created_at)` | — | [src](../../../core/memory/private_inner_note.py#L24) |
| function | `_private_summary` | `(*, status, user_message_preview, work_preview, capability_id, note_kind, focus, uncertainty, work_signal)` | Build a first-person inner reflection on the work that just happened. | [src](../../../core/memory/private_inner_note.py#L65) |
| function | `_uncertainty_phrase` | `(value)` | — | [src](../../../core/memory/private_inner_note.py#L108) |
| function | `_signal_phrase` | `(value)` | — | [src](../../../core/memory/private_inner_note.py#L117) |
| function | `_derive_focus` | `(user_message_preview)` | Derive a short topic label when no capability_id is available. | [src](../../../core/memory/private_inner_note.py#L136) |
| function | `_uncertainty` | `(*, status, work_preview)` | — | [src](../../../core/memory/private_inner_note.py#L165) |
| function | `_work_signal` | `(*, status, capability_id)` | — | [src](../../../core/memory/private_inner_note.py#L174) |

## `core/memory/private_layer_pipeline.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `write_private_terminal_layers` | `(*, run_id, work_id, status, started_at, finished_at, user_message_preview, work_preview, capability_id)` | — | [src](../../../core/memory/private_layer_pipeline.py#L34) |
| function | `_extract_recent_chat` | `(user_message_preview, work_preview)` | Build bounded chat context string from available previews. | [src](../../../core/memory/private_layer_pipeline.py#L149) |

## `core/memory/private_operational_preference.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_operational_preference` | `(*, active, current)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag + | [src](../../../core/memory/private_operational_preference.py#L6) |
| function | `build_private_operational_preference` | `(*, private_initiative_tension, private_temporal_curiosity_state, private_relation_state)` | — | [src](../../../core/memory/private_operational_preference.py#L27) |
| function | `_preferred_lane` | `(*, tension, curiosity, relation)` | — | [src](../../../core/memory/private_operational_preference.py#L86) |
| function | `_preference_reason` | `(*, preferred_lane, tension, curiosity, relation)` | — | [src](../../../core/memory/private_operational_preference.py#L103) |
| function | `_confidence` | `(*, preferred_lane, tension, curiosity, relation)` | — | [src](../../../core/memory/private_operational_preference.py#L122) |

## `core/memory/private_promotion_decision.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_promotion_decision` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN action/scope/ | [src](../../../core/memory/private_promotion_decision.py#L6) |
| function | `build_private_promotion_decision_payload` | `(*, run_id, work_id, private_temporal_promotion_signal, private_development_state, private_growth_note, created_at)` | — | [src](../../../core/memory/private_promotion_decision.py#L26) |
| function | `_promotion_scope` | `(private_temporal_promotion_signal, private_growth_note)` | — | [src](../../../core/memory/private_promotion_decision.py#L69) |

## `core/memory/private_reflective_selection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_reflective_selection` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN selection_kind/ | [src](../../../core/memory/private_reflective_selection.py#L6) |
| function | `build_private_reflective_selection_payload` | `(*, run_id, work_id, private_growth_note, private_self_model, created_at)` | — | [src](../../../core/memory/private_reflective_selection.py#L26) |
| function | `_selection_kind` | `(private_growth_note)` | — | [src](../../../core/memory/private_reflective_selection.py#L65) |
| function | `_reinforce` | `(private_growth_note)` | — | [src](../../../core/memory/private_reflective_selection.py#L74) |
| function | `_reconsider` | `(private_growth_note, private_self_model)` | — | [src](../../../core/memory/private_reflective_selection.py#L81) |
| function | `_fade` | `(private_growth_note)` | — | [src](../../../core/memory/private_reflective_selection.py#L91) |

## `core/memory/private_relation_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_relation_state` | `(*, active, current)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag + | [src](../../../core/memory/private_relation_state.py#L6) |
| function | `build_private_relation_state` | `(*, visible_session_continuity, visible_continuity, visible_selected_work_item, private_retained_memory_projection)` | — | [src](../../../core/memory/private_relation_state.py#L28) |
| function | `_continuity_mode` | `(*, latest_status, session, continuity)` | — | [src](../../../core/memory/private_relation_state.py#L97) |
| function | `_interaction_mode` | `(*, latest_status, user_preview, work_item)` | — | [src](../../../core/memory/private_relation_state.py#L113) |
| function | `_relation_pull` | `(*, user_preview, retained_focus, work_item)` | — | [src](../../../core/memory/private_relation_state.py#L130) |
| function | `_confidence` | `(*, session, continuity, user_preview)` | — | [src](../../../core/memory/private_relation_state.py#L145) |

## `core/memory/private_retained_memory_projection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_private_retained_memory_projection` | `(*, current_record, recent_records)` | — | [src](../../../core/memory/private_retained_memory_projection.py#L4) |

## `core/memory/private_retained_memory_record.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_retained_memory_record` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN kind/scope/horizon/ | [src](../../../core/memory/private_retained_memory_record.py#L6) |
| function | `build_private_retained_memory_record_payload` | `(*, run_id, work_id, private_promotion_decision, private_development_state, private_growth_note, private_self_model, created_at)` | — | [src](../../../core/memory/private_retained_memory_record.py#L27) |
| function | `_retained_kind` | `(private_promotion_decision, private_growth_note)` | — | [src](../../../core/memory/private_retained_memory_record.py#L79) |
| function | `_humanize_scope` | `(scope)` | — | [src](../../../core/memory/private_retained_memory_record.py#L93) |
| function | `_retention_horizon` | `(*, retention_scope, private_development_state, private_self_model)` | — | [src](../../../core/memory/private_retained_memory_record.py#L104) |

## `core/memory/private_self_model.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_self_model` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN skalarer/labels, | [src](../../../core/memory/private_self_model.py#L6) |
| function | `build_private_self_model_payload` | `(*, run_id, private_inner_note, private_growth_note, created_at, updated_at)` | — | [src](../../../core/memory/private_self_model.py#L27) |
| function | `_preferred_work_mode` | `(private_growth_note, private_inner_note)` | — | [src](../../../core/memory/private_self_model.py#L59) |
| function | `_recurring_tension` | `(private_growth_note, private_inner_note)` | — | [src](../../../core/memory/private_self_model.py#L67) |
| function | `_growth_direction` | `(private_growth_note)` | — | [src](../../../core/memory/private_self_model.py#L79) |

## `core/memory/private_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_state` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN skalarer/labels, | [src](../../../core/memory/private_state.py#L6) |
| function | `build_private_state_payload` | `(*, private_inner_note, private_growth_note, private_self_model, private_reflective_selection, private_development_state, created_at, updated_at)` | — | [src](../../../core/memory/private_state.py#L27) |
| function | `_frustration` | `(private_growth_note, private_self_model, private_development_state)` | — | [src](../../../core/memory/private_state.py#L67) |
| function | `_fatigue` | `(private_reflective_selection, private_development_state)` | — | [src](../../../core/memory/private_state.py#L86) |
| function | `_confidence` | `(private_growth_note, private_self_model, private_reflective_selection, private_development_state)` | — | [src](../../../core/memory/private_state.py#L99) |
| function | `_curiosity` | `(private_inner_note, private_growth_note, private_development_state)` | — | [src](../../../core/memory/private_state.py#L117) |

## `core/memory/private_temporal_curiosity_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_temporal_curiosity_state` | `(*, active, current)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag + | [src](../../../core/memory/private_temporal_curiosity_state.py#L6) |
| function | `build_private_temporal_curiosity_state` | `(*, private_state, private_temporal_promotion_signal, private_development_state)` | — | [src](../../../core/memory/private_temporal_curiosity_state.py#L29) |
| function | `_curiosity_carry` | `(*, curiosity_level, preferred_direction, rhythm_window)` | — | [src](../../../core/memory/private_temporal_curiosity_state.py#L96) |
| function | `_rhythm_carry` | `(*, rhythm_window, rhythm_state)` | — | [src](../../../core/memory/private_temporal_curiosity_state.py#L108) |
| function | `_maturation_window` | `(*, curiosity_level, preferred_direction, rhythm_window)` | — | [src](../../../core/memory/private_temporal_curiosity_state.py#L116) |

## `core/memory/private_temporal_promotion_signal.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_private_temporal_promotion_signal` | `(payload)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN rhythm/action/ | [src](../../../core/memory/private_temporal_promotion_signal.py#L6) |
| function | `build_private_temporal_promotion_signal_payload` | `(*, run_id, work_id, private_state, private_reflective_selection, private_development_state, protected_inner_voice, created_at)` | — | [src](../../../core/memory/private_temporal_promotion_signal.py#L27) |
| function | `_rhythm_state` | `(private_state, protected_inner_voice)` | — | [src](../../../core/memory/private_temporal_promotion_signal.py#L72) |
| function | `_rhythm_window` | `(private_state)` | — | [src](../../../core/memory/private_temporal_promotion_signal.py#L85) |
| function | `_promotion_action` | `(private_reflective_selection, private_state)` | — | [src](../../../core/memory/private_temporal_promotion_signal.py#L95) |

## `core/memory/protected_inner_voice.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_protected_inner_voice` | `(*, mood_tone)` | Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN mood_tone-label | [src](../../../core/memory/protected_inner_voice.py#L7) |
| function | `build_protected_inner_voice_payload` | `(*, run_id, work_id, private_state, private_self_model, private_development_state, private_reflective_selection, created_at)` | — | [src](../../../core/memory/protected_inner_voice.py#L23) |
| function | `_mood_tone` | `(private_state)` | — | [src](../../../core/memory/protected_inner_voice.py#L73) |
| function | `_self_position` | `(*, private_state, private_self_model, private_development_state)` | — | [src](../../../core/memory/protected_inner_voice.py#L87) |
| function | `_current_concern` | `(*, private_state, private_development_state, private_reflective_selection)` | — | [src](../../../core/memory/protected_inner_voice.py#L112) |
| function | `_current_pull` | `(*, private_state, private_development_state, private_reflective_selection)` | — | [src](../../../core/memory/protected_inner_voice.py#L138) |
| function | `_voice_line` | `(*, mood_tone, self_position, current_concern, current_pull)` | Synthesise Jarvis' protected inner voice line. | [src](../../../core/memory/protected_inner_voice.py#L160) |
| function | `_humanize_voice_fragment` | `(value)` | — | [src](../../../core/memory/protected_inner_voice.py#L198) |

