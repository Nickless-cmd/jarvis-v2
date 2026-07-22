# `core.services.prompt_sections` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/prompt_sections/__init__.py`
_Prompt-sections udskilt fra prompt_contract.py for læselighed._

_(no top-level classes or functions)_

## `core/services/prompt_sections/attention_frame.py`
_Cognitive-frame cache + attention-budget selection for prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `invalidate_cognitive_frame_cache` | `()` | Force next call to rebuild. For tests + heartbeat-driven refresh. | [src](../../../core/services/prompt_sections/attention_frame.py#L28) |
| function | `_cognitive_frame_section` | `()` | Build a compact cognitive frame section for prompt inclusion. | [src](../../../core/services/prompt_sections/attention_frame.py#L35) |
| function | `_micro_cognitive_frame_section` | `()` | Build a micro cognitive frame for compact visible prompts (~150 chars). | [src](../../../core/services/prompt_sections/attention_frame.py#L70) |
| function | `get_last_attention_traces` | `()` | Return the last attention trace summaries for each prompt path. | [src](../../../core/services/prompt_sections/attention_frame.py#L86) |
| function | `_run_budget_selection` | `(*, profile, sections)` | Run budget-controlled section selection. | [src](../../../core/services/prompt_sections/attention_frame.py#L100) |

## `core/services/prompt_sections/capability_markup.py`
_Capability markup parsing — udskilt fra visible_runs.py (Boy Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_capability_call` | `(text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L49) |
| function | `_parse_capability_call_markup` | `(text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L56) |
| function | `_extract_content_after_capability_tag` | `(raw, capability_id)` | Extract markdown/text content after a self-closing capability tag. | [src](../../../core/services/prompt_sections/capability_markup.py#L75) |
| function | `_parse_capability_attrs` | `(attrs_text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L110) |
| function | `_capability_call_state` | `(text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L117) |
| function | `_strip_capability_markup` | `(text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L143) |
| function | `_try_match_tool_text_markup` | `(text)` | Return length of a leading tool-text-markup block, or 0 if no match, | [src](../../../core/services/prompt_sections/capability_markup.py#L149) |
| function | `_strip_tool_call_text_markup` | `(text)` | Non-streaming variant: strip all occurrences from a finished string. | [src](../../../core/services/prompt_sections/capability_markup.py#L204) |
| class | `_CapabilityMarkupBuffer` | `` | Buffer that holds back streaming deltas that may be capability-call markup. | [src](../../../core/services/prompt_sections/capability_markup.py#L244) |
| method | `_CapabilityMarkupBuffer.__init__` | `(self)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L256) |
| method | `_CapabilityMarkupBuffer.feed` | `(self, text)` | Accept new text; return any content safe to send to the client. | [src](../../../core/services/prompt_sections/capability_markup.py#L259) |
| method | `_CapabilityMarkupBuffer.flush` | `(self)` | Return any remaining buffered content (call at end-of-stream). | [src](../../../core/services/prompt_sections/capability_markup.py#L264) |
| method | `_CapabilityMarkupBuffer._drain` | `(self)` | Return sendable prefix, keeping potential markup buffered. | [src](../../../core/services/prompt_sections/capability_markup.py#L272) |
| method | `_CapabilityMarkupBuffer._is_capability_prefix` | `(text)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L320) |
| function | `_visible_text_without_capability_markup` | `(text, *, had_markup)` | — | [src](../../../core/services/prompt_sections/capability_markup.py#L326) |

## `core/services/prompt_sections/causal_alerts.py`
_Causal alerts — surface failure-event chains in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_recent_failures` | `(limit)` | — | [src](../../../core/services/prompt_sections/causal_alerts.py#L35) |
| function | `_format_chain_for_failure` | `(failure_event)` | — | [src](../../../core/services/prompt_sections/causal_alerts.py#L48) |
| function | `causal_alerts_section` | `()` | Build the causal-alerts awareness section. Returns "" if no alerts. | [src](../../../core/services/prompt_sections/causal_alerts.py#L72) |

## `core/services/prompt_sections/causal_narrative.py`
_Causal narrative — surface "how you landed here" in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_recent_anchor` | `()` | Return the most narrative-worthy event in the lookback window. | [src](../../../core/services/prompt_sections/causal_narrative.py#L84) |
| function | `_format_chain` | `(anchor)` | Render the backward chain from anchor as a compact narrative. | [src](../../../core/services/prompt_sections/causal_narrative.py#L109) |
| function | `_fetch_llm_summary` | `()` | Return latest ``narrative.summary`` event payload if fresh, else "". | [src](../../../core/services/prompt_sections/causal_narrative.py#L140) |
| function | `causal_narrative_section` | `()` | Build the causal-narrative awareness section. Returns "" if no anchor. | [src](../../../core/services/prompt_sections/causal_narrative.py#L165) |
| function | `invalidate_cache` | `()` | Force next call to rebuild. Useful in tests. | [src](../../../core/services/prompt_sections/causal_narrative.py#L214) |

## `core/services/prompt_sections/causal_patterns.py`
_Causal patterns — surface recurring (parent_kind → child_kind) flows._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_plumbing` | `(kind)` | — | [src](../../../core/services/prompt_sections/causal_patterns.py#L81) |
| function | `_fetch_patterns` | `()` | Return aggregated (parent_kind, child_kind) pairs over the lookback. | [src](../../../core/services/prompt_sections/causal_patterns.py#L87) |
| function | `_render` | `(patterns)` | — | [src](../../../core/services/prompt_sections/causal_patterns.py#L128) |
| function | `causal_patterns_section` | `()` | Build the recurring-causal-patterns awareness section. ``""`` if none. | [src](../../../core/services/prompt_sections/causal_patterns.py#L141) |
| function | `invalidate_cache` | `()` | Force next call to rebuild. Useful in tests. | [src](../../../core/services/prompt_sections/causal_patterns.py#L167) |

## `core/services/prompt_sections/cross_session_arc.py`
_Cross-session arc — surface recent named conversations as a temporal arc._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_noise_title` | `(title)` | — | [src](../../../core/services/prompt_sections/cross_session_arc.py#L63) |
| function | `_humanize_dt` | `(iso, now)` | Return short Danish relative time for the arc render. | [src](../../../core/services/prompt_sections/cross_session_arc.py#L75) |
| function | `_fetch_recent_arc` | `()` | — | [src](../../../core/services/prompt_sections/cross_session_arc.py#L97) |
| function | `cross_session_arc_section` | `()` | Render last N user-facing sessions as a chronological arc. | [src](../../../core/services/prompt_sections/cross_session_arc.py#L124) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/prompt_sections/cross_session_arc.py#L157) |

## `core/services/prompt_sections/dead_skills.py`
_Dead-skill detector: installed skills never invoked._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dead_skills_section` | `()` | — | [src](../../../core/services/prompt_sections/dead_skills.py#L23) |

## `core/services/prompt_sections/forgetting_nudge.py`
_Forgetting nudge — reminds Jarvis to consider transience during conversation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_conversation_is_substantial` | `(session_id)` | Return True if there are enough user-turns OR brain-writes | [src](../../../core/services/prompt_sections/forgetting_nudge.py#L33) |
| function | `forgetting_nudge_section` | `(session_id=…)` | Return forgetting nudge text when the conversation is substantial. | [src](../../../core/services/prompt_sections/forgetting_nudge.py#L69) |

## `core/services/prompt_sections/heartbeat_sections.py`
_Heartbeat + future-agent + epistemic prompt sections._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_epistemic_layers_line` | `()` | Build compact line summarizing epistemic layer-distribution + wrongness. | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L15) |
| function | `_heartbeat_capability_truth_instruction` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L46) |
| function | `_future_agent_runtime_truth_instruction` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L61) |
| function | `_heartbeat_runtime_truth_instruction` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L75) |
| function | `_heartbeat_living_context_line` | `()` | Add living heartbeat cycle phase + user mood + intermittence + trust-autonomy to heartbeat prompt. | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L209) |
| function | `_lane_identity_clause` | `(lane)` | 0.5 Multi-model identity contract — who is the entity in each lane? | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L511) |
| function | `_heartbeat_due_summary` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L534) |
| function | `_heartbeat_continuity_summary` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L552) |
| function | `_heartbeat_liveness_summary` | `(context)` | — | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L580) |
| function | `_heartbeat_self_knowledge_section` | `()` | Heartbeat self-knowledge collector. | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L599) |
| function | `_heartbeat_private_brain_section` | `(context)` | Build a bounded private brain excerpt for the heartbeat prompt. | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L612) |
| function | `format_journal_for_heartbeat` | `(*, max_words=…)` | Format the latest creative journal entry for awareness-block injection. | [src](../../../core/services/prompt_sections/heartbeat_sections.py#L647) |

## `core/services/prompt_sections/jarvis_brain.py`
_Always-on Jarvis Brain summary injection for prompt_contract._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_approx_tokens` | `(text)` | Crude estimate: ~4 chars per token. Good enough for budget trim. | [src](../../../core/services/prompt_sections/jarvis_brain.py#L12) |
| function | `build_jarvis_brain_section` | `(*, token_budget=…)` | Returnerer summary som markdown-sektion, eller "" hvis intet at vise. | [src](../../../core/services/prompt_sections/jarvis_brain.py#L17) |

## `core/services/prompt_sections/jarvis_brain_facts.py`
_Auto-inject of relevant brain fakta into prompt awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_contentless_greeting` | `(message)` | True hvis beskeden kun er hilsen/pleasantry uden noget emne at være relevant til. | [src](../../../core/services/prompt_sections/jarvis_brain_facts.py#L32) |
| function | `_ceiling_from_session_id` | `(session_id)` | Map session_id → visibility ceiling. | [src](../../../core/services/prompt_sections/jarvis_brain_facts.py#L44) |
| function | `build_brain_facts_section` | `(*, user_message, session_id, top_k=…, threshold=…)` | Return markdown section with top-K relevant fakta, or "" if none. | [src](../../../core/services/prompt_sections/jarvis_brain_facts.py#L87) |

## `core/services/prompt_sections/jarvis_brain_nudge.py`
_Post-web-search nudge — encourages remember_this after Jarvis uses web tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_brain_post_web_nudge` | `(*, recent_tool_messages)` | Returnér nudge-tekst hvis seneste tool-message har URL-indhold, ellers "". | [src](../../../core/services/prompt_sections/jarvis_brain_nudge.py#L24) |

## `core/services/prompt_sections/loop_compliance.py`
_Loop-compliance self-check section._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decision_signal` | `()` | Return (adherence_score, directive) for the loop-nudge decision, or (None, ''). | [src](../../../core/services/prompt_sections/loop_compliance.py#L38) |
| function | `_r2_telemetry_signal` | `()` | Return (heed_rate, surfaced_total, heeded_total) over last 24h. | [src](../../../core/services/prompt_sections/loop_compliance.py#L54) |
| function | `loop_compliance_section` | `()` | Render the compliance self-check when warnings are being ignored. | [src](../../../core/services/prompt_sections/loop_compliance.py#L80) |

## `core/services/prompt_sections/memory_recall.py`
_Memory recall section builder — udskilt fra prompt_contract.py (Boy Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_user_id` | `(session_id=…)` | Resolve user_id eksplicit (recall-sektionerne kører UDEN current_user_id()-kontekst | [src](../../../core/services/prompt_sections/memory_recall.py#L41) |
| function | `_memory_md_lines` | `(user_id=…)` | Cached MEMORY.md-LINJER (kun tekst, ingen embedding → nul cold-start-cost). | [src](../../../core/services/prompt_sections/memory_recall.py#L58) |
| function | `_keywords` | `(text)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L76) |
| function | `_semantic_dedup_lines` | `(lines, threshold=…)` | Drop linjer der semantisk dublerer en TIDLIGERE beholdt linje (samme budskab, | [src](../../../core/services/prompt_sections/memory_recall.py#L84) |
| function | `_is_semantic_dup_of_memory` | `(text, user_id=…)` | True hvis `text` semantisk matcher en MEMORY.md-linje (allerede gemt, anden ordlyd). | [src](../../../core/services/prompt_sections/memory_recall.py#L121) |
| function | `_visible_memory_recall_bundle_section` | `(*, session_id, user_message, compact)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L153) |
| function | `_private_brain_recall_lines` | `(*, limit)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L184) |
| function | `_recent_tool_recall_lines` | `(session_id, *, limit)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L211) |
| function | `_memory_candidate_recall_lines` | `(*, limit, session_id=…)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L247) |
| function | `_clip_line` | `(value, *, limit)` | — | [src](../../../core/services/prompt_sections/memory_recall.py#L307) |

## `core/services/prompt_sections/memory_scoring.py`
_core/services/prompt_sections/memory_scoring.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/prompt_sections/memory_scoring.py#L12) |
| function | `_memory_line_relevance_score` | `(entry, user_message)` | — | [src](../../../core/services/prompt_sections/memory_scoring.py#L16) |
| function | `_heuristic_relevant_memory_entries` | `(entries, *, user_message, max_lines)` | — | [src](../../../core/services/prompt_sections/memory_scoring.py#L81) |
| function | `_merge_ordered_memory_entries` | `(primary, secondary, *, max_lines)` | — | [src](../../../core/services/prompt_sections/memory_scoring.py#L104) |

## `core/services/prompt_sections/pattern_counterfactuals.py`
_Surface pattern-counterfactual hypotheses in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_recent_counterfactuals` | `()` | — | [src](../../../core/services/prompt_sections/pattern_counterfactuals.py#L30) |
| function | `pattern_counterfactuals_section` | `()` | Build awareness section from recent pattern counterfactuals. | [src](../../../core/services/prompt_sections/pattern_counterfactuals.py#L57) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/prompt_sections/pattern_counterfactuals.py#L94) |

## `core/services/prompt_sections/plan_revision_patterns.py`
_Plan-revision pattern analyzer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bucket` | `(reason)` | — | [src](../../../core/services/prompt_sections/plan_revision_patterns.py#L36) |
| function | `plan_revision_patterns_section` | `()` | Surface recurring revision-reason patterns if any cluster ≥ N. | [src](../../../core/services/prompt_sections/plan_revision_patterns.py#L44) |

## `core/services/prompt_sections/pool_status_section.py`
_Pool-status prompt-sektion — så Jarvis ALTID kender forskellen på de to_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pool_status_line` | `()` | Kompakt to-linjers status af de to pools. Self-safe: enhver datakilde-fejl | [src](../../../core/services/prompt_sections/pool_status_section.py#L12) |

## `core/services/prompt_sections/rule_conclusions.py`
_Rule-engine conclusions — symbolic reasoning surfaced to the LLM._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cached_signals` | `()` | — | [src](../../../core/services/prompt_sections/rule_conclusions.py#L55) |
| function | `invalidate_section_cache` | `()` | Force next call to rebuild. Useful for tests + heartbeat-driven refresh. | [src](../../../core/services/prompt_sections/rule_conclusions.py#L66) |
| function | `_format_conclusion` | `(c)` | One line per conclusion: '[urgency:domain ±Δ] suggestion (rule)'. | [src](../../../core/services/prompt_sections/rule_conclusions.py#L76) |
| function | `_build_section_uncached` | `()` | Compute the section fresh. Slow path — should only run via cache miss. | [src](../../../core/services/prompt_sections/rule_conclusions.py#L89) |
| function | `rule_conclusions_section` | `()` | Build the rule-engine conclusions section for prompt injection. | [src](../../../core/services/prompt_sections/rule_conclusions.py#L121) |

## `core/services/prompt_sections/runtime_self_report.py`
_Runtime self-report + self-model prompt sections._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_self_model_signal_tracking_section` | `()` | Bridge to self_model_signal_tracking prompt section in visible chat. | [src](../../../core/services/prompt_sections/runtime_self_report.py#L15) |
| function | `_runtime_resource_signal_section` | `()` | Bridge to runtime_resource_signal in visible support sections. | [src](../../../core/services/prompt_sections/runtime_self_report.py#L32) |
| function | `_runtime_self_report_instruction` | `(*, user_message, runtime_self_report_context)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L48) |
| function | `_self_deception_guard_lines` | `(*, question_gate=…, autonomy_pressure=…, open_loops=…)` | Build self-deception guard constraint lines for the visible prompt. | [src](../../../core/services/prompt_sections/runtime_self_report.py#L174) |
| function | `_visible_self_knowledge_lines` | `()` | Build compact self-knowledge lines for the visible self-report section. | [src](../../../core/services/prompt_sections/runtime_self_report.py#L216) |
| function | `_runtime_self_report_query_profile` | `(user_message)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L267) |
| function | `_runtime_self_report_routing_lines` | `(*, query_profile, open_loop_count, current_runtime_state)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L333) |
| function | `_merge_runtime_self_report_state` | `(*, regulation_state, regulation_pressure, private_tone, private_pressure)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L376) |
| function | `_runtime_awareness_prompt_surface` | `(*, limit)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L390) |
| function | `_should_include_self_report` | `(text)` | — | [src](../../../core/services/prompt_sections/runtime_self_report.py#L412) |

## `core/services/prompt_sections/transcript_sections.py`
_Transcript rendering + session compaction for prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `chat_session_messages_since_last_compact` | `(*args, **kwargs)` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L25) |
| function | `_lifecycle_enabled` | `()` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L30) |
| function | `_cold_floor_for` | `(session_id)` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L38) |
| function | `recent_chat_session_messages` | `(*args, **kwargs)` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L46) |
| function | `recent_chat_session_messages_by_user_turns` | `(*args, **kwargs)` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L51) |
| function | `visible_session_continuity` | `(*args, **kwargs)` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L56) |
| function | `_visible_session_continuity_instruction` | `()` | — | [src](../../../core/services/prompt_sections/transcript_sections.py#L61) |
| function | `_recent_transcript_section` | `(session_id, *, limit, include)` | Legacy flat-text fallback — used only when structured messages are not viable. | [src](../../../core/services/prompt_sections/transcript_sections.py#L116) |
| function | `_resolve_speaker_display` | `(user_id)` | Map a chat_messages.user_id (Discord ID, etc.) to et afsender-præfiks med | [src](../../../core/services/prompt_sections/transcript_sections.py#L169) |
| function | `_build_structured_transcript_messages` | `(session_id, *, limit, include)` | Build structured chat messages from recent transcript. | [src](../../../core/services/prompt_sections/transcript_sections.py#L207) |
| function | `_get_compact_marker_for_transcript` | `(session_id)` | Fetch the most recent compact marker for this session (monkeypatchable). | [src](../../../core/services/prompt_sections/transcript_sections.py#L417) |
| function | `_ground_truth_for` | `(session_id)` | Best-effort VERIFIED-facts block (git HEAD, recent commits, key files) for the session, | [src](../../../core/services/prompt_sections/transcript_sections.py#L454) |
| function | `_make_structured_summariser` | `(focus=…, *, session_id=…)` | Build a summarise_fn(old_messages)->str for compact_session_history. | [src](../../../core/services/prompt_sections/transcript_sections.py#L466) |
| function | `_run_session_compaction` | `(session_id, keep_recent, *, low_water_tokens=…, focus=…)` | Selve summariserings-arbejdet (baggrundstråd). Skriver compact_marker via det | [src](../../../core/services/prompt_sections/transcript_sections.py#L540) |
| function | `_maybe_auto_compact_session` | `(session_id, current_messages, settings)` | Trigger session compact hvis transcript-tokens overstiger tærsklen — i BAGGRUNDEN. | [src](../../../core/services/prompt_sections/transcript_sections.py#L580) |

## `core/services/prompt_sections/workspace_files.py`
_Workspace file section helpers — udskilt fra prompt_contract.py (Boy Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_effective_size` | `(path)` | Byte-størrelse af workspace-fil, encryption-aware. | [src](../../../core/services/prompt_sections/workspace_files.py#L33) |
| function | `_resolve_with_shared_fallback` | `(path)` | Hvis `path` peger på en stub-tynd identitets-fil og shared/<navn> | [src](../../../core/services/prompt_sections/workspace_files.py#L51) |
| function | `_workspace_file_section` | `(path, *, label, max_lines, max_chars)` | — | [src](../../../core/services/prompt_sections/workspace_files.py#L75) |
| function | `_workspace_guidance_section` | `(path, *, label, max_lines, max_chars)` | — | [src](../../../core/services/prompt_sections/workspace_files.py#L103) |
| function | `_ws_exists` | `(path)` | Eksistens-tjek encryption-aware (.enc tæller for member-filer). | [src](../../../core/services/prompt_sections/workspace_files.py#L119) |
| function | `_workspace_optional_file_section` | `(path, *, fallback_path, label, max_lines, max_chars)` | — | [src](../../../core/services/prompt_sections/workspace_files.py#L127) |

