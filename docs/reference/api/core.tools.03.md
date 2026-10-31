# `core.tools.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/reasoning_store_tools.py`
_Reasoning Store tools for Jarvis — Phase 1 Generalized Learning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_recall_reasoning` | `(args)` | Retrieve stored reasoning conclusions, ranked by relevance. | [src](../../../core/tools/reasoning_store_tools.py#L19) |

## `core/tools/recall_memory_tools.py`
_Semantic recall tools — Jarvis-facing recall across all memory surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_excerpt_for` | `(record, source_table)` | — | [src](../../../core/tools/recall_memory_tools.py#L30) |
| function | `_timestamp_for` | `(record, source_table)` | — | [src](../../../core/tools/recall_memory_tools.py#L44) |
| function | `_exec_recall_memories` | `(args)` | — | [src](../../../core/tools/recall_memory_tools.py#L54) |

## `core/tools/recall_tool.py`
_`recall` — the one memory-search tool (memory repair 2026-09-04, R5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_recall` | `(args)` | — | [src](../../../core/tools/recall_tool.py#L52) |

## `core/tools/recurring_scheduler_tools.py`
_Recurring scheduler tools — Jarvis can schedule repeating tasks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_interval` | `(interval, unit)` | Return interval in minutes, or None on bad input. | [src](../../../core/tools/recurring_scheduler_tools.py#L13) |
| function | `_exec_schedule_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L27) |
| function | `_exec_list_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L82) |
| function | `_exec_cancel_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L102) |
| function | `_exec_set_recurring_channel` | `(args)` | Sæt leverings-kanal på en recurring task (notif-routing spec §3.5). | [src](../../../core/tools/recurring_scheduler_tools.py#L240) |
| function | `_exec_set_recurring_weekdays` | `(args)` | Begræns en recurring task til bestemte ugedage. | [src](../../../core/tools/recurring_scheduler_tools.py#L260) |

## `core/tools/repo_recall_tool.py`
_`repo_recall` — søgning i repoets DOKUMENTATION (ikke kildekoden)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_repo_recall` | `(args)` | — | [src](../../../core/tools/repo_recall_tool.py#L66) |

## `core/tools/restart_self_tools.py`
_restart_self tool — fire-and-forget service restart that survives process death._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_aktive_koersler` | `(graense=…)` | Hvilke synlige koersler LEVER lige nu? | [src](../../../core/tools/restart_self_tools.py#L95) |
| function | `_andre_aktive_koersler` | `(egen_run_id, graense=…)` | Levende koersler UD OVER min egen (13/10-2026). | [src](../../../core/tools/restart_self_tools.py#L148) |
| function | `_exec_restart_self` | `(args)` | — | [src](../../../core/tools/restart_self_tools.py#L161) |
| function | `_wait_for_gateway_connected` | `(max_wait=…, interval=…)` | Vent på at Discord gateway er connected efter restart. | [src](../../../core/tools/restart_self_tools.py#L313) |
| function | `_send_discord_restart_msg` | `(base_msg)` | Send restart-bekræftelse til Bjørn via Discord DM. | [src](../../../core/tools/restart_self_tools.py#L339) |
| function | `_try_fallback_channels` | `(base_msg)` | Forsøg at sende restart-bekræftelse via Telegram eller ntfy som fallback. | [src](../../../core/tools/restart_self_tools.py#L360) |
| function | `_claim_restart_file` | `()` | Atomic claim af restart-confirmation-fil — kun én uvicorn worker vinder. | [src](../../../core/tools/restart_self_tools.py#L391) |
| function | `_genstart_bruger_id` | `(user_id=…)` | Bruger-id til indbakke-posten — fanget ved genstart, ellers ejeren. | [src](../../../core/tools/restart_self_tools.py#L422) |
| function | `_lever_til_samtalen` | `(besked, *, session_id, user_id, services)` | Verifikationen til den SAMTALE genstarten blev sendt fra. | [src](../../../core/tools/restart_self_tools.py#L439) |
| function | `send_pending_restart_confirmation` | `()` | On startup, check for a pending restart confirmation file and send it. | [src](../../../core/tools/restart_self_tools.py#L496) |

## `core/tools/screen_tool.py`
_Screen control — turn Bjørn's monitors on/off/standby, or read their state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dpms_command` | `(action)` | Shell command that sets (or reads) DPMS on every connected DP output. | [src](../../../core/tools/screen_tool.py#L78) |
| function | `_run_on_operator` | `(command, args)` | Run `command` on the operator's desktop via the bridge. | [src](../../../core/tools/screen_tool.py#L85) |
| function | `_exec_screen_control` | `(args)` | Execute the screen control tool. | [src](../../../core/tools/screen_tool.py#L117) |

## `core/tools/security_predicates.py`
_Nummererede security-predikater (spec E, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SecurityPredicate` | `` | — | [src](../../../core/tools/security_predicates.py#L14) |
| function | `_er_ren_laesning` | `(command)` | Er HELE kommandoen ét rent læse-segment? | [src](../../../core/tools/security_predicates.py#L91) |
| function | `evaluate_command` | `(command)` | Første matchende bash-predikat (blocked før destructive) på den normaliserede | [src](../../../core/tools/security_predicates.py#L116) |
| function | `evaluate_write` | `(resolved_path)` | Første matchende write-predikat (substring) på stien, ellers None. | [src](../../../core/tools/security_predicates.py#L158) |
| function | `all_predicates` | `()` | — | [src](../../../core/tools/security_predicates.py#L169) |
| function | `build_security_predicates_surface` | `()` | Central-CLI read-surface: jc raw /central/security-predicates. | [src](../../../core/tools/security_predicates.py#L173) |
| function | `render_predicates_md` | `()` | Genererer docs/security_predicates.md fra registry'en (kilde = koden). | [src](../../../core/tools/security_predicates.py#L187) |

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
| function | `_exec_record_sensory_memory` | `(args)` | — | [src](../../../core/tools/sensory_tools.py#L19) |
| function | `_exec_recall_sensory_memories` | `(args)` | — | [src](../../../core/tools/sensory_tools.py#L94) |

## `core/tools/session_search.py`
_search_sessions tool — cross-channel session search with keyword and semantic modes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_channel_title_filter` | `(channel)` | — | [src](../../../core/tools/session_search.py#L60) |
| function | `_row_to_result` | `(row, *, match_type)` | — | [src](../../../core/tools/session_search.py#L69) |
| function | `_user_scope_clause` | `(user_id)` | Privatlivs-guard (multi-user northstar): begræns søgningen til sessions der | [src](../../../core/tools/session_search.py#L86) |
| function | `_keyword_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L103) |
| function | `_embed_query` | `(text)` | Embed text via Ollama. Returns None if unavailable. | [src](../../../core/tools/session_search.py#L144) |
| function | `_cosine_similarity` | `(a, b)` | — | [src](../../../core/tools/session_search.py#L171) |
| function | `_semantic_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L181) |
| function | `_merge_results` | `(keyword_results, semantic_results, limit)` | — | [src](../../../core/tools/session_search.py#L238) |
| function | `exec_search_sessions` | `(args)` | — | [src](../../../core/tools/session_search.py#L262) |

## `core/tools/simple_tools.py`
_Simple, general-purpose tools for Jarvis visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `canonical_identity_file_path` | `(name)` | Den ENE fil `name` bor i — samme opslag som prompten bruger til at LÆSE. | [src](../../../core/tools/simple_tools.py#L699) |
| function | `_canonicalize_workspace_target` | `(target)` | If target's basename is a canonical workspace file, force it to the | [src](../../../core/tools/simple_tools.py#L741) |
| function | `_emit_security_check` | `(hit, *, target)` | Self-safe audit-emit: et deny/destructive bæres nu med sit nummererede | [src](../../../core/tools/simple_tools.py#L883) |
| function | `_uden_for_quotes` | `(command)` | Fjern quotede strenge, så en ``>`` inde i en streng ikke tælles som redirect. | [src](../../../core/tools/simple_tools.py#L915) |
| function | `_har_skrivende_redirect` | `(command)` | ``>`` eller ``>>`` uden for quotes gør kommandoen muterende. | [src](../../../core/tools/simple_tools.py#L924) |
| function | `_segment_er_laesende` | `(segment)` | Er ÉT pipe-segment en ren læsning? Fail-closed ved tvivl. | [src](../../../core/tools/simple_tools.py#L940) |
| function | `classify_command` | `(command)` | Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L959) |
| function | `classify_file_write` | `(path)` | Classify a file write: 'auto', 'approval', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L1115) |
| function | `execute_tool` | `(name, arguments)` | Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1). | [src](../../../core/tools/simple_tools.py#L1137) |
| function | `_execute_tool_impl` | `(name, arguments)` | Execute a tool call and return the result. | [src](../../../core/tools/simple_tools.py#L1176) |
| function | `execute_tool_force` | `(name, arguments, *, owner_approved=…)` | Execute tool bypassing approval checks. Only call for user-approved requests. | [src](../../../core/tools/simple_tools.py#L1491) |
| function | `_execute_tool_force_impl` | `(name, arguments)` | — | [src](../../../core/tools/simple_tools.py#L1541) |
| function | `_record_tool_outcome_memory` | `(name, arguments, result, *, mode)` | — | [src](../../../core/tools/simple_tools.py#L1648) |
| function | `_med_samtykke` | `(navn, fn)` | — | [src](../../../core/tools/simple_tools.py#L2385) |
| function | `get_tool_definitions` | `(role=…, scope=…)` | Return Ollama-compatible tool definitions, filtered by role + scope. | [src](../../../core/tools/simple_tools.py#L2471) |

## `core/tools/simple_tools_agent_spawn.py`
_spawn_agent_task som modelvendt vaerktoej._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_herkomst` | `(args)` | Hvem og hvilken tur der foedte barnet. Runtime injicerer felterne i hvert | [src](../../../core/tools/simple_tools_agent_spawn.py#L15) |
| function | `_exec_spawn_agent_task` | `(args)` | — | [src](../../../core/tools/simple_tools_agent_spawn.py#L26) |

## `core/tools/simple_tools_definitions.py`
_Tool definitions catalog for Jarvis' visible-lane tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_til_openai_form` | `(td)` | Anthropic-formet definition → OpenAI-formet. Andet passerer urørt. | [src](../../../core/tools/simple_tools_definitions.py#L3663) |
| function | `_ensret_tool_definitions` | `(defs)` | — | [src](../../../core/tools/simple_tools_definitions.py#L3680) |

## `core/tools/simple_tools_enforcement.py`
_Commit-enforcement (repo-state attachment) for Jarvis' tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_state_session_key` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L21) |
| function | `_repo_state_get_counter` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L25) |
| function | `_repo_state_bump_counter` | `(session_id, delta=…)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L36) |
| function | `_repo_state_reset_counter` | `(session_id)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L50) |
| function | `_detect_git_commit_in_bash` | `(command, stdout)` | True when raw Git or the attributed wrapper completed a commit. | [src](../../../core/tools/simple_tools_enforcement.py#L58) |
| function | `_attach_repo_state` | `(result, *, session_id, bumped=…, bash_command=…)` | Augmenter tool-result med _repo_state-blok. Idempotent ved fejl. | [src](../../../core/tools/simple_tools_enforcement.py#L72) |
| function | `_enforce_wrapper` | `(tool_name, fn)` | Returner en wrapper der attacher _repo_state efter fn er kørt. | [src](../../../core/tools/simple_tools_enforcement.py#L143) |
| function | `_commit_enforcement_session_id` | `(args)` | — | [src](../../../core/tools/simple_tools_enforcement.py#L163) |

## `core/tools/simple_tools_explore.py`
_Read-only research-agent tool with runtime/Desk execution routing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/tools/simple_tools_explore.py#L25) |
| function | `_oploes_bruger` | `(args)` | Hvem er den autentificerede Desk-bruger? ÉT sted ejer opslaget. | [src](../../../core/tools/simple_tools_explore.py#L30) |
| function | `_execution_context` | `(args)` | — | [src](../../../core/tools/simple_tools_explore.py#L42) |
| function | `_explore_spawn` | `(*, query, vejledning, provider=…, model=…, target=…, context=…, efterbehandling=…, taalmodighed_s=…)` | — | [src](../../../core/tools/simple_tools_explore.py#L83) |
| function | `_explore_svar` | `(result)` | — | [src](../../../core/tools/simple_tools_explore.py#L128) |
| function | `_bro_kontrol` | `(args)` | Byg de to efterproevninger der slaar op OVER BROEN, paa Bjoerns maskine. | [src](../../../core/tools/simple_tools_explore.py#L142) |
| function | `_bevis_note` | `(bevis, kontrolleret, substans)` | Én saetning der siger praecis hvad der blev efterproevet. | [src](../../../core/tools/simple_tools_explore.py#L246) |
| function | `_vurder_svar` | `(result, *, tjek_paastande, bro_tjek=…, bro_linje=…)` | Fabrikations-værnet på ÉT explore-resultat. | [src](../../../core/tools/simple_tools_explore.py#L264) |
| function | `_vurdering_til_wakeup` | `(vurdering)` | Dommen over et sent explore-svar, som den skal stå i vækningen. | [src](../../../core/tools/simple_tools_explore.py#L346) |
| function | `_vaelg_kandidat` | `(pool, brugt, runde, egnede_modeller)` | Hvilken model skal runde `runde` spoerge? ÉT sted ejer raekkefoelgen. | [src](../../../core/tools/simple_tools_explore.py#L363) |
| function | `_modelnavn` | `(prov, mod)` | Modellens navn i en besked til Bjoern — eller at ingen blev valgt. | [src](../../../core/tools/simple_tools_explore.py#L391) |
| function | `_exec_explore` | `(args)` | — | [src](../../../core/tools/simple_tools_explore.py#L401) |

## `core/tools/simple_tools_native.py`
_Native (non-operator, non-web) tool executors for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _operator_user_id). | [src](../../../core/tools/simple_tools_native.py#L38) |
| function | `_operator_user_id` | `(args)` | Facade → simple_tools._operator_user_id (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_native.py#L44) |
| function | `_exec_list_initiatives` | `(_args)` | Return current initiative queue state. | [src](../../../core/tools/simple_tools_native.py#L49) |
| function | `_exec_push_initiative` | `(args)` | Push a new initiative to the queue. | [src](../../../core/tools/simple_tools_native.py#L103) |
| function | `_exec_read_model_config` | `(_args)` | Read the current model configuration for all runtime lanes. | [src](../../../core/tools/simple_tools_native.py#L129) |
| function | `_exec_read_mood` | `(_args)` | Read current affective/mood state. | [src](../../../core/tools/simple_tools_native.py#L186) |
| function | `_exec_adjust_mood` | `(args)` | Adjust affective parameters in the personality vector. | [src](../../../core/tools/simple_tools_native.py#L237) |
| function | `_exec_resurface_old_memory` | `(args)` | Pick a stale MEMORY.md heading and return it for the model to consider. | [src](../../../core/tools/simple_tools_native.py#L309) |
| function | `_exec_memory_graph_query` | `(args)` | Look up an entity in the memory graph and return its relations. | [src](../../../core/tools/simple_tools_native.py#L335) |
| function | `_exec_search_memory` | `(args)` | Semantic search across workspace memory files. | [src](../../../core/tools/simple_tools_native.py#L367) |
| function | `_exec_propose_source_edit` | `(args)` | File a source-edit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L411) |
| function | `_exec_propose_git_commit` | `(args)` | File a git-commit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L486) |
| function | `_exec_approve_proposal` | `(args)` | Approve and execute a pending autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L562) |
| function | `_exec_list_proposals` | `(_args)` | List pending autonomy proposals. | [src](../../../core/tools/simple_tools_native.py#L588) |
| function | `_exec_schedule_task` | `(args)` | Schedule a task to fire after delay_minutes. | [src](../../../core/tools/simple_tools_native.py#L620) |
| function | `_exec_list_scheduled_tasks` | `(_args)` | List scheduled tasks (pending + recently fired). | [src](../../../core/tools/simple_tools_native.py#L648) |
| function | `_exec_cancel_task` | `(args)` | Cancel a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L680) |
| function | `_exec_edit_task` | `(args)` | Edit a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L695) |
| function | `_exec_read_chronicles` | `(args)` | Return recent cognitive chronicle entries. | [src](../../../core/tools/simple_tools_native.py#L716) |
| function | `_exec_read_dreams` | `(args)` | Return active dream hypothesis signals and adoption candidates. | [src](../../../core/tools/simple_tools_native.py#L762) |
| function | `_exec_notify_user` | `(args)` | Push a proactive message to webchat, Discord, or both. | [src](../../../core/tools/simple_tools_native.py#L828) |
| function | `_exec_read_self_state` | `(_args)` | Return Jarvis's current internal cadence/emotional state. | [src](../../../core/tools/simple_tools_native.py#L899) |
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L988) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1035) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1059) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1080) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1127) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1144) |
| function | `_exec_send_ntfy` | `(args)` | Send en besked til Bjørn gennem routeren. | [src](../../../core/tools/simple_tools_native.py#L1184) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1222) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord, optionally with a file attachment. | [src](../../../core/tools/simple_tools_native.py#L1246) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1329) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1363) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1557) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1627) |
| function | `_explore_spawn` | `(*, query, vejledning, provider=…, model=…)` | Ét explore-spawn. Udskilt så påstands-værnet kan prøve en anden model. | [src](../../../core/tools/simple_tools_native.py#L1747) |
| function | `_explore_svar` | `(result)` | (fund, udbyder_fejl). Kun beskeder af kinden `result` er fund. | [src](../../../core/tools/simple_tools_native.py#L1796) |
| function | `_exec_explore` | `(args)` | Bred, laese-kun undersoegelse — ét spoergsmaal ind, fund ud. | [src](../../../core/tools/simple_tools_native.py#L1816) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1916) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1954) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1978) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2013) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2028) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2037) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2051) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2056) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2062) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L2083) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2088) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L2128) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2199) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2229) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2257) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2285) |
| function | `_exec_look_around` | `(args)` | Look through one of the house cameras now and describe what's there. | [src](../../../core/tools/simple_tools_native.py#L2309) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2342) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2395) |
| function | `_exec_interlanguage_protocol` | `(args)` | Eksportér inter-sprog-protokollen (designets fase 5 — bæring ved modelskift). | [src](../../../core/tools/simple_tools_native.py#L2408) |
| function | `_exec_compact_context_session` | `(session_id)` | Komprimér sessionen. Returnerer CompactResult eller None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2439) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2464) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2486) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2539) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2548) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2557) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2565) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2572) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2593) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2599) |
| function | `_exec_drive_download` | `(args)` | Hent en Drive-fil til brugerens filmappe og returnér et link. | [src](../../../core/tools/simple_tools_native.py#L2606) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2613) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2619) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2626) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2632) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2654) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2673) |
| function | `_exec_docs_create` | `(args)` | Opret et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2695) |
| function | `_exec_sheets_create` | `(args)` | Opret et Google-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2712) |
| function | `_exec_slides_create` | `(args)` | Opret en Google-præsentation — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2733) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2749) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2755) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2760) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2765) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2770) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2775) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2780) |
| function | `_exec_operator_channel` | `(args)` | Aabn/luk/vis operator-kanalen. Owner-only for open/close. | [src](../../../core/tools/simple_tools_native.py#L2868) |
| function | `_exec_mcp` | `(args)` | Én indgang til MCP: se, godkend, list vaerktoejer, kald. | [src](../../../core/tools/simple_tools_native.py#L2886) |
| function | `_exec_checkpoint` | `(args)` | Se eller fortryd en redigeringsrunde. | [src](../../../core/tools/simple_tools_native.py#L2926) |

## `core/tools/simple_tools_operator.py`
_Operator-bridge tool executors for Jarvis (desktop operator lane)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_st` | `()` | Lazy accessor til simple_tools-modulet (facade-søm, §4 monkeypatch). | [src](../../../core/tools/simple_tools_operator.py#L30) |
| function | `_operator_user_id` | `(args)` | Facade → simple_tools._operator_user_id (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_operator.py#L44) |
| function | `_run_operator_async` | `(coro_fn, *, tool_name, timeout_s=…)` | Facade → simple_tools._run_operator_async (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_operator.py#L49) |
| function | `_operator_user_id_impl` | `(args)` | Resolve operator's user_id for bridge routing. | [src](../../../core/tools/simple_tools_operator.py#L54) |
| function | `_record_active_file` | `(path, op, args)` | Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path` på sin | [src](../../../core/tools/simple_tools_operator.py#L106) |
| function | `_run_operator_async_impl` | `(coro_fn, *, tool_name, timeout_s=…)` | Bridge sync tool-handler → async dispatcher. | [src](../../../core/tools/simple_tools_operator.py#L116) |
| function | `_rapporter_gate_svigt` | `(vaerktoej, path, exc)` | Sig højt at et gate-kald svigtede, og lad handlingen fortsætte. | [src](../../../core/tools/simple_tools_operator.py#L201) |
| function | `_exec_operator_read_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L226) |
| function | `_operator_file_exists` | `(path, user_id)` | Best-effort: does `path` exist on the operator's machine? | [src](../../../core/tools/simple_tools_operator.py#L257) |
| function | `_sti_gate_operator` | `(path, args, *, kind, tool, forhaandsvisning=…)` | Sti-gate for operator-fil-skrivning. ``None`` = maa fortsaette. | [src](../../../core/tools/simple_tools_operator.py#L296) |
| function | `_exec_operator_write_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L334) |
| function | `_exec_operator_edit_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L419) |
| function | `_exec_operator_run_in_background` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L503) |
| function | `_exec_operator_bash_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L529) |
| function | `_exec_operator_kill_shell` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L542) |
| function | `_exec_operator_multi_edit` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L554) |
| function | `_exec_operator_glob` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L603) |
| function | `_exec_operator_grep` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L622) |
| function | `_exec_operator_list_dir` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L644) |
| function | `_exec_operator_webfetch` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L658) |
| function | `_exec_operator_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L679) |
| function | `_exec_operator_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L727) |
| function | `_exec_operator_open_url` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L748) |
| function | `_exec_operator_launch_app` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L779) |
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L824) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L840) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L861) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L871) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L890) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L907) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L917) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L927) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L940) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L950) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L976) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L992) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1013) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1028) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1063) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1083) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1104) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1122) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1148) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1168) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1186) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1201) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1214) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1232) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1245) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1263) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1280) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1294) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1315) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1334) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1349) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1366) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1407) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1425) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1442) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1452) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1471) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1492) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1508) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1538) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1548) |

## `core/tools/simple_tools_web.py`
_Web/search/system-info tool executors for Jarvis' native lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_glob_to_regex` | `(pattern)` | Oversæt et glob-mønster (POSIX-relativt) til en regex med KORREKT sti-semantik: | [src](../../../core/tools/simple_tools_web.py#L65) |
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn). | [src](../../../core/tools/simple_tools_web.py#L86) |
| function | `_cached_web_search_fn` | `(*, query, max_results, fetch_fn)` | Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_web.py#L92) |
| function | `_observe_research_result` | `(tool_name, result)` | Best-effort observer; ordinary web calls never depend on research state. | [src](../../../core/tools/simple_tools_web.py#L97) |
| function | `_exec_search` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L106) |
| function | `_exec_find_files` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L235) |
| function | `_get_or_open_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L330) |
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L366) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L372) |
| function | `_html_to_text` | `(raw)` | Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift). | [src](../../../core/tools/simple_tools_web.py#L761) |
| function | `_egress_blokeret` | `(url)` | Fejl-svaret hvis destinationen er intern, ellers None. | [src](../../../core/tools/simple_tools_web.py#L800) |
| function | `_fetch_cache_get` | `(url)` | — | [src](../../../core/tools/simple_tools_web.py#L841) |
| function | `_fetch_cache_put` | `(url, raw)` | — | [src](../../../core/tools/simple_tools_web.py#L852) |
| class | `_RevaliderendeRedirect` | `` | Stopper en omdirigering mod et internt maal, hop for hop. | [src](../../../core/tools/simple_tools_web.py#L870) |
| method | `_RevaliderendeRedirect.redirect_request` | `(self, req, fp, code, msg, headers, newurl)` | — | [src](../../../core/tools/simple_tools_web.py#L873) |
| function | `_hent_side` | `(url)` | Hent en side med redirect-revalidering og kort cache. | [src](../../../core/tools/simple_tools_web.py#L888) |
| function | `_hent_side_via_exa` | `(url)` | Hent en side gennem Exas MCP-server. ``None`` hvis den ikke kan. | [src](../../../core/tools/simple_tools_web.py#L915) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L945) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L1012) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L1031) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L1041) |
| function | `_fetch_serpapi` | `(query, max_results)` | Raw SerpAPI (Google SERP) call — no caching. | [src](../../../core/tools/simple_tools_web.py#L1082) |
| function | `_fetch_exa` | `(query, max_results)` | Raw Exa MCP search — no caching. Bruges som tredje kandidat. | [src](../../../core/tools/simple_tools_web.py#L1129) |
| function | `_fetch_alle_providers` | `(query, max_results)` | Exa først — de to andre som fallback. IKKE en dommer (målt 18/10-2026). | [src](../../../core/tools/simple_tools_web.py#L1231) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L1353) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L1360) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L1374) |
| function | `_er_dato` | `(tekst)` | Sandt hvis ``tekst`` er en gyldig YYYY-MM-DD-dato. | [src](../../../core/tools/simple_tools_web.py#L1402) |
| function | `_owm_get` | `(path, params, api_key, timeout=…)` | Ét OpenWeatherMap-kald. Kaster aldrig — fejl returneres som ``_error``. | [src](../../../core/tools/simple_tools_web.py#L1414) |
| function | `_owm_local` | `(epoch, offset_s)` | Epoch → ISO-lokal tid for STEDET. | [src](../../../core/tools/simple_tools_web.py#L1425) |
| function | `_owm_precip_mm` | `(punkt)` | Regn + sne i mm. Current bruger ``1h``, forecast bruger ``3h`` — vi summer alt. | [src](../../../core/tools/simple_tools_web.py#L1441) |
| function | `_owm_daily` | `(punkter, offset_s, antal)` | Gruppér 3-timers-punkter i lokale døgn og opsummer hvert døgn. | [src](../../../core/tools/simple_tools_web.py#L1455) |
| function | `_exec_get_weather` | `(args)` | Vejr via OpenWeatherMap — nu, prognose, døgn og luftkvalitet. | [src](../../../core/tools/simple_tools_web.py#L1513) |
| function | `_exec_get_exchange_rate` | `(args)` | Valutakurser via exchangerate.host — med lokal konvertering. | [src](../../../core/tools/simple_tools_web.py#L1678) |
| function | `_exec_get_news` | `(args)` | Nyheder via NewsAPI — bred dansk søgning som standard. | [src](../../../core/tools/simple_tools_web.py#L1729) |
| function | `_stage_image_preview` | `(image_bytes, source_path)` | Den sti desk kan hente billedet paa — uden at aabne hvidlisten. | [src](../../../core/tools/simple_tools_web.py#L1812) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L1834) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L1960) |
| function | `_exec_wolfram_query` | `(args)` | Wolfram Alpha — kort svar eller de fulde pods. | [src](../../../core/tools/simple_tools_web.py#L2030) |

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

## `core/tools/skill_dansk_tillaeg.py`
_Danske udtryksmaader for skills der kun beskriver sig selv paa engelsk._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dansk_udtryk` | `(skill_navn)` | Den danske udtryks-linje for et skill, eller "" hvis der ingen er. | [src](../../../core/tools/skill_dansk_tillaeg.py#L113) |

## `core/tools/skill_engine_tools.py`
_Skill Engine tools — Jarvis skill system._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_bilingual_use_when` | `(text)` | Split a use_when block into separate language fragments. | [src](../../../core/tools/skill_engine_tools.py#L31) |
| function | `_noegle` | `(tekst)` | Stabil cache-nøgle for et kandidat-fragment. | [src](../../../core/tools/skill_engine_tools.py#L66) |
| function | `_cosinus` | `(a, b)` | — | [src](../../../core/tools/skill_engine_tools.py#L72) |
| function | `_betydende_ord` | `(tekst)` | — | [src](../../../core/tools/skill_engine_tools.py#L104) |
| function | `_skill_ord` | `(navn, kandidat)` | Skillens egne ord: navnet (med bindestreg som mellemrum) plus det | [src](../../../core/tools/skill_engine_tools.py#L111) |
| function | `_suggest_skills_for_query` | `(query, threshold=…, max_results=…, context_tags=…)` | Match a user query against all installed skills' use_when + description. | [src](../../../core/tools/skill_engine_tools.py#L118) |
| function | `_exec_skill_list` | `(args)` | List all loaded skills, optionally filtered by tag. | [src](../../../core/tools/skill_engine_tools.py#L261) |
| function | `_exec_skill_invoke` | `(args)` | Get a skill's instructions for prompt injection. | [src](../../../core/tools/skill_engine_tools.py#L274) |
| function | `_exec_propose_new_skill` | `(args)` | Propose a new skill via the plan-approval flow. | [src](../../../core/tools/skill_engine_tools.py#L341) |
| function | `_exec_skill_create` | `(args)` | Create a new skill on disk. | [src](../../../core/tools/skill_engine_tools.py#L410) |
| function | `_exec_skill_delete` | `(args)` | Delete a skill from disk. | [src](../../../core/tools/skill_engine_tools.py#L432) |
| function | `_exec_skill_search` | `(args)` | Search skills by keyword. | [src](../../../core/tools/skill_engine_tools.py#L440) |
| function | `_exec_skill_get` | `(args)` | Get full detail on a single skill. | [src](../../../core/tools/skill_engine_tools.py#L453) |
| function | `_exec_skill_reload` | `(args)` | Force-reload all skills from disk. | [src](../../../core/tools/skill_engine_tools.py#L479) |
| function | `_exec_skill_suggest` | `(args)` | Suggest skills relevant to a user query via semantic matching. | [src](../../../core/tools/skill_engine_tools.py#L484) |
| function | `_exec_skill_import` | `(args)` | Import a skill from a local path (directory or zip archive). | [src](../../../core/tools/skill_engine_tools.py#L520) |
| function | `_find_skill_dir_in_tree` | `(root)` | Walk a directory tree and find the first directory containing SKILL.md. | [src](../../../core/tools/skill_engine_tools.py#L683) |
| function | `_fetch_url_capped` | `(url, *, timeout=…)` | Fetch a URL, capped at _MAX_URL_FETCH_BYTES. Returns (content, error). | [src](../../../core/tools/skill_engine_tools.py#L706) |
| function | `_install_skill_md_content` | `(*, content, target_name, source_label)` | Stage SKILL.md content in a tempdir, scan, copy to skills root, reload. | [src](../../../core/tools/skill_engine_tools.py#L730) |
| function | `_exec_skill_import_from_url` | `(args)` | Import a skill from a remote URL. | [src](../../../core/tools/skill_engine_tools.py#L818) |
| function | `_exec_skill_history` | `(args)` | Return audit trail for a single skill. | [src](../../../core/tools/skill_engine_tools.py#L1154) |
| function | `_exec_recent_skill_changes` | `(args)` | Return most recent skill mutations across all skills. | [src](../../../core/tools/skill_engine_tools.py#L1167) |
| function | `_exec_analyze_skill_usage` | `(args)` | Analyze skill usage patterns over the past N days. | [src](../../../core/tools/skill_engine_tools.py#L1177) |

## `core/tools/skill_gate_tool.py`
_Skill Gate Tool — pre-action gate for automatic skill suggestion + invocation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_chain_candidates` | `(suggestions)` | Return top-3 (max) skills within 0.10 of top score. | [src](../../../core/tools/skill_gate_tool.py#L54) |
| function | `_build_chain_hint` | `(candidates)` | Render human-readable chain suggestion from candidates. | [src](../../../core/tools/skill_gate_tool.py#L78) |
| function | `_skill_summary` | `(result, *, max_chars=…)` | — | [src](../../../core/tools/skill_gate_tool.py#L92) |
| function | `_exec_skill_gate` | `(args)` | Pre-action gate: match user query to installed skills, invoke if relevant. | [src](../../../core/tools/skill_gate_tool.py#L106) |

## `core/tools/smart_compact_tools.py`
_Smart context compaction — preserves decisions/facts, discards routine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_smart_compact_prompt` | `()` | Build compact prompt lazily so identity_prompt_prefix resolves at runtime, not module import. | [src](../../../core/tools/smart_compact_tools.py#L9) |
| function | `_estimate_session_tokens` | `()` | Rough estimate of current session's token count. | [src](../../../core/tools/smart_compact_tools.py#L40) |
| function | `_exec_smart_compact` | `(args)` | Compact context with a smarter prompt that preserves decisions/facts. | [src](../../../core/tools/smart_compact_tools.py#L60) |
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

## `core/tools/state_flag_tools.py`
_State-flag tools (leak-kandidat #1, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_uid` | `()` | — | [src](../../../core/tools/state_flag_tools.py#L16) |
| function | `_exec_set_flag` | `(args)` | — | [src](../../../core/tools/state_flag_tools.py#L24) |
| function | `_exec_get_flag` | `(args)` | — | [src](../../../core/tools/state_flag_tools.py#L41) |
| function | `_exec_clear_flag` | `(args)` | — | [src](../../../core/tools/state_flag_tools.py#L52) |
| function | `_exec_list_flags` | `(_args)` | — | [src](../../../core/tools/state_flag_tools.py#L63) |

## `core/tools/streaming_subprocess.py`
_One-shot subprocess execution with best-effort incremental output._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StreamingProcessResult` | `` | — | [src](../../../core/tools/streaming_subprocess.py#L19) |
| function | `run_streaming` | `(argv, *, cwd, timeout_s, on_output)` | — | [src](../../../core/tools/streaming_subprocess.py#L28) |

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

## `core/tools/surface_tools.py`
_`vaelg_flade` — fladebeslutningen, truffet før formuleringen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_as_int` | `(value)` | Negative og ikke-numeriske tal betyder «ved det ikke», ikke en fejl. | [src](../../../core/tools/surface_tools.py#L26) |
| function | `_exec_vaelg_flade` | `(args)` | Afgør fladen. Kaster aldrig — en fejl her må ikke vælte turen. | [src](../../../core/tools/surface_tools.py#L34) |

## `core/tools/think_language_tools.py`
_Værktøj: skift tænke-sprog uden genstart (killswitch, 30/9-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_think_language` | `(args)` | — | [src](../../../core/tools/think_language_tools.py#L17) |

## `core/tools/tool_call_observation.py`
_Alt hvad der KUN observerer et vaerktoejskald — efter det er kaldt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_tool_call` | `(name, arguments, result)` | Observér et faerdigt vaerktoejskald. Kaster aldrig. | [src](../../../core/tools/tool_call_observation.py#L16) |

## `core/tools/tool_call_telemetry.py`
_Hvem kaldte hvilket vaerktoej — gjort taelleligt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internt_kald` | `()` | Markér kaldet som systemets eget — ikke et model-kald. | [src](../../../core/tools/tool_call_telemetry.py#L64) |
| function | `er_internt_kald` | `()` | Er vi inde i et af systemets egne kald? Se `internt_kald`. | [src](../../../core/tools/tool_call_telemetry.py#L76) |
| function | `_fra_args` | `(arguments, navn)` | — | [src](../../../core/tools/tool_call_telemetry.py#L88) |
| function | `identitet` | `(arguments)` | Bruger, samtale og run — fra argumenterne, ellers fra konteksten. | [src](../../../core/tools/tool_call_telemetry.py#L92) |
| function | `byg_payload` | `(name, arguments)` | Selve eventet. Adskilt fra udgivelsen, saa formen kan testes alene. | [src](../../../core/tools/tool_call_telemetry.py#L131) |
| function | `udgiv_tool_invoked` | `(name, arguments)` | Udgiv `tool.invoked`. Maa ALDRIG braekke et vaerktoejskald. | [src](../../../core/tools/tool_call_telemetry.py#L140) |
| function | `udgiv_execution_timing` | `(payload)` | Publish one terminal timing summary without affecting the tool call. | [src](../../../core/tools/tool_call_telemetry.py#L150) |
| function | `byg_completed_payload` | `(name, status, arguments, result=…, pre_read=…)` | `tool.completed` — nu med de to felter der goer parringen mulig. | [src](../../../core/tools/tool_call_telemetry.py#L182) |

## `core/tools/tool_definition_v2.py`
_De tre akser skilt ad — Fase 3, K1._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolDefinitionV2` | `` | — | [src](../../../core/tools/tool_definition_v2.py#L75) |
| method | `ToolDefinitionV2.annonceret_uden_executor` | `(self)` | — | [src](../../../core/tools/tool_definition_v2.py#L86) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/tools/tool_definition_v2.py#L93) |
| function | `_pak_ud` | `(handler)` | Find den ÆGTE funktion bag eventuelle indpakninger. | [src](../../../core/tools/tool_definition_v2.py#L97) |
| function | `_handler_kilde` | `(handler)` | — | [src](../../../core/tools/tool_definition_v2.py#L122) |
| function | `_udled_provider` | `(navn, handler)` | Hvor koerer vaerktoejet? Udledt af KODEN, ikke af navnet. | [src](../../../core/tools/tool_definition_v2.py#L129) |
| function | `_udled_effekt` | `(navn)` | — | [src](../../../core/tools/tool_definition_v2.py#L149) |
| function | `_udled_godkendelse` | `(navn, handler)` | — | [src](../../../core/tools/tool_definition_v2.py#L159) |
| function | `_udled_flader` | `(navn)` | — | [src](../../../core/tools/tool_definition_v2.py#L171) |
| function | `describe` | `(navn)` | Byg V2-beskrivelsen for ét vaerktoej. None hvis det ikke annonceres. | [src](../../../core/tools/tool_definition_v2.py#L183) |
| function | `all_definitions` | `()` | — | [src](../../../core/tools/tool_definition_v2.py#L211) |
| function | `inconsistencies` | `()` | Hvor er de tre sandheder uenige? | [src](../../../core/tools/tool_definition_v2.py#L221) |
| function | `presentation_meta` | `(navn, arguments, result)` | Semantiske hints til klientens kort — udledt af det KONKRETE kald. | [src](../../../core/tools/tool_definition_v2.py#L239) |

## `core/tools/tool_limits.py`
_Grænser for værktøjs-kørsel — ét sted, så de to bash-stier ikke driver fra hinanden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `bash_timeout_s` | `()` | Sekunder en enkelt bash-kommando må tage. Overstyres i runtime.json som | [src](../../../core/tools/tool_limits.py#L22) |
| function | `timeout_note` | `(seconds, command=…)` | Besked når en kommando løber tør for tid. | [src](../../../core/tools/tool_limits.py#L35) |

## `core/tools/tool_result_format.py`
_Formatering af vaerktoejsresultater til modellen + verify-hints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_verify_hint_for` | `(tool, result)` | Build a brief, contextual verify-hint to attach to a mutation's result. | [src](../../../core/tools/tool_result_format.py#L15) |
| function | `_json_safe_default` | `(o)` | json.dumps default= — GARANTERER at serialisering af et tool-resultat | [src](../../../core/tools/tool_result_format.py#L74) |
| function | `_signal_linjer` | `(result)` | Korte linjer for signaler der ellers forsvinder naar ``text`` findes. | [src](../../../core/tools/tool_result_format.py#L90) |
| function | `format_tool_result_for_model` | `(name, result, *, clip=…)` | Format a tool result as text for the model's context. | [src](../../../core/tools/tool_result_format.py#L126) |

## `core/tools/tool_schema_contract.py`
_Kanoniske argumenter mod versionerede skemaer — Fase 3, K2._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Brud` | `` | Ét skema-brud. `haard` siger om det er sikkert at afvise paa. | [src](../../../core/tools/tool_schema_contract.py#L65) |
| method | `Brud.haard` | `(self)` | — | [src](../../../core/tools/tool_schema_contract.py#L72) |
| function | `_indlaes` | `()` | — | [src](../../../core/tools/tool_schema_contract.py#L76) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/tools/tool_schema_contract.py#L89) |
| function | `kendt` | `(tool_name)` | Har vaerktoejet overhovedet et skema at maale imod? | [src](../../../core/tools/tool_schema_contract.py#L96) |
| function | `schema_version` | `(tool_name)` | Indholds-hash over skemaet. Aendrer skemaet sig, aendrer versionen sig. | [src](../../../core/tools/tool_schema_contract.py#L101) |
| function | `canonical_arguments` | `(tool_name, arguments)` | Argumenterne som SKEMAET ser dem. | [src](../../../core/tools/tool_schema_contract.py#L115) |
| function | `_validator` | `(tool_name)` | — | [src](../../../core/tools/tool_schema_contract.py#L127) |
| function | `_kun_bloedt` | `(tool_name, besked)` | Er det manglende felt et af dem der kun er krævet for modellens skyld? | [src](../../../core/tools/tool_schema_contract.py#L145) |
| function | `violations` | `(tool_name, arguments)` | Hvilke skema-brud har dette kald? Tom liste = ingen. | [src](../../../core/tools/tool_schema_contract.py#L152) |
| function | `haarde` | `(brud)` | — | [src](../../../core/tools/tool_schema_contract.py#L177) |
| function | `afvisning` | `(tool_name, brud)` | Svaret et afvist kald skal have. | [src](../../../core/tools/tool_schema_contract.py#L181) |

