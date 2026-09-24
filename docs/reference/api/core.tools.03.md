# `core.tools.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_exec_schedule_task` | `(args)` | Schedule a task to fire after delay_minutes. | [src](../../../core/tools/simple_tools_native.py#L617) |
| function | `_exec_list_scheduled_tasks` | `(_args)` | List scheduled tasks (pending + recently fired). | [src](../../../core/tools/simple_tools_native.py#L644) |
| function | `_exec_cancel_task` | `(args)` | Cancel a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L676) |
| function | `_exec_edit_task` | `(args)` | Edit a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L691) |
| function | `_exec_read_chronicles` | `(args)` | Return recent cognitive chronicle entries. | [src](../../../core/tools/simple_tools_native.py#L712) |
| function | `_exec_read_dreams` | `(args)` | Return active dream hypothesis signals and adoption candidates. | [src](../../../core/tools/simple_tools_native.py#L758) |
| function | `_exec_notify_user` | `(args)` | Push a proactive message to webchat, Discord, or both. | [src](../../../core/tools/simple_tools_native.py#L824) |
| function | `_exec_read_self_state` | `(_args)` | Return Jarvis's current internal cadence/emotional state. | [src](../../../core/tools/simple_tools_native.py#L895) |
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L981) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1026) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1050) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1071) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1113) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1130) |
| function | `_exec_send_ntfy` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1170) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1186) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json. | [src](../../../core/tools/simple_tools_native.py#L1210) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1254) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1288) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1482) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1552) |
| function | `_exec_convene_council` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1669) |
| function | `_exec_council_status` | `(args)` | Hent et raad der blev sat i gang med `convene_council`. | [src](../../../core/tools/simple_tools_native.py#L1722) |
| function | `_exec_quick_council_check` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1728) |
| function | `_exec_spawn_agent_task` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1765) |
| function | `_explore_spawn` | `(*, query, vejledning, provider=…, model=…)` | Ét explore-spawn. Udskilt så påstands-værnet kan prøve en anden model. | [src](../../../core/tools/simple_tools_native.py#L1824) |
| function | `_explore_svar` | `(result)` | (fund, udbyder_fejl). Kun beskeder af kinden `result` er fund. | [src](../../../core/tools/simple_tools_native.py#L1873) |
| function | `_exec_explore` | `(args)` | Bred, laese-kun undersoegelse — ét spoergsmaal ind, fund ud. | [src](../../../core/tools/simple_tools_native.py#L1893) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1993) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2031) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2055) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2090) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2105) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2114) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2128) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2133) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2139) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L2160) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2165) |
| function | `_exec_recall_council_conclusions` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2205) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L2234) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2305) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2335) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2363) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2391) |
| function | `_exec_look_around` | `(args)` | Look through one of the house cameras now and describe what's there. | [src](../../../core/tools/simple_tools_native.py#L2415) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2448) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2501) |
| function | `_exec_interlanguage_protocol` | `(args)` | Eksportér inter-sprog-protokollen (designets fase 5 — bæring ved modelskift). | [src](../../../core/tools/simple_tools_native.py#L2514) |
| function | `_json_safe_cell` | `(v)` | Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8 | [src](../../../core/tools/simple_tools_native.py#L2529) |
| function | `_exec_db_query` | `(args)` | Run a read-only SELECT query against Jarvis' database. | [src](../../../core/tools/simple_tools_native.py#L2548) |
| function | `_exec_compact_context_session` | `(session_id)` | Komprimér sessionen. Returnerer CompactResult eller None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2614) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2639) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2661) |
| function | `_exec_publish_file` | `(args)` | Copy or create a file in ~/.jarvis-v2/files/ and return a download URL. | [src](../../../core/tools/simple_tools_native.py#L2682) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2820) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2829) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2838) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2846) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2853) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2874) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2880) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2887) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2893) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2900) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2906) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2928) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2947) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2969) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2975) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2980) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2985) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2990) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2995) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L3000) |
| function | `_exec_operator_channel` | `(args)` | Aabn/luk/vis operator-kanalen. Owner-only for open/close. | [src](../../../core/tools/simple_tools_native.py#L3091) |
| function | `_exec_mcp` | `(args)` | Én indgang til MCP: se, godkend, list vaerktoejer, kald. | [src](../../../core/tools/simple_tools_native.py#L3105) |
| function | `_exec_checkpoint` | `(args)` | Se eller fortryd en redigeringsrunde. | [src](../../../core/tools/simple_tools_native.py#L3145) |

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
| function | `_exec_operator_bash_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L525) |
| function | `_exec_operator_kill_shell` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L538) |
| function | `_exec_operator_multi_edit` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L550) |
| function | `_exec_operator_glob` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L599) |
| function | `_exec_operator_grep` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L618) |
| function | `_exec_operator_list_dir` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L640) |
| function | `_exec_operator_webfetch` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L654) |
| function | `_exec_operator_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L675) |
| function | `_exec_operator_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L704) |
| function | `_exec_operator_open_url` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L725) |
| function | `_exec_operator_launch_app` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L756) |
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L801) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L817) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L838) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L848) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L867) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L884) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L894) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L904) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L917) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L927) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L953) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L969) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L990) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1005) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1040) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1060) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1081) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1099) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1125) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1145) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1163) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1178) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1191) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1209) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1222) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1240) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1257) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1271) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1292) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1311) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1326) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1343) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1384) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1402) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1419) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1429) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1448) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1469) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1485) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1515) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1525) |

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
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L362) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L368) |
| function | `_html_to_text` | `(raw)` | Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift). | [src](../../../core/tools/simple_tools_web.py#L684) |
| function | `_egress_blokeret` | `(url)` | Fejl-svaret hvis destinationen er intern, ellers None. | [src](../../../core/tools/simple_tools_web.py#L723) |
| function | `_fetch_cache_get` | `(url)` | — | [src](../../../core/tools/simple_tools_web.py#L764) |
| function | `_fetch_cache_put` | `(url, raw)` | — | [src](../../../core/tools/simple_tools_web.py#L775) |
| class | `_RevaliderendeRedirect` | `` | Stopper en omdirigering mod et internt maal, hop for hop. | [src](../../../core/tools/simple_tools_web.py#L793) |
| method | `_RevaliderendeRedirect.redirect_request` | `(self, req, fp, code, msg, headers, newurl)` | — | [src](../../../core/tools/simple_tools_web.py#L796) |
| function | `_hent_side` | `(url)` | Hent en side med redirect-revalidering og kort cache. | [src](../../../core/tools/simple_tools_web.py#L811) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L826) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L893) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L912) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L922) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L963) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L970) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L982) |
| function | `_exec_get_weather` | `(args)` | Current weather via OpenWeatherMap. | [src](../../../core/tools/simple_tools_web.py#L994) |
| function | `_exec_get_exchange_rate` | `(args)` | Currency exchange rates via exchangerate.host. | [src](../../../core/tools/simple_tools_web.py#L1028) |
| function | `_exec_get_news` | `(args)` | Recent news via NewsAPI. | [src](../../../core/tools/simple_tools_web.py#L1055) |
| function | `_stage_image_preview` | `(image_bytes, source_path)` | Give Desk a narrowly whitelisted copy of a server-side image. | [src](../../../core/tools/simple_tools_web.py#L1091) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L1110) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L1236) |
| function | `_exec_wolfram_query` | `(args)` | Precise answers via Wolfram Alpha Short Answers API. | [src](../../../core/tools/simple_tools_web.py#L1306) |

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

## `core/tools/tool_call_observation.py`
_Alt hvad der KUN observerer et vaerktoejskald — efter det er kaldt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_tool_call` | `(name, arguments, result)` | Observér et faerdigt vaerktoejskald. Kaster aldrig. | [src](../../../core/tools/tool_call_observation.py#L16) |

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
| function | `is_local_execution_tool` | `(name)` | True hvis værktøjet kører lokalt i code mode (resultat forlader ikke maskinen). | [src](../../../core/tools/tool_scoping.py#L249) |
| function | `current_tool_scope` | `()` | Nuværende tool-scope ("chat" eller "" for ubegrænset). | [src](../../../core/tools/tool_scoping.py#L260) |
| function | `set_tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L265) |
| function | `reset_tool_scope` | `(token)` | — | [src](../../../core/tools/tool_scoping.py#L269) |
| function | `current_local_exec` | `()` | True når det aktive run er en jarvis-code Path B lokal-exec-tur. | [src](../../../core/tools/tool_scoping.py#L282) |
| function | `set_local_exec` | `(on)` | — | [src](../../../core/tools/tool_scoping.py#L287) |
| function | `tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L292) |
| function | `_owner_has_live_bridge` | `()` | True hvis der findes en levende desk-bro for nuværende bruger (presence, cross-proces). | [src](../../../core/tools/tool_scoping.py#L300) |
| function | `_phone_tool_names` | `()` | Telefonens vaerktoejer — hentet fra ét sted, ikke gentaget her. | [src](../../../core/tools/tool_scoping.py#L314) |
| function | `_owner_has_live_phone` | `()` | True hvis en TELEFON er forbundet for nuvaerende bruger. | [src](../../../core/tools/tool_scoping.py#L332) |
| function | `_phone_adb_tool_names` | `()` | ADB-vaerktoejernes navne — ét sted, ikke gentaget her. | [src](../../../core/tools/tool_scoping.py#L366) |
| function | `_adb_er_opsat` | `()` | Er der overhovedet en telefon at pege adb paa? | [src](../../../core/tools/tool_scoping.py#L379) |
| function | `_forbundne_connector_vaerktoejer` | `()` | Vaerktoejer fra apps brugeren FAKTISK har forbundet. | [src](../../../core/tools/tool_scoping.py#L398) |
| function | `allowed_tool_names` | `(*, role, scope, all_names)` | Beregn det tilladte sæt tool-navne for (role, scope). | [src](../../../core/tools/tool_scoping.py#L432) |
| function | `preferred_tools_for_user_message` | `(user_message)` | Order hint for tool choice; does not grant or revoke permissions. | [src](../../../core/tools/tool_scoping.py#L508) |
| function | `tool_routing_hint` | `(user_message)` | Prompt hint for personal/internal vs external lookup intent. | [src](../../../core/tools/tool_scoping.py#L518) |
| function | `is_tool_allowed` | `(*, role, scope, name)` | Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.) | [src](../../../core/tools/tool_scoping.py#L535) |
| function | `_apply_computer_use_policy` | `(result)` | Computer-use-toggle (§4.7): fjern operator/computer-tools hvis brugeren har | [src](../../../core/tools/tool_scoping.py#L548) |
| function | `_fn_name` | `(td)` | — | [src](../../../core/tools/tool_scoping.py#L572) |
| function | `filter_tool_definitions` | `(defs, *, role, scope)` | Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope). | [src](../../../core/tools/tool_scoping.py#L576) |

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

## `core/tools/web_scrape_tool.py`
_web_scrape_tool — structured content extraction from URLs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_url_cache_key` | `(url)` | SHA256 of the normalised URL string. | [src](../../../core/tools/web_scrape_tool.py#L42) |
| function | `_scrape_ttl` | `(mode)` | Return (policy_name, timedelta) for a scrape mode. | [src](../../../core/tools/web_scrape_tool.py#L47) |
| function | `_cache_lookup` | `(url)` | Return cached scrape result for URL, or None on miss/error. | [src](../../../core/tools/web_scrape_tool.py#L52) |
| function | `_cache_store` | `(*, url, mode, result)` | Store scrape result in web cache. Non-fatal on error. | [src](../../../core/tools/web_scrape_tool.py#L68) |
| function | `_fetch_urllib` | `(url)` | Fetch URL via urllib. Returns (html, final_url). Raises on error. | [src](../../../core/tools/web_scrape_tool.py#L97) |
| function | `_extract_content` | `(html, *, url)` | Extract title, content, metadata from HTML. | [src](../../../core/tools/web_scrape_tool.py#L110) |
| function | `_detect_mode` | `(soup)` | Heuristically detect the best scrape mode from page structure. | [src](../../../core/tools/web_scrape_tool.py#L182) |
| function | `_apply_mode` | `(soup, *, mode, extract)` | Extract structured items for listing/product modes. Returns [] for article/social. | [src](../../../core/tools/web_scrape_tool.py#L195) |
| function | `_extract_links` | `(soup, *, base_url)` | Extract all non-empty links from page. | [src](../../../core/tools/web_scrape_tool.py#L237) |
| function | `web_scrape` | `(url, *, mode=…, extract=…, include_links=…)` | Fetch a URL and return structured, cleaned content. | [src](../../../core/tools/web_scrape_tool.py#L258) |

## `core/tools/webhook_tools.py`
_Webhook tools — send to and manage external HTTP endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/tools/webhook_tools.py#L16) |
| function | `_save` | `(data)` | — | [src](../../../core/tools/webhook_tools.py#L23) |
| function | `_sign_payload` | `(payload_bytes, secret)` | — | [src](../../../core/tools/webhook_tools.py#L28) |
| function | `_do_post` | `(url, payload, secret=…)` | — | [src](../../../core/tools/webhook_tools.py#L32) |
| function | `_exec_webhook_register` | `(args)` | — | [src](../../../core/tools/webhook_tools.py#L53) |
| function | `_exec_webhook_send` | `(args)` | — | [src](../../../core/tools/webhook_tools.py#L76) |
| function | `_exec_webhook_list` | `(args)` | — | [src](../../../core/tools/webhook_tools.py#L105) |
| function | `_exec_webhook_test` | `(args)` | — | [src](../../../core/tools/webhook_tools.py#L121) |
| function | `_exec_webhook_delete` | `(args)` | — | [src](../../../core/tools/webhook_tools.py#L142) |

## `core/tools/workspace_capabilities.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_workspace_capabilities` | `(name=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L144) |
| function | `build_ollama_tool_definitions` | `(name=…)` | Build Ollama-compatible tool definitions from workspace capabilities. | [src](../../../core/tools/workspace_capabilities.py#L347) |
| function | `resolve_tool_call_to_capability` | `(tool_name, arguments)` | Map an Ollama tool_call back to capability invocation parameters. | [src](../../../core/tools/workspace_capabilities.py#L379) |
| function | `invoke_workspace_capability` | `(capability_id, *, name=…, run_id=…, approved=…, write_content=…, target_path=…, command_text=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L403) |
| function | `get_capability_invocation_truth` | `()` | — | [src](../../../core/tools/workspace_capabilities.py#L555) |
| function | `_invoke_runnable_capability` | `(*, workspace_dir, section, summary, approved=…, write_content=…, target_path=…, command_text=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L564) |
| function | `classify_workspace_execution_mode` | `(execution_mode)` | — | [src](../../../core/tools/workspace_capabilities.py#L1870) |
| function | `_read_bounded_text` | `(path)` | — | [src](../../../core/tools/workspace_capabilities.py#L1970) |
| function | `_bounded_exec_output` | `(*, stdout, stderr)` | — | [src](../../../core/tools/workspace_capabilities.py#L1977) |
| function | `_run_bounded_command` | `(*, argv, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities.py#L1993) |
| function | `_run_bounded_shell_command` | `(*, command_text, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities.py#L2014) |
| function | `_search_file_matches` | `(path, query)` | — | [src](../../../core/tools/workspace_capabilities.py#L2035) |
| function | `_bounded_excerpt` | `(text, limit=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2055) |
| function | `_set_last_capability_invocation` | `(invocation, *, invoked_at, capability_id=…, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2062) |
| function | `_publish_capability_invocation_completed` | `(invocation, *, invoked_at, capability_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2100) |
| function | `_persist_capability_invocation` | `(invocation, *, invoked_at, finished_at, capability_id=…, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2129) |
| function | `_now` | `()` | — | [src](../../../core/tools/workspace_capabilities.py#L2183) |

## `core/tools/workspace_capabilities_approval.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_approval_request_user_context` | `()` | — | [src](../../../core/tools/workspace_capabilities_approval.py#L10) |
| function | `_persist_capability_approval_request` | `(invocation, *, requested_at, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities_approval.py#L20) |
| function | `_flade_for_run` | `(run_id)` | Fladen kørslen blev skrevet fra ("desk" | "mobil"), eller "". | [src](../../../core/tools/workspace_capabilities_approval.py#L110) |
| function | `_workspace_write_proposal_content` | `(*, summary, write_content)` | — | [src](../../../core/tools/workspace_capabilities_approval.py#L123) |

## `core/tools/workspace_capabilities_const.py`
_Delte konstanter for workspace-capabilities._

_(no top-level classes or functions)_

## `core/tools/workspace_capabilities_documents.py`
_Workspace-dokument-parsing (TOOLS.md / SKILLS.md → capability-sektioner)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_approval_policy_for_execution_mode` | `(execution_mode)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L49) |
| function | `_document_summary` | `(path, *, kind)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L87) |
| function | `_document_sections` | `(path, *, kind)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L124) |
| function | `_document_section_by_id` | `(path, *, kind, capability_id)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L163) |
| function | `_section_summary` | `(section)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L170) |
| function | `_runtime_capability_record` | `(item)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L289) |
| function | `_normalize_body` | `(lines)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L312) |
| function | `_slugify` | `(value)` | — | [src](../../../core/tools/workspace_capabilities_documents.py#L317) |

## `core/tools/workspace_capabilities_exec.py`
_Exec-kommando-klassifikation for workspace-capabilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_exec_command` | `(command_text)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L33) |
| function | `_classify_shell_composed_exec_command` | `(command_text)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L123) |
| function | `_classify_exec_command_no_shell` | `(command_text)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L187) |
| function | `_split_shell_exec_segments` | `(command_text)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L265) |
| function | `_normalize_exec_argv` | `(argv)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L270) |
| function | `_classify_git_exec_command` | `(argv, *, path_normalization_applied=…, normalization_source=…)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L302) |
| function | `_resolve_git_exec_context` | `(argv)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L397) |
| function | `_is_allowed_bounded_git_log_args` | `(log_args)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L424) |
| function | `_classify_cd_exec_command` | `(argv, *, path_normalization_applied=…, normalization_source=…)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L432) |
| function | `_classify_git_mutation_subcommand` | `(subcommand)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L463) |
| function | `_mutating_exec_proposal_metadata` | `(argv)` | — | [src](../../../core/tools/workspace_capabilities_exec.py#L480) |

## `core/tools/workspace_capabilities_execute.py`
_Read-only capability-udførere (runtime-event-read, grep, multi-read, outline)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_execute_runtime_event_read` | `(summary)` | Execute the runtime-event-read tool: surface recent eventbus events. | [src](../../../core/tools/workspace_capabilities_execute.py#L33) |
| function | `_execute_project_grep` | `(summary, command_text)` | Grep across PROJECT_ROOT for a pattern. Read-only, no approval. | [src](../../../core/tools/workspace_capabilities_execute.py#L90) |
| function | `_execute_multi_file_read` | `(summary, command_text, workspace_dir)` | Read multiple project files in one call. Read-only, no approval. | [src](../../../core/tools/workspace_capabilities_execute.py#L160) |
| function | `_execute_project_outline` | `(summary, command_text)` | List project files with line counts. Read-only, no approval. | [src](../../../core/tools/workspace_capabilities_execute.py#L217) |

## `core/tools/workspace_capabilities_memory.py`
_Workspace-memory-fletning + støjfilter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_durable_memory_line` | `(line)` | True if a line looks like a durable fact, not session noise. | [src](../../../core/tools/workspace_capabilities_memory.py#L70) |
| function | `_merge_workspace_memory_content` | `(*, existing_content, incoming_content)` | — | [src](../../../core/tools/workspace_capabilities_memory.py#L104) |

## `core/tools/workspace_capabilities_results.py`
_Rene result-formende helpers for workspace-capabilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_finalize_capability_result` | `(result)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L18) |
| function | `_capability_status_family` | `(status)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L36) |
| function | `_default_capability_detail` | `(*, status, execution_mode)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L52) |
| function | `_requires_capability_approval` | `(summary)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L68) |
| function | `_approval_result` | `(summary, *, approved, granted)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L72) |
| function | `_preview_text` | `(text, limit=…)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L85) |
| function | `_result_preview` | `(result)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L92) |
| function | `_content_fingerprint` | `(text)` | — | [src](../../../core/tools/workspace_capabilities_results.py#L106) |

## `core/tools/workspace_capabilities_verdict.py`
_Approval-verdicts + proposal/execution-content for mutating/sudo exec._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_approved_mutating_exec_verdict` | `(classification)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L31) |
| function | `_approved_sudo_exec_verdict` | `(classification, *, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L76) |
| function | `_mutating_exec_proposal_content` | `(*, command_text, command_source, classification)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L164) |
| function | `_mutating_exec_execution_content` | `(*, command_text, command_source, classification, exit_code, output_text)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L215) |
| function | `_sudo_exec_execution_content` | `(*, command_text, command_source, classification, exit_code, output_text)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L249) |
| function | `_resolve_target_path_for_sudo_exec` | `(workspace_dir, target)` | — | [src](../../../core/tools/workspace_capabilities_verdict.py#L284) |

## `core/tools/workspace_capabilities_wsio.py`
_Encryption-aware workspace-fil I/O-helpers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ws_read_text` | `(path)` | Læs workspace-fil encryption-aware (member .enc transparent). None hvis | [src](../../../core/tools/workspace_capabilities_wsio.py#L14) |
| function | `_ws_write_text` | `(path, content)` | Skriv workspace-fil encryption-aware (member → .enc når ENCRYPT_ON_WRITE on; | [src](../../../core/tools/workspace_capabilities_wsio.py#L22) |
| function | `_ws_path_exists` | `(path)` | Eksistens encryption-aware: plaintext eller member .enc. | [src](../../../core/tools/workspace_capabilities_wsio.py#L29) |

## `core/tools/workspace_capability_decl.py`
_Capability body declaration-parsere + workspace-sti-resolution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_declared_read_file_path` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L18) |
| function | `_declared_search_file_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L22) |
| function | `_declared_external_file_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L36) |
| function | `_declared_exec_spec` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L53) |
| function | `_declared_write_target_path` | `(body)` | — | [src](../../../core/tools/workspace_capability_decl.py#L70) |
| function | `_declared_body_value` | `(body, key, *, validate=…)` | — | [src](../../../core/tools/workspace_capability_decl.py#L74) |
| function | `_is_valid_workspace_relative_path` | `(value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L91) |
| function | `_resolve_workspace_relative_path` | `(workspace_dir, value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L102) |
| function | `_resolve_external_path` | `(workspace_dir, value)` | — | [src](../../../core/tools/workspace_capability_decl.py#L114) |
| function | `_is_within_workspace_root` | `(workspace_dir, candidate)` | — | [src](../../../core/tools/workspace_capability_decl.py#L126) |
| function | `_expand_declared_path` | `(value, *, workspace_dir)` | — | [src](../../../core/tools/workspace_capability_decl.py#L135) |

