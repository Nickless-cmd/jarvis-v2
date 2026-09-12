# `core.services.07` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/cheap_provider_runtime_keys.py`
_Udbydere hvis ejer-nøgle bor i `runtime.json` — ikke i auth-profil-arkivet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `runtime_owner_key` | `(provider)` | Den delte ejer-nøgle for `provider`, eller "" hvis den ikke findes. | [src](../../../core/services/cheap_provider_runtime_keys.py#L40) |
| function | `has_runtime_owner_key` | `(provider)` | Bruges af readiness. Adskilt fra `runtime_owner_key` så kaldere ikke | [src](../../../core/services/cheap_provider_runtime_keys.py#L59) |

## `core/services/cheap_provider_runtime_selection.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L40) |
| function | `_execute_provider_chat` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L47) |
| function | `provider_runtime_defaults` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L51) |
| function | `record_cheap_provider_invocation` | `(*args, **kwargs)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L55) |
| function | `cheap_lane_status_surface` | `()` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L77) |
| function | `invalidate_cheap_lane_status_cache` | `()` | Force-clear the status-surface and quota caches. | [src](../../../core/services/cheap_provider_runtime_selection.py#L128) |
| function | `test_provider_target` | `(*, provider, model, auth_profile, base_url=…, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L141) |
| function | `smoke_cheap_lane` | `(*, message=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L169) |
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L315) |
| function | `_central_route_shadow` | `()` | Task 9: kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_provider_runtime_selection.py#L319) |
| function | `_central_route_live` | `()` | Task 9: brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_provider_runtime_selection.py#L328) |
| function | `_flag_multiprofile` | `()` | Task 6: yield én kandidat pr. (provider, klar auth-profil) i stedet for kun | [src](../../../core/services/cheap_provider_runtime_selection.py#L337) |
| function | `_flag_profile_roundrobin` | `()` | A (2026-07-24): when multiprofile is on AND a provider has >1 ready auth | [src](../../../core/services/cheap_provider_runtime_selection.py#L348) |
| function | `_roundrobin_profiles` | `(provider, profiles)` | Rotate ``profiles`` by a per-provider counter (PEEK — does not advance) so | [src](../../../core/services/cheap_provider_runtime_selection.py#L367) |
| function | `_advance_profile_rr` | `(provider)` | Advance the round-robin counter for ``provider`` by one — call exactly once | [src](../../../core/services/cheap_provider_runtime_selection.py#L381) |
| function | `_resolve_proxy` | `(egress, endpoints=…)` | Task 8b: map an egress ('home'|'vpn'|'he6') to its proxy endpoint URL. | [src](../../../core/services/cheap_provider_runtime_selection.py#L387) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_provider_runtime_selection.py#L409) |
| function | `_maybe_shadow_compare` | `(old_target)` | Shadow-hook før select returnerer. OFF → no-op, byte-identisk. | [src](../../../core/services/cheap_provider_runtime_selection.py#L426) |
| function | `_maybe_central_route_live` | `(old_target, candidates, kind, skip_providers)` | Task 9 live: når central_route_live er ON henter selection sit pick fra det | [src](../../../core/services/cheap_provider_runtime_selection.py#L438) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L478) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…, lane=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L579) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L738) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L817) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L858) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L907) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1055) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1112) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1129) |
| function | `_record_provider_success` | `(*, provider, model, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1170) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1221) |
| function | `_decode_state_metadata` | `(state)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1287) |
| function | `_rolling_average` | `(*, current_avg, current_count, new_value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1298) |
| function | `_smoke_quality_score` | `(*, expected, actual)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1304) |
| function | `_normalize_probe_text` | `(value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1314) |

## `core/services/cheap_provider_runtime_streaming.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_streaming.py#L24) |
| function | `_iter_openai_compatible_chat_events` | `(*, provider, model, auth_profile, base_url, messages, tools=…, temperature=…, top_p=…, extra_body=…)` | Stream OpenAI-compatible /chat/completions deltas via SSE. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L33) |
| function | `_list_openai_codex_models` | `()` | Static model list for OpenAI Codex (ChatGPT Plus OAuth). | [src](../../../core/services/cheap_provider_runtime_streaming.py#L339) |
| function | `_execute_openai_codex_chat` | `(*, model, auth_profile, base_url, message)` | Execute a chat call via OpenAI's Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L351) |
| function | `_convert_tools_to_responses_format` | `(tools)` | Convert Chat-Completions tool defs to Responses API format. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L504) |
| function | `_iter_openai_codex_chat_events` | `(*, model, auth_profile, base_url, message, tools=…, input_items=…)` | Stream raw SSE events from the OpenAI Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L536) |

## `core/services/child_authority.py`
_Et barn maa ikke laane foraeldrens autoritet — Fase 5._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `uden_foraeldrens_godkendelse` | `()` | Koer barnets arbejde UDEN foraeldrens ejer-godkendelse. | [src](../../../core/services/child_authority.py#L41) |

## `core/services/child_failure_signal.py`
_Et barn der doer, skal kunne SES — Fase 5._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `note_child_ended` | `(agent_id, *, status, role=…, provider=…, model=…, error=…, parent_run_id=…)` | Sig hoejt at et barn endte uden at levere. Kaster ALDRIG. | [src](../../../core/services/child_failure_signal.py#L43) |
| function | `note_from_registry` | `(agent)` | Bekvem indgang naar man allerede har registry-raekken. | [src](../../../core/services/child_failure_signal.py#L92) |

## `core/services/chronicle_consolidation_brief_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_briefs_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_brief_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_brief_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_brief_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_briefs` | `(*, briefs, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, brief)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L326) |
| function | `_brief_type` | `(*, chronicle_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L356) |
| function | `_brief_weight` | `(*, chronicle_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L403) |
| function | `_weight_from_brief_type` | `(brief_type)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_brief_tracking.py#L454) |

## `core/services/chronicle_consolidation_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L30) |
| function | `refresh_runtime_chronicle_consolidation_proposal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L53) |
| function | `build_runtime_chronicle_consolidation_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L84) |
| function | `_extract_chronicle_consolidation_proposal_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L117) |
| function | `_persist_chronicle_consolidation_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L241) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L310) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L326) |
| function | `_proposal_type` | `(*, brief_type, has_remembered_fact, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L356) |
| function | `_proposal_weight` | `(*, brief_weight, contradiction_pressure, has_temporal_promotion)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L366) |
| function | `_grounding_mode` | `(*, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L376) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L392) |
| function | `_focus_title` | `(domain_key)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L399) |
| function | `_canonical_segment` | `(canonical_key, *, index)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L403) |
| function | `_weight_from_proposal_type` | `(proposal_type)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L410) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L419) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L428) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L437) |
| function | `_value` | `(*values, default)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L446) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/chronicle_consolidation_proposal_tracking.py#L454) |

## `core/services/chronicle_consolidation_signal_tracking.py`
_Chronicle/consolidation signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L51) |
| function | `refresh_runtime_chronicle_consolidation_signal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L77) |
| function | `build_runtime_chronicle_consolidation_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L81) |
| function | `_extract_chronicle_consolidation_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L85) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L243) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L262) |
| function | `_chronicle_consolidation_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L300) |
| function | `_chronicle_type` | `(*, cadence_state, promotion_type, has_remembered_fact)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L319) |
| function | `_chronicle_weight` | `(*, cadence_state, has_promotion, contradiction_pressure, outcome_status)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L334) |
| function | `_focus_text` | `(outcome, cadence, *, domain_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L348) |
| function | `_summary_line` | `(*, chronicle_type, chronicle_focus)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L364) |
| function | `_grounding_mode` | `(*, has_private_state, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L370) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L389) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L396) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L403) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L409) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L421) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L432) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L440) |

## `core/services/chronicle_engine.py`
_Chronicle Engine — Jarvis' narrative autobiography that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ChronicleAppraisal` | `` | Structured chronicle context — replaces hardcoded narrative prompts. | [src](../../../core/services/chronicle_engine.py#L36) |
| function | `maybe_write_chronicle_entry` | `()` | Write a chronicle entry if enough time has passed since the last one. | [src](../../../core/services/chronicle_engine.py#L57) |
| function | `compare_self_over_time` | `()` | Temporal self-perception — how have I changed? | [src](../../../core/services/chronicle_engine.py#L208) |
| function | `build_chronicle_surface` | `()` | — | [src](../../../core/services/chronicle_engine.py#L236) |
| function | `get_chronicle_context_for_prompt` | `(n=…, max_chars=…)` | Return recent chronicle entries formatted for prompt injection. | [src](../../../core/services/chronicle_engine.py#L249) |
| function | `_build_appraisal` | `(recent_runs, period, previous_entries=…)` | Build a structured ChronicleAppraisal from raw run data. | [src](../../../core/services/chronicle_engine.py#L295) |
| function | `_build_narrative` | `(recent_runs, period, previous_entries=…)` | Build a chronicle entry narrative, preferring LLM prose. | [src](../../../core/services/chronicle_engine.py#L349) |
| function | `_render_template_narrative` | `(appraisal)` | Render a deterministic fallback narrative from a structured appraisal. | [src](../../../core/services/chronicle_engine.py#L379) |
| function | `_render_narrative_prompt` | `(appraisal)` | Render an LLM narrative prompt from a structured ChronicleAppraisal. | [src](../../../core/services/chronicle_engine.py#L400) |
| function | `_collect_topics` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L448) |
| function | `_sanitize_narrative` | `(text)` | — | [src](../../../core/services/chronicle_engine.py#L468) |
| function | `project_entry_to_markdown` | `(entry)` | — | [src](../../../core/services/chronicle_engine.py#L483) |
| function | `_chronicle_markdown_path` | `()` | — | [src](../../../core/services/chronicle_engine.py#L514) |
| function | `_rotate_chronicle_if_needed` | `(chronicle_path)` | — | [src](../../../core/services/chronicle_engine.py#L518) |
| function | `_coerce_text_list` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L545) |
| function | `_emit_degraded_event` | `(*, period, reason)` | — | [src](../../../core/services/chronicle_engine.py#L560) |
| function | `_extract_key_events` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L570) |
| function | `_extract_lessons` | `(recent_runs)` | — | [src](../../../core/services/chronicle_engine.py#L580) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/chronicle_engine.py#L591) |

## `core/services/claim_scanner.py`
_Claim Scanner — output gate for the Lying Engine (Layer 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_active_time_pin` | `()` | Read the current Time Pin from the prompt contract's cache. | [src](../../../core/services/claim_scanner.py#L69) |
| function | `_extract_time_from_pin` | `(pin_text)` | Extract the 'LIGE NU' timestamp block from a Time Pin section. | [src](../../../core/services/claim_scanner.py#L78) |
| function | `_now_as_pin_string` | `()` | Get current time formatted as the Time Pin would show it. | [src](../../../core/services/claim_scanner.py#L90) |
| function | `_categorize_line` | `(line)` | For a single line of text, return list of (category, matched_text, match). | [src](../../../core/services/claim_scanner.py#L98) |
| function | `_verify_time_claim` | `(matched_text)` | Verify a time claim against the active Time Pin. | [src](../../../core/services/claim_scanner.py#L130) |
| function | `_verify_env_claim` | `(matched_text)` | Verify environment claims — non-trivial, always True for now (future: check tool cache). | [src](../../../core/services/claim_scanner.py#L175) |
| function | `_verify_system_claim` | `(matched_text)` | Verify system claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L180) |
| function | `_verify_stats_claim` | `(matched_text)` | Verify statistic claims against Ground Truth Registry (Layer 3). | [src](../../../core/services/claim_scanner.py#L190) |
| function | `_repair_time_claim` | `(line, matched_text)` | Replace a time claim with the correct time from the Time Pin. | [src](../../../core/services/claim_scanner.py#L210) |
| function | `_is_current_time_claim` | `(line, matched_text)` | True kun hvis linjen EKSPLICIT hævder hvad klokken er lige nu. | [src](../../../core/services/claim_scanner.py#L239) |
| function | `_repair_claim` | `(line, category, matched_text)` | Apply category-specific repair to a line. | [src](../../../core/services/claim_scanner.py#L248) |
| function | `_system_footnote` | `(matched_text)` | 2026-07-06: byg en fodnote for en ⚙️ system-claim (IP/host/path) i den | [src](../../../core/services/claim_scanner.py#L291) |
| function | `_extract_number` | `(text)` | Extract the first number from a string for replacement. | [src](../../../core/services/claim_scanner.py#L307) |
| function | `_commit_exists` | `(h)` | True hvis `h` resolver til et commit i hovedrepoet. Fail-open: ved | [src](../../../core/services/claim_scanner.py#L334) |
| function | `flag_unknown_commit_hashes` | `(text, *, max_check=…)` | Markér backtick-wrappede commit-hashes der ikke findes i hovedrepoet. | [src](../../../core/services/claim_scanner.py#L353) |
| function | `_collect_unknown_commit_hash_footnotes` | `(text, *, max_check=…)` | 2026-07-06: samme detektion som flag_unknown_commit_hashes, men i stedet | [src](../../../core/services/claim_scanner.py#L384) |
| function | `scan_response` | `(text)` | Scan a response text for unverified factual claims and repair them. | [src](../../../core/services/claim_scanner.py#L412) |
| function | `_fabricated_tool_result_footnote` | `(text)` | Kør fabrikations-gaten og gør verdiktet SYNLIGT — uden at dræbe runden. | [src](../../../core/services/claim_scanner.py#L505) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L545) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L553) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L583) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L655) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L723) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L750) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

## `core/services/client_turn_absorb.py`
_client_turn_absorb.py — fyr den fulde post-tur-hjerne for en KLIENT-drevet tur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_do_absorb` | `(run, assistant_response, user_id)` | Synkron post-process-firing (testbar). Kører i user_context så memory/workspace | [src](../../../core/services/client_turn_absorb.py#L23) |
| function | `persist_client_turn` | `(*, session_id, user_message, assistant_response, user_id=…)` | Fase C1 (delte sessioner): persistér en KLIENT-drevet turs beskeder til den DELTE | [src](../../../core/services/client_turn_absorb.py#L45) |
| function | `absorb_client_turn` | `(*, session_id, run_id, user_message, assistant_response, provider=…, model=…, user_id=…, lane=…)` | Konstruér en VisibleRun fra klient-data og fyr post-process i en baggrundstråd | [src](../../../core/services/client_turn_absorb.py#L69) |

## `core/services/client_turn_live.py`
_client_turn_live.py — cross-device live-broadcast for en KLIENT-drevet tur (C2b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `begin_live_turn` | `(*, session_id, run_id, user_message=…, provider=…, model=…, user_id=…)` | Registrér turen som det aktive visible run + åbn run_follow (kun for ægte | [src](../../../core/services/client_turn_live.py#L23) |
| function | `end_live_turn` | `(*, session_id, run_id=…)` | Ryd active-run (kun hvis det stadig er DETTE run — undgå at rydde en efterfølger) | [src](../../../core/services/client_turn_live.py#L66) |

## `core/services/cluster_daemon.py`
_Cluster-daemon primitive — one Central-governed daemon per FAMILY of nerves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `shadow_mode_enabled` | `()` | True when cluster-daemons run in SHADOW (observe-only) mode. | [src](../../../core/services/cluster_daemon.py#L65) |
| class | `ClusterMember` | `` | One function inside a cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L87) |
| class | `ClusterDaemon` | `` | One Central-governed daemon for a FAMILY of member functions. | [src](../../../core/services/cluster_daemon.py#L122) |
| method | `ClusterDaemon._snapshot` | `(self, snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L136) |
| method | `ClusterDaemon._aggregate_signals` | `(self, snapshot)` | Collect every member's signals into ONE namespaced dict for the gate. | [src](../../../core/services/cluster_daemon.py#L148) |
| method | `ClusterDaemon._gate_fires` | `(self, snapshot)` | Run the family's SINGLE event-gate. Fail-OPEN → fire. | [src](../../../core/services/cluster_daemon.py#L167) |
| method | `ClusterDaemon.tick` | `(self, snapshot=…, *, shadow=…)` | Run the family for one heartbeat tick. NEVER raises. | [src](../../../core/services/cluster_daemon.py#L188) |
| method | `ClusterDaemon._report_to_central` | `(self, result, is_shadow)` | Best-effort parity telemetry to the Central trace-sink. Never raises. | [src](../../../core/services/cluster_daemon.py#L242) |
| function | `_somatic_signals` | `(snapshot)` | Somatic member gate-signal: machine pressure (drain + energy band). | [src](../../../core/services/cluster_daemon.py#L308) |
| function | `_somatic_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L320) |
| function | `_experienced_time_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L329) |
| function | `_experienced_time_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L346) |
| function | `_absence_signals` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L355) |
| function | `_absence_observe` | `(snapshot)` | — | [src](../../../core/services/cluster_daemon.py#L366) |
| function | `_collect_somatic_snapshot` | `()` | Gather the somatic family's shared snapshot. | [src](../../../core/services/cluster_daemon.py#L374) |
| function | `_somatic_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L435) |
| function | `_experienced_time_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L440) |
| function | `_absence_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L449) |
| function | `build_somatic_family` | `()` | Construct the somatic/embodiment cluster-daemon (family #1). | [src](../../../core/services/cluster_daemon.py#L463) |
| function | `somatic_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L498) |
| function | `_run_somatic_members` | `(snap, result)` | Run every somatic member UNCONDITIONALLY (no generative gate — they are | [src](../../../core/services/cluster_daemon.py#L505) |
| function | `tick_cluster_somatic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the somatic cluster-daemon family (#1). | [src](../../../core/services/cluster_daemon.py#L522) |
| function | `_iv_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (mirrors the daemons' | [src](../../../core/services/cluster_daemon.py#L601) |
| function | `_collect_innervoice_snapshot` | `()` | Gather the inner-voice family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L609) |
| function | `_iv_thought_stream_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L696) |
| function | `_iv_reflection_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L704) |
| function | `_iv_meta_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L712) |
| function | `_iv_irony_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L720) |
| function | `_iv_wonder_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L727) |
| function | `_iv_drift_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L737) |
| function | `_iv_thought_stream_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L748) |
| function | `_iv_reflection_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L757) |
| function | `_iv_meta_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L771) |
| function | `_iv_irony_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L789) |
| function | `_iv_wonder_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L794) |
| function | `_iv_drift_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L803) |
| function | `_iv_surface_observe` | `(builder_path, keys)` | — | [src](../../../core/services/cluster_daemon.py#L811) |
| function | `build_innervoice_family` | `()` | Construct the inner-voice cluster-daemon (family #2), LIVE. | [src](../../../core/services/cluster_daemon.py#L823) |
| function | `innervoice_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L899) |
| function | `tick_cluster_innervoice` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the inner-voice cluster-daemon family. | [src](../../../core/services/cluster_daemon.py#L906) |
| function | `_affect_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state (no hash randomisation). | [src](../../../core/services/cluster_daemon.py#L980) |
| function | `_collect_affect_snapshot` | `()` | Gather the affect family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L987) |
| function | `_affect_surprise_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1071) |
| function | `_affect_conflict_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1078) |
| function | `_affect_desire_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1087) |
| function | `_affect_surprise_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1099) |
| function | `_affect_conflict_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1108) |
| function | `_affect_desire_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1113) |
| function | `build_affect_family` | `()` | Construct the affect cluster-daemon (family #3), LIVE. | [src](../../../core/services/cluster_daemon.py#L1118) |
| function | `affect_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1166) |
| function | `_run_affect_nonllm_members` | `(snap, result)` | Run the NON-LLM affect members UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon.py#L1173) |
| function | `tick_cluster_affect` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the affect cluster-daemon family (#3). | [src](../../../core/services/cluster_daemon.py#L1211) |
| function | `_narrative_no_signals` | `(_snap)` | No gate signals — this family is TIME-BASED, not event-gated. Declaring | [src](../../../core/services/cluster_daemon.py#L1287) |
| function | `_narrative_development_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1296) |
| function | `_narrative_summary_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1301) |
| function | `_narrative_identity_drift_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1306) |
| function | `_narrative_identity_sketch_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1311) |
| function | `_narrative_consolidation_judge_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1316) |
| function | `build_narrative_family` | `()` | Construct the narrative/self-history cluster-daemon (family #4), LIVE. | [src](../../../core/services/cluster_daemon.py#L1321) |
| function | `narrative_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1388) |
| function | `_run_narrative_members` | `(snap, result)` | Run every narrative member UNCONDITIONALLY (no event-gate — time-based), | [src](../../../core/services/cluster_daemon.py#L1395) |
| function | `tick_cluster_narrative` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the narrative cluster-daemon family (#4). | [src](../../../core/services/cluster_daemon.py#L1414) |
| function | `_collect_cognition_snapshot` | `()` | Gather the cognition family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon.py#L1494) |
| function | `_cog_pattern_cf_signals` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1516) |
| function | `_cog_pattern_cf_observe` | `(snap)` | — | [src](../../../core/services/cluster_daemon.py#L1523) |
| function | `_cog_pattern_cf_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1527) |
| function | `build_cognition_family` | `()` | Construct the cognition cluster-daemon (family #5), LIVE. | [src](../../../core/services/cluster_daemon.py#L1532) |
| function | `cognition_family` | `()` | — | [src](../../../core/services/cluster_daemon.py#L1558) |
| function | `_cog_causal_inference_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1568) |
| function | `_cog_active_sensing_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon.py#L1573) |
| function | `_cog_dream_insight_live` | `(_snap)` | dream_insight is signal-driven (not a timer): gather the latest dream- | [src](../../../core/services/cluster_daemon.py#L1578) |
| function | `_cog_autonomous_council_live` | `(_snap)` | Spontan selv-udloest raadsdeliberation via signal-scoring. Self-throttler | [src](../../../core/services/cluster_daemon.py#L1597) |
| function | `_run_cognition_nonllm_members` | `(snap, result)` | Run the NON-LLM cognition members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon.py#L1616) |
| function | `tick_cluster_cognition` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the cognition cluster-daemon family (#5). | [src](../../../core/services/cluster_daemon.py#L1632) |

## `core/services/cluster_daemon_families.py`
_Cluster-daemon FAMILIES — the second file of consolidated nerve-families._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_collect_memory_snapshot` | `()` | Gather the memory family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L81) |
| function | `_mem_council_signals` | `(snap)` | council_memory gate signal: how much council history there is to weigh. | [src](../../../core/services/cluster_daemon_families.py#L111) |
| function | `_mem_council_live` | `(snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L117) |
| function | `build_memory_family` | `()` | Construct the memory/maintenance cluster-daemon (family #6), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L122) |
| function | `memory_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L152) |
| function | `_mem_decay_live` | `(_snap)` | Daily decay + re-discovery. Replicates the old heartbeat influence site: | [src](../../../core/services/cluster_daemon_families.py#L164) |
| function | `_mem_pruning_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L182) |
| function | `_mem_maintenance_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L187) |
| function | `_mem_safeguard_live` | `(_snap)` | The safeguard daemon exposes ``run()`` (its old heartbeat site imported a | [src](../../../core/services/cluster_daemon_families.py#L192) |
| function | `_mem_selective_consolidation_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L200) |
| function | `_mem_associative_recall_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L205) |
| function | `_mem_write_queue_live` | `(_snap)` | LOAD-BEARING + FREQUENT — drains the deferred write queue every 120s. | [src](../../../core/services/cluster_daemon_families.py#L210) |
| function | `_run_memory_nonllm_members` | `(snap, result)` | Run the NON-LLM maintenance members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon_families.py#L229) |
| function | `tick_cluster_memory` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the memory/maintenance cluster-daemon family (#6). | [src](../../../core/services/cluster_daemon_families.py#L245) |
| function | `_feed_aesthetic_choice` | `()` | Record the latest visible run's style/mode into the taste daemon. | [src](../../../core/services/cluster_daemon_families.py#L314) |
| function | `_collect_aesthetic_snapshot` | `()` | Gather the aesthetic family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L344) |
| function | `_aesthetic_taste_signals` | `(snap)` | aesthetic_taste gate signals: how much taste-evidence has accumulated. | [src](../../../core/services/cluster_daemon_families.py#L379) |
| function | `_aesthetic_taste_live` | `(_snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L394) |
| function | `build_aesthetic_family` | `()` | Construct the aesthetic/curiosity cluster-daemon (family #7), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L405) |
| function | `aesthetic_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L435) |
| function | `_aesthetic_curiosity_live` | `(snap)` | Rules-based gap scan over the thought-stream fragment buffer. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L447) |
| function | `_aesthetic_code_aesthetic_live` | `(_snap)` | Ugentlig aestetisk refleksion over kodebasen. Self-throttler INTERNT | [src](../../../core/services/cluster_daemon_families.py#L458) |
| function | `_run_aesthetic_nonllm_members` | `(snap, result)` | Run the NON-LLM member(s) UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon_families.py#L475) |
| function | `tick_cluster_aesthetic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the aesthetic/curiosity cluster-daemon family (#7). | [src](../../../core/services/cluster_daemon_families.py#L490) |
| function | `_collect_relation_snapshot` | `()` | Gather the relation family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L571) |
| function | `_relation_user_model_signals` | `(snap)` | user_model gate signals: how much (and what shape of) user interaction has | [src](../../../core/services/cluster_daemon_families.py#L613) |
| function | `_relation_user_model_live` | `(snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L628) |
| function | `build_relation_family` | `()` | Construct the relation cluster-daemon (family #8), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L641) |
| function | `relation_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L671) |
| function | `_relation_comm_guard_live` | `(_snap)` | Godnat-split guard: sweep expired TTL communication-triggers + log active | [src](../../../core/services/cluster_daemon_families.py#L683) |
| function | `_relation_map_refresh_live` | `(_snap)` | Refresh the relation map (primary last_seen + stale secondary ToM stamps). | [src](../../../core/services/cluster_daemon_families.py#L691) |
| function | `_run_relation_nonllm_members` | `(snap, result)` | Run the NON-LLM members UNCONDITIONALLY (independent of the family generative | [src](../../../core/services/cluster_daemon_families.py#L708) |
| function | `tick_cluster_relation` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the relation cluster-daemon family (#8). | [src](../../../core/services/cluster_daemon_families.py#L724) |
| function | `_projects_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L812) |
| function | `_collect_projects_snapshot` | `()` | Gather the projects family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L830) |
| function | `build_projects_family` | `()` | Construct the projects/work-execution cluster-daemon (family #9), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L850) |
| function | `projects_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L872) |
| function | `_projects_task_worker_live` | `(_snap)` | LOAD-BEARING + EVERY TICK — drain up to 3 queued runtime_tasks. NO throttle: | [src](../../../core/services/cluster_daemon_families.py#L884) |
| function | `_projects_my_projects_live` | `(_snap)` | Restart Jarvis' dead background processes. Rules-based, no LLM. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L892) |
| function | `_projects_life_reassessment_live` | `(_snap)` | Re-assess active life projects; publish reassessment_due for stale ones. | [src](../../../core/services/cluster_daemon_families.py#L902) |
| function | `_projects_thought_action_live` | `(snap)` | Classify the latest thought-stream fragment into an action-proposal. Rules- | [src](../../../core/services/cluster_daemon_families.py#L913) |
| function | `_run_projects_unconditional` | `(snap, result)` | Run every projects member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L937) |
| function | `tick_cluster_projects` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the projects/work-execution cluster-daemon family (#9). | [src](../../../core/services/cluster_daemon_families.py#L953) |
| function | `_infra_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L1099) |
| function | `_collect_infra_snapshot` | `()` | Gather the infra family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L1118) |
| function | `build_infra_family` | `()` | Construct the infra/maintenance cluster-daemon (family #10), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L1129) |
| function | `infra_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L1154) |
| function | `_infra_file_awareness_live` | `(_snap)` | Ensure the file-awareness watcher thread is running (tamper detection). | [src](../../../core/services/cluster_daemon_families.py#L1166) |
| function | `_infra_cache_maintenance_live` | `(_snap)` | 6h web_cache cleanup. Rules-based, no LLM. Self-throttles INTERNALLY | [src](../../../core/services/cluster_daemon_families.py#L1175) |
| function | `_infra_signal_decay_live` | `(_snap)` | Archive+delete stale signals + refresh signal runtime statuses. Rules-based, | [src](../../../core/services/cluster_daemon_families.py#L1183) |
| function | `_infra_wakeup_cleanup_live` | `(_snap)` | Prune stale consumed/cancelled/fired wakeups. Rules-based, no LLM. Self- | [src](../../../core/services/cluster_daemon_families.py#L1191) |
| function | `_infra_cost_optimization_live` | `(_snap)` | Monitor daily/weekly spend vs budget; emit cost.* events. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1201) |
| function | `_infra_ground_truth_live` | `(_snap)` | Refresh the Ground-Truth Registry cache (Lying Engine, Lag 3). Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1211) |
| function | `_infra_mail_checker_live` | `(_snap)` | Poll IMAP for new mail; publish events for unseen messages. Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1222) |
| function | `_infra_visual_memory_live` | `(_snap)` | Webcam snapshot + LOCAL ollama vision-model description (Lag 6, 0 API tokens). | [src](../../../core/services/cluster_daemon_families.py#L1232) |
| function | `_infra_provider_autodiscovery_live` | `(_snap)` | Dagligt /models-scan af alle providers → nye modeller til pending_models. | [src](../../../core/services/cluster_daemon_families.py#L1247) |
| function | `_infra_approval_expiry_live` | `(_snap)` | Markér udløbne, ikke-besluttede godkendelser. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1259) |
| function | `_run_infra_unconditional` | `(snap, result)` | Run every infra member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L1286) |
| function | `tick_cluster_infra` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the infra/maintenance cluster-daemon family (#10). | [src](../../../core/services/cluster_daemon_families.py#L1303) |

## `core/services/cluster_family_scheduler.py`
_Cluster-familiernes egen løkke — tråden der spørger «hvilken familie er det tid til?»_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_running` | `()` | Lever tråden? Siger intet om hvorvidt den udretter noget — se iterations(). | [src](../../../core/services/cluster_family_scheduler.py#L70) |
| function | `iterations` | `()` | Gennemløb siden start. Står tallet stille, er løkken væk. | [src](../../../core/services/cluster_family_scheduler.py#L75) |
| function | `stop_event` | `()` | — | [src](../../../core/services/cluster_family_scheduler.py#L80) |
| function | `_enabled` | `()` | Kill-switch. Self-safe: kan config ikke læses, kører vi videre. | [src](../../../core/services/cluster_family_scheduler.py#L84) |
| function | `_tick_functions` | `()` | Slå familiernes tick-funktioner op. De bor i to moduler efter en udskillelse. | [src](../../../core/services/cluster_family_scheduler.py#L93) |
| function | `_is_due` | `(family, cadence_minutes, last_run_at)` | Er familien forfalden efter sin egen kadence? | [src](../../../core/services/cluster_family_scheduler.py#L114) |
| function | `run_due_families` | `()` | Kør de familier der er forfaldne. Returnerer hvad der skete — også til test. | [src](../../../core/services/cluster_family_scheduler.py#L130) |
| function | `_loop` | `()` | — | [src](../../../core/services/cluster_family_scheduler.py#L177) |
| function | `start` | `()` | Start løkken. Kører den allerede, sker der ingenting. | [src](../../../core/services/cluster_family_scheduler.py#L211) |
| function | `stop` | `()` | — | [src](../../../core/services/cluster_family_scheduler.py#L226) |
| function | `build_cluster_family_scheduler_surface` | `()` | Hvad løkken laver — til Central og til at svare på «kører de?». | [src](../../../core/services/cluster_family_scheduler.py#L236) |

## `core/services/code_aesthetic_daemon.py`
_Code aesthetic daemon — weekly aesthetic reflection on the codebase._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_code_aesthetic_daemon` | `()` | Run aesthetic analysis if cadence elapsed. Returns {generated, reflection}. | [src](../../../core/services/code_aesthetic_daemon.py#L39) |
| function | `get_latest_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L64) |
| function | `build_code_aesthetic_surface` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L68) |
| function | `_get_recent_git_changes` | `()` | Get last 10 commit messages and changed file summary. | [src](../../../core/services/code_aesthetic_daemon.py#L81) |
| function | `_generate_aesthetic_reflection` | `()` | — | [src](../../../core/services/code_aesthetic_daemon.py#L101) |
| function | `_store_reflection` | `(reflection, now)` | — | [src](../../../core/services/code_aesthetic_daemon.py#L119) |

## `core/services/cognitive_architecture_surface.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_cognitive_architecture_surface` | `()` | Cached MC/self-model cognitive-architecture-surface. Self-safe → falder til fersk build. | [src](../../../core/services/cognitive_architecture_surface.py#L11) |
| function | `_build_cognitive_architecture_surface_uncached` | `()` | Build a shared cognitive architecture surface for MC and self-model. | [src](../../../core/services/cognitive_architecture_surface.py#L23) |

## `core/services/cognitive_chronicle.py`
_Cognitive Chronicle — user-scoped read layer for chronicle entries._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `query_chronicle_for_user` | `(limit=…)` | Return chronicle entries visible to the current user. | [src](../../../core/services/cognitive_chronicle.py#L15) |

## `core/services/cognitive_core_experiments.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe_build` | `(builder, system_id, label)` | Call a builder function, returning a disabled-stub on any error. | [src](../../../core/services/cognitive_core_experiments.py#L6) |
| function | `build_cognitive_core_experiments_surface` | `()` | Build shared runtime truth for the bounded cognitive-core experiment state. | [src](../../../core/services/cognitive_core_experiments.py#L31) |
| function | `_build_recurrence_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L100) |
| function | `_build_global_workspace_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L127) |
| function | `_build_hot_meta_cognition_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L155) |
| function | `_build_surprise_afterimage_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L182) |
| function | `_build_attention_blink_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L212) |
| function | `_activity_state` | `(*, enabled, active)` | — | [src](../../../core/services/cognitive_core_experiments.py#L239) |
| function | `_strongest_carry_item` | `(items)` | — | [src](../../../core/services/cognitive_core_experiments.py#L247) |

## `core/services/cognitive_episodes.py`
_Cognitive episodes as an active learning primitive._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_episode` | `(*, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Persist a cognitive episode and publish an eventbus signal. | [src](../../../core/services/cognitive_episodes.py#L25) |
| function | `record_visible_run_episode` | `(*, run_id, session_id=…, provider=…, model=…, status=…, user_message=…, assistant_text=…, error=…)` | Record a post-run episode grounded in the visible-run event trail. | [src](../../../core/services/cognitive_episodes.py#L178) |
| function | `derive_episode_fields` | `(*, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Derive the five cognitive dimensions plus next-behavior policy. | [src](../../../core/services/cognitive_episodes.py#L211) |
| function | `build_cognitive_episode_surface` | `(*, limit=…)` | Return active directives for the conductor/prompt path. | [src](../../../core/services/cognitive_episodes.py#L297) |
| function | `build_cognitive_episode_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/cognitive_episodes.py#L327) |
| function | `_tool_names_for_run` | `(run_id)` | — | [src](../../../core/services/cognitive_episodes.py#L343) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/cognitive_episodes.py#L370) |
| function | `_summarize_visible_run` | `(*, status, tool_names, assistant_text, error)` | — | [src](../../../core/services/cognitive_episodes.py#L389) |
| function | `_fallback_summary` | `(*, status, tool_names, error)` | — | [src](../../../core/services/cognitive_episodes.py#L400) |
| function | `_confidence` | `(*, status, error, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L408) |
| function | `_uncertainty_sources` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L418) |
| function | `_self_check` | `(*, status, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L437) |
| function | `_what_would_change_mind` | `(*, interrupted, proposal_error)` | — | [src](../../../core/services/cognitive_episodes.py#L447) |
| function | `_salience` | `(*, interrupted, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L455) |
| function | `_attention_directive` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L463) |
| function | `_ignore_or_defer` | `(*, tool_heavy, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L481) |
| function | `_learning_lesson` | `(*, interrupted, proposal_error, status, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L489) |
| function | `_policy_update` | `(*, interrupted, proposal_error, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L507) |
| function | `_social_directive` | `(*, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L517) |
| function | `_user_state_hypothesis` | `(*, user_l, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L523) |
| function | `_perception_directive` | `(*, tool_names, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L533) |
| function | `_observed_changes` | `(*, tool_names, status, error)` | — | [src](../../../core/services/cognitive_episodes.py#L541) |
| function | `_next_behavior` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy, status)` | — | [src](../../../core/services/cognitive_episodes.py#L550) |
| function | `_prompt_priority` | `(*, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L571) |

## `core/services/cognitive_state_assembly.py`
_Cognitive state assembly — closes the loop between accumulated state and visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cognitive_cache_key` | `(mode_key)` | — | [src](../../../core/services/cognitive_state_assembly.py#L68) |
| function | `_cache_ttl_seconds` | `()` | Read TTL from settings; default 120s. TTL=0 disables caching. | [src](../../../core/services/cognitive_state_assembly.py#L72) |
| function | `_cache_enabled` | `()` | Check if caching is enabled in settings. TTL=0 also disables. | [src](../../../core/services/cognitive_state_assembly.py#L82) |
| function | `_build_invalidation_snapshot` | `()` | Snapshot the key state signals that invalidate the cache. | [src](../../../core/services/cognitive_state_assembly.py#L94) |
| function | `_is_cache_valid` | `(cache_key)` | Check if cached state for `mode_key` (e.g. 'full') is fresh+coherent. | [src](../../../core/services/cognitive_state_assembly.py#L129) |
| function | `_get_cached_state` | `(cache_key)` | Return cached cognitive state string if valid, None otherwise. | [src](../../../core/services/cognitive_state_assembly.py#L145) |
| function | `_set_cached_state` | `(cache_key, text, sources)` | Store assembled cognitive state in shared_cache (cross-worker). | [src](../../../core/services/cognitive_state_assembly.py#L193) |
| function | `invalidate_cognitive_state_cache` | `()` | Explicitly invalidate all cognitive state caches across workers. | [src](../../../core/services/cognitive_state_assembly.py#L227) |
| function | `get_cognitive_state_cache_status` | `()` | Return cache status for MC transparency. | [src](../../../core/services/cognitive_state_assembly.py#L242) |
| function | `build_cognitive_state_for_prompt` | `(*, compact=…, force=…)` | Build the [COGNITIVE STATE] section for visible chat prompt injection. | [src](../../../core/services/cognitive_state_assembly.py#L295) |
| function | `build_cognitive_state_injection_surface` | `()` | MC surface showing exactly what was injected into the last visible prompt. | [src](../../../core/services/cognitive_state_assembly.py#L1024) |
| function | `_safe_call` | `(fn)` | Call a DB function, return None on any error. | [src](../../../core/services/cognitive_state_assembly.py#L1044) |
| function | `_safe_json` | `(value)` | Parse JSON string or return dict/list directly. | [src](../../../core/services/cognitive_state_assembly.py#L1053) |
| function | `_appraisal_record` | `(*, kind, state, evidence, allowed_effects, confidence, ttl_minutes=…)` | Structured truth record for optional narrative rendering. | [src](../../../core/services/cognitive_state_assembly.py#L1068) |
| function | `_build_cognitive_core_experiment_state_line` | `(*, compact)` | Build a bounded cognitive-state line for mainline experiment carry. | [src](../../../core/services/cognitive_state_assembly.py#L1093) |
| function | `_safe_cognitive_core_experiments_surface` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1157) |
| function | `_safe_cognitive_experiment_carry_frame` | `()` | — | [src](../../../core/services/cognitive_state_assembly.py#L1168) |
| function | `_narrativize_embodied_state` | `()` | LLM-narrativize current embodied state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1180) |
| function | `_narrativize_affective_state` | `()` | LLM-narrativize current affective meta state into a felt-experience line. | [src](../../../core/services/cognitive_state_assembly.py#L1237) |
| function | `_narrativize_self_anchor` | `()` | LLM-narrativize the [SELF] ownership line from real personality state. | [src](../../../core/services/cognitive_state_assembly.py#L1290) |
| function | `_narrativize_boundary` | `()` | LLM-narrativize boundary awareness from real runtime context. | [src](../../../core/services/cognitive_state_assembly.py#L1339) |

## `core/services/cognitive_state_narrativizer.py`
_LLM-based narrativizer for cognitive state lines._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_narrativizer_llm` | `(system_prompt, user_message)` | Call the compact LLM (heartbeat model) for narrative line generation. | [src](../../../core/services/cognitive_state_narrativizer.py#L44) |
| class | `_CachedNarrative` | `` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L101) |
| function | `_fingerprint` | `(state)` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L114) |
| function | `_generate_in_background` | `(*, line_key, fingerprint, system_prompt, user_message)` | Run the LLM call in a background thread and update cache. | [src](../../../core/services/cognitive_state_narrativizer.py#L119) |
| function | `narrativize_line` | `(*, line_key, state, system_prompt, user_message_builder, fallback=…)` | Return an LLM-narrativized line for this state, or fallback. | [src](../../../core/services/cognitive_state_narrativizer.py#L151) |
| function | `cache_snapshot` | `()` | Expose current cache state for MC observability. | [src](../../../core/services/cognitive_state_narrativizer.py#L228) |

## `core/services/collective_pulse_daemon.py`
_Collective Pulse — what is the air full of right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L43) |
| function | `_collective_dir` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L47) |
| function | `_load` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L51) |
| function | `_save` | `(data)` | — | [src](../../../core/services/collective_pulse_daemon.py#L67) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/collective_pulse_daemon.py#L79) |
| function | `_gather_week_text` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L86) |
| function | `_week_mood_trajectory` | `()` | Average mood over the week, if mood samples are available. | [src](../../../core/services/collective_pulse_daemon.py#L123) |
| function | `_describe_zeitgeist` | `(top_terms, mood_info)` | — | [src](../../../core/services/collective_pulse_daemon.py#L142) |
| function | `_write_weekly_note` | `(pulse)` | — | [src](../../../core/services/collective_pulse_daemon.py#L156) |
| function | `run_pulse` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L192) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/collective_pulse_daemon.py#L233) |
| function | `build_collective_pulse_surface` | `()` | — | [src](../../../core/services/collective_pulse_daemon.py#L246) |
| function | `_surface_summary` | `(latest)` | — | [src](../../../core/services/collective_pulse_daemon.py#L259) |
| function | `build_collective_pulse_prompt_section` | `()` | Surface the week's zeitgeist while it's still current (within 7 days). | [src](../../../core/services/collective_pulse_daemon.py#L266) |

## `core/services/commit_attribution.py`
_Canonical, audit-only attribution metadata for Git commit messages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActorRule` | `` | Stable actor type and the origins that actor may claim. | [src](../../../core/services/commit_attribution.py#L28) |
| class | `CommitAttribution` | `` | The six required audit fields stored in a commit trailer block. | [src](../../../core/services/commit_attribution.py#L36) |
| method | `CommitAttribution.as_trailers` | `(self)` | — | [src](../../../core/services/commit_attribution.py#L46) |
| class | `AttributionError` | `` | Raised when attribution cannot satisfy the commit contract. | [src](../../../core/services/commit_attribution.py#L57) |
| function | `new_manual_run_id` | `(now=…, suffix=…)` | Return a sortable id for a commit without an existing runtime run. | [src](../../../core/services/commit_attribution.py#L69) |
| function | `parse_git_trailers` | `(message)` | Parse the final trailer block with Git's own trailer semantics. | [src](../../../core/services/commit_attribution.py#L85) |
| function | `validate_trailers` | `(trailers)` | Validate parsed trailers without reading process or repository state. | [src](../../../core/services/commit_attribution.py#L106) |
| function | `validate_commit_message` | `(message)` | Return every attribution error in a complete commit message. | [src](../../../core/services/commit_attribution.py#L159) |
| function | `_split_final_trailer_block` | `(message)` | — | [src](../../../core/services/commit_attribution.py#L165) |
| function | `render_attributed_message` | `(message, attribution)` | Replace managed trailers and return a deterministic commit message. | [src](../../../core/services/commit_attribution.py#L180) |

## `core/services/commit_gate_arbiter.py`
_Pre-eksekverings commit-gate arbitrage — udskilt fra visible_runs (Boy Scout, 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CommitGateOutcome` | `` | Udfald af commit-gate-arbitrage. ``blocked`` → værktøjet må ikke køre; ``soft_warn`` → | [src](../../../core/services/commit_gate_arbiter.py#L21) |
| function | `evaluate_commit_gates` | `(*, name, arguments, user_message, session_id, run_id)` | Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér | [src](../../../core/services/commit_gate_arbiter.py#L30) |

## `core/services/communication_guard.py`
_Communication guard — scanner assistant-output for boundary violations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_hard` | `(trigger)` | Er denne trigger en HÅRD blok (afvis besked før send) eller blød | [src](../../../core/services/communication_guard.py#L143) |
| function | `_load` | `()` | — | [src](../../../core/services/communication_guard.py#L160) |
| function | `_save` | `(triggers)` | — | [src](../../../core/services/communication_guard.py#L172) |
| function | `add_trigger` | `(phrase, *, kind=…, reason=…, ttl_turns=…, ttl_hours=…)` | Tilfoj en triggerfrase til guarden. | [src](../../../core/services/communication_guard.py#L177) |
| function | `remove_trigger` | `(phrase)` | Fjern en triggerfrase. Returner True hvis den blev fjernet. | [src](../../../core/services/communication_guard.py#L224) |
| function | `scan` | `(text)` | Skan en tekst for triggerfraser. | [src](../../../core/services/communication_guard.py#L235) |
| function | `_trigger_active` | `(t, now)` | Er en trigger aktiv lige nu (permanent, eller TTL ikke udløbet)? | [src](../../../core/services/communication_guard.py#L282) |
| function | `enforce_outgoing` | `(text)` | Hård-gate for udga°ende assistant-tekst — kaldes FØR afsendelse. | [src](../../../core/services/communication_guard.py#L299) |
| function | `record_breach` | `(channel, removed, *, original=…)` | Log en boundary-breach (hård frase fanget ved kanal-dispatch). | [src](../../../core/services/communication_guard.py#L350) |
| function | `guard_channel_text` | `(text, channel)` | Convenience for kanal-dispatch: scrub hård afslutnings-fraser fra | [src](../../../core/services/communication_guard.py#L374) |
| function | `_active_hard_phrases` | `(now)` | — | [src](../../../core/services/communication_guard.py#L394) |
| function | `scrub_outgoing` | `(text)` | Kanal-backstop: fjern den SÆTNING/linje der indeholder en hård | [src](../../../core/services/communication_guard.py#L402) |
| function | `prompt_section` | `()` | Bygger en høj-salient påmindelse til system-prompten med de aktive | [src](../../../core/services/communication_guard.py#L433) |
| function | `consume_turn` | `()` | Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver | [src](../../../core/services/communication_guard.py#L467) |
| function | `cleanup_expired` | `()` | Rens udloebne TTL-triggers og triggers med ttl_turns <= 0. | [src](../../../core/services/communication_guard.py#L485) |
| function | `_safe_parse_iso` | `(s, now)` | — | [src](../../../core/services/communication_guard.py#L510) |
| function | `list_triggers` | `()` | Returner alle aktive triggers. | [src](../../../core/services/communication_guard.py#L519) |
| function | `active_count` | `()` | Antal aktive triggerfraser (permanente + ikke-udloebne TTL). | [src](../../../core/services/communication_guard.py#L524) |

## `core/services/communication_guard_daemon.py`
_Communication guard daemon — vedligeholder TTL-rydning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_communication_guard_daemon` | `()` | Daemon tick: cleanup expired TTL triggers + log active count. | [src](../../../core/services/communication_guard_daemon.py#L18) |

## `core/services/compaction_runtime.py`
_`CompactionRuntime` — kontekst-pres lettes ved ERSTATNING, aldrig ved sletning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NotAdvancing` | `` | Kompakteringen frigav ingenting. Et genforsøg ville være en løkke. | [src](../../../core/services/compaction_runtime.py#L55) |
| class | `Node` | `` | En knude i den overflade der kan erstattes. | [src](../../../core/services/compaction_runtime.py#L60) |
| class | `Policy` | `` | — | [src](../../../core/services/compaction_runtime.py#L71) |
| class | `Surface` | `` | — | [src](../../../core/services/compaction_runtime.py#L80) |
| method | `Surface.tokens` | `(self)` | — | [src](../../../core/services/compaction_runtime.py#L84) |
| class | `Result` | `` | — | [src](../../../core/services/compaction_runtime.py#L89) |
| function | `_uafsluttede_par` | `(nodes)` | Værktøjskald hvis resultat mangler — og resultaterne selv. | [src](../../../core/services/compaction_runtime.py#L98) |
| function | `protected_ids` | `(s, p, *, current_user_input=…)` | Alt der ikke må erstattes. | [src](../../../core/services/compaction_runtime.py#L116) |
| function | `prune_tool_results` | `(s, p, *, current_user_input=…)` | Deterministisk beskæring. Ingen model, ingen risiko for at tage fejl. | [src](../../../core/services/compaction_runtime.py#L127) |
| function | `replaceable_range` | `(s, p, *, current_user_input=…)` | Ét SAMMENHÆNGENDE spænd der må erstattes. `(0, 0)` hvis intet kan. | [src](../../../core/services/compaction_runtime.py#L150) |
| function | `summarize` | `(s, p, *, summary_text, summary_tokens, current_user_input=…)` | Erstat ét spænd med en opsummering. Atomisk eller slet ikke. | [src](../../../core/services/compaction_runtime.py#L172) |
| function | `failed` | `(s, error)` | En mislykket kompaktering. Generationen står UÆNDRET. | [src](../../../core/services/compaction_runtime.py#L200) |
| function | `may_retry_after_overflow` | `(before, after)` | Må overløbet prøves igen? | [src](../../../core/services/compaction_runtime.py#L210) |
| function | `require_advance` | `(before, after)` | Som ovenfor, men kaster. Til kaldesteder der ellers ville løkke. | [src](../../../core/services/compaction_runtime.py#L220) |

## `core/services/companion_initiative.py`
_Proaktivitet — Jarvis må dele en tanke uden at blive spurgt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Offer` | `` | — | [src](../../../core/services/companion_initiative.py#L44) |
| method | `Offer.as_dict` | `(self)` | — | [src](../../../core/services/companion_initiative.py#L49) |
| function | `_now` | `()` | — | [src](../../../core/services/companion_initiative.py#L54) |
| function | `_parse` | `(ts)` | — | [src](../../../core/services/companion_initiative.py#L58) |
| function | `_read_journal` | `()` | — | [src](../../../core/services/companion_initiative.py#L69) |
| function | `_write_journal` | `(entries)` | — | [src](../../../core/services/companion_initiative.py#L86) |
| function | `is_quiet_hour` | `(moment)` | Er det tidspunkt hvor en tanke ville vække frem for at nå frem? | [src](../../../core/services/companion_initiative.py#L94) |
| function | `next_quiet_end` | `(moment)` | Hvornår må den stille periode brydes igen. | [src](../../../core/services/companion_initiative.py#L103) |
| function | `_recent_for` | `(user_id, journal)` | — | [src](../../../core/services/companion_initiative.py#L113) |
| function | `check_allowed` | `(user_id, *, now=…)` | Må en tanke sendes lige nu? Ren vurdering — sender ingenting. | [src](../../../core/services/companion_initiative.py#L117) |
| function | `offer_thought` | `(user_id, text, *, title=…, now=…)` | Tilbyd en tanke. Sender kun hvis grænserne tillader det. | [src](../../../core/services/companion_initiative.py#L144) |
| function | `recent_thoughts` | `(user_id, *, limit=…)` | Tankerne, nyeste først — også dem der blev holdt tilbage. | [src](../../../core/services/companion_initiative.py#L184) |

## `core/services/companion_presence.py`
_Livstegn — er Jarvis vågen lige nu, og hvad lavede han sidst?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse` | `(ts)` | — | [src](../../../core/services/companion_presence.py#L29) |
| function | `_last_heartbeat` | `()` | Seneste hjerteslag: hvornår, og hvad det endte med at gøre. | [src](../../../core/services/companion_presence.py#L40) |
| function | `_running_now` | `()` | Er en synlig kørsel i gang? Det er stærkere end et hjerteslag: det | [src](../../../core/services/companion_presence.py#L96) |
| function | `_short` | `(text, limit=…)` | — | [src](../../../core/services/companion_presence.py#L107) |
| function | `build_presence` | `(*, now=…)` | Det ærlige livstegn. Kaster aldrig — men lyver heller aldrig. | [src](../../../core/services/companion_presence.py#L112) |

## `core/services/compass_engine.py`
_Compass Engine — weekly strategic bearing based on open loops and priorities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `maybe_update_compass` | `(*, open_loops=…, recent_decisions=…)` | Update compass if >3 days since last update. | [src](../../../core/services/compass_engine.py#L21) |
| function | `build_compass_surface` | `()` | — | [src](../../../core/services/compass_engine.py#L65) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/compass_engine.py#L74) |

## `core/services/completion_satisfaction.py`
_Completion Satisfaction — "det er nok, jeg er tilfreds."_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_completion_satisfaction` | `(*, task_outcomes, repetition_on_same_topic=…, user_mood=…)` | — | [src](../../../core/services/completion_satisfaction.py#L8) |
| function | `build_completion_satisfaction_surface` | `()` | — | [src](../../../core/services/completion_satisfaction.py#L45) |
| function | `_publish_completion_satisfaction_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/completion_satisfaction.py#L48) |

## `core/services/composite_tools.py`
_Composite tools — safe self-extension through composition only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose` | `(*, name, description, input_schema, steps, created_by=…)` | Validate and store a proposal. Raises ValueError on invalid input. | [src](../../../core/services/composite_tools.py#L44) |
| function | `approve` | `(name, *, approved_by=…)` | — | [src](../../../core/services/composite_tools.py#L115) |
| function | `revoke` | `(name)` | — | [src](../../../core/services/composite_tools.py#L128) |
| function | `delete` | `(name)` | — | [src](../../../core/services/composite_tools.py#L138) |
| function | `get` | `(name)` | — | [src](../../../core/services/composite_tools.py#L148) |
| function | `list_available` | `(*, status=…)` | — | [src](../../../core/services/composite_tools.py#L152) |
| function | `invoke` | `(name, args)` | Execute an approved composite. Returns {status, steps, result}. | [src](../../../core/services/composite_tools.py#L156) |
| function | `get_stats` | `()` | — | [src](../../../core/services/composite_tools.py#L224) |
| function | `_substitute` | `(value, context)` | — | [src](../../../core/services/composite_tools.py#L237) |
| function | `_resolve_string` | `(s, context)` | Resolve {{...}} templates. | [src](../../../core/services/composite_tools.py#L247) |
| function | `_lookup` | `(path, context)` | — | [src](../../../core/services/composite_tools.py#L267) |

## `core/services/computer_use_policy.py`
_Computer-use-politik (§4.7) — per-bruger on/off for operator/computer-tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_computer_use_tool` | `(name)` | — | [src](../../../core/services/computer_use_policy.py#L25) |
| function | `_load` | `()` | — | [src](../../../core/services/computer_use_policy.py#L30) |
| function | `computer_use_enabled` | `(user_id)` | Default TIL — kun eksplicit fravalg slår fra. | [src](../../../core/services/computer_use_policy.py#L37) |
| function | `set_computer_use` | `(user_id, enabled)` | — | [src](../../../core/services/computer_use_policy.py#L42) |

## `core/services/concept_baseline_tracker.py`
_Concept baseline tracker — Layer 3 of emotion concepts integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cluster_for_concept` | `(concept)` | Look up cluster for a concept. Falls back to UNKNOWN. | [src](../../../core/services/concept_baseline_tracker.py#L19) |
| function | `_tracker_enabled` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L31) |
| function | `_now` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L39) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/concept_baseline_tracker.py#L43) |
| function | `record_concept_trigger` | `(*, concept, intensity, triggered_at, source)` | Real-time: update per-concept stats when a concept fires. | [src](../../../core/services/concept_baseline_tracker.py#L47) |
| function | `_aggregate_clusters` | `()` | Compute cluster-level share from total_triggers across all concepts. | [src](../../../core/services/concept_baseline_tracker.py#L87) |
| function | `_detect_drift` | `(cluster_stats, per_concept_stats)` | Detect drift signals from current stats. | [src](../../../core/services/concept_baseline_tracker.py#L129) |
| function | `_workspace_dir` | `()` | Return path to Jarvis' shared state directory. Indirected for tests. | [src](../../../core/services/concept_baseline_tracker.py#L156) |
| function | `_write_concept_baseline_md` | `(cluster_stats, per_concept_stats)` | Write auto-managed CONCEPT_BASELINE.md to workspace dir. | [src](../../../core/services/concept_baseline_tracker.py#L162) |
| function | `_propose_identity_update` | `(signal)` | Forward a drift signal to identity_drift_proposer. | [src](../../../core/services/concept_baseline_tracker.py#L210) |
| function | `evaluate_baseline_drift` | `()` | Daily: compute stats, write MD, propose drift updates if stable. | [src](../../../core/services/concept_baseline_tracker.py#L242) |
| function | `build_concept_baseline_surface` | `()` | Read-only: return current state for Mission Control consumption. | [src](../../../core/services/concept_baseline_tracker.py#L300) |

## `core/services/config_drift.py`
_Config-drift-nerve (§7) — fang når DEKLARERET config og RUNTIME-virkelighed er ude af sync._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_declared_port` | `()` | Læs den DEKLAREREDE port DIREKTE fra runtime.json på disk — IKKE in-memory settings. | [src](../../../core/services/config_drift.py#L19) |
| function | `_api_responds` | `(port)` | True hvis NOGET svarer HTTP på 127.0.0.1:port (selv 4xx/5xx = porten lytter). | [src](../../../core/services/config_drift.py#L42) |
| function | `check_port_drift` | `()` | Probe deklareret port + alternativer. drift=True hvis API'en svarer, men IKKE på den | [src](../../../core/services/config_drift.py#L55) |
| function | `observe_config_drift` | `()` | Kør drift-check → observe til Centralen + flag incident hvis drift. Kadence-kaldt. | [src](../../../core/services/config_drift.py#L73) |
| function | `build_config_drift_surface` | `()` | MC-surface — read-only config-drift-projektion. | [src](../../../core/services/config_drift.py#L119) |

## `core/services/conflict_daemon.py`
_Conflict daemon — detects when Jarvis' signals pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_conflict_daemon` | `(snapshot, skip_event_gate=…)` | Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode, | [src](../../../core/services/conflict_daemon.py#L31) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/conflict_daemon.py#L81) |
| function | `_conflict_tension` | `(conflict_type, snapshot)` | Rå spændings-score 0–1 fra rule-based signaler. Ingen LLM. | [src](../../../core/services/conflict_daemon.py#L95) |
| function | `_build_raw_conflict_phrase` | `(conflict_type, snapshot)` | Byg frasen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/conflict_daemon.py#L111) |
| function | `_detect_conflict` | `(snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L121) |
| function | `_generate_conflict_phrase` | `(conflict_type, snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L147) |
| function | `_store_conflict` | `(phrase, conflict_type)` | — | [src](../../../core/services/conflict_daemon.py#L196) |
| function | `get_latest_conflict` | `()` | — | [src](../../../core/services/conflict_daemon.py#L227) |
| function | `build_conflict_surface` | `()` | — | [src](../../../core/services/conflict_daemon.py#L231) |

## `core/services/conflict_prompt_service.py`
_Conflict memory prompt service — surfaces recent conversation conflicts in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_conflict_memory_prompt_section` | `(limit=…)` | Return a prompt section with recent conflict lessons, or None if empty. | [src](../../../core/services/conflict_prompt_service.py#L11) |
| function | `build_conflict_memory_surface` | `(limit=…)` | — | [src](../../../core/services/conflict_prompt_service.py#L37) |

## `core/services/conflict_resolution.py`
_Bounded conflict resolution — deterministic arbitration between competing runtime pressures._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ConflictTrace` | `` | Observable trace of a conflict resolution decision. | [src](../../../core/services/conflict_resolution.py#L29) |
| method | `ConflictTrace.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L40) |
| class | `QuietInitiative` | `` | A quietly held user-facing initiative under maturation. | [src](../../../core/services/conflict_resolution.py#L61) |
| method | `QuietInitiative.to_dict` | `(self)` | — | [src](../../../core/services/conflict_resolution.py#L73) |
| function | `get_quiet_initiative` | `()` | Return the current quiet initiative state for MC observability. | [src](../../../core/services/conflict_resolution.py#L92) |
| function | `_start_quiet_hold` | `(*, focus, reason_code, dominant_factor, decision_type)` | Start or refresh a quiet hold on a user-facing initiative. | [src](../../../core/services/conflict_resolution.py#L97) |
| function | `_expire_quiet_initiative` | `(reason=…)` | Mark the current quiet initiative as expired/released. | [src](../../../core/services/conflict_resolution.py#L126) |
| function | `_promote_quiet_initiative` | `()` | Mark the current quiet initiative as promoted to user-facing. | [src](../../../core/services/conflict_resolution.py#L135) |
| function | `resolve_heartbeat_initiative_conflict` | `(*, decision_type, liveness, question_gate, autonomy_pressure, open_loops, conductor_mode=…, cognitive_frame=…, policy_allow_propose=…, policy_allow_ping=…)` | Resolve competing pressures into a single bounded initiative outcome. | [src](../../../core/services/conflict_resolution.py#L148) |
| function | `apply_conflict_resolution` | `(*, decision, trace)` | Apply conflict resolution outcome to modify the heartbeat decision. | [src](../../../core/services/conflict_resolution.py#L508) |
| function | `get_last_conflict_trace` | `()` | Return the last conflict resolution trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L601) |
| function | `set_last_conflict_trace` | `(trace)` | Store the latest conflict trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L610) |
| function | `build_conflict_resolution_surface` | `()` | — | [src](../../../core/services/conflict_resolution.py#L615) |
| function | `_emit_resolved_event` | `(winning, losing)` | — | [src](../../../core/services/conflict_resolution.py#L624) |

