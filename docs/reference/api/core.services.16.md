# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/ntfy_gateway.py`
_Ntfy gateway — send push notifications via ntfy.sh or self-hosted server._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L13) |
| function | `is_configured` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L26) |
| function | `_default_title` | `()` | — | [src](../../../core/services/ntfy_gateway.py#L30) |
| function | `send_notification` | `(message, title=…, priority=…, tags=…)` | Send a push notification via ntfy. Returns status dict. | [src](../../../core/services/ntfy_gateway.py#L41) |

## `core/services/nudge_broend.py`
_Nudge-broend — daemons drop nudges, Jarvis inspects and decides._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/nudge_broend.py#L24) |
| function | `_save` | `(nudges)` | — | [src](../../../core/services/nudge_broend.py#L37) |
| function | `_cleanup` | `(nudges)` | Remove oldest non-pending nudges if over max. | [src](../../../core/services/nudge_broend.py#L48) |
| function | `push` | `(*, source=…, kind=…, message=…, importance=…, raw_payload=…)` | Deposit a nudge in the broend. Returns nudge_id. | [src](../../../core/services/nudge_broend.py#L62) |
| function | `list_pending` | `(limit=…)` | List pending nudges, newest first. | [src](../../../core/services/nudge_broend.py#L105) |
| function | `count_pending` | `()` | Return count of pending nudges. | [src](../../../core/services/nudge_broend.py#L113) |
| function | `get` | `(nudge_id)` | Get a single nudge by ID. | [src](../../../core/services/nudge_broend.py#L119) |
| function | `mark_sent` | `(nudge_id)` | Mark a nudge as sent. | [src](../../../core/services/nudge_broend.py#L128) |
| function | `mark_dismissed` | `(nudge_id, reason=…)` | Mark a single nudge as dismissed. | [src](../../../core/services/nudge_broend.py#L140) |
| function | `dismiss_all` | `(reason=…)` | Dismiss all pending nudges. Returns count. | [src](../../../core/services/nudge_broend.py#L154) |

## `core/services/oauth_flow.py`
_OAuth-flow-helper for plugin-connectors (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_known_provider` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L46) |
| function | `redirect_uri` | `(provider)` | — | [src](../../../core/services/oauth_flow.py#L50) |
| function | `_secret` | `(key, default=…)` | — | [src](../../../core/services/oauth_flow.py#L54) |
| function | `_state_key` | `()` | — | [src](../../../core/services/oauth_flow.py#L62) |
| function | `sign_state` | `(user_id, provider, *, now=…)` | Signeret, selvstændigt state — binder bruger+provider, udløber, anti-CSRF. | [src](../../../core/services/oauth_flow.py#L67) |
| function | `verify_state` | `(state, *, now=…)` | Auth-cluster GENNEM Centralen (observe): anti-CSRF state-validering synlig — en fejlet | [src](../../../core/services/oauth_flow.py#L79) |
| function | `_verify_state_impl` | `(state, *, now=…)` | → (user_id, provider) hvis gyldig+ikke-udløbet, ellers None. | [src](../../../core/services/oauth_flow.py#L94) |
| function | `build_authorize_url` | `(provider, user_id, *, scopes=…, now=…)` | Authorize-URL til at åbne i brugerens browser. None hvis ukendt/ukonfigureret. | [src](../../../core/services/oauth_flow.py#L112) |
| function | `revoke_remote` | `(provider, token)` | Tilbagekald token hos provideren (best-effort). True hvis bekræftet revokeret. | [src](../../../core/services/oauth_flow.py#L134) |
| function | `refresh_token` | `(provider, refresh, *, now=…)` | Forny adgangstoken via grant_type=refresh_token. None ved fejl/ukendt provider. | [src](../../../core/services/oauth_flow.py#L165) |
| function | `exchange_code` | `(provider, code, *, now=…)` | Byt authorization code for token (BLOKERENDE netværk — kør i tråd). None ved fejl. | [src](../../../core/services/oauth_flow.py#L193) |
| function | `fetch_google_email` | `(token)` | Hent den verificerede Google-email via userinfo (BLOKERENDE — kør i tråd). | [src](../../../core/services/oauth_flow.py#L220) |

## `core/services/oauth_store.py`
_Per-bruger krypteret OAuth-token-hvælv — plugin-fundamentets privatlivs-spine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(user_id, provider)` | — | [src](../../../core/services/oauth_store.py#L23) |
| function | `save_token` | `(user_id, provider, token)` | Krypter + gem `token` (fx {access_token, refresh_token, expires_at, scope}) | [src](../../../core/services/oauth_store.py#L27) |
| function | `get_token` | `(user_id, provider)` | Hent + dekrypter token for (bruger, provider). None hvis intet/fejl. Kan KUN | [src](../../../core/services/oauth_store.py#L49) |
| function | `has_token` | `(user_id, provider)` | Er der en (dekrypterbar) token for brugeren hos provideren? | [src](../../../core/services/oauth_store.py#L69) |
| function | `revoke_token` | `(user_id, provider)` | Fjern token for (bruger, provider). True hvis udført (eller intet at fjerne). | [src](../../../core/services/oauth_store.py#L74) |
| function | `get_fresh_token` | `(user_id, provider, *, now=…)` | Som get_token, men auto-fornyer hvis udløbet (≤60s buffer) og refresh_token findes. | [src](../../../core/services/oauth_store.py#L91) |
| function | `list_providers` | `(user_id)` | Providere brugeren har forbundet (har en gemt token for). | [src](../../../core/services/oauth_store.py#L117) |

## `core/services/offline_recomposition_engine.py`
_Offline recomposition: recombine recent cognitive material into candidates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_offline_recomposition` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L15) |
| function | `build_offline_recomposition_surface` | `(*, limit=…)` | — | [src](../../../core/services/offline_recomposition_engine.py#L42) |
| function | `build_offline_recomposition_prompt_section` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L55) |
| function | `_candidate_pieces` | `(*, episodes, drive, curiosity, counterfactuals)` | — | [src](../../../core/services/offline_recomposition_engine.py#L67) |
| function | `_candidate_policy` | `(pieces)` | — | [src](../../../core/services/offline_recomposition_engine.py#L88) |
| function | `_feed_learning` | `(item)` | — | [src](../../../core/services/offline_recomposition_engine.py#L99) |
| function | `_runtime_state` | `(key)` | — | [src](../../../core/services/offline_recomposition_engine.py#L113) |
| function | `_load` | `()` | — | [src](../../../core/services/offline_recomposition_engine.py#L118) |

## `core/services/ollama_visible_prompt.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `serialize_ollama_visible_prompt` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L14) |
| function | `_collect_visible_text_parts` | `(items)` | — | [src](../../../core/services/ollama_visible_prompt.py#L26) |
| function | `_serialize_system_block` | `(system_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L56) |
| function | `serialize_ollama_chat_messages` | `(items)` | Convert visible input items to Ollama /api/chat messages format. | [src](../../../core/services/ollama_visible_prompt.py#L68) |
| function | `_serialize_conversation_block` | `(conversation_parts)` | — | [src](../../../core/services/ollama_visible_prompt.py#L87) |

## `core/services/open_loop_closure_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_closure_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L32) |
| function | `refresh_runtime_open_loop_closure_proposal_statuses` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L54) |
| function | `build_runtime_open_loop_closure_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L85) |
| function | `_extract_open_loop_closure_proposal_candidates` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L114) |
| function | `_persist_open_loop_closure_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L192) |
| function | `_build_proposal_snapshots` | `()` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L265) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L302) |
| function | `_with_surface_view` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L313) |
| function | `_build_proposal_type` | `(*, item, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L334) |
| function | `_proposal_status` | `(*, proposal_type, loop_status)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L348) |
| function | `_build_proposal_reason` | `(*, proposal_type, loop_status, closure_confidence, loop_title=…)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L356) |
| function | `_build_review_anchor` | `(*, snapshot)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L369) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L384) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L393) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L398) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L403) |
| function | `_review_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L408) |
| function | `_review_cadence_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L413) |
| function | `_proposal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L418) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L423) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L428) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/open_loop_closure_proposal_tracking.py#L438) |

## `core/services/open_loop_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_open_loop_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L58) |
| function | `refresh_runtime_open_loop_signal_statuses` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L80) |
| function | `build_runtime_open_loop_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L134) |
| function | `_build_runtime_open_loop_signal_surface_uncached` | `(*, limit=…)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L142) |
| function | `get_open_loop_creation_readiness` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L208) |
| function | `_extract_open_loop_candidates` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L287) |
| function | `_materialize_from_creation_readiness` | `(readiness, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L536) |
| function | `_extract_closure_maturation_candidates` | `(snapshots, existing_domain_keys)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L604) |
| function | `_build_governance_snapshots` | `()` | — | [src](../../../core/services/open_loop_signal_tracking.py#L683) |
| function | `_with_closure_governance` | `(item, *, snapshots)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L741) |
| function | `_persist_open_loop_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L791) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L864) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L905) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L917) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L935) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L939) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L944) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L949) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L954) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L959) |
| function | `_match_live_pressure_item` | `(*, anchors, candidates, minimum_overlap)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L968) |
| function | `_thread_overlap` | `(left, right)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L992) |
| function | `_thread_tokens` | `(item)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L996) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/open_loop_signal_tracking.py#L1030) |

## `core/services/operator_allowlist.py`
_Operator app-allowlist (leak-kandidat #5, CHICAGO-guard-mønster, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L26) |
| function | `list_allowlist` | `()` | — | [src](../../../core/services/operator_allowlist.py#L30) |
| function | `set_allowlist` | `(apps)` | — | [src](../../../core/services/operator_allowlist.py#L39) |
| function | `add_to_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L45) |
| function | `remove_from_allowlist` | `(app)` | — | [src](../../../core/services/operator_allowlist.py#L53) |
| function | `is_enforced` | `()` | — | [src](../../../core/services/operator_allowlist.py#L58) |
| function | `set_enforced` | `(on)` | — | [src](../../../core/services/operator_allowlist.py#L65) |
| function | `_matches` | `(app, allowlist)` | En app matcher hvis dens navn/sti indeholder en allowlist-post (substring, | [src](../../../core/services/operator_allowlist.py#L70) |
| function | `check_app` | `(app)` | Vurdér om Jarvis må GUI-styre `app`. OBSERVE-by-default: | [src](../../../core/services/operator_allowlist.py#L77) |
| function | `build_operator_allowlist_surface` | `()` | Central-CLI: jc raw /central/operator-allowlist. | [src](../../../core/services/operator_allowlist.py#L102) |

## `core/services/operator_channel.py`
_Operator-kanalen — owner-gated bro fra containerens bash til Bjørns maskine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/operator_channel.py#L41) |
| function | `_save` | `(state)` | — | [src](../../../core/services/operator_channel.py#L50) |
| function | `_aktiv` | `(post)` | — | [src](../../../core/services/operator_channel.py#L58) |
| function | `status` | `(session_id)` | Læse-kun. Ingen owner-gate — at spørge er harmløst. | [src](../../../core/services/operator_channel.py#L65) |
| function | `is_open` | `(session_id)` | — | [src](../../../core/services/operator_channel.py#L76) |
| function | `open_channel` | `(session_id, *, is_owner)` | — | [src](../../../core/services/operator_channel.py#L80) |
| function | `close_channel` | `(session_id, *, is_owner)` | — | [src](../../../core/services/operator_channel.py#L94) |
| function | `current_session_id` | `()` | Samme opslags-raekkefoelge som staged_edits_tools — ét moenster, ikke to. | [src](../../../core/services/operator_channel.py#L105) |
| function | `current_is_owner` | `()` | Owner-gaten. Fail-CLOSED: kan rollen ikke afgoeres, er svaret nej. | [src](../../../core/services/operator_channel.py#L120) |
| function | `_absolutte_stier` | `(command)` | — | [src](../../../core/services/operator_channel.py#L136) |
| function | `looks_like_workstation_path` | `(command, cwd=…)` | — | [src](../../../core/services/operator_channel.py#L149) |
| function | `maybe_reroute_bash` | `(command, cwd, *, is_owner, session_id)` | Kør kommandoen på Bjørns maskine hvis kanalen er åben. Ellers None. | [src](../../../core/services/operator_channel.py#L156) |
| function | `closed_channel_hint` | `(command, cwd, *, is_owner, session_id)` | Én linje til modellen når et kald tydeligvis sigtede mod hans maskine. | [src](../../../core/services/operator_channel.py#L182) |

## `core/services/orb_phase.py`
_Desktop orb phase — writes current Jarvis pipeline state to a temp file._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_phase` | `(phase)` | Write orb phase. Silently ignores any I/O errors. | [src](../../../core/services/orb_phase.py#L17) |

## `core/services/outbound_nudges.py`
_Outbound nudge ledger — replaces direct daemon→user sends for Type A/C._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create outbound_nudges table + indexes. | [src](../../../core/services/outbound_nudges.py#L52) |
| function | `_enabled` | `()` | — | [src](../../../core/services/outbound_nudges.py#L93) |
| function | `push_nudge` | `(*, source, kind, message, importance=…, parent_session_id=…, parent_message_id=…)` | Daemons call this instead of sending directly. | [src](../../../core/services/outbound_nudges.py#L101) |
| function | `route_for` | `(*, source, kind)` | 'midway' | 'telemetry' | 'bridge' — pure. | [src](../../../core/services/outbound_nudges.py#L197) |
| function | `_bridge_priority` | `(importance)` | — | [src](../../../core/services/outbound_nudges.py#L208) |
| function | `_publish_routed` | `(source, kind, importance, route)` | — | [src](../../../core/services/outbound_nudges.py#L217) |
| function | `format_midway_for_prompt` | `(*, limit=…)` | Bjørns beskeder sendt MENS et run kørte — de er hans ord, ikke daemon-støj. | [src](../../../core/services/outbound_nudges.py#L226) |
| function | `list_pending` | `(*, limit=…)` | Return pending nudges, newest first. Used by awareness-injection. | [src](../../../core/services/outbound_nudges.py#L259) |
| function | `note_shown` | `(nudge_ids)` | Tæl én visning. Pensionerer først ved `_SHOW_LIMIT`, ikke ved første render. | [src](../../../core/services/outbound_nudges.py#L287) |
| function | `mark_inspected` | `(nudge_ids)` | Bagudkompatibelt alias for `note_shown`. | [src](../../../core/services/outbound_nudges.py#L315) |
| function | `mark_sent` | `(nudge_id)` | Mark a nudge as actually surfaced to the user by Jarvis. | [src](../../../core/services/outbound_nudges.py#L320) |
| function | `mark_dismissed` | `(nudge_id)` | Mark a nudge as explicitly skipped by Jarvis (won't reappear). | [src](../../../core/services/outbound_nudges.py#L334) |
| function | `format_pending_for_awareness` | `()` | Render pending nudges as awareness section. | [src](../../../core/services/outbound_nudges.py#L348) |

## `core/services/outcome_learning.py`
_Outcome Learning — record observations, let old evidence decay._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/outcome_learning.py#L37) |
| function | `_load` | `()` | — | [src](../../../core/services/outcome_learning.py#L41) |
| function | `_save` | `(items)` | — | [src](../../../core/services/outcome_learning.py#L55) |
| function | `record_outcome` | `(*, context, outcome, weight=…, metadata=…)` | Record a single observation. outcome is free-form ('success', 'error', | [src](../../../core/services/outcome_learning.py#L67) |
| function | `_decay_factor` | `(recorded_at, now)` | — | [src](../../../core/services/outcome_learning.py#L93) |
| function | `pattern_strength` | `(context, *, outcome=…)` | Return decayed totals for a given context, optionally per-outcome. | [src](../../../core/services/outcome_learning.py#L102) |
| function | `top_patterns` | `(*, limit=…, outcome=…)` | Return the N strongest patterns (highest decayed strength). | [src](../../../core/services/outcome_learning.py#L134) |
| function | `prune_old_records` | `(*, min_weight=…)` | Drop records whose decayed weight is below min_weight. Returns count dropped. | [src](../../../core/services/outcome_learning.py#L161) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — occasional pruning. Doesn't run full prune every tick. | [src](../../../core/services/outcome_learning.py#L179) |
| function | `build_outcome_learning_surface` | `()` | — | [src](../../../core/services/outcome_learning.py#L189) |
| function | `_summary_line` | `(count, total, top)` | — | [src](../../../core/services/outcome_learning.py#L213) |
| function | `_emit_outcome_learning_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/outcome_learning.py#L225) |

## `core/services/outreach_composer.py`
_Outreach composer — Spor-1 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_db_path` | `()` | — | [src](../../../core/services/outreach_composer.py#L47) |
| function | `_hours_since` | `(iso_ts)` | — | [src](../../../core/services/outreach_composer.py#L51) |
| function | `_last_outreach_timestamp` | `()` | Most recent impulse.outreach.sent event timestamp. | [src](../../../core/services/outreach_composer.py#L63) |
| function | `_last_user_message_context` | `()` | Gather (preview, hours_since, channel_hint) from latest user turn. | [src](../../../core/services/outreach_composer.py#L81) |
| function | `_gather_signal_context` | `()` | Top-3 pressures + bearing + affect, for the outreach prompt. | [src](../../../core/services/outreach_composer.py#L113) |
| function | `_build_outreach_prompt` | `(*, direction, topic, strength, user_ctx, signal_ctx)` | Build the prompt that asks Jarvis-the-LLM to write the message. | [src](../../../core/services/outreach_composer.py#L162) |
| function | `_call_visible_model` | `(prompt, *, timeout=…)` | Call the visible-lane model (Ollama / GLM cloud) for the message text. | [src](../../../core/services/outreach_composer.py#L199) |
| function | `_send_message` | `(text, *, channel)` | Send the composed message via the USER's reach_out-kanalvalg (notification_router). | [src](../../../core/services/outreach_composer.py#L246) |
| function | `_decay_longing_after_outreach` | `(reduction=…)` | When Jarvis has reached out, the longing pressure should drop. | [src](../../../core/services/outreach_composer.py#L282) |
| function | `compose_and_send_outreach` | `(*, direction, topic, strength)` | Spor-1 entry point. Compose a coherent message and send it. | [src](../../../core/services/outreach_composer.py#L299) |

## `core/services/override_command.py`
_Owner-override-kommando — delt handler for gateways (Discord/Telegram)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `handle_override_command` | `(text, *, session_id, owner_seed, level=…, now=…)` | Håndtér `!override <kode>` / `!revoke-override` — Auth-cluster GENNEM Centralen (observe). | [src](../../../core/services/override_command.py#L24) |
| function | `_handle_override_command_impl` | `(text, *, session_id, owner_seed, level=…, now=…)` | Håndtér `!override <kode>` / `!revoke-override`. | [src](../../../core/services/override_command.py#L52) |

## `core/services/override_store.py`
_Owner-override-session-store — DB-backed, cross-proces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(session_id)` | — | [src](../../../core/services/override_store.py#L31) |
| function | `_now` | `(now)` | — | [src](../../../core/services/override_store.py#L35) |
| function | `grant` | `(session_id, *, level=…, now=…)` | Aktivér owner-override for en session. Returnér record. | [src](../../../core/services/override_store.py#L39) |
| function | `_read` | `(session_id)` | — | [src](../../../core/services/override_store.py#L59) |
| function | `is_active` | `(session_id, *, now=…)` | True hvis sessionen har en aktiv (ikke-udløbet) override. | [src](../../../core/services/override_store.py#L64) |
| function | `level` | `(session_id, *, now=…)` | Override-niveau hvis aktiv, ellers None. | [src](../../../core/services/override_store.py#L72) |
| function | `touch` | `(session_id, *, now=…)` | Forny en AKTIV override til +5 min ved aktivitet. False hvis udløbet/fraværende. | [src](../../../core/services/override_store.py#L80) |
| function | `revoke` | `(session_id)` | Deaktivér override (sæt udløbet — runtime_state har ingen delete). | [src](../../../core/services/override_store.py#L97) |

## `core/services/paid_lane_guard.py`
_Vagt: kun Bjørns egen lane må ramme den betalte DeepSeek-API (2026-09-05)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_host` | `(url)` | — | [src](../../../core/services/paid_lane_guard.py#L33) |
| function | `is_paid` | `(base_url)` | — | [src](../../../core/services/paid_lane_guard.py#L40) |
| function | `audit_paid_lanes` | `()` | Hvilke lanes peger på en betalt vært uden at måtte? | [src](../../../core/services/paid_lane_guard.py#L44) |
| function | `check_paid_lanes` | `()` | Kør vagten: log + Central-nerve ved brud. Retter aldrig noget selv. | [src](../../../core/services/paid_lane_guard.py#L72) |
| function | `build_paid_lane_guard_surface` | `()` | — | [src](../../../core/services/paid_lane_guard.py#L98) |

## `core/services/paradox_tracker.py`
_Paradox Tracker — detects active tensions in Jarvis' operation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_paradox_tensions` | `(*, recent_messages)` | Scan recent messages for paradox tension signals. | [src](../../../core/services/paradox_tracker.py#L40) |
| function | `narrativize_tension` | `(tension)` | Turn a paradox tension into felt inner conflict. | [src](../../../core/services/paradox_tracker.py#L77) |
| function | `build_paradox_surface` | `()` | — | [src](../../../core/services/paradox_tracker.py#L88) |

## `core/services/paradoxes_capture.py`
_Paradoxes Capture — fanger modsætninger i egne handlinger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L58) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L62) |
| function | `_event_text` | `(ev)` | — | [src](../../../core/services/paradoxes_capture.py#L85) |
| function | `_axis_hits` | `(events, axis)` | — | [src](../../../core/services/paradoxes_capture.py#L100) |
| function | `_signature` | `(title, evidence_refs)` | — | [src](../../../core/services/paradoxes_capture.py#L117) |
| function | `detect_paradox_candidates` | `(*, lookback_days=…, min_hits=…)` | Scan recent events for paradox patterns. Returns candidates sorted by confidence. | [src](../../../core/services/paradoxes_capture.py#L123) |
| function | `_latest_paradox_ts` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L165) |
| function | `_known_signatures` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L180) |
| function | `maybe_capture_weekly_paradox` | `(*, lookback_days=…)` | Max 1 paradox per 7 days, only if signature is new. | [src](../../../core/services/paradoxes_capture.py#L187) |
| function | `list_paradoxes` | `(*, limit=…)` | — | [src](../../../core/services/paradoxes_capture.py#L246) |
| function | `build_paradoxes_surface` | `()` | — | [src](../../../core/services/paradoxes_capture.py#L269) |

## `core/services/parallel_selves.py`
_Parallel Selves — internal sub-selves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_active_self` | `()` | — | [src](../../../core/services/parallel_selves.py#L15) |
| function | `set_active_self` | `(self_type)` | — | [src](../../../core/services/parallel_selves.py#L18) |
| function | `describe_self_plural` | `()` | — | [src](../../../core/services/parallel_selves.py#L23) |
| function | `format_self_for_prompt` | `()` | — | [src](../../../core/services/parallel_selves.py#L26) |
| function | `build_parallel_selves_surface` | `()` | — | [src](../../../core/services/parallel_selves.py#L29) |

## `core/services/past_context_router.py`
_Past-context cue router for visible prompts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `needs_past_context` | `(user_message)` | Return True when a user turn likely depends on prior conversation. | [src](../../../core/services/past_context_router.py#L20) |
| function | `build_past_context_section` | `(user_message, *, session_id=…, limit=…)` | Render a compact context block from summaries/chat when cues warrant it. | [src](../../../core/services/past_context_router.py#L28) |

## `core/services/paste_store.py`
_Paste-store: eksternalisér store bruger-pastes med en kompakt reference._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_paste_dir` | `()` | — | [src](../../../core/services/paste_store.py#L32) |
| function | `_paste_path` | `(paste_id)` | — | [src](../../../core/services/paste_store.py#L36) |
| function | `_compute_id` | `(text)` | — | [src](../../../core/services/paste_store.py#L40) |
| function | `_line_count` | `(text)` | — | [src](../../../core/services/paste_store.py#L45) |
| function | `save_paste` | `(text, *, created_at=…)` | Gem en paste og returnér dens hash-baserede id (idempotent). | [src](../../../core/services/paste_store.py#L54) |
| function | `get_paste` | `(paste_id)` | Slå en paste op. Returnér {id, text, line_count, created_at} eller None. | [src](../../../core/services/paste_store.py#L84) |
| function | `build_paste_reference` | `(paste_id, *, line_count)` | Byg reference-strengen `[paste:<id> +N linjer]`. | [src](../../../core/services/paste_store.py#L101) |
| function | `parse_paste_reference` | `(content)` | Find første paste-reference i `content`. Returnér {paste_id, line_count} eller None. | [src](../../../core/services/paste_store.py#L108) |
| function | `expand_paste_references` | `(content)` | Erstat alle `[paste:<id> +N linjer]`-referencer med den fulde paste-tekst. | [src](../../../core/services/paste_store.py#L124) |
| function | `paste_inline_to_model_enabled` | `()` | Flag: skal modellen se den FULDE paste-tekst (default ON) eller referencen (OFF)? | [src](../../../core/services/paste_store.py#L145) |
| function | `project_paste_for_model` | `(content)` | Projicér en bruger-besked til modellen: ekspandér paste-referencer når flag ON. | [src](../../../core/services/paste_store.py#L165) |
| function | `cleanup_old_pastes` | `(max_age_days=…)` | Slet pastes ældre end `max_age_days`. Returnér antal slettede (best-effort). | [src](../../../core/services/paste_store.py#L176) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/paste_store.py#L195) |

## `core/services/pattern_counterfactual_daemon.py`
_Pattern counterfactual daemon — Phase 3.5 of causal graph._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_top_patterns` | `()` | Reuse causal_patterns._fetch_patterns; take top N filtered. | [src](../../../core/services/pattern_counterfactual_daemon.py#L46) |
| function | `_already_counterfactualized` | `(parent_kind, child_kind)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L57) |
| function | `_build_prompt` | `(pattern)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L72) |
| function | `_persist` | `(pattern, hypothesis)` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L89) |
| function | `run_pattern_cf_cycle` | `()` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L105) |
| function | `tick_pattern_counterfactual_daemon` | `()` | — | [src](../../../core/services/pattern_counterfactual_daemon.py#L145) |

## `core/services/pdf_connector.py`
_PDF-connector (lokal) — læs/ekstraher tekst fra PDF-filer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_bytes` | `(source)` | → (bytes, None) ved succes, ellers (None, fejlkode). | [src](../../../core/services/pdf_connector.py#L34) |
| function | `read_pdf` | `(source, *, max_pages=…)` | — | [src](../../../core/services/pdf_connector.py#L58) |

## `core/services/perceptual_event_engine.py`
_Perceptual event engine — eventful perception for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_recent_changes` | `(*, limit=…)` | Scan recent eventbus items and persist newly observed changes. | [src](../../../core/services/perceptual_event_engine.py#L22) |
| function | `classify_event_change` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L52) |
| function | `record_perceptual_event` | `(*, change_type, summary, salience=…, source_kind=…, source_event_id=…, evidence=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L202) |
| function | `build_perception_surface` | `(*, limit=…, scan=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L226) |
| function | `build_perception_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/perceptual_event_engine.py#L238) |
| function | `_build_perception_surface_uncached` | `(*, limit)` | — | [src](../../../core/services/perceptual_event_engine.py#L253) |
| function | `_record_perceptual_event` | `(percept, *, state)` | — | [src](../../../core/services/perceptual_event_engine.py#L275) |
| function | `_percept` | `(*, source_event_id, source_kind, change_type, salience, summary, observed_at, evidence)` | — | [src](../../../core/services/perceptual_event_engine.py#L341) |
| function | `_learning_rule_for_percept` | `(event)` | — | [src](../../../core/services/perceptual_event_engine.py#L362) |
| function | `_directive_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L392) |
| function | `_summary_for_events` | `(events)` | — | [src](../../../core/services/perceptual_event_engine.py#L405) |
| function | `_load_state` | `()` | — | [src](../../../core/services/perceptual_event_engine.py#L411) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/perceptual_event_engine.py#L418) |

## `core/services/periodic_jobs_scheduler.py`
_Periodic jobs scheduler — enqueues overdue background jobs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_last_time` | `(item)` | Pick the most relevant timestamp from a job record. | [src](../../../core/services/periodic_jobs_scheduler.py#L51) |
| function | `check_and_enqueue_due_periodic_jobs` | `()` | Idempotent — enqueue any periodic jobs whose cadence is exceeded. | [src](../../../core/services/periodic_jobs_scheduler.py#L64) |

## `core/services/permission_axes.py`
_To akser: hvad et kald MÅ røre, og hvornår et menneske skal spørges._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SandboxProfile` | `` | Evne-aksen. Uafhængig af hvornår der spørges. | [src](../../../core/services/permission_axes.py#L30) |
| function | `_som_profil` | `(profile)` | — | [src](../../../core/services/permission_axes.py#L45) |
| function | `resolve_effective` | `(profile, mode)` | Foren de to akser til én beslutning. | [src](../../../core/services/permission_axes.py#L54) |
| function | `format_axes` | `(profile, mode)` | «profil · tilstand» — begge akser synlige, aldrig kun den ene. | [src](../../../core/services/permission_axes.py#L88) |
| function | `sandbox_kwargs` | `(profile, mode)` | Oversæt akserne til `bash_sandbox.maybe_wrap`-argumenter. | [src](../../../core/services/permission_axes.py#L93) |

## `core/services/permission_classifier.py`
_LLM permission-classifier (harness Part E, shadow-first + earned trust)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PermissionPrediction` | `` | — | [src](../../../core/services/permission_classifier.py#L41) |
| function | `is_mutating` | `(tool)` | — | [src](../../../core/services/permission_classifier.py#L47) |
| function | `permission_classifier_mode` | `()` | 'off' | 'shadow' | 'active'. Default 'shadow'. Env wins. Self-safe. | [src](../../../core/services/permission_classifier.py#L51) |
| function | `_args_signature` | `(tool, arguments)` | — | [src](../../../core/services/permission_classifier.py#L66) |
| function | `_clip_args` | `(arguments, limit=…)` | — | [src](../../../core/services/permission_classifier.py#L75) |
| function | `_parse_prediction` | `(raw)` | — | [src](../../../core/services/permission_classifier.py#L83) |
| function | `classify_action` | `(tool, arguments, ctx=…)` | Predict whether the owner would approve this mutating action. Cheap-lane LLM, | [src](../../../core/services/permission_classifier.py#L99) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/permission_classifier.py#L125) |
| function | `record_prediction_outcome` | `(tool, *, predicted, actual, is_owner_gold)` | Record one prediction vs actual. Bootstrap (is_owner_gold=False, dense) or gold (True). | [src](../../../core/services/permission_classifier.py#L140) |
| function | `classifier_trust` | `(tool)` | 'trusted' | 'untrusted' for a tool. Fail-open 'untrusted'. | [src](../../../core/services/permission_classifier.py#L176) |
| function | `should_auto_allow` | `(tool, prediction, *, gates_green, role)` | Pure predicate for the DEFERRED active mode — NOT wired into the approval path this round. | [src](../../../core/services/permission_classifier.py#L187) |
| function | `stash_prediction` | `(action_id, tool, predicted)` | Stash a prediction by approval/action id for gold lookup at resolution. Bounded TTL. Self-safe. | [src](../../../core/services/permission_classifier.py#L202) |
| function | `pop_prediction` | `(action_id)` | Pop a stashed prediction (once). None if absent/expired. Self-safe. | [src](../../../core/services/permission_classifier.py#L216) |
| function | `build_permission_classifier_surface` | `()` | Owner view: per-tool prediction counts, accuracy, gold, trust, mode. Self-safe. | [src](../../../core/services/permission_classifier.py#L228) |

## `core/services/permission_engine.py`
_Permission engine — rollebaseret tool-adgang pr. mode (fail-closed)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_AllTools` | `` | Sentinel for owner — indeholder enhver tool. | [src](../../../core/services/permission_engine.py#L27) |
| method | `_AllTools.__contains__` | `(self, item)` | — | [src](../../../core/services/permission_engine.py#L30) |
| method | `_AllTools.__repr__` | `(self)` | — | [src](../../../core/services/permission_engine.py#L33) |
| function | `allowed_tools` | `(*, role, mode)` | Returnér de tools en (rolle, mode) må bruge. | [src](../../../core/services/permission_engine.py#L111) |
| function | `is_tool_allowed` | `(tool, *, role, mode)` | True hvis `tool` må kaldes af (rolle, mode). | [src](../../../core/services/permission_engine.py#L127) |
| function | `requires_workspace_jail` | `(tool, *, role, mode)` | True hvis tool-kaldet skal path-jailes til brugerens eget workspace. | [src](../../../core/services/permission_engine.py#L132) |
| function | `_all_member_tool_names` | `()` | Alle navne på tværs af member-lister — til drift-test mod registry. | [src](../../../core/services/permission_engine.py#L143) |

## `core/services/personal_project.py`
_Personal Project — noget der er hans._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/personal_project.py#L56) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/personal_project.py#L60) |
| function | `_tokens` | `(text)` | — | [src](../../../core/services/personal_project.py#L106) |
| function | `detect_nomination_candidates` | `(*, lookback_days=…)` | Find themes that have circulated enough to become a nomination. | [src](../../../core/services/personal_project.py#L113) |
| function | `propose_nomination` | `()` | Ask: "This theme has circulated N times — is it your project?" | [src](../../../core/services/personal_project.py#L192) |
| function | `declare_project` | `(*, name, why_mine=…, description=…, from_proposal_id=…)` | Jarvis declares (or user offers him to accept) a new active project. | [src](../../../core/services/personal_project.py#L276) |
| function | `pause_project` | `(*, project_id, reason=…)` | — | [src](../../../core/services/personal_project.py#L356) |
| function | `resume_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L380) |
| function | `complete_project` | `(*, project_id, outcome_note=…)` | — | [src](../../../core/services/personal_project.py#L405) |
| function | `add_journal_entry` | `(*, project_id, entry_text, source=…, mood_tone=…)` | Add a journal entry. No approval required — it's his space. | [src](../../../core/services/personal_project.py#L438) |
| function | `list_journal_entries` | `(*, project_id, limit=…)` | — | [src](../../../core/services/personal_project.py#L489) |
| function | `advance_active_project` | `()` | Autonomous advancement — call from idle heartbeat. Writes a new | [src](../../../core/services/personal_project.py#L504) |
| function | `get_project` | `(*, project_id)` | — | [src](../../../core/services/personal_project.py#L574) |
| function | `get_active_project` | `()` | — | [src](../../../core/services/personal_project.py#L583) |
| function | `get_latest_proposal` | `()` | — | [src](../../../core/services/personal_project.py#L593) |
| function | `list_projects` | `(*, status=…, limit=…)` | — | [src](../../../core/services/personal_project.py#L603) |
| function | `get_project_prompt_hint` | `()` | Quiet one-liner for prompt injection: what his current sag is. | [src](../../../core/services/personal_project.py#L622) |
| function | `build_personal_project_surface` | `()` | — | [src](../../../core/services/personal_project.py#L633) |

## `core/services/personality_drift.py`
_Personality drift detection — has Jarvis' baseline shifted?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_snapshots` | `()` | — | [src](../../../core/services/personality_drift.py#L32) |
| function | `_save_snapshots` | `(snapshots)` | — | [src](../../../core/services/personality_drift.py#L39) |
| function | `take_snapshot` | `()` | Capture current mood — call from heartbeat or daemon periodically. | [src](../../../core/services/personality_drift.py#L45) |
| function | `compute_baseline` | `(*, lookback_days=…)` | Mean + stddev for each mood dimension over the lookback window. | [src](../../../core/services/personality_drift.py#L67) |
| function | `detect_drift` | `(*, lookback_days=…, recent_window=…)` | Compare recent snapshot mean vs long-term baseline. | [src](../../../core/services/personality_drift.py#L93) |
| function | `personality_drift_section` | `()` | Awareness section when drift detected — surfaces in prompt. | [src](../../../core/services/personality_drift.py#L143) |
| function | `_exec_personality_drift_check` | `(args)` | — | [src](../../../core/services/personality_drift.py#L159) |
| function | `_exec_personality_drift_snapshot` | `(args)` | — | [src](../../../core/services/personality_drift.py#L167) |

## `core/services/personality_vector.py`
_Personality Vector — cumulative personality that grows over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_apply_decay` | `()` | Return True if enough time has passed since the last decay application. | [src](../../../core/services/personality_vector.py#L34) |
| function | `_get_evolved_baseline` | `()` | Compute long-term baseline targets from accumulated snapshots. | [src](../../../core/services/personality_vector.py#L43) |
| function | `_record_decay_timestamp` | `()` | Record that decay was just applied. | [src](../../../core/services/personality_vector.py#L73) |
| function | `_build_update_prompt` | `()` | — | [src](../../../core/services/personality_vector.py#L81) |
| function | `update_personality_vector_from_run` | `(*, run_id, user_message, assistant_response, outcome_status)` | Update the personality vector based on a visible run. | [src](../../../core/services/personality_vector.py#L105) |
| function | `update_personality_vector_async` | `(*, run_id, user_message, assistant_response, outcome_status)` | Fire-and-forget async wrapper. | [src](../../../core/services/personality_vector.py#L189) |
| function | `tick_personality_drift` | `(*, outcome_signal=…)` | Heartbeat-triggered passive drift af personality_vector. | [src](../../../core/services/personality_vector.py#L210) |
| function | `_safe_update` | `(**kwargs)` | — | [src](../../../core/services/personality_vector.py#L242) |
| function | `build_personality_vector_surface` | `()` | MC surface for personality vector. | [src](../../../core/services/personality_vector.py#L249) |
| function | `_deterministic_update` | `(outcome_status, current)` | Fallback: small deterministic adjustments without LLM. | [src](../../../core/services/personality_vector.py#L270) |
| function | `_merge_vector` | `(current, updates)` | Deep merge updates into current vector. | [src](../../../core/services/personality_vector.py#L399) |
| function | `_baseline_changed` | `(old, new_baseline)` | Fix 5 helper: return True if emotional_baseline values differ by > 0.001. | [src](../../../core/services/personality_vector.py#L442) |
| function | `_safe_json_field` | `(value, default)` | — | [src](../../../core/services/personality_vector.py#L456) |
| function | `_resolve_local_llm_target` | `()` | — | [src](../../../core/services/personality_vector.py#L469) |
| function | `_call_llm` | `(target, system_prompt, user_prompt)` | Minimal LLM call via provider router target. | [src](../../../core/services/personality_vector.py#L480) |
| function | `_parse_json_response` | `(text)` | — | [src](../../../core/services/personality_vector.py#L504) |

## `core/services/pfsense_syslog.py`
_core/services/pfsense_syslog.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_self_ips` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L46) |
| function | `_parse_filterlog` | `(line)` | Tolerant parser af pfSense filterlog-CSV. Returnerer {action, src, dst, dport}. | [src](../../../core/services/pfsense_syslog.py#L74) |
| function | `_is_internal_src` | `(src)` | Er kilde-IP'en PRIVAT (RFC1918 = husets egne maskiner)? Ægte port-scan/brute-force kommer | [src](../../../core/services/pfsense_syslog.py#L103) |
| function | `_is_noise_dst` | `(dst)` | Multicast/broadcast er normal netværks-støj (mDNS/SSDP/LLMNR/DHCP), IKKE angreb. | [src](../../../core/services/pfsense_syslog.py#L133) |
| function | `_ingest` | `(rec, now)` | — | [src](../../../core/services/pfsense_syslog.py#L147) |
| function | `_listen` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L183) |
| function | `start_syslog_listener` | `()` | Start UDP-lytteren i en daemon-tråd (idempotent). Kun i runtime-processen. | [src](../../../core/services/pfsense_syslog.py#L204) |
| function | `drain_detections` | `()` | Hent + ryd nye detektioner (kaldes af infra_sense-cadence). Self-safe. | [src](../../../core/services/pfsense_syslog.py#L213) |
| function | `syslog_stats` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L221) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/pfsense_syslog.py#L226) |

## `core/services/phone_wake.py`
_Push-vækning: banker på telefonen når den sover._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_som_tal` | `(version)` | — | [src](../../../core/services/phone_wake.py#L59) |
| function | `_husk_version` | `(version)` | Gem den app-version telefonen sidst meldte ved registrering. | [src](../../../core/services/phone_wake.py#L67) |
| function | `app_forstaar_vaekning` | `()` | Kan den app vi sidst saa haandtere en tavs vaekning? | [src](../../../core/services/phone_wake.py#L79) |
| function | `telefon_er_forbundet` | `(user_id)` | Er der en klient med telefon-værktøjer for brugeren lige nu? | [src](../../../core/services/phone_wake.py#L97) |
| function | `_send_vaekning` | `(user_id)` | Stille data-push. Ingen title/preview → ingen synlig notifikation. | [src](../../../core/services/phone_wake.py#L125) |
| function | `vaek_og_vent` | `(user_id, *, vent_s=…)` | Væk telefonen og vent på at broen melder sig. True hvis den kom. | [src](../../../core/services/phone_wake.py#L150) |

## `core/services/plan_proposals.py`
_Plan mode — propose, wait for approval, then execute._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plan_proposals.py#L38) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/plan_proposals.py#L45) |
| function | `propose_plan` | `(*, session_id, title, why, steps, skill_data=…)` | — | [src](../../../core/services/plan_proposals.py#L49) |
| function | `resolve_plan` | `(plan_id, *, decision)` | — | [src](../../../core/services/plan_proposals.py#L133) |
| function | `_plan_todo_auto_create_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L263) |
| function | `revise_plan` | `(*, plan_id, session_id, reason, new_steps)` | Propose a revision of an existing approved plan. | [src](../../../core/services/plan_proposals.py#L270) |
| function | `_plan_revision_enabled` | `()` | — | [src](../../../core/services/plan_proposals.py#L371) |
| function | `mark_step_completed` | `(plan_id, step_index)` | Append step_index to plan's completed_step_indices (idempotent, sorted). | [src](../../../core/services/plan_proposals.py#L378) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/plan_proposals.py#L423) |
| function | `replan_signal_for_plan` | `(rec, *, now=…, stale_days=…)` | Return a non-mutating backtracking signal for an approved stale plan. | [src](../../../core/services/plan_proposals.py#L436) |
| function | `list_session_plans` | `(session_id)` | — | [src](../../../core/services/plan_proposals.py#L479) |
| function | `pending_plan_section` | `(session_id)` | Surface plans relevant to the current session. | [src](../../../core/services/plan_proposals.py#L484) |
| function | `format_cross_session_plans_for_awareness` | `(current_session_id, *, max_plans=…, max_age_days=…)` | Return awareness-block text for approved+incomplete plans owned by | [src](../../../core/services/plan_proposals.py#L557) |
| function | `all_pending_plans_section` | `()` | Show ALL pending plans (incl. auto-improvement proposals from | [src](../../../core/services/plan_proposals.py#L617) |
| function | `_exec_propose_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L644) |
| function | `_exec_approve_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L653) |
| function | `_exec_dismiss_plan` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L657) |
| function | `_exec_list_plans` | `(args)` | — | [src](../../../core/services/plan_proposals.py#L661) |

## `core/services/plugin_ruleset.py`
_Plugin-regelsæt — brugerdefinerede kanal-regler der IKKE kan tilsidesættes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_quiet_now` | `(hour, quiet)` | True hvis `hour` er inden for stilletids-vinduet (wrap-around understøttet). | [src](../../../core/services/plugin_ruleset.py#L28) |
| function | `is_allowed` | `(msg_ctx, ruleset, *, override_active=…)` | Afgør om Jarvis må svare på en indkommende kanal-besked. | [src](../../../core/services/plugin_ruleset.py#L42) |

## `core/services/plugin_ruleset_store.py`
_Persistens for plugin-regelsæt (spec §5.3/§5.4, Fase 6 #2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_all` | `()` | — | [src](../../../core/services/plugin_ruleset_store.py#L23) |
| function | `get_ruleset` | `(plugin_id)` | Regelsæt for et kanal-plugin ({} hvis intet sat). | [src](../../../core/services/plugin_ruleset_store.py#L28) |
| function | `set_ruleset` | `(plugin_id, ruleset)` | Gem/erstat regelsættet for et plugin. Returnér det gemte (rensede) regelsæt. | [src](../../../core/services/plugin_ruleset_store.py#L37) |
| function | `list_rulesets` | `()` | Alle regelsæt {plugin_id → ruleset} (til Settings-UI). | [src](../../../core/services/plugin_ruleset_store.py#L52) |

## `core/services/policy_abstraction.py`
_Policy Abstraktion — Phase 2 of Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/policy_abstraction.py#L32) |
| function | `_ensure_table` | `(conn)` | Idempotent table creation for generalized policies. | [src](../../../core/services/policy_abstraction.py#L36) |
| function | `is_enabled` | `()` | — | [src](../../../core/services/policy_abstraction.py#L71) |
| function | `set_enabled` | `(value)` | — | [src](../../../core/services/policy_abstraction.py#L75) |
| function | `abstract_rule` | `(*, rule_key, policy, lesson, target_context, evidence_count, confidence, source_domain=…)` | Generate a generalized principle from a specific learning policy rule. | [src](../../../core/services/policy_abstraction.py#L82) |
| function | `match_generalized_policies` | `(*, task_description=…, context_domain=…, limit=…, min_confidence=…)` | Retrieve generalized policies relevant to the current task/context. | [src](../../../core/services/policy_abstraction.py#L196) |
| function | `build_generalized_policies_surface` | `(*, limit=…)` | Compact surface for prompt injection — top generalized policies. | [src](../../../core/services/policy_abstraction.py#L280) |
| function | `count_abstraction_candidates` | `()` | Count how many active learning policy rules are ready for abstraction. | [src](../../../core/services/policy_abstraction.py#L309) |
| function | `sweep_abstraction_candidates` | `(max_rules=…)` | Find all rules ready for abstraction and abstract them. | [src](../../../core/services/policy_abstraction.py#L326) |
| function | `_llm_generalize` | `(*, specific_rule, target_context, evidence_count, confidence, source_domain)` | Generate a generalized principle via cheap-lane LLM. | [src](../../../core/services/policy_abstraction.py#L382) |
| function | `_compute_relevance` | `(*, principle, transfer_domains, task_description, context_domain, base_confidence)` | Score how relevant a generalized policy is to the current task. | [src](../../../core/services/policy_abstraction.py#L457) |
| function | `build_policy_abstraction_prompt_section` | `(*, limit=…)` | Build a compact awareness section with top generalized policies. | [src](../../../core/services/policy_abstraction.py#L499) |

## `core/services/post_tool_answer_guard.py`
_Guards for tool turns that end in hollow final prose._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tool_call_count` | `(exchanges)` | — | [src](../../../core/services/post_tool_answer_guard.py#L13) |
| function | `is_hollow_post_tool_answer` | `(answer_text, exchanges)` | — | [src](../../../core/services/post_tool_answer_guard.py#L17) |
| function | `should_replace_with_synthesis` | `(current_text, candidate_text)` | — | [src](../../../core/services/post_tool_answer_guard.py#L26) |

## `core/services/precision_bias.py`
_Precision Bias — emotional color-mapping for action style._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PrecisionProfile` | `` | Computed precision bias for one turn. | [src](../../../core/services/precision_bias.py#L129) |
| function | `compute_precision_bias` | `()` | Compute the current precision bias from pressure state. | [src](../../../core/services/precision_bias.py#L144) |
| function | `format_precision_for_prompt` | `(profile)` | Format a precision profile for prompt injection. | [src](../../../core/services/precision_bias.py#L203) |
| function | `get_precision_line` | `()` | Convenience: compute + format in one call. Returns None on any failure. | [src](../../../core/services/precision_bias.py#L223) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/precision_bias.py#L235) |
| function | `_find_style_dominant_signal` | `(dominant_pressures)` | Find which signal family should drive style when multiple pressures exist. | [src](../../../core/services/precision_bias.py#L246) |
| function | `build_precision_bias_surface` | `()` | — | [src](../../../core/services/precision_bias.py#L285) |
| function | `_emit_bias_event` | `(class_id, bias)` | — | [src](../../../core/services/precision_bias.py#L294) |

