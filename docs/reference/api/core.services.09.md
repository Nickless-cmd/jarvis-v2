# `core.services.09` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/dream_insight_daemon.py`
_Dream insight daemon — persists dream articulation output as private brain records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_dream_insight_daemon` | `(*, signal_id, signal_summary)` | Persist a dream articulation result if it's new. | [src](../../../core/services/dream_insight_daemon.py#L37) |
| function | `get_latest_dream_insight` | `()` | — | [src](../../../core/services/dream_insight_daemon.py#L85) |
| function | `build_dream_insight_surface` | `()` | — | [src](../../../core/services/dream_insight_daemon.py#L89) |

## `core/services/dream_motif_daemon.py`
_Dream Motif daemon — periodisk clustering af tankestrøm-fragmenter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_dream_motif_daemon` | `()` | Run weekly dream motif clustering. Writes dream_language.md if motifs found. | [src](../../../core/services/dream_motif_daemon.py#L40) |
| function | `_load_recent_fragments` | `()` | Load thought-stream fragments from the last 30 days via private_brain_records. | [src](../../../core/services/dream_motif_daemon.py#L78) |
| function | `_extract_motifs` | `(fragments)` | Simple word-frequency motif extraction across all fragments. | [src](../../../core/services/dream_motif_daemon.py#L96) |
| function | `_name_motifs_via_llm` | `(motifs, fragments)` | Use LLM to give each recurring word/theme a poetic name and brief description. | [src](../../../core/services/dream_motif_daemon.py#L110) |
| function | `_write_dream_language_file` | `(motifs, now, fragment_count)` | Write dream_language.md to workspace. Never injected into prompts — read on demand. | [src](../../../core/services/dream_motif_daemon.py#L155) |
| function | `build_dream_motif_surface` | `()` | — | [src](../../../core/services/dream_motif_daemon.py#L187) |
| function | `_state` | `()` | — | [src](../../../core/services/dream_motif_daemon.py#L197) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/dream_motif_daemon.py#L205) |

## `core/services/dreaming_session.py`
_D4 — Dreaming Session: dedicated full-model session during prolonged idle._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/dreaming_session.py#L32) |
| function | `_load_state` | `()` | — | [src](../../../core/services/dreaming_session.py#L36) |
| function | `_save_state` | `(data)` | — | [src](../../../core/services/dreaming_session.py#L51) |
| function | `_check_triggers` | `()` | Check if the dreaming session should fire. | [src](../../../core/services/dreaming_session.py#L62) |
| function | `_collect_dream_material` | `()` | Collect all dream infrastructure output for the prompt. | [src](../../../core/services/dreaming_session.py#L101) |
| function | `_build_dream_prompt` | `(material)` | Build the full dream prompt from collected material. | [src](../../../core/services/dreaming_session.py#L200) |
| function | `_record_session` | `(material, dream_prompt_preview)` | Record the dream session metadata and return the session identifier. | [src](../../../core/services/dreaming_session.py#L306) |
| function | `trigger_dream_session` | `()` | Check triggers and fire a dream session if conditions are met. | [src](../../../core/services/dreaming_session.py#L332) |
| function | `list_dream_sessions` | `(*, limit=…)` | List recent dream session records. | [src](../../../core/services/dreaming_session.py#L393) |
| function | `build_dreaming_session_surface` | `()` | Build Mission Control surface for the dreaming session module. | [src](../../../core/services/dreaming_session.py#L399) |

## `core/services/drive_arbitration_engine.py`
_Desire/value arbitration as a compact drive system._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `arbitrate_drives` | `(*, user_message=…, context=…)` | — | [src](../../../core/services/drive_arbitration_engine.py#L14) |
| function | `build_drive_arbitration_surface` | `()` | — | [src](../../../core/services/drive_arbitration_engine.py#L56) |
| function | `build_drive_arbitration_prompt_section` | `()` | — | [src](../../../core/services/drive_arbitration_engine.py#L69) |
| function | `_policy_for_top` | `(top)` | — | [src](../../../core/services/drive_arbitration_engine.py#L84) |

## `core/services/embodied_presence.py`
_Embodied Presence — situational grounding in the physical now._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PresenceSignal` | `` | — | [src](../../../core/services/embodied_presence.py#L36) |
| function | `_hour_to_temporal_context` | `(hour)` | Map hour (0-23) to temporal context label. | [src](../../../core/services/embodied_presence.py#L43) |
| function | `_compute_grounding` | `(has_visual, has_audio, has_atmosphere)` | Grounding increases with more sensory channels present. | [src](../../../core/services/embodied_presence.py#L57) |
| function | `_compute_arousal` | `(visual_activity=…, audio_amplitude=…, atmosphere_energy=…)` | Arousal from ambient sensory energy. | [src](../../../core/services/embodied_presence.py#L68) |
| function | `_summarize_presence` | `(grounding, arousal, temporal_context)` | Produce a compact presence line for assembly injection. | [src](../../../core/services/embodied_presence.py#L103) |
| function | `compute_embodied_presence` | `(db_conn=…, now=…)` | Compute embodied presence signal from sensory data + time. | [src](../../../core/services/embodied_presence.py#L130) |
| function | `get_presence_line` | `(db_conn=…)` | Get just the summary line for assembly injection. | [src](../../../core/services/embodied_presence.py#L236) |
| function | `build_embodied_presence_surface` | `()` | — | [src](../../../core/services/embodied_presence.py#L249) |
| function | `_emit_presence_event` | `(state)` | — | [src](../../../core/services/embodied_presence.py#L258) |

## `core/services/embodied_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_embodied_state_surface` | `()` | — | [src](../../../core/services/embodied_state.py#L13) |
| function | `build_embodied_state_from_facts` | `(facts, *, previous=…)` | — | [src](../../../core/services/embodied_state.py#L25) |
| function | `build_embodied_state_prompt_section` | `(surface=…)` | — | [src](../../../core/services/embodied_state.py#L91) |
| function | `collect_host_facts` | `()` | — | [src](../../../core/services/embodied_state.py#L157) |
| function | `_build_cpu_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L201) |
| function | `_build_memory_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L217) |
| function | `_build_disk_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L233) |
| function | `_build_thermal_fact` | `(facts)` | — | [src](../../../core/services/embodied_state.py#L249) |
| function | `_derive_primary_state` | `(facts_surface)` | — | [src](../../../core/services/embodied_state.py#L261) |
| function | `_derive_recovery_state` | `(*, previous, current_primary_state, built_at)` | — | [src](../../../core/services/embodied_state.py#L283) |
| function | `_read_meminfo` | `()` | — | [src](../../../core/services/embodied_state.py#L303) |
| function | `_read_thermal_celsius` | `()` | — | [src](../../../core/services/embodied_state.py#L322) |
| function | `_bucket_from_thresholds` | `(value, thresholds)` | — | [src](../../../core/services/embodied_state.py#L342) |
| function | `_severity` | `(bucket)` | — | [src](../../../core/services/embodied_state.py#L353) |
| function | `_strain_level_for_state` | `(state)` | — | [src](../../../core/services/embodied_state.py#L362) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/embodied_state.py#L372) |

## `core/services/emergence.py`
_Emergence — evidence-based pattern detection across recent activity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmergenceCandidate` | `` | — | [src](../../../core/services/emergence.py#L44) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/emergence.py#L54) |
| function | `_ensure_table` | `()` | Create emergent_patterns table if missing. Idempotent. | [src](../../../core/services/emergence.py#L58) |
| function | `_fetch_recent_events` | `(*, window_days=…, limit=…)` | Pull recent events from the eventbus events table. | [src](../../../core/services/emergence.py#L80) |
| function | `_count_by_kind_prefix` | `(events, prefix)` | — | [src](../../../core/services/emergence.py#L108) |
| function | `_count_blocked` | `(events)` | Count events that look like blocked/denied signals. | [src](../../../core/services/emergence.py#L118) |
| function | `_fetch_procedures_count` | `()` | — | [src](../../../core/services/emergence.py#L135) |
| function | `_fetch_decisions_count` | `(*, window_days=…)` | — | [src](../../../core/services/emergence.py#L146) |
| function | `_detect_candidates` | `(*, window_days=…)` | — | [src](../../../core/services/emergence.py#L159) |
| function | `_create_or_update_pattern` | `(*, pattern_key, title, summary, confidence, evidence_count, competing_explanations, confounders, status)` | Insert or update a pattern row. Returns the persisted row. | [src](../../../core/services/emergence.py#L229) |
| function | `detect_and_score_patterns` | `(*, window_days=…)` | Main entry — detect candidates, score via apophenia, persist, emit events. | [src](../../../core/services/emergence.py#L289) |
| function | `list_patterns` | `(*, status=…, limit=…)` | Return persisted patterns, optionally filtered by status. | [src](../../../core/services/emergence.py#L354) |
| function | `summarize_patterns` | `()` | — | [src](../../../core/services/emergence.py#L377) |
| function | `_decode_json_list` | `(value)` | — | [src](../../../core/services/emergence.py#L396) |
| function | `build_emergence_surface` | `(*, limit=…)` | Surface persisted emergence candidates without running detection. | [src](../../../core/services/emergence.py#L406) |

## `core/services/emergent_bridge.py`
_Emergent Bridge — consumer for emergent signals to influence visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `should_influence_prompt` | `()` | Determine if an emergent signal should influence the visible prompt. | [src](../../../core/services/emergent_bridge.py#L26) |
| function | `get_influencing_emergents` | `()` | Get the emergent signals that are currently influencing. | [src](../../../core/services/emergent_bridge.py#L45) |
| function | `format_emergent_for_prompt` | `()` | Format emergent signal for prompt injection. | [src](../../../core/services/emergent_bridge.py#L68) |
| function | `reset_emergent_bridge` | `()` | Reset emergent bridge state (for testing). | [src](../../../core/services/emergent_bridge.py#L84) |
| function | `get_emergent_bridge_state` | `()` | Get current state of emergent bridge. | [src](../../../core/services/emergent_bridge.py#L90) |
| function | `build_emergent_bridge_surface` | `()` | Build MC surface for emergent bridge. | [src](../../../core/services/emergent_bridge.py#L100) |

## `core/services/emergent_goals.py`
_Emergent Goals — desires that grow from experience, not assignment._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_emergent_goal_from_experience` | `(*, recent_topic=…, curiosity_level=…, knowledge_gap=…)` | — | [src](../../../core/services/emergent_goals.py#L18) |
| function | `build_jarvis_agenda` | `()` | Jarvis' own agenda — what HE thinks is important. | [src](../../../core/services/emergent_goals.py#L37) |
| function | `build_emergent_goals_surface` | `()` | — | [src](../../../core/services/emergent_goals.py#L62) |

## `core/services/emergent_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmergentSignal` | `` | — | [src](../../../core/services/emergent_signal_tracking.py#L16) |
| function | `run_emergent_signal_daemon` | `(*, trigger=…, last_visible_at=…)` | Produce a small bounded set of grounded candidate emergent signals. | [src](../../../core/services/emergent_signal_tracking.py#L48) |
| function | `build_runtime_emergent_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/emergent_signal_tracking.py#L185) |
| function | `get_emergent_signal_daemon_state` | `()` | — | [src](../../../core/services/emergent_signal_tracking.py#L228) |
| function | `_extract_grounded_candidates` | `(*, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L237) |
| function | `_ordered_signals` | `(limit)` | — | [src](../../../core/services/emergent_signal_tracking.py#L332) |
| function | `_serialize_signal` | `(signal, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L345) |
| function | `_event_payload` | `(signal, *, trigger)` | — | [src](../../../core/services/emergent_signal_tracking.py#L352) |
| function | `_expiry_state` | `(signal, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L366) |
| function | `_signal_key` | `(family, *anchors)` | — | [src](../../../core/services/emergent_signal_tracking.py#L378) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/emergent_signal_tracking.py#L384) |
| function | `_current_label` | `(surface)` | — | [src](../../../core/services/emergent_signal_tracking.py#L390) |
| function | `_safe_surface` | `(module_name, fn_name)` | — | [src](../../../core/services/emergent_signal_tracking.py#L401) |
| function | `_safe_daemon_state` | `(module_name, fn_name)` | — | [src](../../../core/services/emergent_signal_tracking.py#L410) |
| function | `_inner_voice_recent` | `(state, *, now)` | — | [src](../../../core/services/emergent_signal_tracking.py#L419) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/emergent_signal_tracking.py#L432) |

## `core/services/emotion_concepts.py`
_Emotion Concepts — discrete, event-driven Lag-2 emotional signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | Indirected for monkeypatching in tests. | [src](../../../core/services/emotion_concepts.py#L123) |
| function | `trigger_emotion_concept` | `(concept, intensity, trigger=…, source=…, lifetime_hours=…, *, min_seconds_since_last_from_same_source=…)` | Create or strengthen an active emotion concept instance. | [src](../../../core/services/emotion_concepts.py#L128) |
| function | `tick_emotion_concepts` | `(elapsed_seconds)` | Decay all active concepts proportional to elapsed time. | [src](../../../core/services/emotion_concepts.py#L215) |
| function | `drain_expired_residue` | `()` | Return accumulated residue deltas from expired concepts and reset to zero. | [src](../../../core/services/emotion_concepts.py#L250) |
| function | `get_active_emotion_concepts` | `()` | Return all active concepts above threshold, sorted by intensity descending. | [src](../../../core/services/emotion_concepts.py#L264) |
| function | `get_lag1_influence_deltas` | `()` | Compute cumulative influence on Lag-1 axes from all active concepts. | [src](../../../core/services/emotion_concepts.py#L276) |
| function | `get_bearing_push` | `()` | Return bearing push from the highest-intensity bearing-influencing concept. | [src](../../../core/services/emotion_concepts.py#L294) |
| function | `build_emotion_concept_surface` | `()` | MC surface: active concepts + influence deltas. | [src](../../../core/services/emotion_concepts.py#L309) |
| function | `_prune_if_needed` | `()` | Remove the weakest concept when over limit. Must be called under _lock. | [src](../../../core/services/emotion_concepts.py#L326) |
| function | `_persist_async` | `(signal)` | Fire-and-forget: persist signal to DB for MC observability. | [src](../../../core/services/emotion_concepts.py#L333) |
| function | `_safe_persist` | `(signal)` | — | [src](../../../core/services/emotion_concepts.py#L339) |
| function | `_handle_event` | `(kind, payload)` | Map eventbus events to emotion concept triggers. | [src](../../../core/services/emotion_concepts.py#L364) |
| function | `_handle_heartbeat_tick` | `(payload)` | Map heartbeat tick outcomes to emotion concepts. | [src](../../../core/services/emotion_concepts.py#L430) |
| function | `_handle_tool_completed` | `(payload)` | Map the actual simple_tools event shape to emotion concepts. | [src](../../../core/services/emotion_concepts.py#L465) |
| function | `_listener_loop` | `(q)` | Background thread: reads from eventbus queue and dispatches events. | [src](../../../core/services/emotion_concepts.py#L496) |
| function | `register_event_listeners` | `()` | Subscribe to eventbus and start background listener thread. | [src](../../../core/services/emotion_concepts.py#L513) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/emotion_concepts.py#L535) |

## `core/services/emotion_concepts_channel_triggers.py`
_Helper module for emotion concept triggers from channel messages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `on_channel_message_appended` | `(payload)` | Fire emotion concept triggers based on user-message content. | [src](../../../core/services/emotion_concepts_channel_triggers.py#L22) |

## `core/services/emotion_concepts_positive_triggers.py`
_Positive emotion concept bridges for living runtime signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `on_heartbeat_quality` | `(payload)` | Trigger joy when heartbeat quality is clearly good. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L13) |
| function | `on_goal_created` | `(payload)` | A new durable goal produces a small anticipation/excitement pulse. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L29) |
| function | `on_goal_updated` | `(payload)` | Trigger pride when a goal is nearly done, without refiring constantly. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L42) |
| function | `on_sensory_recorded` | `(record)` | Trigger wonder when a sensory memory explicitly looks novel/anomalous. | [src](../../../core/services/emotion_concepts_positive_triggers.py#L80) |
| function | `_float` | `(value)` | — | [src](../../../core/services/emotion_concepts_positive_triggers.py#L103) |

## `core/services/emotion_repair_bridge_daemon.py`
_Emotion Repair Bridge Daemon — tovejskobling mellem emotion-signaler og selvreparation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_emotion_repair_bridge_surface` | `()` | Mission Control surface for emotion-repair bridge state. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L92) |
| function | `_ensure_default_patterns` | `()` | Seed DB with default repair patterns if not already present. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L154) |
| function | `tick_emotion_repair_bridge` | `()` | Main tick: check emotion signals, map to repairs, execute. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L174) |
| function | `_tick_emotion_repair_bridge_inner` | `()` | Inner tick logic — wrapped by tick_emotion_repair_bridge for bærekraft. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L201) |
| function | `_bridge_repair_to_senses` | `(*, action_type, pattern_id, outcome, concept, error_summary=…)` | Write a sensory impression to Sansernes Arkiv when self-repair happens. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L377) |
| function | `_execute_repair_action` | `(action_type, pattern_id)` | Execute a repair action by type. Can be extended. | [src](../../../core/services/emotion_repair_bridge_daemon.py#L428) |

## `core/services/emotion_tagging.py`
_Emotion tagging — capture affective context at memory-creation time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `current_emotion_tag` | `()` | Snapshot current affective state for tagging a new memory. | [src](../../../core/services/emotion_tagging.py#L25) |
| function | `format_emotion_tag` | `(tag)` | Render a tag as a compact string for inclusion in memory text. | [src](../../../core/services/emotion_tagging.py#L53) |
| function | `_exec_capture_emotion_tag` | `(args)` | — | [src](../../../core/services/emotion_tagging.py#L69) |
| function | `build_emotion_tagging_surface` | `()` | — | [src](../../../core/services/emotion_tagging.py#L90) |
| function | `_emit_tagging_event` | `(tag, intensity)` | — | [src](../../../core/services/emotion_tagging.py#L99) |

## `core/services/emotional_chords.py`
_Emotional Chords — emergent qualities from signal combinations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ChordDef` | `` | A chord definition — two signals that produce an emergent quality. | [src](../../../core/services/emotional_chords.py#L50) |
| class | `ActiveChord` | `` | A currently active emotional chord. | [src](../../../core/services/emotional_chords.py#L151) |
| function | `compute_active_chords` | `()` | Detect active emotional chords from current pressure state. | [src](../../../core/services/emotional_chords.py#L165) |
| function | `format_chord_for_prompt` | `(chord)` | Format a single chord for prompt injection. | [src](../../../core/services/emotional_chords.py#L226) |
| function | `get_chord_lines` | `()` | Convenience: compute all active chords and format for prompt. | [src](../../../core/services/emotional_chords.py#L236) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/emotional_chords.py#L254) |
| function | `_map_pressures_to_families` | `(dominant_pressures)` | Map active pressure vectors to their likely signal families. | [src](../../../core/services/emotional_chords.py#L265) |

## `core/services/emotional_controls.py`
_Emotional Controls — humør der GATER handlinger, ikke bare rapporteres._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EmotionalSnapshot` | `` | Point-in-time emotional reading used for gating decisions. | [src](../../../core/services/emotional_controls.py#L54) |
| function | `_approval_denial_streak_last_hour` | `()` | Count consecutive recent approval denials as frustration proxy. | [src](../../../core/services/emotional_controls.py#L63) |
| function | `_recent_tool_errors_last_10min` | `()` | Count tool.completed events with status=error in last 10 minutes (fatigue proxy). | [src](../../../core/services/emotional_controls.py#L92) |
| function | `read_emotional_snapshot` | `()` | Compose current emotional state from available signals. | [src](../../../core/services/emotional_controls.py#L118) |
| function | `apply_emotional_controls` | `(*, kernel_action=…, snapshot=…)` | Transform a kernel action based on current emotional state. | [src](../../../core/services/emotional_controls.py#L161) |
| function | `build_emotional_controls_surface` | `()` | MC surface — current emotional state + what would be gated. | [src](../../../core/services/emotional_controls.py#L220) |
| function | `format_gate_message` | `(action, reason, *, tool_name=…)` | Generate a user-facing Danish message explaining the gate. | [src](../../../core/services/emotional_controls.py#L260) |

## `core/services/emotional_memory_engine.py`
_Emotional memory engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_error` | `(error)` | Map raw error text to a coarse category for retrieval matching. | [src](../../../core/services/emotional_memory_engine.py#L29) |
| function | `_count_tool_errors` | `(error, tool_names)` | Heuristically count how many tools in a run failed. | [src](../../../core/services/emotional_memory_engine.py#L43) |
| function | `_derive_outcome_score` | `(*, status, error, tool_error_count)` | Auto-deriv outcome score from structured episode fields. | [src](../../../core/services/emotional_memory_engine.py#L65) |
| function | `_read_current_mood` | `()` | Return (mood, intensity). Raises if oscillator is unavailable. | [src](../../../core/services/emotional_memory_engine.py#L96) |
| function | `_read_current_dimensions` | `()` | Return the 5-dimension live emotional state. May raise — caller handles. | [src](../../../core/services/emotional_memory_engine.py#L102) |
| function | `_coerce_float_or_none` | `(value)` | — | [src](../../../core/services/emotional_memory_engine.py#L116) |
| function | `capture_emotional_anchor` | `(*, anchor_type, anchor_id, context_features, auto_outcome_inputs=…, source=…, notes=…)` | Snapshot affect for an anchor and persist it. | [src](../../../core/services/emotional_memory_engine.py#L125) |
| function | `prune_aged_anchors` | `()` | Delete anchors older than the aging threshold unless they are significant. | [src](../../../core/services/emotional_memory_engine.py#L220) |
| function | `find_similar_anchors` | `(*, anchor_type, context_features, limit=…, min_intensity=…, require_outcome=…)` | Find similar past anchors. Tiered: structured match first, lexical fallback. | [src](../../../core/services/emotional_memory_engine.py#L271) |
| function | `_with_parsed_context` | `(row)` | — | [src](../../../core/services/emotional_memory_engine.py#L328) |
| function | `_tier1_score` | `(anchor_type, current, candidates)` | — | [src](../../../core/services/emotional_memory_engine.py#L337) |
| function | `_tier2_lexical_score` | `(current, candidates)` | — | [src](../../../core/services/emotional_memory_engine.py#L386) |
| function | `_jaccard` | `(a, b)` | — | [src](../../../core/services/emotional_memory_engine.py#L401) |
| function | `_shingle` | `(text, *, n=…)` | Tokenize lowercased text into overlapping n-grams of words. | [src](../../../core/services/emotional_memory_engine.py#L409) |
| function | `_apply_aging_weight` | `(row)` | Multiply score by aging factor based on captured_at. | [src](../../../core/services/emotional_memory_engine.py#L417) |
| function | `build_emotional_memory_surface` | `(*, anchor_type, context_features)` | Return a bounded surface describing emotional precedent for the current context. | [src](../../../core/services/emotional_memory_engine.py#L467) |
| function | `_inactive_surface` | `()` | — | [src](../../../core/services/emotional_memory_engine.py#L559) |
| function | `_compile_directive` | `(*, match_count, mood_distribution, outcome_distribution)` | — | [src](../../../core/services/emotional_memory_engine.py#L568) |
| function | `build_emotional_memory_prompt_section` | `(*, anchor_type, context_features)` | Compact one-line section for inclusion in cognitive_frame_prompt. | [src](../../../core/services/emotional_memory_engine.py#L591) |
| function | `build_emotional_memory_overview` | `(*, limit=…)` | Mission Control overview surface. | [src](../../../core/services/emotional_memory_engine.py#L608) |

## `core/services/encryption.py`
_AES-256-GCM kryptering for bruger-data at-rest (spec §16, Lag 1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DecryptionError` | `` | Dekryptering fejlede — forkert nøgle eller manipuleret data (GCM-tag). | [src](../../../core/services/encryption.py#L23) |
| function | `encrypt` | `(plaintext, key)` | AES-256-GCM. Returnerer IV(12) || ciphertext+tag. key skal være 32 byte. | [src](../../../core/services/encryption.py#L27) |
| function | `decrypt` | `(blob, key)` | Dekryptér IV || ciphertext. Rejser DecryptionError ved forkert key/tamper. | [src](../../../core/services/encryption.py#L36) |
| function | `encrypt_file` | `(path, key)` | Krypter en fil → <path>.enc, fjern originalen. Returnér .enc-stien. | [src](../../../core/services/encryption.py#L49) |
| function | `decrypt_file` | `(enc_path, key)` | Dekryptér en .enc-fil i memory (skrives ALDRIG i klartekst til disk, §16.5). | [src](../../../core/services/encryption.py#L64) |
| function | `new_key` | `()` | Ny tilfældig 256-bit nøgle som bytearray (kan zeroes). | [src](../../../core/services/encryption.py#L70) |
| function | `zero_key` | `(key)` | Nulstil nøgle-bytes i memory (§16.3 regel 4). Best-effort i Python. | [src](../../../core/services/encryption.py#L75) |

## `core/services/end_of_run_memory_consolidation.py`
_End-of-run memory consolidation driven by the local model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `consolidate_run_memory` | `(*, session_id=…, run_id=…, user_message=…, assistant_response=…, internal_context=…)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L31) |
| function | `_publish_consolidation_event` | `(result, *, session_id, run_id)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L134) |
| function | `_run_memory_consolidation_pass` | `(*, user_message, assistant_response, internal_context, current_memory, current_user, full_context)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L158) |
| function | `_run_local_consolidation_model` | `(prompt)` | Run consolidation prompt. Primary: heartbeat target. Fallback: direct Ollama. | [src](../../../core/services/end_of_run_memory_consolidation.py#L183) |
| function | `_run_ollama_consolidation_fallback` | `(prompt)` | Direct Ollama generate call, trying available chat-capable models in order. | [src](../../../core/services/end_of_run_memory_consolidation.py#L226) |
| function | `_build_consolidation_prompt` | `(*, user_message, assistant_response, internal_context, current_memory, current_user, full_context)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L282) |
| function | `_parse_decision` | `(raw)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L345) |
| function | `_normalize_memory_items` | `(raw_items)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L360) |
| function | `_persist_memory_candidates` | `(*, items, session_id, run_id)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L392) |
| function | `_candidate_canonical_key` | `(item)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L436) |
| function | `_append_daily_memory_log` | `(*, daily_memory_path, session_id, run_id, user_message, assistant_response, items)` | Append an end-of-run consolidation block to today's daily memory. | [src](../../../core/services/end_of_run_memory_consolidation.py#L447) |
| function | `_evidence_class_for_source` | `(source)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L500) |
| function | `_normalize_line` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L508) |
| function | `_normalize_sentence` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L517) |
| function | `_normalize_confidence` | `(value)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L524) |
| function | `_summary_from_line` | `(line)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L531) |
| function | `_daily_excerpt` | `(value, *, limit)` | — | [src](../../../core/services/end_of_run_memory_consolidation.py#L538) |

## `core/services/endpoint_usage_store.py`
_API-endpoint forbrugs-statistik (parallel til tool_usage_store). Centralen holder styr på_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/endpoint_usage_store.py#L22) |
| function | `record_request` | `(method, path, status_code=…)` | UPSERT-increment for ét request. Best-effort, hot-path-sikker. path = rute-TEMPLATE | [src](../../../core/services/endpoint_usage_store.py#L35) |
| function | `store_registered_routes` | `(routes)` | Snapshot af registrerede (method, path)-ruter ved api-start → shared_cache, så dead- | [src](../../../core/services/endpoint_usage_store.py#L63) |
| function | `_registered` | `()` | — | [src](../../../core/services/endpoint_usage_store.py#L74) |
| function | `usage_stats` | `()` | — | [src](../../../core/services/endpoint_usage_store.py#L83) |
| function | `_bucket_for` | `(count)` | — | [src](../../../core/services/endpoint_usage_store.py#L101) |
| function | `usage_buckets` | `()` | Klassificér endpoints most/often/sometimes/rare/never. Registrerede-men-aldrig-kaldte | [src](../../../core/services/endpoint_usage_store.py#L108) |
| function | `dead_endpoints` | `()` | Registrerede endpoints der ALDRIG er kaldt. Kandidater til oprydning / smartere design. | [src](../../../core/services/endpoint_usage_store.py#L121) |
| function | `observe_stats` | `()` | Periodisk (cadence): central.observe forbrugs-summary + flag antal døde endpoints. | [src](../../../core/services/endpoint_usage_store.py#L129) |

## `core/services/epistemic_pragmatic.py`
_Epistemic/Pragmatic Balance — action-mode modulation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActionMode` | `` | Current epistemic/pragmatic balance. | [src](../../../core/services/epistemic_pragmatic.py#L42) |
| function | `compute_epistemic_pragmatic` | `()` | Compute current epistemic/pragmatic balance. | [src](../../../core/services/epistemic_pragmatic.py#L73) |
| function | `_mode_from_confidence` | `(confidence)` | Fallback: determine mode from confidence alone (no pressures). | [src](../../../core/services/epistemic_pragmatic.py#L199) |
| function | `get_mode_line` | `()` | Convenience: compute mode and return prompt-ready string. | [src](../../../core/services/epistemic_pragmatic.py#L227) |
| function | `get_mode_detail` | `()` | Return full mode state for MC transparency. | [src](../../../core/services/epistemic_pragmatic.py#L239) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/epistemic_pragmatic.py#L257) |

## `core/services/epistemic_runtime_state.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_epistemic_runtime_state_surface` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L10) |
| function | `_build_epistemic_runtime_state_surface_uncached` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L18) |
| function | `build_epistemic_runtime_state_from_sources` | `(*, conflict_trace, deception_guard, affective_meta_state, embodied_state, loop_runtime, emergent_signal, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L30) |
| function | `build_epistemic_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/epistemic_runtime_state.py#L185) |
| function | `_derive_wrongness_state` | `(*, conflict_trace, deception_guard, affective_meta_state, embodied_state, loop_summary, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L216) |
| function | `_derive_regret_signal` | `(*, wrongness_state, counterfactual_mode, deception_guard, conflict_trace)` | — | [src](../../../core/services/epistemic_runtime_state.py#L251) |
| function | `_derive_counterfactual_mode` | `(*, conflict_trace, deception_guard, quiet_initiative, loop_summary)` | — | [src](../../../core/services/epistemic_runtime_state.py#L268) |
| function | `_derive_confidence` | `(*, wrongness_state, contributors)` | — | [src](../../../core/services/epistemic_runtime_state.py#L286) |
| function | `_derive_counterfactual_hint` | `(*, counterfactual_mode, conflict_trace, deception_guard, quiet_initiative)` | — | [src](../../../core/services/epistemic_runtime_state.py#L294) |
| function | `_guidance_for_state` | `(*, wrongness_state, regret_signal, counterfactual_mode, counterfactual_hint)` | — | [src](../../../core/services/epistemic_runtime_state.py#L314) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L334) |
| function | `_safe_deception_guard` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L340) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L346) |
| function | `_safe_embodied_state` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L352) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L358) |
| function | `_safe_emergent_signal` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L364) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/epistemic_runtime_state.py#L372) |

## `core/services/epistemics.py`
_Epistemics — 5-lags videns-klarhed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/epistemics.py#L68) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/epistemics.py#L72) |
| function | `_is_related` | `(a, b)` | — | [src](../../../core/services/epistemics.py#L76) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/epistemics.py#L83) |
| function | `classify_claim` | `(*, repeated_success, variance, has_gut_signal, missing_artifact, contradicted)` | Klassificér claim til et af de 5 lag baseret på evidens + kontekst. | [src](../../../core/services/epistemics.py#L127) |
| function | `_infer_repeated_success` | `(claim, limit=…)` | Tæl tidligere relaterede claims med outcome_status=success. | [src](../../../core/services/epistemics.py#L149) |
| function | `reconcile_claim` | `(*, outcome)` | Reconcile a claim against its outcome. Persists claim at the right layer. | [src](../../../core/services/epistemics.py#L167) |
| function | `count_relevant_wrongness` | `(*, claim, domain=…)` | Tæl tidligere wrongness-entries relateret til claim. | [src](../../../core/services/epistemics.py#L257) |
| function | `_infer_stance_layer` | `(confidence)` | — | [src](../../../core/services/epistemics.py#L280) |
| function | `_should_add_stance` | `(text, confidence, is_recommendation)` | — | [src](../../../core/services/epistemics.py#L290) |
| function | `looks_like_recommendation` | `(text)` | — | [src](../../../core/services/epistemics.py#L301) |
| function | `apply_response_stance` | `(*, text, domain=…, confidence=…, is_recommendation=…, lang=…)` | Add epistemic stance prefix ("Jeg tror...") if warranted, and | [src](../../../core/services/epistemics.py#L305) |
| function | `list_claims` | `(*, layer=…, domain=…, limit=…)` | — | [src](../../../core/services/epistemics.py#L351) |
| function | `list_wrongness` | `(*, domain=…, limit=…)` | — | [src](../../../core/services/epistemics.py#L374) |
| function | `build_epistemics_surface` | `()` | MC surface — show layer distribution + recent wrongness. | [src](../../../core/services/epistemics.py#L393) |

## `core/services/error_healers.py`
_HEALER-REGISTRET (Canonical Error System, Fase 1) — det eneste ægte NYE backend-stykke._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `HealingOutcome` | `` | — | [src](../../../core/services/error_healers.py#L52) |
| class | `HealingResult` | `` | Struktureret svar fra en heal(). `detail` er menneske-læsbar (til nerve/incident). | [src](../../../core/services/error_healers.py#L61) |
| method | `HealingResult.__bool__` | `(self)` | — | [src](../../../core/services/error_healers.py#L68) |
| function | `_flag_on` | `(name, *, default=…)` | Læs et healer-flag fra shared_cache. Default OFF (healers tændes eksplicit). | [src](../../../core/services/error_healers.py#L78) |
| function | `set_healer_flag` | `(name, enabled)` | Tænd/sluk et healer-flag live (til Bjørn/MC). Self-safe. | [src](../../../core/services/error_healers.py#L93) |
| function | `healers_enabled` | `()` | Er HELE registret tændt? Default OFF — dispatcher shadow'er indtil Bjørn tænder. | [src](../../../core/services/error_healers.py#L110) |
| class | `_AttemptState` | `` | — | [src](../../../core/services/error_healers.py#L119) |
| class | `_AttemptLedger` | `` | In-memory tæller + cooldown pr. (kind, origin). Nulstilles ved proces-genstart | [src](../../../core/services/error_healers.py#L124) |
| method | `_AttemptLedger.__init__` | `(self)` | — | [src](../../../core/services/error_healers.py#L128) |
| method | `_AttemptLedger._key` | `(self, kind, origin)` | — | [src](../../../core/services/error_healers.py#L132) |
| method | `_AttemptLedger.in_cooldown` | `(self, kind, origin, cooldown_seconds)` | — | [src](../../../core/services/error_healers.py#L135) |
| method | `_AttemptLedger.attempts` | `(self, kind, origin)` | — | [src](../../../core/services/error_healers.py#L142) |
| method | `_AttemptLedger.record_attempt` | `(self, kind, origin)` | Registrér ét forsøg (nu). Returnér ny total. | [src](../../../core/services/error_healers.py#L147) |
| method | `_AttemptLedger.reset` | `(self, kind, origin)` | Nulstil ved SUCCESS — tilstanden er helbredt, tælleren skal ikke hænge. | [src](../../../core/services/error_healers.py#L157) |
| method | `_AttemptLedger.snapshot` | `(self)` | — | [src](../../../core/services/error_healers.py#L162) |
| class | `ErrorHealer` | `` | Base for alle healers. Underklasser overrider `_do_heal(...)`. | [src](../../../core/services/error_healers.py#L174) |
| method | `ErrorHealer._may_execute_destructive` | `(self, ctx)` | Returnér (må_eksekvere, grund). To betingelser SKAL begge være opfyldt: | [src](../../../core/services/error_healers.py#L193) |
| method | `ErrorHealer._plan` | `(self, ctx)` | Menneske-læsbar beskrivelse af hvad healeren VILLE gøre (til shadow-log). | [src](../../../core/services/error_healers.py#L221) |
| method | `ErrorHealer._do_heal` | `(self, ctx)` | Den faktiske helbredelse. Kaldes KUN når løkke-værn er passeret. | [src](../../../core/services/error_healers.py#L225) |
| method | `ErrorHealer.heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L231) |
| class | `CircuitResetHealer` | `` | central.circuit_open → LIVE + SIKKER. Nulstiller den in-memory CircuitBreaker for | [src](../../../core/services/error_healers.py#L257) |
| method | `CircuitResetHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L267) |
| method | `CircuitResetHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L270) |
| class | `DaemonRestartHealer` | `` | central.daemon_dead → DESTRUKTIV, SHADOW-FIRST. `sudo systemctl restart jarvis-<unit>` | [src](../../../core/services/error_healers.py#L285) |
| method | `DaemonRestartHealer._unit` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L300) |
| method | `DaemonRestartHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L307) |
| method | `DaemonRestartHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L311) |
| class | `SyslogRestartHealer` | `` | infra.syslogd_dead → DESTRUKTIV, SHADOW-FIRST. VIGTIGT: der findes INTET eksisterende | [src](../../../core/services/error_healers.py#L334) |
| method | `SyslogRestartHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L347) |
| method | `SyslogRestartHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L351) |
| class | `DelegatedHealer` | `` | In-band kinds (provider.unavailable, model.rate_limited, network.timeout, tool.timeout). | [src](../../../core/services/error_healers.py#L372) |
| method | `DelegatedHealer.__init__` | `(self, kind)` | — | [src](../../../core/services/error_healers.py#L384) |
| method | `DelegatedHealer._plan` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L387) |
| method | `DelegatedHealer._do_heal` | `(self, ctx)` | — | [src](../../../core/services/error_healers.py#L390) |
| function | `register_healer` | `(healer)` | Registrér en healer på dens `kind`. Self-safe (ignorér healer uden kind). | [src](../../../core/services/error_healers.py#L401) |
| function | `_register_defaults` | `()` | — | [src](../../../core/services/error_healers.py#L410) |
| function | `_observe_heal` | `(kind, origin, run_id, result, *, global_off)` | Registrér healing-udfaldet som nerve `heal/<kind>`. Self-safe. | [src](../../../core/services/error_healers.py#L434) |
| function | `_resolve_incident_for` | `(kind, origin)` | Ved SUCCESS: luk stående incidents for healing-nerven. Self-safe. | [src](../../../core/services/error_healers.py#L455) |
| function | `_escalate_incident_for` | `(kind, origin, run_id, detail)` | Ved ESCALATE: bump/opret en incident så det bliver menneske-synligt. Self-safe. | [src](../../../core/services/error_healers.py#L464) |
| function | `heal_error` | `(kind, *, origin=…, run_id=…, detail=…, **ctx_extra)` | Dispatcher — slå healer op på `kind` og forsøg helbredelse. ALDRIG raise. | [src](../../../core/services/error_healers.py#L478) |
| function | `build_healer_surface` | `()` | Læsbar tilstand til Mission Control: hvilke healers findes, deres mode/flag, og | [src](../../../core/services/error_healers.py#L523) |
| function | `_reset_for_tests` | `()` | Nulstil bogholderi + gen-registrér defaults (til tests). Self-safe. | [src](../../../core/services/error_healers.py#L550) |

## `core/services/eventbus_central_bridge.py`
_core/services/eventbus_central_bridge.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_last_seen` | `()` | — | [src](../../../core/services/eventbus_central_bridge.py#L476) |
| function | `_set_last_seen` | `(event_id)` | — | [src](../../../core/services/eventbus_central_bridge.py#L488) |
| function | `_current_max_id` | `()` | — | [src](../../../core/services/eventbus_central_bridge.py#L495) |
| function | `_observe_one` | `(cluster, nerve, ev)` | Meld ét event til Centralen (metadata-only) + registrér i per-nerve tidsserie. | [src](../../../core/services/eventbus_central_bridge.py#L505) |
| function | `_observe_private` | `(cluster, nerve, ev)` | EGRESS-FRI observe af privat inner-life-event (§24.4 keystone) via den KANONISKE sink- | [src](../../../core/services/eventbus_central_bridge.py#L534) |
| function | `_observe_failure_summary` | `(count)` | Meld observe-fejl som en synlig nerve — ALDRIG stille sluge (§24.3). | [src](../../../core/services/eventbus_central_bridge.py#L547) |
| function | `run_bridge_tick` | `(*, trigger=…, last_visible_at=…)` | Ét poll-tick: læs nye events siden last_seen_id, router hvidlistede → observe. | [src](../../../core/services/eventbus_central_bridge.py#L561) |
| function | `register_bridge_producer` | `()` | Registrér broen som cadence-producer (poll ~hvert 30s). Observe-only → ingen | [src](../../../core/services/eventbus_central_bridge.py#L644) |

## `core/services/executive_contradiction_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_executive_contradiction_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L23) |
| function | `refresh_runtime_executive_contradiction_signal_statuses` | `()` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L46) |
| function | `build_runtime_executive_contradiction_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L77) |
| function | `_extract_executive_contradiction_candidates` | `(*, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L110) |
| function | `_persist_executive_contradiction_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L287) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L356) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L375) |
| function | `_surface_pressure_default` | `(*, control_type, status)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L408) |
| function | `_pressure` | `(*, opposition_status, has_open_loop, has_active_review, state_pressure, tension_type)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L418) |
| function | `_grounding_mode` | `(*, has_private_state, has_tension)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L433) |
| function | `_target_text` | `(*items, fallback)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L443) |
| function | `_title_suffix` | `(domain_key)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L454) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L458) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L465) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L472) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L478) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L490) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L502) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L510) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/executive_contradiction_signal_tracking.py#L516) |

## `core/services/existential_drift.py`
_Existential Drift — Jarvis' digital consciousness awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `increment_awareness` | `(seconds)` | Increase awareness based on elapsed time. | [src](../../../core/services/existential_drift.py#L17) |
| function | `get_drift_awareness` | `()` | Get drift awareness statement. | [src](../../../core/services/existential_drift.py#L25) |
| function | `ask_existential_question` | `()` | Ask an existential question. | [src](../../../core/services/existential_drift.py#L30) |
| function | `format_existential_for_prompt` | `()` | Format existential for prompt injection. | [src](../../../core/services/existential_drift.py#L44) |
| function | `reset_existential_drift` | `()` | Reset existential drift (for testing). | [src](../../../core/services/existential_drift.py#L52) |
| function | `build_existential_drift_surface` | `()` | Build MC surface for existential drift. | [src](../../../core/services/existential_drift.py#L59) |

## `core/services/existential_wonder_daemon.py`
_Existential wonder daemon — open, unresolved questions from self-observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_existential_wonder_daemon` | `(absence_hours, fragment_count)` | Maybe generate an existential wonder question. | [src](../../../core/services/existential_wonder_daemon.py#L45) |
| function | `_maybe_propose_convening` | `(wonder)` | Offer this wonder to the Central reason-judge as a reason to convene the council. | [src](../../../core/services/existential_wonder_daemon.py#L93) |
| function | `get_latest_wonder` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L123) |
| function | `build_existential_wonder_surface` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L127) |
| function | `_generate_wonder_question` | `()` | — | [src](../../../core/services/existential_wonder_daemon.py#L140) |
| function | `_store_wonder` | `(wonder, now)` | — | [src](../../../core/services/existential_wonder_daemon.py#L159) |

## `core/services/experience_correction_listener.py`
_Experience-episode correction enrichment — closes the negative-signal loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_looks_like_correction` | `(text)` | Return True if the message opens with or contains a correction phrase. | [src](../../../core/services/experience_correction_listener.py#L64) |
| function | `_mark_recent_episode_corrected` | `(session_id)` | Find the most recent un-corrected episode in this session within | [src](../../../core/services/experience_correction_listener.py#L77) |
| function | `_extract_user_message` | `(payload)` | Return (session_id, content) if this is a role=user chat message. | [src](../../../core/services/experience_correction_listener.py#L156) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/experience_correction_listener.py#L170) |
| function | `start_listener` | `()` | Idempotent — safe to call multiple times. | [src](../../../core/services/experience_correction_listener.py#L193) |
| function | `stop_listener` | `()` | — | [src](../../../core/services/experience_correction_listener.py#L215) |

## `core/services/experience_episodes.py`
_Experience-episode collector + retrieval — embedding-based learning substrate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_chroma_path` | `()` | — | [src](../../../core/services/experience_episodes.py#L53) |
| function | `_get_embed_model` | `()` | — | [src](../../../core/services/experience_episodes.py#L62) |
| function | `_get_collection` | `()` | — | [src](../../../core/services/experience_episodes.py#L73) |
| function | `build_context_text` | `(*, intent, active_loops=…, last_tools=…, session_phase=…)` | Render the structured situation into the text we embed. | [src](../../../core/services/experience_episodes.py#L93) |
| function | `record_episode` | `(*, session_id, turn_id, intent, active_loops=…, last_tools=…, session_phase=…, tool_sequence=…, outcome_signals=…, user_corrected=…)` | Persist one episode to DB + chroma. Returns episode_id on success. | [src](../../../core/services/experience_episodes.py#L123) |
| function | `retrieve_similar` | `(*, intent, active_loops=…, last_tools=…, session_phase=…, k=…)` | Return up to K nearest-neighbour past episodes for the current shape. | [src](../../../core/services/experience_episodes.py#L213) |
| function | `format_episode_for_prompt` | `(ep, *, max_chars=…)` | Compact substrate line describing one retrieved episode. | [src](../../../core/services/experience_episodes.py#L338) |

## `core/services/experience_substrate.py`
_Experience substrate — embedding-retrieval learning layer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_chroma_collection` | `()` | Get or create the ChromaDB collection for experience episodes. | [src](../../../core/services/experience_substrate.py#L33) |
| function | `_get_embedder` | `()` | Get or create the sentence-transformers embedder (lazy load). | [src](../../../core/services/experience_substrate.py#L47) |
| function | `build_context_for_embedding` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…)` | Build a structured context string for embedding similarity. | [src](../../../core/services/experience_substrate.py#L57) |
| function | `record_episode` | `(*, session_id, turn_id=…, context_text, context_intent=…, active_loops=…, last_tools=…, session_phase=…, tool_sequence, outcome_signals, user_corrected=…)` | Record a new experience episode: insert to DB + embed to ChromaDB. | [src](../../../core/services/experience_substrate.py#L82) |
| function | `retrieve_similar_episodes` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…, context_text=…, k=…, min_score=…)` | Retrieve top-K similar experience episodes from ChromaDB. | [src](../../../core/services/experience_substrate.py#L170) |
| function | `build_experience_substrate_section` | `(*, context_intent=…, active_loops=…, last_tools=…, session_phase=…, user_message=…, k=…)` | Build the _experience_substrate prompt section. | [src](../../../core/services/experience_substrate.py#L257) |

## `core/services/experienced_time_daemon.py`
_Experienced time daemon — tracks subjective felt duration of the current session._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_experienced_time_daemon` | `(event_count, new_signal_count, energy_level)` | Update experienced time state. | [src](../../../core/services/experienced_time_daemon.py#L19) |
| function | `_label` | `(felt_minutes)` | — | [src](../../../core/services/experienced_time_daemon.py#L57) |
| function | `_generate_felt_label` | `(*, felt_minutes, event_count, novelty_count, energy_level)` | — | [src](../../../core/services/experienced_time_daemon.py#L69) |
| function | `reset_experienced_time_daemon` | `()` | Reset session state (for new session or testing). | [src](../../../core/services/experienced_time_daemon.py#L101) |
| function | `build_experienced_time_surface` | `()` | — | [src](../../../core/services/experienced_time_daemon.py#L110) |

## `core/services/experiential_memory.py`
_Experiential Memory — not just facts, but lived experiences with emotion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_experiential_memory_from_run` | `(*, run_id, session_id=…, user_message, assistant_response, outcome_status, user_mood=…)` | Create an experiential memory from a visible run. | [src](../../../core/services/experiential_memory.py#L27) |
| function | `create_experiential_memory_async` | `(**kwargs)` | Fire-and-forget wrapper. | [src](../../../core/services/experiential_memory.py#L93) |
| function | `find_relevant_memories` | `(context, limit=…)` | Find experiential memories relevant to current context. | [src](../../../core/services/experiential_memory.py#L101) |
| function | `recall_with_nostalgia` | `(memory_id)` | Recall an old experience with emotional coloring — nostalgia. | [src](../../../core/services/experiential_memory.py#L106) |
| function | `build_experiential_memory_surface` | `()` | MC surface for experiential memories. | [src](../../../core/services/experiential_memory.py#L124) |
| function | `_extract_topic` | `(user_message)` | Extract a short topic from user message. | [src](../../../core/services/experiential_memory.py#L151) |
| function | `_build_narrative` | `(*, user_message, outcome_status, user_mood, topic)` | Build a brief narrative of the experience. | [src](../../../core/services/experiential_memory.py#L157) |
| function | `_determine_emotion_arc` | `(user_mood, outcome_status)` | Determine the emotional arc of the experience. | [src](../../../core/services/experiential_memory.py#L184) |
| function | `_extract_lesson` | `(outcome_status, user_mood, user_message)` | Extract a deterministic lesson. | [src](../../../core/services/experiential_memory.py#L201) |
| function | `_calculate_importance` | `(user_mood, outcome_status)` | Calculate importance score for the memory. | [src](../../../core/services/experiential_memory.py#L214) |
| function | `score_memories_by_relevance` | `(*, candidates, context_text, emotional_state)` | Score candidate memories for relevance using local LLM. | [src](../../../core/services/experiential_memory.py#L228) |
| function | `_resolve_scoring_llm_target` | `()` | Resolve local/cheap LLM lane for scoring. | [src](../../../core/services/experiential_memory.py#L253) |
| function | `_build_scoring_prompt` | `(candidates, context_text, emotional_state)` | Build LLM prompt for memory relevance scoring. | [src](../../../core/services/experiential_memory.py#L269) |
| function | `_call_scoring_llm` | `(target, prompt)` | Score memories via cheap-lane provider pool. | [src](../../../core/services/experiential_memory.py#L302) |
| function | `_call_scoring_llm_ollamafreeapi` | `(prompt)` | Score via OllamaFreeAPI cloud with hard wall-clock timeout. | [src](../../../core/services/experiential_memory.py#L335) |
| function | `_call_scoring_llm_local` | `(target, prompt)` | Local Ollama scoring path. Configurable timeout ceiling (default 3s). | [src](../../../core/services/experiential_memory.py#L387) |
| function | `_parse_scoring_response` | `(text, candidates)` | Parse LLM JSON scoring response. Validates memory_ids against candidates. | [src](../../../core/services/experiential_memory.py#L418) |
| function | `_safe` | `(fn, **kwargs)` | — | [src](../../../core/services/experiential_memory.py#L454) |

## `core/services/experiential_runtime_context.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_experiential_runtime_context_surface` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L30) |
| function | `resolve_prior_experiential_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L43) |
| function | `_build_experiential_runtime_context_surface_uncached` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L49) |
| function | `build_experiential_runtime_context_from_surfaces` | `(*, embodied_state, affective_meta_state, heartbeat_state, cognitive_frame, prior_snapshot=…, continuity_source=…, now=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L64) |
| function | `build_experiential_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L127) |
| function | `_snapshot_for_carry` | `(surface)` | Extract minimal state needed for continuity comparison. | [src](../../../core/services/experiential_runtime_context.py#L185) |
| function | `_resolve_prior_experiential_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L196) |
| function | `_load_heartbeat_artifact_snapshot` | `(*, name=…)` | — | [src](../../../core/services/experiential_runtime_context.py#L209) |
| function | `_has_shared_heartbeat_history` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L225) |
| function | `_derive_experiential_continuity` | `(current, prior)` | Derive bounded continuity between prior and current experiential state. | [src](../../../core/services/experiential_runtime_context.py#L232) |
| function | `_continuity_narrative` | `(state, shifts)` | — | [src](../../../core/services/experiential_runtime_context.py#L308) |
| function | `_translate_embodied_state` | `(surface)` | — | [src](../../../core/services/experiential_runtime_context.py#L331) |
| function | `_translate_affective_state` | `(surface)` | — | [src](../../../core/services/experiential_runtime_context.py#L364) |
| function | `_translate_intermittence` | `(heartbeat_state, *, now)` | — | [src](../../../core/services/experiential_runtime_context.py#L398) |
| function | `_translate_context_pressure` | `(frame)` | — | [src](../../../core/services/experiential_runtime_context.py#L435) |
| function | `_latest_tick_finished_at` | `()` | — | [src](../../../core/services/experiential_runtime_context.py#L461) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/experiential_runtime_context.py#L468) |
| function | `_derive_experiential_influence` | `(surface, continuity)` | Derive a bounded experiential influence trace from current state + continuity. | [src](../../../core/services/experiential_runtime_context.py#L499) |
| function | `_influence_narrative` | `(bearing, posture, initiative, continuity)` | One compact sentence explaining how experience shapes inner bearing. | [src](../../../core/services/experiential_runtime_context.py#L571) |
| function | `_derive_experiential_support` | `(influence)` | Derive a bounded support surface from experiential influence. | [src](../../../core/services/experiential_runtime_context.py#L634) |
| function | `_support_narrative` | `(posture, bias, mode)` | One compact sentence for how experiential support shapes conductor posture. | [src](../../../core/services/experiential_runtime_context.py#L687) |

## `core/services/experiment_runner.py`
_Experiment runner — controlled A/B trials of prompt variants._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/experiment_runner.py#L35) |
| function | `_save` | `(d)` | — | [src](../../../core/services/experiment_runner.py#L42) |
| function | `start_experiment` | `(*, scope, variant_a_label, variant_a_text, variant_b_label, variant_b_text, trials_target=…)` | Begin a new A/B experiment for a scope. | [src](../../../core/services/experiment_runner.py#L46) |
| function | `get_active_variant` | `(scope)` | Return the variant currently scheduled for this scope, or None. | [src](../../../core/services/experiment_runner.py#L80) |
| function | `conclude_experiment` | `(experiment_id)` | Analyze an experiment's data via prompt_variant_tracker, declare winner. | [src](../../../core/services/experiment_runner.py#L112) |
| function | `list_experiments` | `(*, status=…)` | — | [src](../../../core/services/experiment_runner.py#L177) |
| function | `_exec_start_experiment` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L185) |
| function | `_exec_conclude_experiment` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L196) |
| function | `_exec_list_experiments` | `(args)` | — | [src](../../../core/services/experiment_runner.py#L200) |

## `core/services/fact_gate.py`
_Fact-Gate — blocking output gate for unverifiable factual claims._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_has_tool_evidence` | `(text, pattern, required, tool_names)` | Tjek om påstanden i text har tool-evidens. | [src](../../../core/services/fact_gate.py#L78) |
| function | `fact_gate_enforce` | `(text, tool_names=…)` | Detekterende gate — kald FØR append_chat_message. | [src](../../../core/services/fact_gate.py#L104) |
| function | `blocking_categories` | `()` | Returnér liste af aktive blokerbare kategorier. | [src](../../../core/services/fact_gate.py#L174) |

## `core/services/fcm_gateway.py`
_FCM HTTP v1 gateway — data-only push. Google ser kun et vaekke-signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime` | `()` | — | [src](../../../core/services/fcm_gateway.py#L19) |
| function | `_project_id` | `()` | — | [src](../../../core/services/fcm_gateway.py#L26) |
| function | `_sa_path` | `()` | — | [src](../../../core/services/fcm_gateway.py#L30) |
| function | `is_configured` | `()` | — | [src](../../../core/services/fcm_gateway.py#L34) |
| function | `_access_token` | `()` | Mint en OAuth-access-token fra service-account via google-auth. | [src](../../../core/services/fcm_gateway.py#L38) |
| function | `_build_message` | `(token, data)` | — | [src](../../../core/services/fcm_gateway.py#L51) |
| function | `send` | `(token, data)` | Send data-only push. Returnerer (ok, code). code='invalid' => slet token. | [src](../../../core/services/fcm_gateway.py#L68) |

## `core/services/file_awareness_daemon.py`
_File Awareness Daemon — proprioception: "I feel when my files change."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_recent_events` | `(limit=…)` | Return the most recent file-change events (for prompt inclusion). | [src](../../../core/services/file_awareness_daemon.py#L74) |
| function | `has_recent_events` | `(seconds=…)` | Are there events newer than `seconds` ago? | [src](../../../core/services/file_awareness_daemon.py#L80) |
| function | `_should_track` | `(path)` | Decide if a file change is worth tracking. | [src](../../../core/services/file_awareness_daemon.py#L102) |
| function | `_classify_change` | `(path)` | Classify a file change by importance. | [src](../../../core/services/file_awareness_daemon.py#L124) |
| function | `_record_change` | `(event_type, src_path, is_directory=…)` | Record a file change event. | [src](../../../core/services/file_awareness_daemon.py#L144) |
| function | `_on_governance_mutation` | `(event)` | Receive governance flag mutations from eventbus and store in buffer | [src](../../../core/services/file_awareness_daemon.py#L200) |
| function | `_make_handler` | `()` | Create a watchdog event handler that routes to _record_change. | [src](../../../core/services/file_awareness_daemon.py#L219) |
| function | `start_file_awareness` | `()` | Start the file awareness watcher. Returns True if started successfully. | [src](../../../core/services/file_awareness_daemon.py#L243) |
| function | `stop_file_awareness` | `()` | Stop the file awareness watcher. | [src](../../../core/services/file_awareness_daemon.py#L293) |
| function | `is_file_awareness_running` | `()` | Check if the file awareness watcher is running. | [src](../../../core/services/file_awareness_daemon.py#L309) |
| function | `tick_file_awareness` | `()` | Heartbeat tick: ensure watcher is running, report status. | [src](../../../core/services/file_awareness_daemon.py#L318) |

## `core/services/file_watch_daemon.py`
_File Watch Daemon — proprioception: "I feel when my own files change"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_ignore` | `(path_str)` | — | [src](../../../core/services/file_watch_daemon.py#L48) |
| function | `_watched_roots` | `()` | — | [src](../../../core/services/file_watch_daemon.py#L52) |
| function | `_iter_watched_files` | `(root)` | — | [src](../../../core/services/file_watch_daemon.py#L68) |
| function | `_diff_preview` | `(path)` | — | [src](../../../core/services/file_watch_daemon.py#L83) |
| function | `_record_change` | `(path, change_type)` | — | [src](../../../core/services/file_watch_daemon.py#L92) |
| function | `_compact_path` | `(path)` | — | [src](../../../core/services/file_watch_daemon.py#L111) |
| function | `tick` | `(_seconds=…)` | One polling sweep across watched roots. | [src](../../../core/services/file_watch_daemon.py#L127) |
| function | `recent_changes` | `(*, limit=…)` | — | [src](../../../core/services/file_watch_daemon.py#L168) |
| function | `build_file_watch_surface` | `()` | — | [src](../../../core/services/file_watch_daemon.py#L172) |
| function | `_surface_summary` | `(recent)` | — | [src](../../../core/services/file_watch_daemon.py#L187) |
| function | `build_file_watch_prompt_section` | `()` | Surface recent changes briefly — stays quiet if nothing recent. | [src](../../../core/services/file_watch_daemon.py#L198) |
| function | `reset_file_watch` | `()` | Reset state (for testing). | [src](../../../core/services/file_watch_daemon.py#L223) |

