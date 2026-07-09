# `core.tools.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/pause_and_ask_tools.py`
_pause_and_ask — structured clarification prompts mid-run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_pause_and_ask` | `(args)` | — | [src](../../../core/tools/pause_and_ask_tools.py#L28) |

## `core/tools/plan_revise_tool.py`
_Plan revision tool — revise_plan._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_revise_plan` | `(args)` | Tool handler for revise_plan. | [src](../../../core/tools/plan_revise_tool.py#L27) |

## `core/tools/pollinations_tools.py`
_Pollinations.ai tools — free, no-auth image + video generation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_api_key` | `()` | Read pollinations API key from runtime.json (never hardcoded). | [src](../../../core/tools/pollinations_tools.py#L57) |
| function | `_auth_headers` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L69) |
| function | `_generated_dir` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L77) |
| function | `_video_dir` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L82) |
| function | `_clamp` | `(value, lo, hi)` | — | [src](../../../core/tools/pollinations_tools.py#L87) |
| function | `_safe_filename` | `(prompt, gen_id, ext)` | — | [src](../../../core/tools/pollinations_tools.py#L91) |
| function | `_write_sidecar` | `(image_path, metadata)` | — | [src](../../../core/tools/pollinations_tools.py#L100) |
| function | `generate_image` | `(*, prompt, model=…, width=…, height=…, seed=…, nologo=…, enhance=…, save_dir=…)` | Fetch an image from Pollinations and save to disk. Returns result dict. | [src](../../../core/tools/pollinations_tools.py#L109) |
| function | `_exec_pollinations_image` | `(args)` | — | [src](../../../core/tools/pollinations_tools.py#L222) |
| function | `generate_video` | `(*, prompt, model=…, duration=…, aspect_ratio=…, audio=…, image_url=…, save_dir=…)` | Generate a video via pollinations.ai. Requires pollinations_api_key | [src](../../../core/tools/pollinations_tools.py#L261) |
| function | `_exec_pollinations_video` | `(args)` | — | [src](../../../core/tools/pollinations_tools.py#L377) |

## `core/tools/process_supervisor_tools.py`
_Tool wrappers for the process supervisor._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_process_spawn` | `(args)` | — | [src](../../../core/tools/process_supervisor_tools.py#L15) |
| function | `_exec_process_list` | `(args)` | — | [src](../../../core/tools/process_supervisor_tools.py#L25) |
| function | `_exec_process_stop` | `(args)` | — | [src](../../../core/tools/process_supervisor_tools.py#L29) |
| function | `_exec_process_tail` | `(args)` | — | [src](../../../core/tools/process_supervisor_tools.py#L36) |
| function | `_exec_process_remove` | `(args)` | — | [src](../../../core/tools/process_supervisor_tools.py#L43) |

## `core/tools/process_tools.py`
_Process and system health monitoring tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_service_status` | `(args)` | — | [src](../../../core/tools/process_tools.py#L8) |
| function | `_exec_process_list` | `(args)` | — | [src](../../../core/tools/process_tools.py#L28) |
| function | `_exec_disk_usage` | `(args)` | — | [src](../../../core/tools/process_tools.py#L55) |
| function | `_exec_memory_usage` | `(args)` | — | [src](../../../core/tools/process_tools.py#L88) |
| function | `_exec_tail_log` | `(args)` | Read recent journalctl lines for a systemd service. | [src](../../../core/tools/process_tools.py#L112) |
| function | `_exec_gpu_status` | `(_args)` | Snapshot of NVIDIA GPU state (memory, utilization, processes). | [src](../../../core/tools/process_tools.py#L142) |
| function | `_exec_run_pytest` | `(args)` | Run a specific pytest target so the model can verify behavior by test. | [src](../../../core/tools/process_tools.py#L177) |

## `core/tools/process_watcher_tools.py`
_Tool wrappers for the process_watcher service._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_add_process_watch` | `(args)` | — | [src](../../../core/tools/process_watcher_tools.py#L21) |
| function | `_exec_list_process_watches` | `(_args)` | — | [src](../../../core/tools/process_watcher_tools.py#L33) |
| function | `_exec_remove_process_watch` | `(args)` | — | [src](../../../core/tools/process_watcher_tools.py#L39) |
| function | `_exec_set_watch_enabled` | `(args)` | — | [src](../../../core/tools/process_watcher_tools.py#L44) |

## `core/tools/project_notes_tools.py`
_Tools for project-scoped persistent notes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_notes_path` | `()` | — | [src](../../../core/tools/project_notes_tools.py#L21) |
| function | `_exec_read_project_notes` | `(_args)` | — | [src](../../../core/tools/project_notes_tools.py#L31) |
| function | `_exec_update_project_notes` | `(args)` | — | [src](../../../core/tools/project_notes_tools.py#L58) |

## `core/tools/reasoning_store_tools.py`
_Reasoning Store tools for Jarvis — Phase 1 Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_recall_reasoning` | `(args)` | Retrieve stored reasoning conclusions, ranked by relevance. | [src](../../../core/tools/reasoning_store_tools.py#L19) |

## `core/tools/recall_memory_tools.py`
_Semantic recall tools — Jarvis-facing recall across all memory surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_excerpt_for` | `(record, source_table)` | — | [src](../../../core/tools/recall_memory_tools.py#L29) |
| function | `_timestamp_for` | `(record, source_table)` | — | [src](../../../core/tools/recall_memory_tools.py#L43) |
| function | `_exec_recall_memories` | `(args)` | — | [src](../../../core/tools/recall_memory_tools.py#L53) |

## `core/tools/recurring_scheduler_tools.py`
_Recurring scheduler tools — Jarvis can schedule repeating tasks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_interval` | `(interval, unit)` | Return interval in minutes, or None on bad input. | [src](../../../core/tools/recurring_scheduler_tools.py#L13) |
| function | `_exec_schedule_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L27) |
| function | `_exec_list_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L65) |
| function | `_exec_cancel_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L81) |
| function | `_exec_set_recurring_channel` | `(args)` | Sæt leverings-kanal på en recurring task (notif-routing spec §3.5). | [src](../../../core/tools/recurring_scheduler_tools.py#L186) |

## `core/tools/restart_self_tools.py`
_restart_self tool — fire-and-forget service restart that survives process death._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_restart_self` | `(args)` | — | [src](../../../core/tools/restart_self_tools.py#L68) |
| function | `_wait_for_gateway_connected` | `(max_wait=…, interval=…)` | Vent på at Discord gateway er connected efter restart. | [src](../../../core/tools/restart_self_tools.py#L123) |
| function | `_send_discord_restart_msg` | `(base_msg)` | Send restart-bekræftelse til Bjørn via Discord DM. | [src](../../../core/tools/restart_self_tools.py#L149) |
| function | `_try_fallback_channels` | `(base_msg)` | Forsøg at sende restart-bekræftelse via Telegram eller ntfy som fallback. | [src](../../../core/tools/restart_self_tools.py#L170) |
| function | `_claim_restart_file` | `()` | Atomic claim af restart-confirmation-fil — kun én uvicorn worker vinder. | [src](../../../core/tools/restart_self_tools.py#L206) |
| function | `send_pending_restart_confirmation` | `()` | On startup, check for a pending restart confirmation file and send it. | [src](../../../core/tools/restart_self_tools.py#L237) |

## `core/tools/screen_tool.py`
_Screen control tool — Jarvis can turn monitors on/off/standby._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_xset_dpms` | `(action)` | Run an xset dpms command and return structured result. | [src](../../../core/tools/screen_tool.py#L35) |
| function | `_xset_dpms_status` | `()` | Query DPMS status and return structured result. | [src](../../../core/tools/screen_tool.py#L82) |
| function | `_exec_screen_control` | `(args)` | Execute the screen control tool. | [src](../../../core/tools/screen_tool.py#L119) |

## `core/tools/semantic_search_tools.py`
_Semantic code search — natural language queries over the Jarvis codebase._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_definitions` | `(repo_root, dirs)` | Extract function/class definitions with file:line and docstring snippet. | [src](../../../core/tools/semantic_search_tools.py#L15) |
| function | `_keyword_prefilter` | `(definitions, query, limit=…)` | Quick keyword pre-filter to reduce candidates before expensive scoring. | [src](../../../core/tools/semantic_search_tools.py#L46) |
| function | `_score_with_llm` | `(query, candidates, top_k)` | Use LLM to rank candidates by semantic relevance to query. | [src](../../../core/tools/semantic_search_tools.py#L62) |
| function | `_read_context` | `(file, line, context=…)` | — | [src](../../../core/tools/semantic_search_tools.py#L92) |
| function | `_exec_semantic_search_code` | `(args)` | — | [src](../../../core/tools/semantic_search_tools.py#L103) |

## `core/tools/sensory_tools.py`
_Sensory archive tools — record and recall sensory experiences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_record_sensory_memory` | `(args)` | — | [src](../../../core/tools/sensory_tools.py#L18) |
| function | `_exec_recall_sensory_memories` | `(args)` | — | [src](../../../core/tools/sensory_tools.py#L79) |

## `core/tools/session_search.py`
_search_sessions tool — cross-channel session search with keyword and semantic modes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_channel_title_filter` | `(channel)` | — | [src](../../../core/tools/session_search.py#L60) |
| function | `_row_to_result` | `(row, *, match_type)` | — | [src](../../../core/tools/session_search.py#L69) |
| function | `_user_scope_clause` | `(user_id)` | Privatlivs-guard (multi-user northstar): begræns søgningen til sessions der | [src](../../../core/tools/session_search.py#L86) |
| function | `_keyword_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L104) |
| function | `_embed_query` | `(text)` | Embed text via Ollama. Returns None if unavailable. | [src](../../../core/tools/session_search.py#L145) |
| function | `_cosine_similarity` | `(a, b)` | — | [src](../../../core/tools/session_search.py#L164) |
| function | `_semantic_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L174) |
| function | `_merge_results` | `(keyword_results, semantic_results, limit)` | — | [src](../../../core/tools/session_search.py#L231) |
| function | `exec_search_sessions` | `(args)` | — | [src](../../../core/tools/session_search.py#L255) |

## `core/tools/simple_tools.py`
_Simple, general-purpose tools for Jarvis visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_canonicalize_workspace_target` | `(target)` | If target's basename is a canonical workspace file, force it to the | [src](../../../core/tools/simple_tools.py#L636) |
| function | `classify_command` | `(command)` | Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L732) |
| function | `classify_file_write` | `(path)` | Classify a file write: 'auto', 'approval', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L820) |
| function | `execute_tool` | `(name, arguments)` | Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1). | [src](../../../core/tools/simple_tools.py#L840) |
| function | `_execute_tool_impl` | `(name, arguments)` | Execute a tool call and return the result. | [src](../../../core/tools/simple_tools.py#L913) |
| function | `execute_tool_force` | `(name, arguments)` | Execute tool bypassing approval checks. Only call for user-approved requests. | [src](../../../core/tools/simple_tools.py#L1053) |
| function | `_record_tool_outcome_memory` | `(name, arguments, result, *, mode)` | — | [src](../../../core/tools/simple_tools.py#L1134) |
| function | `_force_write_file` | `(args)` | Write file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1778) |
| function | `_force_edit_file` | `(args)` | Edit file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1799) |
| function | `_force_bash` | `(args)` | Run bash command bypassing approval (blocked still blocked). | [src](../../../core/tools/simple_tools.py#L1826) |
| function | `_force_operator_bash` | `(args)` | Kør operator_bash direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1858) |
| function | `_force_operator_open_url` | `(args)` | Åbn URL direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1863) |
| function | `_force_operator_launch_app` | `(args)` | Start program direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1868) |
| function | `_force_operator_browser_evaluate` | `(args)` | Kør browser-JavaScript direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1873) |
| function | `_force_operator_kill_process` | `(args)` | Afslut proces direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1878) |
| function | `_force_operator_record_audio` | `(args)` | Optag lyd direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1883) |
| function | `get_tool_definitions` | `(role=…, scope=…)` | Return Ollama-compatible tool definitions, filtered by role + scope. | [src](../../../core/tools/simple_tools.py#L1944) |
| function | `_verify_hint_for` | `(tool, result)` | Build a brief, contextual verify-hint to attach to a mutation's result. | [src](../../../core/tools/simple_tools.py#L1982) |
| function | `format_tool_result_for_model` | `(name, result)` | Format a tool result as text for the model's context. | [src](../../../core/tools/simple_tools.py#L2031) |

## `core/tools/simple_tools_definitions.py`
_Tool definitions catalog for Jarvis' visible-lane tools._

_(no top-level classes or functions)_

## `core/tools/simple_tools_enforcement.py`
_Commit-enforcement (repo-state attachment) for Jarvis' tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_state_session_key` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L21) |
| function | `_repo_state_get_counter` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L25) |
| function | `_repo_state_bump_counter` | `(session_id, delta=…)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L36) |
| function | `_repo_state_reset_counter` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L50) |
| function | `_detect_git_commit_in_bash` | `(command, stdout)` | True hvis bash-kommandoen kørte en git commit der lykkedes. | [src](../../../core/tools/simple_tools_enforcement.py#L58) |
| function | `_attach_repo_state` | `(result, *, session_id, bumped=…, bash_command=…)` | Augmenter tool-result med _repo_state-blok. Idempotent ved fejl. | [src](../../../core/tools/simple_tools_enforcement.py#L74) |
| function | `_enforce_wrapper` | `(tool_name, fn)` | Returner en wrapper der attacher _repo_state efter fn er kørt. | [src](../../../core/tools/simple_tools_enforcement.py#L145) |
| function | `_commit_enforcement_session_id` | `(args)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L165) |

## `core/tools/simple_tools_native.py`
_Native (non-operator, non-web) tool executors for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _operator_user_id). | [src](../../../core/tools/simple_tools_native.py#L39) |
| function | `_operator_user_id` | `(args)` | Facade → simple_tools._operator_user_id (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_native.py#L45) |
| function | `_exec_list_initiatives` | `(_args)` | Return current initiative queue state. | [src](../../../core/tools/simple_tools_native.py#L50) |
| function | `_exec_push_initiative` | `(args)` | Push a new initiative to the queue. | [src](../../../core/tools/simple_tools_native.py#L104) |
| function | `_exec_read_model_config` | `(_args)` | Read the current model configuration for all runtime lanes. | [src](../../../core/tools/simple_tools_native.py#L130) |
| function | `_exec_read_mood` | `(_args)` | Read current affective/mood state. | [src](../../../core/tools/simple_tools_native.py#L187) |
| function | `_exec_adjust_mood` | `(args)` | Adjust affective parameters in the personality vector. | [src](../../../core/tools/simple_tools_native.py#L238) |
| function | `_exec_resurface_old_memory` | `(args)` | Pick a stale MEMORY.md heading and return it for the model to consider. | [src](../../../core/tools/simple_tools_native.py#L310) |
| function | `_exec_memory_graph_query` | `(args)` | Look up an entity in the memory graph and return its relations. | [src](../../../core/tools/simple_tools_native.py#L336) |
| function | `_exec_search_memory` | `(args)` | Semantic search across workspace memory files. | [src](../../../core/tools/simple_tools_native.py#L368) |
| function | `_exec_propose_source_edit` | `(args)` | File a source-edit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L412) |
| function | `_exec_propose_git_commit` | `(args)` | File a git-commit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L487) |
| function | `_exec_approve_proposal` | `(args)` | Approve and execute a pending autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L563) |
| function | `_exec_list_proposals` | `(_args)` | List pending autonomy proposals. | [src](../../../core/tools/simple_tools_native.py#L589) |
| function | `_exec_schedule_task` | `(args)` | Schedule a task to fire after delay_minutes. | [src](../../../core/tools/simple_tools_native.py#L618) |
| function | `_exec_list_scheduled_tasks` | `(_args)` | List scheduled tasks (pending + recently fired). | [src](../../../core/tools/simple_tools_native.py#L645) |
| function | `_exec_cancel_task` | `(args)` | Cancel a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L677) |
| function | `_exec_edit_task` | `(args)` | Edit a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L692) |
| function | `_exec_read_chronicles` | `(args)` | Return recent cognitive chronicle entries. | [src](../../../core/tools/simple_tools_native.py#L713) |
| function | `_exec_read_dreams` | `(args)` | Return active dream hypothesis signals and adoption candidates. | [src](../../../core/tools/simple_tools_native.py#L759) |
| function | `_exec_notify_user` | `(args)` | Push a proactive message to webchat, Discord, or both. | [src](../../../core/tools/simple_tools_native.py#L825) |
| function | `_exec_read_self_state` | `(_args)` | Return Jarvis's current internal cadence/emotional state. | [src](../../../core/tools/simple_tools_native.py#L884) |
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L970) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1015) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1039) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1060) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1077) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1094) |
| function | `_exec_send_ntfy` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1134) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1150) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json. | [src](../../../core/tools/simple_tools_native.py#L1165) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1209) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1243) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1437) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1507) |
| function | `_exec_convene_council` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1624) |
| function | `_exec_quick_council_check` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1684) |
| function | `_exec_spawn_agent_task` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1721) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1769) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1795) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1819) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1851) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L1866) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1871) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L1885) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1890) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1896) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L1916) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1921) |
| function | `_exec_recall_council_conclusions` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1961) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L1990) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2051) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2081) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2109) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2137) |
| function | `_exec_look_around` | `(args)` | Take a webcam snapshot now and describe what's there via VLM. | [src](../../../core/tools/simple_tools_native.py#L2161) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2190) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2243) |
| function | `_exec_db_query` | `(args)` | Run a read-only SELECT query against Jarvis' database. | [src](../../../core/tools/simple_tools_native.py#L2256) |
| function | `_exec_compact_context_session` | `(session_id)` | Run session compact for session_id. Returns CompactResult or None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2309) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2341) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2360) |
| function | `_exec_publish_file` | `(args)` | Copy or create a file in ~/.jarvis-v2/files/ and return a download URL. | [src](../../../core/tools/simple_tools_native.py#L2381) |
| function | `_tool_load_more_tools` | `(arguments)` | Resolve which tools to add to the next round. Logs to DB + events. | [src](../../../core/tools/simple_tools_native.py#L2451) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2542) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2551) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2560) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2568) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2575) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2596) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2602) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2609) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2615) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2622) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2628) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2650) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2669) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2691) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2697) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2702) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2707) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2712) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2717) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2722) |

## `core/tools/simple_tools_operator.py`
_Operator-bridge tool executors for Jarvis (desktop operator lane)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_st` | `()` | Lazy accessor til simple_tools-modulet (facade-søm, §4 monkeypatch). | [src](../../../core/tools/simple_tools_operator.py#L30) |
| function | `_operator_user_id` | `(args)` | Facade → simple_tools._operator_user_id (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_operator.py#L44) |
| function | `_run_operator_async` | `(coro_fn, *, tool_name, timeout_s=…)` | Facade → simple_tools._run_operator_async (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_operator.py#L49) |
| function | `_operator_user_id_impl` | `(args)` | Resolve operator's user_id for bridge routing. | [src](../../../core/tools/simple_tools_operator.py#L54) |
| function | `_record_active_file` | `(path, op, args)` | Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path` på sin | [src](../../../core/tools/simple_tools_operator.py#L103) |
| function | `_run_operator_async_impl` | `(coro_fn, *, tool_name, timeout_s=…)` | Bridge sync tool-handler → async dispatcher. | [src](../../../core/tools/simple_tools_operator.py#L113) |
| function | `_exec_operator_read_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L197) |
| function | `_operator_file_exists` | `(path, user_id)` | Best-effort: does `path` exist on the operator's machine? | [src](../../../core/tools/simple_tools_operator.py#L226) |
| function | `_exec_operator_write_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L265) |
| function | `_exec_operator_edit_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L337) |
| function | `_exec_operator_glob` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L406) |
| function | `_exec_operator_grep` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L424) |
| function | `_exec_operator_list_dir` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L445) |
| function | `_exec_operator_webfetch` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L457) |
| function | `_exec_operator_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L478) |
| function | `_exec_operator_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L503) |
| function | `_exec_operator_open_url` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L524) |
| function | `_exec_operator_launch_app` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L555) |
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L594) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L610) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L631) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L641) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L660) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L677) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L687) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L697) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L710) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L720) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L739) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L755) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L776) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L791) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L826) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L846) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L867) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L885) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L911) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L931) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L949) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L964) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L977) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L995) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1008) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1026) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1043) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1057) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1078) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1097) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1112) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1129) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1170) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1188) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1205) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1215) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1234) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1255) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1271) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1301) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1311) |

## `core/tools/simple_tools_web.py`
_Web/search/system-info tool executors for Jarvis' native lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn). | [src](../../../core/tools/simple_tools_web.py#L45) |
| function | `_cached_web_search_fn` | `(*, query, max_results, fetch_fn)` | Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_web.py#L51) |
| function | `_exec_search` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L56) |
| function | `_exec_find_files` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L114) |
| function | `_get_or_open_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L188) |
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L212) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L218) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L331) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L362) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L373) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L383) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L418) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L425) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L435) |
| function | `_exec_get_weather` | `(args)` | Current weather via OpenWeatherMap. | [src](../../../core/tools/simple_tools_web.py#L447) |
| function | `_exec_get_exchange_rate` | `(args)` | Currency exchange rates via exchangerate.host. | [src](../../../core/tools/simple_tools_web.py#L481) |
| function | `_exec_get_news` | `(args)` | Recent news via NewsAPI. | [src](../../../core/tools/simple_tools_web.py#L508) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L544) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L643) |
| function | `_exec_wolfram_query` | `(args)` | Precise answers via Wolfram Alpha Short Answers API. | [src](../../../core/tools/simple_tools_web.py#L713) |

## `core/tools/skill_chain_propose_tool.py`
_propose_skill_chain tool — Skill Chain Phase 2 (AGI track #10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_phase2_enabled` | `()` | — | [src](../../../core/tools/skill_chain_propose_tool.py#L36) |
| function | `_exec_propose_skill_chain` | `(args)` | Tool handler for propose_skill_chain. | [src](../../../core/tools/skill_chain_propose_tool.py#L43) |
| function | `_publish_propose_event` | `(*, plan, confidence, rationale_length, model_used, provider_used, task_excerpt)` | Defensively publish cognitive_skill_chain.proposed. Never blocks. | [src](../../../core/tools/skill_chain_propose_tool.py#L152) |
| function | `_build_propose_prompt` | `(*, task_description, catalog)` | Build the cheap-lane prompt. Compact — ~2-3k tokens for 50 skills. | [src](../../../core/tools/skill_chain_propose_tool.py#L220) |
| function | `_extract_json_blob` | `(text)` | Tolerate markdown fences and prose around JSON. | [src](../../../core/tools/skill_chain_propose_tool.py#L262) |
| function | `_parse_propose_response` | `(text)` | Parse cheap-lane response. Returns {status, plan, rationale, confidence} | [src](../../../core/tools/skill_chain_propose_tool.py#L275) |

## `core/tools/skill_chain_revise_tool.py`
_revise_skill_chain tool — Skill Chain Phase 2 (AGI track #10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_phase2_enabled` | `()` | — | [src](../../../core/tools/skill_chain_revise_tool.py#L37) |
| function | `_exec_revise_skill_chain` | `(args)` | Tool handler for revise_skill_chain. | [src](../../../core/tools/skill_chain_revise_tool.py#L44) |
| function | `_publish_revise_event` | `(*, new_plan, reason, revision_context, instructions_length)` | Defensively publish cognitive_skill_chain.revised. Never blocks. | [src](../../../core/tools/skill_chain_revise_tool.py#L129) |

## `core/tools/skill_chain_tool.py`
_skill_chain tool — Lag #4 sequential skill composition._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_validate_plan_existence` | `(plan)` | Return list of missing skill names (empty list if all exist). | [src](../../../core/tools/skill_chain_tool.py#L32) |
| function | `_build_combined_instructions` | `(plan)` | Header-format combination — instructions verbatim, step-headers added. | [src](../../../core/tools/skill_chain_tool.py#L37) |
| function | `_build_note` | `(plan, instructions)` | Build the user-visible note. Warns when over soft cap. | [src](../../../core/tools/skill_chain_tool.py#L57) |
| function | `_publish_chain_event` | `(*, plan, instructions_length, rationale_provided, status)` | Publish to eventbus. Metadata only — NO rationale text. | [src](../../../core/tools/skill_chain_tool.py#L73) |
| function | `_exec_skill_chain` | `(args)` | Validate plan, build combined instructions, return. | [src](../../../core/tools/skill_chain_tool.py#L96) |

## `core/tools/skill_engine_tools.py`
_Skill Engine tools — Jarvis skill system._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_bilingual_use_when` | `(text)` | Split a use_when block into separate language fragments. | [src](../../../core/tools/skill_engine_tools.py#L30) |
| function | `_suggest_skills_for_query` | `(query, threshold=…, max_results=…, context_tags=…)` | Match a user query against all installed skills' use_when + description. | [src](../../../core/tools/skill_engine_tools.py#L61) |
| function | `_exec_skill_list` | `(args)` | List all loaded skills, optionally filtered by tag. | [src](../../../core/tools/skill_engine_tools.py#L158) |
| function | `_exec_skill_invoke` | `(args)` | Get a skill's instructions for prompt injection. | [src](../../../core/tools/skill_engine_tools.py#L171) |
| function | `_exec_propose_new_skill` | `(args)` | Propose a new skill via the plan-approval flow. | [src](../../../core/tools/skill_engine_tools.py#L212) |
| function | `_exec_skill_create` | `(args)` | Create a new skill on disk. | [src](../../../core/tools/skill_engine_tools.py#L281) |
| function | `_exec_skill_delete` | `(args)` | Delete a skill from disk. | [src](../../../core/tools/skill_engine_tools.py#L303) |
| function | `_exec_skill_search` | `(args)` | Search skills by keyword. | [src](../../../core/tools/skill_engine_tools.py#L311) |
| function | `_exec_skill_get` | `(args)` | Get full detail on a single skill. | [src](../../../core/tools/skill_engine_tools.py#L324) |
| function | `_exec_skill_reload` | `(args)` | Force-reload all skills from disk. | [src](../../../core/tools/skill_engine_tools.py#L350) |
| function | `_exec_skill_suggest` | `(args)` | Suggest skills relevant to a user query via semantic matching. | [src](../../../core/tools/skill_engine_tools.py#L355) |
| function | `_exec_skill_import` | `(args)` | Import a skill from a local path (directory or zip archive). | [src](../../../core/tools/skill_engine_tools.py#L391) |
| function | `_find_skill_dir_in_tree` | `(root)` | Walk a directory tree and find the first directory containing SKILL.md. | [src](../../../core/tools/skill_engine_tools.py#L554) |
| function | `_fetch_url_capped` | `(url, *, timeout=…)` | Fetch a URL, capped at _MAX_URL_FETCH_BYTES. Returns (content, error). | [src](../../../core/tools/skill_engine_tools.py#L577) |
| function | `_install_skill_md_content` | `(*, content, target_name, source_label)` | Stage SKILL.md content in a tempdir, scan, copy to skills root, reload. | [src](../../../core/tools/skill_engine_tools.py#L601) |
| function | `_exec_skill_import_from_url` | `(args)` | Import a skill from a remote URL. | [src](../../../core/tools/skill_engine_tools.py#L689) |
| function | `_exec_skill_history` | `(args)` | Return audit trail for a single skill. | [src](../../../core/tools/skill_engine_tools.py#L1025) |
| function | `_exec_recent_skill_changes` | `(args)` | Return most recent skill mutations across all skills. | [src](../../../core/tools/skill_engine_tools.py#L1038) |
| function | `_exec_analyze_skill_usage` | `(args)` | Analyze skill usage patterns over the past N days. | [src](../../../core/tools/skill_engine_tools.py#L1048) |

## `core/tools/skill_gate_tool.py`
_Skill Gate Tool — pre-action gate for automatic skill suggestion + invocation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_chain_candidates` | `(suggestions)` | Return top-3 (max) skills within 0.10 of top score. | [src](../../../core/tools/skill_gate_tool.py#L54) |
| function | `_build_chain_hint` | `(candidates)` | Render human-readable chain suggestion from candidates. | [src](../../../core/tools/skill_gate_tool.py#L78) |
| function | `_exec_skill_gate` | `(args)` | Pre-action gate: match user query to installed skills, invoke if relevant. | [src](../../../core/tools/skill_gate_tool.py#L94) |

## `core/tools/smart_compact_tools.py`
_Smart context compaction — preserves decisions/facts, discards routine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_smart_compact_prompt` | `()` | Build compact prompt lazily so identity_prompt_prefix resolves at runtime, not module import. | [src](../../../core/tools/smart_compact_tools.py#L9) |
| function | `_estimate_session_tokens` | `()` | Rough estimate of current session's token count. | [src](../../../core/tools/smart_compact_tools.py#L40) |
| function | `_exec_smart_compact` | `(args)` | Compact context with a smarter prompt that preserves decisions/facts. | [src](../../../core/tools/smart_compact_tools.py#L56) |
| function | `_exec_context_size_check` | `(args)` | Estimate current context size and advise whether compaction is needed. | [src](../../../core/tools/smart_compact_tools.py#L112) |

## `core/tools/smart_outline.py`
_smart_outline — structural file summary, much cheaper than read_file._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_python_outline` | `(source)` | — | [src](../../../core/tools/smart_outline.py#L54) |
| function | `_regex_outline` | `(source, suffix)` | — | [src](../../../core/tools/smart_outline.py#L110) |
| function | `_exec_smart_outline` | `(args)` | — | [src](../../../core/tools/smart_outline.py#L127) |

## `core/tools/speak_tool.py`
_Speak tool — Jarvis speaks aloud through system speakers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_speak` | `(args)` | Execute the speak tool: synthesize text and play through speakers. | [src](../../../core/tools/speak_tool.py#L26) |

## `core/tools/staged_edits_tools.py`
_Tool registry entries for staged edits._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_session_id` | `()` | Resolve the session_id for staging scope. | [src](../../../core/tools/staged_edits_tools.py#L29) |
| function | `_exec_stage_edit_file` | `(args)` | — | [src](../../../core/tools/staged_edits_tools.py#L55) |
| function | `_exec_stage_write_file` | `(args)` | — | [src](../../../core/tools/staged_edits_tools.py#L66) |
| function | `_exec_list_staged_edits` | `(args)` | — | [src](../../../core/tools/staged_edits_tools.py#L75) |
| function | `_exec_commit_staged_edits` | `(args)` | — | [src](../../../core/tools/staged_edits_tools.py#L82) |
| function | `_exec_discard_staged_edits` | `(args)` | — | [src](../../../core/tools/staged_edits_tools.py#L90) |

## `core/tools/stripe_tools.py`
_Stripe integration tools — balance, transactions, and Issuing virtual cards._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_stripe_unavailable_response` | `()` | — | [src](../../../core/tools/stripe_tools.py#L33) |
| function | `_load_stripe_key` | `()` | Load the Stripe secret key from runtime config. | [src](../../../core/tools/stripe_tools.py#L47) |
| function | `_init_stripe` | `()` | Initialise the Stripe SDK with the stored key. Returns mode label. | [src](../../../core/tools/stripe_tools.py#L60) |
| function | `_to_dict` | `(obj)` | Convert a Stripe object to a plain dict safely. | [src](../../../core/tools/stripe_tools.py#L72) |
| function | `_exec_stripe_balance` | `(_args)` | Get the Stripe account balance. | [src](../../../core/tools/stripe_tools.py#L86) |
| function | `_exec_stripe_transactions` | `(args)` | — | [src](../../../core/tools/stripe_tools.py#L118) |
| function | `_exec_stripe_payouts` | `(args)` | — | [src](../../../core/tools/stripe_tools.py#L150) |
| function | `_exec_stripe_create_issuing_card` | `(args)` | — | [src](../../../core/tools/stripe_tools.py#L181) |

## `core/tools/team_tools.py`
_Native team-tools til Jarvis (Teams-feature, spec 2026-06-20)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_uid` | `(args)` | — | [src](../../../core/tools/team_tools.py#L14) |
| function | `exec_create_team` | `(args)` | — | [src](../../../core/tools/team_tools.py#L25) |
| function | `exec_list_teams` | `(args)` | — | [src](../../../core/tools/team_tools.py#L44) |
| function | `_looks_like_email` | `(s)` | — | [src](../../../core/tools/team_tools.py#L56) |
| function | `_deliver_invite` | `(team_id, invitee, token, inviter)` | Best-effort levering: in-app proactive-kort til en eksisterende bruger + | [src](../../../core/tools/team_tools.py#L60) |
| function | `exec_invite_to_team` | `(args)` | — | [src](../../../core/tools/team_tools.py#L109) |

## `core/tools/tiktok_analytics_tools.py`
_TikTok analytics tools for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_saved_cookies` | `(username)` | Load session cookies from TK_cookies_{username}.json (tiktokautouploader format). | [src](../../../core/tools/tiktok_analytics_tools.py#L47) |
| function | `_fetch_profile` | `(username)` | Scrape profile stats + secUid + userId from UNIVERSAL_DATA. | [src](../../../core/tools/tiktok_analytics_tools.py#L67) |
| function | `_get_tiktok_cookies` | `(seed_cookies)` | Run headless Playwright to generate msToken and session cookies. | [src](../../../core/tools/tiktok_analytics_tools.py#L91) |
| function | `_fetch_video_list` | `(sec_uid, cookies, count)` | Call TikTok's internal video list API. | [src](../../../core/tools/tiktok_analytics_tools.py#L115) |
| function | `_parse_video` | `(v)` | — | [src](../../../core/tools/tiktok_analytics_tools.py#L136) |
| function | `_exec_tiktok_analytics` | `(args)` | Fetch TikTok video statistics for a user. | [src](../../../core/tools/tiktok_analytics_tools.py#L155) |

## `core/tools/tiktok_content_tools.py`
_TikTok content generation tool — wraps jarvis_pollinations_pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_tiktok_generate_video` | `(args)` | — | [src](../../../core/tools/tiktok_content_tools.py#L21) |

## `core/tools/tiktok_tools.py`
_TikTok auto-uploader integration tools for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_tiktok_upload` | `(args)` | Upload a video to TikTok using tiktokautouploader. | [src](../../../core/tools/tiktok_tools.py#L38) |
| function | `_exec_tiktok_login` | `(args)` | Log into TikTok via headless browser using username + password. | [src](../../../core/tools/tiktok_tools.py#L114) |
| function | `_exec_tiktok_show` | `(args)` | List saved TikTok cookie profiles and available videos. | [src](../../../core/tools/tiktok_tools.py#L185) |
| function | `_get_display` | `()` | Return a DISPLAY value for browser operations. | [src](../../../core/tools/tiktok_tools.py#L217) |

## `core/tools/tool_scoping.py`
_Tool-scoping policy — hvilke værktøjer er tilgængelige pr. rolle og mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_local_execution_tool` | `(name)` | True hvis værktøjet kører lokalt i code mode (resultat forlader ikke maskinen). | [src](../../../core/tools/tool_scoping.py#L133) |
| function | `current_tool_scope` | `()` | Nuværende tool-scope ("chat" eller "" for ubegrænset). | [src](../../../core/tools/tool_scoping.py#L144) |
| function | `set_tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L149) |
| function | `reset_tool_scope` | `(token)` | — | [src](../../../core/tools/tool_scoping.py#L153) |
| function | `tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L158) |
| function | `_owner_has_live_bridge` | `()` | True hvis der findes en levende desk-bro for nuværende bruger (presence, cross-proces). | [src](../../../core/tools/tool_scoping.py#L166) |
| function | `allowed_tool_names` | `(*, role, scope, all_names)` | Beregn det tilladte sæt tool-navne for (role, scope). | [src](../../../core/tools/tool_scoping.py#L180) |
| function | `is_tool_allowed` | `(*, role, scope, name)` | Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.) | [src](../../../core/tools/tool_scoping.py#L226) |
| function | `_apply_computer_use_policy` | `(result)` | Computer-use-toggle (§4.7): fjern operator/computer-tools hvis brugeren har | [src](../../../core/tools/tool_scoping.py#L239) |
| function | `_fn_name` | `(td)` | — | [src](../../../core/tools/tool_scoping.py#L263) |
| function | `filter_tool_definitions` | `(defs, *, role, scope)` | Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope). | [src](../../../core/tools/tool_scoping.py#L267) |

## `core/tools/ui_panel_tools.py`
_open_ui_panel-tool (spec §8.2, Fase 6 #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_open_ui_panel` | `(args)` | — | [src](../../../core/tools/ui_panel_tools.py#L17) |

## `core/tools/verify_tools.py`
_Verification tools — wrap "do then check" into one call._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_verify_file_contains` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L32) |
| function | `_exec_verify_service_active` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L72) |
| function | `_exec_verify_endpoint_responds` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L95) |

## `core/tools/visual_memory_tool.py`
_Visual memory tool — Jarvis kan læse sine egne visuelle minder._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_read_visual_memory` | `(args)` | Read recent visual memories (webcam room descriptions). | [src](../../../core/tools/visual_memory_tool.py#L23) |

## `core/tools/voice_journal_tool.py`
_Voice Journal tool — dedicated longer recording → density note._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_voice_journal` | `(args)` | — | [src](../../../core/tools/voice_journal_tool.py#L26) |

