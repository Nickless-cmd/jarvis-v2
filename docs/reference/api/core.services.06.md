# `core.services.06` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_watch.py`
_core/services/central_watch.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_watch.py#L48) |
| function | `_notify_owner` | `(title, message, importance)` | — | [src](../../../core/services/central_watch.py#L56) |
| function | `_raise_flag` | `(cluster, nerve, *, severity, message, importance=…, make_incident=…)` | Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe. | [src](../../../core/services/central_watch.py#L70) |
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L103) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L108) |
| function | `_event_is_recent` | `(r, *, max_age_min=…)` | True hvis event-record er nyere end max_age_min. Fail-open ved ukendt/uparsbar | [src](../../../core/services/central_watch.py#L323) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen NYLIGT. Cross-proces. | [src](../../../core/services/central_watch.py#L338) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L352) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, failed) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L360) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra NYLIGE tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L376) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L394) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L403) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L417) |

## `core/services/central_white_rabbit.py`
_Follow the White Rabbit — serendipitets-motoren._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dark_doors` | `()` | Mørke/stille nerver ingen rører — de uåbnede døre. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L25) |
| function | `follow_rabbit` | `(*, seed=…)` | Vælg én uåbnet dør at undre sig over — ren ikke-målrettet udforskning. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L36) |
| function | `_observe` | `(door, total)` | — | [src](../../../core/services/central_white_rabbit.py#L49) |
| function | `build_white_rabbit_surface` | `()` | — | [src](../../../core/services/central_white_rabbit.py#L58) |
| function | `record_white_rabbit` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_white_rabbit.py#L62) |

## `core/services/central_xproc.py`
_Cross-proces trace-tee for Den Intelligente Central._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `process_role` | `()` | 'api' (visible-lane, JARVIS_ENABLE_RUNTIME_SERVICES=0) eller 'runtime' (daemons). | [src](../../../core/services/central_xproc.py#L37) |
| function | `maybe_publish` | `()` | Throttled publish af denne proces' feed + sundhed. Kaldt fra trace-record (hot path) | [src](../../../core/services/central_xproc.py#L43) |
| function | `_publish_now` | `()` | — | [src](../../../core/services/central_xproc.py#L70) |
| function | `foreign_feeds` | `(own_role)` | Records fra ALLE andre processer end ens egen (ens egen har vi in-memory, friskere). | [src](../../../core/services/central_xproc.py#L120) |
| function | `merged_timeseries` | `()` | Alle processers per-nerve tidsserie merget: nerve-key → {proces: {latest,count,meta,recent}}. | [src](../../../core/services/central_xproc.py#L139) |
| function | `all_health` | `()` | Per-proces sundhed for hver kendt proces der har publiceret (ikke udløbet). Self-safe. | [src](../../../core/services/central_xproc.py#L161) |

## `core/services/channel_inbound.py`
_Kanal-plugin inbound-routing (spec §5.2/§5.3, Fase 5 Lag 1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_builtin_channel_plugins` | `()` | Idempotent registrering af indbyggede kanal-plugins (kaldes fra plugins-route). | [src](../../../core/services/channel_inbound.py#L33) |
| function | `resolve_inbound_mode` | `(requested_mode=…, *, author_role=…, override_active=…)` | Afgør den effektive mode for en indkommende kanal-besked (§18.9). | [src](../../../core/services/channel_inbound.py#L45) |
| function | `route_inbound` | `(**kwargs)` | Auth-cluster GENNEM Den Intelligente Central (observe). A2+A4: plugin-hardblock + | [src](../../../core/services/channel_inbound.py#L63) |
| function | `_route_inbound_impl` | `(*, plugin_id, channel, author_role=…, author_user_id=…, text=…, hour=…, now=…, mode=…, override_active=…)` | Afgør om en indkommende kanal-besked må nå Jarvis (plugin_ruleset hardblock), | [src](../../../core/services/channel_inbound.py#L84) |

## `core/services/chat_sessions.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_tool_result_for_reconstruct` | `(result_id)` | Serve-on-read loader: slå et gammelt tool-resultat op fra tool_result_store. | [src](../../../core/services/chat_sessions.py#L18) |
| function | `_content_json_for_row` | `(role, content, raw_json)` | Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort, | [src](../../../core/services/chat_sessions.py#L36) |
| function | `create_chat_session` | `(*, title=…, workspace_kind=…, workspace_root=…, team_id=…)` | — | [src](../../../core/services/chat_sessions.py#L51) |
| function | `get_or_create_named_session` | `(session_id, title)` | Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny). | [src](../../../core/services/chat_sessions.py#L86) |
| function | `_teams` | `()` | Lazy-import af teams-modulet (undgår import-cyklus ved opstart). | [src](../../../core/services/chat_sessions.py#L117) |
| function | `list_chat_sessions` | `(*, user_id=…)` | List chat sessions, optionally filtered to one user. | [src](../../../core/services/chat_sessions.py#L123) |
| function | `_make_snippet` | `(content, query, width=…)` | Byg et kort uddrag centreret om første match (case-insensitive). | [src](../../../core/services/chat_sessions.py#L202) |
| function | `search_chat_sessions` | `(query, *, user_id=…, limit=…)` | Søg sessioner på titel ELLER besked-indhold (user/assistant). | [src](../../../core/services/chat_sessions.py#L217) |
| function | `get_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L294) |
| function | `set_session_workspace` | `(session_id, *, kind, root)` | Bind (eller skift) en sessions Code-mode workspace. | [src](../../../core/services/chat_sessions.py#L346) |
| function | `append_chat_message` | `(*, session_id, role, content, created_at=…, tool_name=…, tool_arguments=…, user_id=…, workspace_name=…, reasoning_content=…, content_json=…)` | — | [src](../../../core/services/chat_sessions.py#L361) |
| function | `_infer_tool_name_from_content` | `(content)` | — | [src](../../../core/services/chat_sessions.py#L497) |
| function | `recent_chat_session_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L504) |
| function | `chat_session_messages_since_last_compact` | `(session_id, *, max_total=…)` | Hent ALT efter seneste compact_marker (eller hele session hvis ingen). | [src](../../../core/services/chat_sessions.py#L531) |
| function | `recent_chat_session_messages_by_user_turns` | `(session_id, *, user_turns=…, max_total=…)` | Hent de seneste N *user-turns* og alt der hører til dem. | [src](../../../core/services/chat_sessions.py#L592) |
| function | `_ensure_compact_marker_git_sha_column` | `()` | Add git_sha column to chat_messages if it doesn't exist (idempotent migration). | [src](../../../core/services/chat_sessions.py#L668) |
| function | `store_compact_marker` | `(session_id, summary_text, git_sha=…)` | Store a compact marker for the session. Returns the marker message_id. | [src](../../../core/services/chat_sessions.py#L680) |
| function | `get_compact_marker_with_sha` | `(session_id)` | Return (summary, git_sha) of the most recent compact marker, or (None, None). | [src](../../../core/services/chat_sessions.py#L711) |
| function | `get_compact_marker` | `(session_id)` | Return the most recent compact marker summary for the session, or None. | [src](../../../core/services/chat_sessions.py#L735) |
| function | `recent_chat_tool_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L753) |
| function | `rename_chat_session` | `(session_id, *, title)` | — | [src](../../../core/services/chat_sessions.py#L778) |
| function | `delete_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L792) |
| function | `_session_summary` | `(row)` | — | [src](../../../core/services/chat_sessions.py#L802) |
| function | `_normalize_title` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L814) |
| function | `_preview_text` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L821) |
| function | `_time_label` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L828) |
| function | `parse_channel_from_session_title` | `(title)` | Parse channel type and detail from a session title. | [src](../../../core/services/chat_sessions.py#L836) |
| function | `get_session_owner` | `(session_id)` | Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel. | [src](../../../core/services/chat_sessions.py#L866) |

## `core/services/cheap_lane_balancer.py`
_Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BalancerSlot` | `` | Immutable identity of a (provider, model) lane. | [src](../../../core/services/cheap_lane_balancer.py#L19) |
| method | `BalancerSlot.slot_id` | `(self)` | — | [src](../../../core/services/cheap_lane_balancer.py#L30) |
| class | `SlotState` | `` | Per-slot mutable runtime state. Persisted to JSON (timestamps deque is in-memory only). | [src](../../../core/services/cheap_lane_balancer.py#L35) |
| function | `_provider_router_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L67) |
| function | `_router_enabled_models` | `()` | Return list of dicts {provider, model, enabled, auth_profile, lane} | [src](../../../core/services/cheap_lane_balancer.py#L74) |
| function | `_credentials_ready` | `(provider, auth_profile)` | Check if provider has working credentials. Wraps existing helper. | [src](../../../core/services/cheap_lane_balancer.py#L104) |
| function | `_provider_metadata` | `(provider)` | Lookup provider's static config (rpm_limit, daily_limit, base_url, etc.). | [src](../../../core/services/cheap_lane_balancer.py#L113) |
| function | `_state_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L130) |
| function | `_state_to_dict` | `(state)` | Serialize SlotState to JSON-safe dict (skips deque). | [src](../../../core/services/cheap_lane_balancer.py#L137) |
| function | `_state_from_dict` | `(d)` | — | [src](../../../core/services/cheap_lane_balancer.py#L155) |
| function | `_load_state` | `()` | Load all slot-states from disk. Returns empty dict on missing/corrupt file. | [src](../../../core/services/cheap_lane_balancer.py#L172) |
| function | `_save_state` | `(states)` | Atomic write to state file. | [src](../../../core/services/cheap_lane_balancer.py#L190) |
| function | `_save_state_debounced` | `(states)` | — | [src](../../../core/services/cheap_lane_balancer.py#L209) |
| function | `_ensure_state` | `(states, slot_id)` | Get-or-create slot state. Mutates `states` in place. | [src](../../../core/services/cheap_lane_balancer.py#L219) |
| function | `_today_iso` | `(now=…)` | Returns UTC date string. Override hookable via module-level _datetime_for_today. | [src](../../../core/services/cheap_lane_balancer.py#L238) |
| function | `_count_recent_calls` | `(timestamps, now, window_seconds)` | Count timestamps falling within [now - window, now]. | [src](../../../core/services/cheap_lane_balancer.py#L244) |
| function | `_compute_weight` | `(slot, state, now)` | Returns non-negative weight; 0 means slot is ineligible right now. | [src](../../../core/services/cheap_lane_balancer.py#L250) |
| function | `_register_failure` | `(state, error_kind, *, retry_after_s=…, now)` | Update state after a failed call. | [src](../../../core/services/cheap_lane_balancer.py#L289) |
| function | `_register_success` | `(state, now)` | Update state after a successful call. | [src](../../../core/services/cheap_lane_balancer.py#L321) |
| function | `_is_dns_or_connection_error` | `(error_kind, exc=…)` | True if error indicates network-level (provider-wide) issue, not slot-specific. | [src](../../../core/services/cheap_lane_balancer.py#L338) |
| function | `_register_provider_wide_failure` | `(states, pool, provider, now, *, reason, cooldown_s=…)` | Apply cooldown to ALL slots from `provider`. Returns number of slots affected. | [src](../../../core/services/cheap_lane_balancer.py#L356) |
| function | `_select_slot` | `(states, pool, now)` | Pick a slot via weighted-random; returns None if all blocked. | [src](../../../core/services/cheap_lane_balancer.py#L399) |
| function | `_call_provider_chat` | `(*, provider, model, auth_profile, base_url, message)` | Wrapper around cheap_provider_runtime._execute_provider_chat. | [src](../../../core/services/cheap_lane_balancer.py#L437) |
| function | `_append_recent_call` | `(slot_id, daemon, status, latency_ms, *, error=…)` | — | [src](../../../core/services/cheap_lane_balancer.py#L462) |
| function | `recent_calls` | `()` | Returns ring-buffer of last 75 calls (newest first). | [src](../../../core/services/cheap_lane_balancer.py#L480) |
| function | `call_balanced` | `(*, prompt, daemon_name=…, max_retries=…)` | Pick a slot via weighted-random; execute; on failure retry next slot. | [src](../../../core/services/cheap_lane_balancer.py#L485) |
| function | `build_slot_pool` | `()` | Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS. | [src](../../../core/services/cheap_lane_balancer.py#L673) |
| function | `reset_slot` | `(slot_id)` | Clear breaker, cooldown, and consecutive-failure streak for a slot. | [src](../../../core/services/cheap_lane_balancer.py#L718) |
| function | `disable_slot` | `(slot_id)` | Force a slot's weight to 0 until enable_slot is called. | [src](../../../core/services/cheap_lane_balancer.py#L730) |
| function | `enable_slot` | `(slot_id)` | Re-enable a manually-disabled slot. | [src](../../../core/services/cheap_lane_balancer.py#L739) |
| function | `refresh_pool` | `()` | Re-build the slot pool from provider_router.json. Returns current size. | [src](../../../core/services/cheap_lane_balancer.py#L748) |
| function | `_is_enabled` | `()` | Check RuntimeSettings.daemon_balancer_enabled. Default True. | [src](../../../core/services/cheap_lane_balancer.py#L759) |
| function | `balancer_snapshot` | `()` | Return full state surface for Mission Control telemetry. | [src](../../../core/services/cheap_lane_balancer.py#L768) |

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L24) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L204) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L205) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L222) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L232) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L236) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L269) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L343) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L366) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L448) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Map composer's thinking_mode to the right Deepseek model alias. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L548) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L584) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L639) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L666) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L693) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L718) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L735) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L759) |
| function | `_ofa_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L774) |
| function | `_ofa_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L781) |
| function | `_ofa_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L788) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L793) |
| function | `_arko_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L837) |
| function | `_arko_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L844) |
| function | `_arko_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L851) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L856) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L888) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message)` | Call the local Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L956) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1010) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1041) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1066) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1117) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1170) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1193) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1206) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1230) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1251) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1271) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1315) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1327) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1349) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1360) |

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
| function | `_is_public_proxy` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L299) |
| function | `select_cheap_lane_target` | `(*, skip_providers=…, task_kind=…)` | Pick a cheap-lane provider. See task_kind notes above for routing. | [src](../../../core/services/cheap_provider_runtime_selection.py#L303) |
| function | `execute_cheap_lane_via_pool` | `(*, message, skip_providers=…, task_kind=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L379) |
| function | `_public_safe_candidates` | `()` | Build the public-safe candidate pool: ollamafreeapi (lane=cheap) | [src](../../../core/services/cheap_provider_runtime_selection.py#L495) |
| function | `select_public_safe_cheap_lane_target` | `()` | Pick the highest-priority ready public-safe provider for cheap-lane work. | [src](../../../core/services/cheap_provider_runtime_selection.py#L574) |
| function | `execute_public_safe_cheap_lane` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L615) |
| function | `_configured_cheap_candidates` | `(*, include_public_proxy, skip_providers=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L664) |
| function | `_candidate_quota_snapshot` | `(candidate)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L771) |
| function | `_fallback_after_failure` | `(*, failed_provider, failed_model)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L828) |
| function | `_candidate_adaptive_snapshot` | `(candidate, *, state=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L845) |
| function | `_record_provider_success` | `(*, provider, model, latency_ms, quality_score, smoke_test)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L886) |
| function | `_register_provider_failure` | `(*, provider, model, auth_profile, error, smoke_test=…)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L937) |
| function | `_decode_state_metadata` | `(state)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1002) |
| function | `_rolling_average` | `(*, current_avg, current_count, new_value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1013) |
| function | `_smoke_quality_score` | `(*, expected, actual)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1019) |
| function | `_normalize_probe_text` | `(value)` | — | [src](../../../core/services/cheap_provider_runtime_selection.py#L1029) |

## `core/services/cheap_provider_runtime_streaming.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_streaming.py#L24) |
| function | `_iter_openai_compatible_chat_events` | `(*, provider, model, auth_profile, base_url, messages, tools=…, temperature=…, top_p=…)` | Stream OpenAI-compatible /chat/completions deltas via SSE. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L33) |
| function | `_list_openai_codex_models` | `()` | Static model list for OpenAI Codex (ChatGPT Plus OAuth). | [src](../../../core/services/cheap_provider_runtime_streaming.py#L315) |
| function | `_execute_openai_codex_chat` | `(*, model, auth_profile, base_url, message)` | Execute a chat call via OpenAI's Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L327) |
| function | `_convert_tools_to_responses_format` | `(tools)` | Convert Chat-Completions tool defs to Responses API format. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L480) |
| function | `_iter_openai_codex_chat_events` | `(*, model, auth_profile, base_url, message, tools=…, input_items=…)` | Stream raw SSE events from the OpenAI Codex Responses API. | [src](../../../core/services/cheap_provider_runtime_streaming.py#L512) |

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_chronicle_consolidation_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L36) |
| function | `refresh_runtime_chronicle_consolidation_signal_statuses` | `()` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L59) |
| function | `build_runtime_chronicle_consolidation_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L90) |
| function | `_extract_chronicle_consolidation_candidates` | `(*, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L123) |
| function | `_persist_chronicle_consolidation_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L280) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L349) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L368) |
| function | `_chronicle_type` | `(*, cadence_state, promotion_type, has_remembered_fact)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L406) |
| function | `_chronicle_weight` | `(*, cadence_state, has_promotion, contradiction_pressure, outcome_status)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L421) |
| function | `_focus_text` | `(outcome, cadence, *, domain_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L435) |
| function | `_summary_line` | `(*, chronicle_type, chronicle_focus)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L451) |
| function | `_grounding_mode` | `(*, has_private_state, has_temporal_promotion, has_remembered_fact, has_executive_contradiction)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L457) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L476) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L483) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L490) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L496) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L508) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L519) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L527) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/chronicle_consolidation_signal_tracking.py#L533) |

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
| function | `_is_planned_time_context` | `(line, matched_text)` | True hvis linjen indeholder ord der indikerer at tidspunktet er | [src](../../../core/services/claim_scanner.py#L234) |
| function | `_repair_claim` | `(line, category, matched_text)` | Apply category-specific repair to a line. | [src](../../../core/services/claim_scanner.py#L247) |
| function | `_system_footnote` | `(matched_text)` | 2026-07-06: byg en fodnote for en ⚙️ system-claim (IP/host/path) i den | [src](../../../core/services/claim_scanner.py#L290) |
| function | `_extract_number` | `(text)` | Extract the first number from a string for replacement. | [src](../../../core/services/claim_scanner.py#L306) |
| function | `_commit_exists` | `(h)` | True hvis `h` resolver til et commit i hovedrepoet. Fail-open: ved | [src](../../../core/services/claim_scanner.py#L333) |
| function | `flag_unknown_commit_hashes` | `(text, *, max_check=…)` | Markér backtick-wrappede commit-hashes der ikke findes i hovedrepoet. | [src](../../../core/services/claim_scanner.py#L352) |
| function | `_collect_unknown_commit_hash_footnotes` | `(text, *, max_check=…)` | 2026-07-06: samme detektion som flag_unknown_commit_hashes, men i stedet | [src](../../../core/services/claim_scanner.py#L383) |
| function | `scan_response` | `(text)` | Scan a response text for unverified factual claims and repair them. | [src](../../../core/services/claim_scanner.py#L411) |
| function | `scan_enabled` | `()` | Whether the Claim Scanner is active. | [src](../../../core/services/claim_scanner.py#L495) |
| function | `active_categories` | `()` | Return list of currently active scan categories. | [src](../../../core/services/claim_scanner.py#L503) |
| class | `FabricatedClaim` | `` | En work-claim der ikke har tool-evidens i samme run. | [src](../../../core/services/claim_scanner.py#L533) |
| function | `detect_fabricated_work_claims` | `(text, tool_call_names)` | Returnér liste af work-claims uden matching tool-evidens. | [src](../../../core/services/claim_scanner.py#L605) |
| function | `detect_shadow_claims` | `(text, tool_call_names)` | Shadow-mode måling: fakta-påstande (nye kategorier) uden tool-evidens | [src](../../../core/services/claim_scanner.py#L673) |
| function | `format_fabrication_warning` | `(claims)` | Byg system-besked til injektion ved næste turn. Tom hvis ingen claims. | [src](../../../core/services/claim_scanner.py#L700) |

## `core/services/clarification_classifier.py`
_Clarification classifier — score user-message ambiguity._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `score_message` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L39) |
| function | `clarification_prompt_section` | `(message)` | — | [src](../../../core/services/clarification_classifier.py#L78) |
| function | `_exec_classify_clarification` | `(args)` | — | [src](../../../core/services/clarification_classifier.py#L91) |
| function | `build_clarification_classifier_surface` | `()` | Mission Control surface — does not call the classifier (would need a | [src](../../../core/services/clarification_classifier.py#L116) |
| function | `_emit_classifier_event` | `(verdict, score)` | — | [src](../../../core/services/clarification_classifier.py#L128) |

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
| function | `record_visible_run_episode` | `(*, run_id, session_id=…, provider=…, model=…, status=…, user_message=…, assistant_text=…, error=…)` | Record a post-run episode grounded in the visible-run event trail. | [src](../../../core/services/cognitive_episodes.py#L176) |
| function | `derive_episode_fields` | `(*, trigger=…, outcome_status=…, summary=…, tool_names=…, error=…, user_message=…, assistant_text=…)` | Derive the five cognitive dimensions plus next-behavior policy. | [src](../../../core/services/cognitive_episodes.py#L209) |
| function | `build_cognitive_episode_surface` | `(*, limit=…)` | Return active directives for the conductor/prompt path. | [src](../../../core/services/cognitive_episodes.py#L295) |
| function | `build_cognitive_episode_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/cognitive_episodes.py#L325) |
| function | `_tool_names_for_run` | `(run_id)` | — | [src](../../../core/services/cognitive_episodes.py#L341) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/cognitive_episodes.py#L368) |
| function | `_summarize_visible_run` | `(*, status, tool_names, assistant_text, error)` | — | [src](../../../core/services/cognitive_episodes.py#L387) |
| function | `_fallback_summary` | `(*, status, tool_names, error)` | — | [src](../../../core/services/cognitive_episodes.py#L398) |
| function | `_confidence` | `(*, status, error, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L406) |
| function | `_uncertainty_sources` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L416) |
| function | `_self_check` | `(*, status, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L435) |
| function | `_what_would_change_mind` | `(*, interrupted, proposal_error)` | — | [src](../../../core/services/cognitive_episodes.py#L445) |
| function | `_salience` | `(*, interrupted, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L453) |
| function | `_attention_directive` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L461) |
| function | `_ignore_or_defer` | `(*, tool_heavy, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L479) |
| function | `_learning_lesson` | `(*, interrupted, proposal_error, status, tool_names)` | — | [src](../../../core/services/cognitive_episodes.py#L487) |
| function | `_policy_update` | `(*, interrupted, proposal_error, tool_heavy)` | — | [src](../../../core/services/cognitive_episodes.py#L505) |
| function | `_social_directive` | `(*, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L515) |
| function | `_user_state_hypothesis` | `(*, user_l, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L521) |
| function | `_perception_directive` | `(*, tool_names, interrupted)` | — | [src](../../../core/services/cognitive_episodes.py#L531) |
| function | `_observed_changes` | `(*, tool_names, status, error)` | — | [src](../../../core/services/cognitive_episodes.py#L539) |
| function | `_next_behavior` | `(*, interrupted, proposal_error, high_social_charge, tool_heavy, status)` | — | [src](../../../core/services/cognitive_episodes.py#L548) |
| function | `_prompt_priority` | `(*, interrupted, high_social_charge)` | — | [src](../../../core/services/cognitive_episodes.py#L569) |

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
| class | `_CachedNarrative` | `` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L72) |
| function | `_fingerprint` | `(state)` | — | [src](../../../core/services/cognitive_state_narrativizer.py#L85) |
| function | `_generate_in_background` | `(*, line_key, fingerprint, system_prompt, user_message)` | Run the LLM call in a background thread and update cache. | [src](../../../core/services/cognitive_state_narrativizer.py#L90) |
| function | `narrativize_line` | `(*, line_key, state, system_prompt, user_message_builder, fallback=…)` | Return an LLM-narrativized line for this state, or fallback. | [src](../../../core/services/cognitive_state_narrativizer.py#L122) |
| function | `cache_snapshot` | `()` | Expose current cache state for MC observability. | [src](../../../core/services/cognitive_state_narrativizer.py#L199) |

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
| function | `tick_conflict_daemon` | `(snapshot)` | Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode, | [src](../../../core/services/conflict_daemon.py#L18) |
| function | `_detect_conflict` | `(snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L40) |
| function | `_generate_conflict_phrase` | `(conflict_type, snapshot)` | — | [src](../../../core/services/conflict_daemon.py#L66) |
| function | `_store_conflict` | `(phrase, conflict_type)` | — | [src](../../../core/services/conflict_daemon.py#L115) |
| function | `get_latest_conflict` | `()` | — | [src](../../../core/services/conflict_daemon.py#L146) |
| function | `build_conflict_surface` | `()` | — | [src](../../../core/services/conflict_daemon.py#L150) |

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
| function | `get_last_conflict_trace` | `()` | Return the last conflict resolution trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L566) |
| function | `set_last_conflict_trace` | `(trace)` | Store the latest conflict trace for MC observability. | [src](../../../core/services/conflict_resolution.py#L575) |
| function | `build_conflict_resolution_surface` | `()` | — | [src](../../../core/services/conflict_resolution.py#L580) |
| function | `_emit_resolved_event` | `(winning, losing)` | — | [src](../../../core/services/conflict_resolution.py#L589) |

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
_Connector-katalog + per-bruger status (v1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_enabled_store` | `()` | — | [src](../../../core/services/connectors.py#L143) |
| function | `is_enabled` | `(user_id, connector_id)` | Default ON; kun False hvis brugeren eksplicit har slået den fra. | [src](../../../core/services/connectors.py#L148) |
| function | `set_enabled` | `(user_id, connector_id, enabled)` | — | [src](../../../core/services/connectors.py#L157) |
| function | `_provider_of` | `(c)` | OAuth-provider for en connector. Google-pakken deler provider='google'. | [src](../../../core/services/connectors.py#L171) |
| function | `_connected` | `(user_id, c)` | — | [src](../../../core/services/connectors.py#L176) |
| function | `oauth_request_for` | `(connector_id)` | Map et connector-id → (oauth_provider, scopes) til /api/oauth/{id}/start. | [src](../../../core/services/connectors.py#L182) |
| function | `list_for_user` | `(user_id)` | Hele kataloget beriget med per-bruger `connected` + `enabled`. | [src](../../../core/services/connectors.py#L194) |
| function | `_audit` | `(event, user_id, connector_id)` | — | [src](../../../core/services/connectors.py#L213) |
| function | `delete_for_user` | `(user_id, connector_id)` | Afbryd & slet: revoke hos provider (best-effort) + lokal token-wipe + ryd flag. | [src](../../../core/services/connectors.py#L221) |

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
| function | `_build_stillingtagen` | `(evidence)` | Construct 3-5 concrete stillingtagen (items requiring judgment). | [src](../../../core/services/consolidation_judge_daemon.py#L126) |
| function | `_render_judgments` | `(items, evidence)` | Present each stillingtagen to the LLM and force a verdict. | [src](../../../core/services/consolidation_judge_daemon.py#L207) |
| function | `_parse_judgment` | `(raw, item)` | Parse the LLM's judgment response. | [src](../../../core/services/consolidation_judge_daemon.py#L248) |
| function | `_enforce_judgments` | `(judgments)` | Carry out the concrete actions from judgments. | [src](../../../core/services/consolidation_judge_daemon.py#L279) |
| function | `_enforce_reject` | `(j)` | Handle rejected items — typically revoke or pause. | [src](../../../core/services/consolidation_judge_daemon.py#L289) |
| function | `_enforce_accept` | `(j)` | Handle accepted items — typically recommit or flag. | [src](../../../core/services/consolidation_judge_daemon.py#L322) |
| function | `_record_judgment_session` | `(judgments, evidence)` | Write the full judgment session as a private brain record. | [src](../../../core/services/consolidation_judge_daemon.py#L342) |
| function | `build_consolidation_judge_surface` | `()` | Build surface data for prompt injection. | [src](../../../core/services/consolidation_judge_daemon.py#L377) |
| function | `now_date_str` | `()` | — | [src](../../../core/services/consolidation_judge_daemon.py#L385) |

