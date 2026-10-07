# `core.services.08` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/ci_status_watch.py`
_CI-status — set, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nu` | `()` | — | [src](../../../core/services/ci_status_watch.py#L74) |
| class | `ApiUkendt` | `` | Vi kunne ikke se CI. | [src](../../../core/services/ci_status_watch.py#L78) |
| function | `_rapporterede` | `()` | {run_id: iso-tidsstempel} for det vi allerede har set. | [src](../../../core/services/ci_status_watch.py#L88) |
| function | `_husk` | `(ids)` | Skriv id'erne som sete — atomisk, så api og runtime ikke overskriver | [src](../../../core/services/ci_status_watch.py#L111) |
| function | `_grundlinje` | `()` | Tidsstemplet for hvornår vagtposten vågnede. Sættes én gang. | [src](../../../core/services/ci_status_watch.py#L127) |
| function | `_hent_runs` | `()` | Kørslerne på `main`. Rejser `ApiUkendt` når vi ikke kunne se dem. | [src](../../../core/services/ci_status_watch.py#L143) |
| function | `scan_roede` | `()` | Nye røde kørsler på `main` siden sidst — efter grundlinjen. | [src](../../../core/services/ci_status_watch.py#L167) |
| function | `_beskriv` | `(run)` | — | [src](../../../core/services/ci_status_watch.py#L208) |
| function | `_sekunder_siden` | `(sidste)` | Sekunder siden forrige tjek — eller None når stemplet mangler eller er | [src](../../../core/services/ci_status_watch.py#L218) |
| function | `tik` | `()` | Tjek CI på `main` og læg én followup for nye røde kørsler. | [src](../../../core/services/ci_status_watch.py#L230) |

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
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L552) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L560) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L590) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L662) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L730) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L757) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

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
| function | `_run_cognition_nonllm_members` | `(snap, result)` | Run the NON-LLM cognition members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon.py#L1642) |
| function | `tick_cluster_cognition` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the cognition cluster-daemon family (#5). | [src](../../../core/services/cluster_daemon.py#L1658) |

## `core/services/cluster_daemon_families.py`
_Cluster-daemon FAMILIES — the second file of consolidated nerve-families._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_collect_memory_snapshot` | `()` | Familiens faelles snapshot. Tom siden 7/10-2026. | [src](../../../core/services/cluster_daemon_families.py#L78) |
| function | `build_memory_family` | `()` | Construct the memory/maintenance cluster-daemon (family #6), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L101) |
| function | `memory_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L136) |
| function | `_mem_decay_live` | `(_snap)` | Daily decay + re-discovery. Replicates the old heartbeat influence site: | [src](../../../core/services/cluster_daemon_families.py#L148) |
| function | `_mem_pruning_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L166) |
| function | `_mem_maintenance_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L171) |
| function | `_mem_safeguard_live` | `(_snap)` | The safeguard daemon exposes ``run()`` (its old heartbeat site imported a | [src](../../../core/services/cluster_daemon_families.py#L176) |
| function | `_mem_selective_consolidation_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L184) |
| function | `_mem_associative_recall_live` | `(_snap)` | — | [src](../../../core/services/cluster_daemon_families.py#L189) |
| function | `_mem_write_queue_live` | `(_snap)` | LOAD-BEARING + FREQUENT — drains the deferred write queue every 120s. | [src](../../../core/services/cluster_daemon_families.py#L194) |
| function | `_mem_candidate_digest_live` | `(_snap)` | Ugentlig push-digest over kandidat-review-koeen (1/10-2026). Self-throttler. | [src](../../../core/services/cluster_daemon_families.py#L200) |
| function | `_run_memory_nonllm_members` | `(snap, result)` | Run the NON-LLM maintenance members UNCONDITIONALLY (independent of the | [src](../../../core/services/cluster_daemon_families.py#L220) |
| function | `tick_cluster_memory` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the memory/maintenance cluster-daemon family (#6). | [src](../../../core/services/cluster_daemon_families.py#L236) |
| function | `_feed_aesthetic_choice` | `()` | Record the latest visible run's style/mode into the taste daemon. | [src](../../../core/services/cluster_daemon_families.py#L306) |
| function | `_collect_aesthetic_snapshot` | `()` | Gather the aesthetic family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L336) |
| function | `_aesthetic_taste_signals` | `(snap)` | aesthetic_taste gate signals: how much taste-evidence has accumulated. | [src](../../../core/services/cluster_daemon_families.py#L371) |
| function | `_aesthetic_taste_live` | `(_snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L386) |
| function | `build_aesthetic_family` | `()` | Construct the aesthetic/curiosity cluster-daemon (family #7), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L397) |
| function | `aesthetic_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L427) |
| function | `_aesthetic_curiosity_live` | `(snap)` | Rules-based gap scan over the thought-stream fragment buffer. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L439) |
| function | `_aesthetic_code_aesthetic_live` | `(_snap)` | Ugentlig aestetisk refleksion over kodebasen. Self-throttler INTERNT | [src](../../../core/services/cluster_daemon_families.py#L450) |
| function | `_run_aesthetic_nonllm_members` | `(snap, result)` | Run the NON-LLM member(s) UNCONDITIONALLY (independent of the family | [src](../../../core/services/cluster_daemon_families.py#L467) |
| function | `tick_cluster_aesthetic` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the aesthetic/curiosity cluster-daemon family (#7). | [src](../../../core/services/cluster_daemon_families.py#L482) |
| function | `_collect_relation_snapshot` | `()` | Gather the relation family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L563) |
| function | `_relation_user_model_signals` | `(snap)` | user_model gate signals: how much (and what shape of) user interaction has | [src](../../../core/services/cluster_daemon_families.py#L605) |
| function | `_relation_user_model_live` | `(snap)` | The family gate already fired → skip the daemon's per-daemon event-gate. | [src](../../../core/services/cluster_daemon_families.py#L620) |
| function | `build_relation_family` | `()` | Construct the relation cluster-daemon (family #8), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L633) |
| function | `relation_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L663) |
| function | `_relation_comm_guard_live` | `(_snap)` | Godnat-split guard: sweep expired TTL communication-triggers + log active | [src](../../../core/services/cluster_daemon_families.py#L675) |
| function | `_relation_map_refresh_live` | `(_snap)` | Refresh the relation map (primary last_seen + stale secondary ToM stamps). | [src](../../../core/services/cluster_daemon_families.py#L683) |
| function | `_run_relation_nonllm_members` | `(snap, result)` | Run the NON-LLM members UNCONDITIONALLY (independent of the family generative | [src](../../../core/services/cluster_daemon_families.py#L700) |
| function | `tick_cluster_relation` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the relation cluster-daemon family (#8). | [src](../../../core/services/cluster_daemon_families.py#L716) |
| function | `_projects_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L804) |
| function | `_collect_projects_snapshot` | `()` | Gather the projects family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L822) |
| function | `build_projects_family` | `()` | Construct the projects/work-execution cluster-daemon (family #9), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L842) |
| function | `projects_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L864) |
| function | `_projects_task_worker_live` | `(_snap)` | LOAD-BEARING + EVERY TICK — drain up to 3 queued runtime_tasks. NO throttle: | [src](../../../core/services/cluster_daemon_families.py#L876) |
| function | `_projects_my_projects_live` | `(_snap)` | Restart Jarvis' dead background processes. Rules-based, no LLM. Self-throttles | [src](../../../core/services/cluster_daemon_families.py#L884) |
| function | `_projects_life_reassessment_live` | `(_snap)` | Re-assess active life projects; publish reassessment_due for stale ones. | [src](../../../core/services/cluster_daemon_families.py#L894) |
| function | `_projects_thought_action_live` | `(snap)` | Classify the latest thought-stream fragment into an action-proposal. Rules- | [src](../../../core/services/cluster_daemon_families.py#L905) |
| function | `_run_projects_unconditional` | `(snap, result)` | Run every projects member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L929) |
| function | `tick_cluster_projects` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the projects/work-execution cluster-daemon family (#9). | [src](../../../core/services/cluster_daemon_families.py#L945) |
| function | `_infra_throttle_ready` | `(key, minutes)` | Return True (and stamp 'now') iff ``minutes`` have elapsed since the last | [src](../../../core/services/cluster_daemon_families.py#L1091) |
| function | `_collect_infra_snapshot` | `()` | Gather the infra family's shared snapshot once per tick. | [src](../../../core/services/cluster_daemon_families.py#L1110) |
| function | `build_infra_family` | `()` | Construct the infra/maintenance cluster-daemon (family #10), LIVE. | [src](../../../core/services/cluster_daemon_families.py#L1121) |
| function | `infra_family` | `()` | — | [src](../../../core/services/cluster_daemon_families.py#L1146) |
| function | `_infra_file_awareness_live` | `(_snap)` | Ensure the file-awareness watcher thread is running (tamper detection). | [src](../../../core/services/cluster_daemon_families.py#L1158) |
| function | `_infra_cache_maintenance_live` | `(_snap)` | 6h web_cache cleanup. Rules-based, no LLM. Self-throttles INTERNALLY | [src](../../../core/services/cluster_daemon_families.py#L1167) |
| function | `_infra_signal_decay_live` | `(_snap)` | Archive+delete stale signals + refresh signal runtime statuses. Rules-based, | [src](../../../core/services/cluster_daemon_families.py#L1175) |
| function | `_infra_wakeup_cleanup_live` | `(_snap)` | Prune stale consumed/cancelled/fired wakeups. Rules-based, no LLM. Self- | [src](../../../core/services/cluster_daemon_families.py#L1183) |
| function | `_infra_cost_optimization_live` | `(_snap)` | Monitor daily/weekly spend vs budget; emit cost.* events. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1193) |
| function | `_infra_ground_truth_live` | `(_snap)` | Refresh the Ground-Truth Registry cache (Lying Engine, Lag 3). Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1203) |
| function | `_infra_mail_checker_live` | `(_snap)` | Poll IMAP for new mail; publish events for unseen messages. Rules-based, no | [src](../../../core/services/cluster_daemon_families.py#L1214) |
| function | `_infra_visual_memory_live` | `(_snap)` | Webcam snapshot + LOCAL ollama vision-model description (Lag 6, 0 API tokens). | [src](../../../core/services/cluster_daemon_families.py#L1224) |
| function | `_infra_provider_autodiscovery_live` | `(_snap)` | Dagligt /models-scan af alle providers → nye modeller til pending_models. | [src](../../../core/services/cluster_daemon_families.py#L1239) |
| function | `_infra_visible_drift_live` | `(_snap)` | Luk `visible_runs`-rækker der står `recovering`, men er beviseligt slut. | [src](../../../core/services/cluster_daemon_families.py#L1251) |
| function | `_infra_beslutninger_i_indbakken_live` | `(_snap)` | Giv beslutninger under tærsklen en adresse i indbakken. | [src](../../../core/services/cluster_daemon_families.py#L1284) |
| function | `_infra_approval_expiry_live` | `(_snap)` | Markér udløbne, ikke-besluttede godkendelser. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1330) |
| function | `_infra_feedback_review_live` | `(snap)` | Giv Jarvis månedens tommel-op/ned at tænke over. Rules-based, no LLM. | [src](../../../core/services/cluster_daemon_families.py#L1343) |
| function | `_run_infra_unconditional` | `(snap, result)` | Run every infra member UNCONDITIONALLY (this family has no LLM/gated tier), | [src](../../../core/services/cluster_daemon_families.py#L1378) |
| function | `tick_cluster_infra` | `(snapshot=…, *, shadow=…)` | Heartbeat entry-point for the infra/maintenance cluster-daemon family (#10). | [src](../../../core/services/cluster_daemon_families.py#L1395) |

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
| function | `_build_recurrence_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L110) |
| function | `_build_global_workspace_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L137) |
| function | `_build_hot_meta_cognition_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L165) |
| function | `_build_surprise_afterimage_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L192) |
| function | `_build_attention_blink_state` | `()` | — | [src](../../../core/services/cognitive_core_experiments.py#L222) |
| function | `_activity_state` | `(*, enabled, active)` | — | [src](../../../core/services/cognitive_core_experiments.py#L249) |
| function | `_strongest_carry_item` | `(items)` | — | [src](../../../core/services/cognitive_core_experiments.py#L257) |

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
| function | `evaluate_commit_gates` | `(*, name, arguments, user_message, session_id, run_id, user_present=…)` | Kør veto + decision_gate gennem central().decide, observér arbitrage, og returnér | [src](../../../core/services/commit_gate_arbiter.py#L30) |

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
| function | `prompt_section` | `()` | Bygger en høj-salient påmindelse til system-prompten med de aktive | [src](../../../core/services/communication_guard.py#L441) |
| function | `consume_turn` | `()` | Traek en TTL-turn fra alle TTL-baserede triggers. Kald efter hver | [src](../../../core/services/communication_guard.py#L475) |
| function | `cleanup_expired` | `()` | Rens udloebne TTL-triggers og triggers med ttl_turns <= 0. | [src](../../../core/services/communication_guard.py#L493) |
| function | `_safe_parse_iso` | `(s, now)` | — | [src](../../../core/services/communication_guard.py#L518) |
| function | `list_triggers` | `()` | Returner alle aktive triggers. | [src](../../../core/services/communication_guard.py#L527) |
| function | `active_count` | `()` | Antal aktive triggerfraser (permanente + ikke-udloebne TTL). | [src](../../../core/services/communication_guard.py#L532) |

## `core/services/communication_guard_daemon.py`
_Communication guard daemon — vedligeholder TTL-rydning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_communication_guard_daemon` | `()` | Daemon tick: cleanup expired TTL triggers + log active count. | [src](../../../core/services/communication_guard_daemon.py#L18) |

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

## `core/services/composer_moenster.py`
_Hvad Bjørn plejer at bede om — udledt af hans valg, ikke af hans ord._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `art` | `(forslag)` | Hvad et forslag beder om. Altid ét ord-par, aldrig tomt. | [src](../../../core/services/composer_moenster.py#L77) |
| function | `_valg_i_vinduet` | `()` | De terminale valg indenfor vinduet. Egen funktion, så testene kan sætte dem. | [src](../../../core/services/composer_moenster.py#L94) |
| function | `moenster` | `()` | Én linje til prompten — eller `""` når der ikke er noget at sige. | [src](../../../core/services/composer_moenster.py#L111) |
| function | `er_taendt` | `()` | Kontakten. Et mønster der peger galt skal kunne tages ud uden et deploy. | [src](../../../core/services/composer_moenster.py#L151) |

## `core/services/composer_suggest.py`
_Forslag i komponisten — hvad der kunne skrives videre, mens man skriver._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_samtale` | `(session_id)` | De seneste beskeder. Egen funktion, så testene kan sætte dem. | [src](../../../core/services/composer_suggest.py#L51) |
| function | `_tomt` | `()` | Intet forslag — og dermed intet at melde tilbage om. | [src](../../../core/services/composer_suggest.py#L57) |
| function | `foreslaa_naeste` | `(session_id)` | Et bud på brugerens næste besked, eller `""`. | [src](../../../core/services/composer_suggest.py#L62) |
| function | `foreslaa_naeste_detaljer` | `(session_id)` | Forslaget OG det klienten skal bruge for at kunne melde valget tilbage. | [src](../../../core/services/composer_suggest.py#L71) |

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

## `core/services/computer_use_samtykke.py`
_Samtykke til at røre Bjørns mus og tastatur — én gang pr. samtale._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kraever_samtykke` | `(vaerktoej)` | Er dette et værktøj der rører hans maskine? | [src](../../../core/services/computer_use_samtykke.py#L56) |
| function | `har_samtykke` | `(session_id)` | — | [src](../../../core/services/computer_use_samtykke.py#L61) |
| function | `giv_samtykke` | `(session_id)` | Kaldes når han har sagt ja. Gælder resten af samtalen i denne proces. | [src](../../../core/services/computer_use_samtykke.py#L66) |
| function | `traek_tilbage` | `(session_id=…)` | Stop-knappen. Tom session_id trækker ALT tilbage — nødbremsen. | [src](../../../core/services/computer_use_samtykke.py#L75) |
| function | `aktive_samtaler` | `()` | Hvilke samtaler har adgang lige nu? Desk viser mærket ud fra den her. | [src](../../../core/services/computer_use_samtykke.py#L85) |

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
| function | `build_config_drift_surface` | `()` | MC-surface — read-only config-drift-projektion. | [src](../../../core/services/config_drift.py#L120) |

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

## `core/services/connections.py`
_Connections-cluster — gør forbindelses-LIVSCYKLUSSEN synlig i Den Intelligente Central:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/connections.py#L18) |
| function | `note_presence` | `(user_id, device_key, platform=…, **meta)` | En device-presence-ping (jarvis-desk/mobile companion). Metadata-only. | [src](../../../core/services/connections.py#L26) |
| function | `note_ws` | `(event, client=…, **meta)` | MC-websocket-livscyklus: event ∈ {connected, disconnected, error}. client = host:port. | [src](../../../core/services/connections.py#L35) |
| function | `note_connection_error` | `(client, reason, **meta)` | Forbindelses-FEJL (WS-error, broken pipe, abort). → observe (synlig, ikke severe). | [src](../../../core/services/connections.py#L41) |
| function | `note_unauthorized` | `(user_id, session_id, resource, reason, *, role=…, run_id=…)` | UAUTORISERET adgang (tool-deny / identity-spoof / rate-limit) på en forbindelse → | [src](../../../core/services/connections.py#L46) |
| function | `session_activity` | `(session_id, *, limit=…)` | Forbindelses-debugging pr. session: hvilke tools blev brugt, hvilke FEJLEDE (+ årsag), | [src](../../../core/services/connections.py#L75) |
| function | `active_summary` | `(*, window=…)` | Read-only: hvem/hvad har været forbundet i den seneste trace (til MC/adaptiv-læring). | [src](../../../core/services/connections.py#L112) |

## `core/services/connectors.py`
_Connector-registret — hvad brugeren har forbundet, og hvad det laaser op._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_enabled_store` | `()` | — | [src](../../../core/services/connectors.py#L177) |
| function | `is_enabled` | `(user_id, connector_id)` | Default ON; kun False hvis brugeren eksplicit har slået den fra. | [src](../../../core/services/connectors.py#L182) |
| function | `set_enabled` | `(user_id, connector_id, enabled)` | — | [src](../../../core/services/connectors.py#L191) |
| function | `_provider_of` | `(c)` | OAuth-provider for en connector. Google-pakken deler provider='google'. | [src](../../../core/services/connectors.py#L205) |
| function | `_connected` | `(user_id, c)` | Er DENNE connector brugbar — ikke bare: findes der en token hos udbyderen. | [src](../../../core/services/connectors.py#L210) |
| function | `oauth_request_for` | `(connector_id)` | Map et connector-id → (oauth_provider, scopes) til /api/oauth/{id}/start. | [src](../../../core/services/connectors.py#L248) |
| function | `list_for_user` | `(user_id)` | Hele kataloget beriget med per-bruger `connected` + `enabled`. | [src](../../../core/services/connectors.py#L260) |
| function | `_audit` | `(event, user_id, connector_id)` | — | [src](../../../core/services/connectors.py#L283) |
| function | `delete_for_user` | `(user_id, connector_id)` | Afbryd & slet: revoke hos provider (best-effort) + lokal token-wipe + ryd flag. | [src](../../../core/services/connectors.py#L291) |

## `core/services/consent_registry.py`
_Consent Registry — user preferences and boundaries that persist across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_file` | `()` | — | [src](../../../core/services/consent_registry.py#L26) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/consent_registry.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/consent_registry.py#L44) |
| function | `_save` | `()` | — | [src](../../../core/services/consent_registry.py#L55) |
| function | `register_consent` | `(*, kind, statement, source_session_id=…, confidence=…)` | Register a user preference or boundary. | [src](../../../core/services/consent_registry.py#L67) |
| function | `revoke_consent` | `(consent_id)` | Mark a consent entry as inactive. | [src](../../../core/services/consent_registry.py#L101) |
| function | `get_active_consents` | `()` | — | [src](../../../core/services/consent_registry.py#L112) |
| function | `build_consent_prompt_section` | `()` | Return a prompt section with active consent entries, or None if empty. | [src](../../../core/services/consent_registry.py#L117) |
| function | `build_consent_registry_surface` | `()` | — | [src](../../../core/services/consent_registry.py#L143) |

## `core/services/consolidation_judge_daemon.py`
_Consolidation Judge Daemon — nightly reckoning, not observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_consolidation_judge_daemon` | `()` | Run the nightly consolidation judge if cadence allows. | [src](../../../core/services/consolidation_judge_daemon.py#L29) |
| function | `_gather_evidence` | `()` | Collect today's operational data for judgment. | [src](../../../core/services/consolidation_judge_daemon.py#L74) |
| function | `_build_stillingtagen` | `(evidence)` | Construct 3-5 concrete stillingtagen (items requiring judgment). | [src](../../../core/services/consolidation_judge_daemon.py#L128) |
| function | `_render_judgments` | `(items, evidence)` | Present each stillingtagen to the LLM and force a verdict. | [src](../../../core/services/consolidation_judge_daemon.py#L209) |
| function | `_parse_judgment` | `(raw, item)` | Parse the LLM's judgment response. | [src](../../../core/services/consolidation_judge_daemon.py#L250) |
| function | `_enforce_judgments` | `(judgments)` | Carry out the concrete actions from judgments. | [src](../../../core/services/consolidation_judge_daemon.py#L281) |
| function | `_enforce_reject` | `(j)` | Handle rejected items — typically revoke or pause. | [src](../../../core/services/consolidation_judge_daemon.py#L291) |
| function | `_enforce_accept` | `(j)` | Handle accepted items — typically recommit or flag. | [src](../../../core/services/consolidation_judge_daemon.py#L329) |
| function | `_record_judgment_session` | `(judgments, evidence)` | Write the full judgment session as a private brain record. | [src](../../../core/services/consolidation_judge_daemon.py#L350) |
| function | `build_consolidation_judge_surface` | `()` | Build surface data for prompt injection. | [src](../../../core/services/consolidation_judge_daemon.py#L385) |
| function | `now_date_str` | `()` | — | [src](../../../core/services/consolidation_judge_daemon.py#L393) |

