# `core.tools.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `evaluate_command` | `(command)` | Første matchende bash-predikat (blocked før destructive) på den normaliserede | [src](../../../core/tools/security_predicates.py#L57) |
| function | `evaluate_write` | `(resolved_path)` | Første matchende write-predikat (substring) på stien, ellers None. | [src](../../../core/tools/security_predicates.py#L75) |
| function | `all_predicates` | `()` | — | [src](../../../core/tools/security_predicates.py#L86) |
| function | `build_security_predicates_surface` | `()` | Central-CLI read-surface: jc raw /central/security-predicates. | [src](../../../core/tools/security_predicates.py#L90) |
| function | `render_predicates_md` | `()` | Genererer docs/security_predicates.md fra registry'en (kilde = koden). | [src](../../../core/tools/security_predicates.py#L104) |

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
| function | `canonical_identity_file_path` | `(name)` | Den ENE fil `name` bor i — samme opslag som prompten bruger til at LÆSE. | [src](../../../core/tools/simple_tools.py#L701) |
| function | `_canonicalize_workspace_target` | `(target)` | If target's basename is a canonical workspace file, force it to the | [src](../../../core/tools/simple_tools.py#L730) |
| function | `_emit_security_check` | `(hit, *, target)` | Self-safe audit-emit: et deny/destructive bæres nu med sit nummererede | [src](../../../core/tools/simple_tools.py#L848) |
| function | `classify_command` | `(command)` | Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L862) |
| function | `classify_file_write` | `(path)` | Classify a file write: 'auto', 'approval', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L960) |
| function | `execute_tool` | `(name, arguments)` | Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1). | [src](../../../core/tools/simple_tools.py#L982) |
| function | `_execute_tool_impl` | `(name, arguments)` | Execute a tool call and return the result. | [src](../../../core/tools/simple_tools.py#L1018) |
| function | `execute_tool_force` | `(name, arguments, *, owner_approved=…)` | Execute tool bypassing approval checks. Only call for user-approved requests. | [src](../../../core/tools/simple_tools.py#L1181) |
| function | `_execute_tool_force_impl` | `(name, arguments)` | — | [src](../../../core/tools/simple_tools.py#L1214) |
| function | `_record_tool_outcome_memory` | `(name, arguments, result, *, mode)` | — | [src](../../../core/tools/simple_tools.py#L1304) |
| function | `_med_samtykke` | `(navn, fn)` | — | [src](../../../core/tools/simple_tools.py#L2022) |
| function | `get_tool_definitions` | `(role=…, scope=…)` | Return Ollama-compatible tool definitions, filtered by role + scope. | [src](../../../core/tools/simple_tools.py#L2108) |

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
| function | `_til_openai_form` | `(td)` | Anthropic-formet definition → OpenAI-formet. Andet passerer urørt. | [src](../../../core/tools/simple_tools_definitions.py#L3555) |
| function | `_ensret_tool_definitions` | `(defs)` | — | [src](../../../core/tools/simple_tools_definitions.py#L3572) |

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
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L985) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1030) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1054) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1075) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1122) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1139) |
| function | `_exec_send_ntfy` | `(args)` | Send en besked til Bjørn gennem routeren. | [src](../../../core/tools/simple_tools_native.py#L1179) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1207) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord, optionally with a file attachment. | [src](../../../core/tools/simple_tools_native.py#L1231) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1314) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1348) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1542) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1612) |
| function | `_explore_spawn` | `(*, query, vejledning, provider=…, model=…)` | Ét explore-spawn. Udskilt så påstands-værnet kan prøve en anden model. | [src](../../../core/tools/simple_tools_native.py#L1732) |
| function | `_explore_svar` | `(result)` | (fund, udbyder_fejl). Kun beskeder af kinden `result` er fund. | [src](../../../core/tools/simple_tools_native.py#L1781) |
| function | `_exec_explore` | `(args)` | Bred, laese-kun undersoegelse — ét spoergsmaal ind, fund ud. | [src](../../../core/tools/simple_tools_native.py#L1801) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1901) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1939) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1963) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1998) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2013) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2022) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2036) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2041) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2047) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L2068) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2073) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L2113) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2184) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2214) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2242) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2270) |
| function | `_exec_look_around` | `(args)` | Look through one of the house cameras now and describe what's there. | [src](../../../core/tools/simple_tools_native.py#L2294) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2327) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2380) |
| function | `_exec_interlanguage_protocol` | `(args)` | Eksportér inter-sprog-protokollen (designets fase 5 — bæring ved modelskift). | [src](../../../core/tools/simple_tools_native.py#L2393) |
| function | `_exec_compact_context_session` | `(session_id)` | Komprimér sessionen. Returnerer CompactResult eller None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2424) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2449) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2471) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2524) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2533) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2542) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2550) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2557) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2578) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2584) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2591) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2597) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2604) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2610) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2632) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2651) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2673) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2679) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2684) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2689) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2694) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2699) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2704) |
| function | `_exec_operator_channel` | `(args)` | Aabn/luk/vis operator-kanalen. Owner-only for open/close. | [src](../../../core/tools/simple_tools_native.py#L2792) |
| function | `_exec_mcp` | `(args)` | Én indgang til MCP: se, godkend, list vaerktoejer, kald. | [src](../../../core/tools/simple_tools_native.py#L2810) |
| function | `_exec_checkpoint` | `(args)` | Se eller fortryd en redigeringsrunde. | [src](../../../core/tools/simple_tools_native.py#L2850) |

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
| function | `_rapporter_gate_svigt` | `(vaerktoej, path, exc)` | Sig højt at et gate-kald svigtede, og lad handlingen fortsætte. | [src](../../../core/tools/simple_tools_operator.py#L198) |
| function | `_exec_operator_read_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L223) |
| function | `_operator_file_exists` | `(path, user_id)` | Best-effort: does `path` exist on the operator's machine? | [src](../../../core/tools/simple_tools_operator.py#L254) |
| function | `_sti_gate_operator` | `(path, args, *, kind, tool, forhaandsvisning=…)` | Sti-gate for operator-fil-skrivning. ``None`` = maa fortsaette. | [src](../../../core/tools/simple_tools_operator.py#L293) |
| function | `_exec_operator_write_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L331) |
| function | `_exec_operator_edit_file` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L416) |
| function | `_exec_operator_run_in_background` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L500) |
| function | `_exec_operator_bash_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L526) |
| function | `_exec_operator_kill_shell` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L539) |
| function | `_exec_operator_multi_edit` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L551) |
| function | `_exec_operator_glob` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L600) |
| function | `_exec_operator_grep` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L619) |
| function | `_exec_operator_list_dir` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L641) |
| function | `_exec_operator_webfetch` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L655) |
| function | `_exec_operator_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L676) |
| function | `_exec_operator_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L711) |
| function | `_exec_operator_open_url` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L732) |
| function | `_exec_operator_launch_app` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L763) |
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L808) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L824) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L845) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L855) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L874) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L891) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L901) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L911) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L924) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L934) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L960) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L976) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L997) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1012) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1047) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1067) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1088) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1106) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1132) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1152) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1170) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1185) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1198) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1216) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1229) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1247) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1264) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1278) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1299) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1318) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1333) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1350) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1391) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1409) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1426) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1436) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1455) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1476) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1492) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1522) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1532) |

## `core/tools/simple_tools_web.py`
_Web/search/system-info tool executors for Jarvis' native lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_glob_to_regex` | `(pattern)` | Oversæt et glob-mønster (POSIX-relativt) til en regex med KORREKT sti-semantik: | [src](../../../core/tools/simple_tools_web.py#L63) |
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn). | [src](../../../core/tools/simple_tools_web.py#L84) |
| function | `_cached_web_search_fn` | `(*, query, max_results, fetch_fn)` | Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_web.py#L90) |
| function | `_observe_research_result` | `(tool_name, result)` | Best-effort observer; ordinary web calls never depend on research state. | [src](../../../core/tools/simple_tools_web.py#L95) |
| function | `_exec_search` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L104) |
| function | `_exec_find_files` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L233) |
| function | `_get_or_open_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L328) |
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L364) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L370) |
| function | `_html_to_text` | `(raw)` | Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift). | [src](../../../core/tools/simple_tools_web.py#L719) |
| function | `_egress_blokeret` | `(url)` | Fejl-svaret hvis destinationen er intern, ellers None. | [src](../../../core/tools/simple_tools_web.py#L758) |
| function | `_fetch_cache_get` | `(url)` | — | [src](../../../core/tools/simple_tools_web.py#L799) |
| function | `_fetch_cache_put` | `(url, raw)` | — | [src](../../../core/tools/simple_tools_web.py#L810) |
| class | `_RevaliderendeRedirect` | `` | Stopper en omdirigering mod et internt maal, hop for hop. | [src](../../../core/tools/simple_tools_web.py#L828) |
| method | `_RevaliderendeRedirect.redirect_request` | `(self, req, fp, code, msg, headers, newurl)` | — | [src](../../../core/tools/simple_tools_web.py#L831) |
| function | `_hent_side` | `(url)` | Hent en side med redirect-revalidering og kort cache. | [src](../../../core/tools/simple_tools_web.py#L846) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L861) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L928) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L947) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L957) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L998) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L1005) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L1017) |
| function | `_exec_get_weather` | `(args)` | Current weather via OpenWeatherMap. | [src](../../../core/tools/simple_tools_web.py#L1029) |
| function | `_exec_get_exchange_rate` | `(args)` | Currency exchange rates via exchangerate.host. | [src](../../../core/tools/simple_tools_web.py#L1063) |
| function | `_exec_get_news` | `(args)` | Recent news via NewsAPI. | [src](../../../core/tools/simple_tools_web.py#L1090) |
| function | `_stage_image_preview` | `(image_bytes, source_path)` | Den sti desk kan hente billedet paa — uden at aabne hvidlisten. | [src](../../../core/tools/simple_tools_web.py#L1126) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L1148) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L1274) |
| function | `_exec_wolfram_query` | `(args)` | Precise answers via Wolfram Alpha Short Answers API. | [src](../../../core/tools/simple_tools_web.py#L1344) |

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
| function | `_fra_args` | `(arguments, navn)` | — | [src](../../../core/tools/tool_call_telemetry.py#L49) |
| function | `identitet` | `(arguments)` | Bruger, samtale og run — fra argumenterne, ellers fra konteksten. | [src](../../../core/tools/tool_call_telemetry.py#L53) |
| function | `byg_payload` | `(name, arguments)` | Selve eventet. Adskilt fra udgivelsen, saa formen kan testes alene. | [src](../../../core/tools/tool_call_telemetry.py#L76) |
| function | `udgiv_tool_invoked` | `(name, arguments)` | Udgiv `tool.invoked`. Maa ALDRIG braekke et vaerktoejskald. | [src](../../../core/tools/tool_call_telemetry.py#L85) |
| function | `byg_completed_payload` | `(name, status, arguments)` | `tool.completed` — nu med de to felter der goer parringen mulig. | [src](../../../core/tools/tool_call_telemetry.py#L95) |

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

## `core/tools/tool_scoping.py`
_Tool-scoping policy — hvilke værktøjer er tilgængelige pr. rolle og mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_local_execution_tool` | `(name)` | True hvis værktøjet kører lokalt i code mode (resultat forlader ikke maskinen). | [src](../../../core/tools/tool_scoping.py#L305) |
| function | `current_tool_scope` | `()` | Nuværende tool-scope ("chat" eller "" for ubegrænset). | [src](../../../core/tools/tool_scoping.py#L316) |
| function | `set_tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L321) |
| function | `reset_tool_scope` | `(token)` | — | [src](../../../core/tools/tool_scoping.py#L325) |
| function | `current_local_exec` | `()` | True når det aktive run er en jarvis-code Path B lokal-exec-tur. | [src](../../../core/tools/tool_scoping.py#L338) |
| function | `set_local_exec` | `(on)` | — | [src](../../../core/tools/tool_scoping.py#L343) |
| function | `tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L348) |
| function | `_owner_has_live_bridge` | `()` | True hvis der findes en levende desk-bro for nuværende bruger (presence, cross-proces). | [src](../../../core/tools/tool_scoping.py#L356) |
| function | `_phone_tool_names` | `()` | Telefonens vaerktoejer — hentet fra ét sted, ikke gentaget her. | [src](../../../core/tools/tool_scoping.py#L370) |
| function | `_owner_has_live_phone` | `()` | True hvis en TELEFON er forbundet for nuvaerende bruger. | [src](../../../core/tools/tool_scoping.py#L388) |
| function | `_phone_adb_tool_names` | `()` | ADB-vaerktoejernes navne — ét sted, ikke gentaget her. | [src](../../../core/tools/tool_scoping.py#L422) |
| function | `_adb_er_opsat` | `()` | Er der overhovedet en telefon at pege adb paa? | [src](../../../core/tools/tool_scoping.py#L435) |
| function | `_forbundne_connector_vaerktoejer` | `()` | Vaerktoejer fra apps brugeren FAKTISK har forbundet. | [src](../../../core/tools/tool_scoping.py#L454) |
| function | `allowed_tool_names` | `(*, role, scope, all_names)` | Beregn det tilladte sæt tool-navne for (role, scope). | [src](../../../core/tools/tool_scoping.py#L488) |
| function | `preferred_tools_for_user_message` | `(user_message)` | Order hint for tool choice; does not grant or revoke permissions. | [src](../../../core/tools/tool_scoping.py#L564) |
| function | `tool_routing_hint` | `(user_message)` | Prompt hint for personal/internal vs external lookup intent. | [src](../../../core/tools/tool_scoping.py#L574) |
| function | `is_tool_allowed` | `(*, role, scope, name)` | Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.) | [src](../../../core/tools/tool_scoping.py#L591) |
| function | `_apply_computer_use_policy` | `(result)` | Computer-use-toggle (§4.7): fjern operator/computer-tools hvis brugeren har | [src](../../../core/tools/tool_scoping.py#L604) |
| function | `_fn_name` | `(td)` | — | [src](../../../core/tools/tool_scoping.py#L628) |
| function | `filter_tool_definitions` | `(defs, *, role, scope)` | Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope). | [src](../../../core/tools/tool_scoping.py#L632) |

## `core/tools/tool_text_render.py`
_Læsbar `text`-form for strukturerede tool-resultater._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cell` | `(value, limit=…)` | — | [src](../../../core/tools/tool_text_render.py#L31) |
| function | `render_daemons` | `(daemons)` | Én linje pr. dæmon: navn, om den kører, kadence, hvornår sidst. | [src](../../../core/tools/tool_text_render.py#L37) |
| function | `render_events` | `(events)` | Én linje pr. hændelse: tid, art, og begyndelsen af payload. | [src](../../../core/tools/tool_text_render.py#L77) |
| function | `render_rows` | `(columns, rows, *, capped=…)` | Et resultatsæt som en justeret tabel. | [src](../../../core/tools/tool_text_render.py#L102) |

## `core/tools/ui_panel_tools.py`
_open_ui_panel-tool (spec §8.2, Fase 6 #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_open_ui_panel` | `(args)` | — | [src](../../../core/tools/ui_panel_tools.py#L24) |

## `core/tools/verify_tools.py`
_Verification tools — wrap "do then check" into one call._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_verify_file_contains` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L32) |
| function | `_exec_verify_service_active` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L98) |
| function | `_exec_verify_endpoint_responds` | `(args)` | — | [src](../../../core/tools/verify_tools.py#L121) |

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

## `core/tools/wake_word_tool.py`
_Wake-word tool — Jarvis listens for 'Hey Jarvis' in the background._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_on_wake` | `(phrase)` | Callback fired when wake word detected. | [src](../../../core/tools/wake_word_tool.py#L33) |
| function | `_run_listener` | `()` | Entry for the background listener thread. | [src](../../../core/tools/wake_word_tool.py#L109) |
| function | `start_wake_word` | `(*, auto_listen=…, auto_listen_duration=…)` | Start the background wake-word listener. Idempotent. | [src](../../../core/tools/wake_word_tool.py#L118) |
| function | `stop_wake_word` | `()` | Stop the background wake-word listener. | [src](../../../core/tools/wake_word_tool.py#L180) |
| function | `wake_word_status` | `()` | — | [src](../../../core/tools/wake_word_tool.py#L217) |
| function | `_exec_wake_word` | `(args)` | — | [src](../../../core/tools/wake_word_tool.py#L230) |

## `core/tools/web_cache.py`
_Web search result cache — normalization, TTL classification, orchestration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_query` | `(raw)` | Normalize query and produce SHA256 cache key. | [src](../../../core/tools/web_cache.py#L10) |
| function | `classify_ttl` | `(query)` | Classify query into a TTL policy. First match wins, default medium. | [src](../../../core/tools/web_cache.py#L31) |
| function | `cached_web_search` | `(*, query, max_results, fetch_fn, conn=…)` | Check cache, call fetch_fn on miss, store result. | [src](../../../core/tools/web_cache.py#L40) |

