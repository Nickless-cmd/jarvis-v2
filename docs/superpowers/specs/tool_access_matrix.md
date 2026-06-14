# Tool Access Matrix — kanonisk kilde for permission_engine

> Genereret 2026-06-14 mod live registry (`get_tool_definitions`, 397 tools).
> Kilde til sandhed for `core/services/permission_engine.py`. Re-validér mod
> registry når nye tools tilføjes (test asserter at alle member-navne findes).

## Princip: fail-closed default-deny

**Owner (Bjørn) = ALLE tools, alle modes.** **Guest = ∅** (læser kun samtalen).
**Member = kun de eksplicit listede tools pr. mode.** Alt andet er automatisk
owner-only. Derfor er Jarvis' egen kode, native indre tools, finans og runtime
**utilgængelige for member uden at vi opremser dem** — de er bare ikke på listen.

🔒 = path-jailed til brugerens eget workspace (håndhæves i Fase 4 dispatch, ikke i permission_engine).

## Adgangsmatrix

| Mode | Owner | Member | Guest |
|------|-------|--------|-------|
| Chat | ALLE | web/info + utils + memory🔒 (15) | ∅ |
| Code | ALLE | operator_* + web + fil🔒 (60) | — (utilgængelig) |
| Cowork | ALLE | plans/todos/proposals/kanal (11) | — (utilgængelig) |

## Member-allowlists (eksplicit)

### MEMBER · CHAT
**Web/info (read-only ekstern):** `web_search`, `web_scrape`, `web_fetch`, `get_news`, `get_weather`, `get_exchange_rate`, `wolfram_query`, `analyze_image`

**Utils:** `calculate`, `unit_convert`, `percentage`

**Memory 🔒 (eget workspace):** `remember_this`, `search_memory`, `recall_memories`, `memory_list_headings`

> Bemærk: `cross_agent_recall` er IKKE her — cross-user recall er owner-only (privatlivs-grænse).

### MEMBER · CODE  (= det Claude har)
**Operator (kører på brugerens EGEN maskine via bridge):**
`operator_bash`, `operator_browser_click`, `operator_browser_close`, `operator_browser_evaluate`, `operator_browser_get_links`, `operator_browser_get_text`, `operator_browser_open`, `operator_browser_screenshot`, `operator_browser_status`, `operator_browser_type`, `operator_clipboard_read`, `operator_clipboard_write`, `operator_edit_file`, `operator_find_image`, `operator_focus_window`, `operator_glob`, `operator_grep`, `operator_keyboard_press`, `operator_keyboard_type`, `operator_kill_process`, `operator_launch_app`, `operator_list_dir`, `operator_list_processes`, `operator_list_windows`, `operator_mouse_click`, `operator_mouse_drag`, `operator_mouse_move`, `operator_mouse_position`, `operator_mouse_scroll`, `operator_notify`, `operator_ocr_region`, `operator_open_url`, `operator_process_kill`, `operator_process_list`, `operator_process_output`, `operator_process_spawn`, `operator_process_status`, `operator_read_file`, `operator_record_audio`, `operator_reminder`, `operator_scheduled_cancel`, `operator_scheduled_list`, `operator_screen_size`, `operator_screenshot`, `operator_screenshot_window`, `operator_speak`, `operator_unwatch_folder`, `operator_wakeup`, `operator_watch_events`, `operator_watch_folder`, `operator_webfetch`, `operator_write_file`

**Web-læsning:** `web_search`, `web_scrape`, `web_fetch`, `analyze_image`

**Server-side fil 🔒 (KUN eget workspace, path-jailed):** `read_file`, `write_file`, `edit_file`, `find_files`

> Bemærk: server-side `bash`, `git_*`, `edit_file` mod Jarvis' repo er IKKE her.
> Member får shell KUN via `operator_bash` (deres egen maskine). Jarvis' server røres aldrig.

### MEMBER · COWORK
`propose_plan`, `revise_plan`, `list_plans`, `dismiss_plan`, `todo_add`, `todo_list`, `todo_set`, `todo_update_status`, `todo_remove`, `list_proposals`, `discord_channel`

> ⚠️ BESLUTNING: `approve_plan`/`approve_proposal` er bevidst UDELADT — at godkende
> Jarvis' self-improvement-forslag er en owner-autoritet. Member kan foreslå + se, ikke godkende.

## Owner-only (315 tools — default-deny, til review)

### Avanceret memory/cross-agent (14)
`memory_check_duplicate`, `memory_cold_tier`, `memory_consolidate`, `memory_graph_query`, `memory_hot_tier`, `memory_upsert_section`, `memory_usage`, `memory_warm_tier`, `read_visual_memory`, `recall_before_act`, `recall_reasoning`, `release_memory`, `resurface_old_memory`, `unified_recall`

### Bjørns hjem/devices (5)
`home_assistant`, `mic_listen`, `screen_control`, `voice_journal`, `wake_word`

### Finans/brand-konti (9)
`stripe_balance`, `stripe_create_issuing_card`, `stripe_payouts`, `stripe_transactions`, `tiktok_analytics`, `tiktok_generate_video`, `tiktok_login`, `tiktok_show`, `tiktok_upload`

### Jarvis egen kode/skills/runtime (38)
`analyze_skill_usage`, `append_skill_observation`, `conclude_prompt_experiment`, `dispatch_to_claude_code`, `find_symbol`, `find_usages`, `get_agent_skills`, `list_prompt_experiments`, `list_skill_mutations`, `list_skill_roles`, `propose_new_skill`, `propose_skill_chain`, `propose_source_edit`, `recent_skill_changes`, `restart_overdue_daemons`, `restart_self`, `revise_skill_chain`, `rollback_skill_mutation`, `run_pytest`, `semantic_search_code`, `skill_chain`, `skill_create`, `skill_delete`, `skill_gate`, `skill_get`, `skill_history`, `skill_import`, `skill_import_from_url`, `skill_invoke`, `skill_list`, `skill_reload`, `skill_search`, `skill_suggest`, `start_prompt_experiment`, `worktree_create`, `worktree_discard`, `worktree_list`, `worktree_merge`

### Kanaler/udgående kommunikation (23)
`discord_status`, `dismiss_nudge`, `list_pending_nudges`, `notify_channel_add`, `notify_channel_delete`, `notify_channel_list`, `notify_out`, `notify_user`, `nudge_dismiss`, `nudge_inspect`, `nudge_send`, `read_mail`, `send_discord_dm`, `send_mail`, `send_ntfy`, `send_telegram_message`, `send_webchat_message`, `surface_nudge`, `webhook_delete`, `webhook_list`, `webhook_register`, `webhook_send`, `webhook_test`

### Media/browser/connector (chat-plugin senere) (21)
`browser_click`, `browser_find_tabs`, `browser_navigate`, `browser_read`, `browser_screenshot`, `browser_submit`, `browser_switch_tab`, `browser_type`, `comfyui_history`, `comfyui_objects`, `comfyui_status`, `comfyui_workflow`, `create_event`, `delete_event`, `hf_embed`, `hf_text_to_video`, `hf_transcribe_audio`, `hf_vision_analyze`, `hf_zero_shot_classify`, `pollinations_image`, `pollinations_video`

### Native/indre (følelser, drøm, brain, identitet) (33)
`adjust_mood`, `adopt_brain_proposal`, `archive_brain_entry`, `capture_emotion_tag`, `convene_council`, `curiosity_list_skills`, `curiosity_list_tools`, `curiosity_read_chronicles`, `curiosity_read_dreams`, `curiosity_read_model_config`, `curiosity_read_mood`, `curiosity_search_events`, `curiosity_search_memory`, `curiosity_search_sessions`, `discard_brain_proposal`, `identity_mutation_status`, `list_identity_mutations`, `list_identity_pins`, `pin_identity`, `propose_identity_drift_update`, `quick_council_check`, `read_brain_entry`, `read_chronicles`, `read_dreams`, `read_identity_sketch`, `read_mood`, `recall_council_conclusions`, `recall_sensory_memories`, `record_sensory_memory`, `rollback_identity_mutation`, `search_jarvis_brain`, `unpin_identity`, `update_identity_sketch`

### Planlægning/agenter/initiativ (owner-styret) (54)
`activate_side_task`, `agent_relay_message`, `agent_relay_to_role`, `approve_plan`, `approve_proposal`, `build_subagent_context`, `cancel_agent`, `cancel_self_wakeup`, `composite_approve`, `composite_get`, `composite_invoke`, `composite_list`, `composite_propose`, `composite_revoke`, `compress_agent_run`, `cross_agent_recall`, `decision_adherence_summary`, `decision_create`, `decision_get`, `decision_list`, `decision_review`, `decision_revoke`, `detect_stale_goals`, `dismiss_side_task`, `dispatch_due_wakeups`, `flag_side_task`, `get_agent_observation`, `goal_create`, `goal_decompose`, `goal_get`, `goal_list`, `goal_update`, `goal_update_status`, `list_agent_observations`, `list_agent_roles`, `list_agents`, `list_initiatives`, `list_scheduled_tasks`, `list_self_wakeups`, `list_side_tasks`, `mark_wakeup_consumed`, `my_project_accept_proposal`, `my_project_declare`, `my_project_journal_write`, `my_project_status`, `push_initiative`, `read_project_notes`, `relay_to_agent`, `schedule_recurring`, `schedule_self_wakeup`, `schedule_task`, `send_message_to_agent`, `spawn_agent_task`, `update_project_notes`

### Runtime/infra/observability (32)
`auto_compact_check`, `auto_compact_run`, `compact_context`, `context_pressure`, `context_size_check`, `control_daemon`, `daemon_alert_status`, `daemon_health_alert`, `daemon_status`, `db_query`, `disk_usage`, `eventbus_recent`, `gpu_status`, `health_check`, `health_history`, `health_register`, `health_status`, `heartbeat_sense`, `heartbeat_status`, `internal_api`, `list_context_versions`, `manage_context_window`, `phased_heartbeat_tick`, `provider_health_check`, `provider_health_status`, `read_model_config`, `recall_context_version`, `service_status`, `smart_compact`, `tail_log`, `trigger_heartbeat_tick`, `update_setting`

### Server-side kode/git/shell (Jarvis repo) (15)
`bash`, `bash_session_close`, `bash_session_list`, `bash_session_open`, `bash_session_run`, `commit_staged_edits`, `discard_staged_edits`, `git_blame`, `git_branch`, `git_diff`, `git_log`, `git_status`, `publish_file`, `stage_edit_file`, `stage_write_file`

### Øvrige interne (71)
`add_process_watch`, `cancel_recurring`, `cancel_task`, `check_good_enough`, `check_surprises`, `classify_clarification`, `counterfactual_summary`, `deep_analyze`, `delegation_advisor`, `dispatch_cancel`, `dispatch_status`, `edit_task`, `generate_improvement_proposals`, `list_arcs`, `list_attachments`, `list_counterfactuals`, `list_crisis_markers`, `list_events`, `list_learning_memos`, `list_process_watches`, `list_recurring`, `list_signal_surfaces`, `list_staged_edits`, `load_more_tools`, `log_variant_outcome`, `look_around`, `mine_tool_patterns`, `monitor_close`, `monitor_list`, `monitor_open`, `pause_and_ask`, `personality_drift_check`, `personality_drift_snapshot`, `predict_outcome`, `process_list`, `process_remove`, `process_spawn`, `process_stop`, `process_tail`, `query_why`, `queue_followup`, `read_archive`, `read_attachment`, `read_counterfactual`, `read_learning_memo`, `read_self_docs`, `read_self_state`, `read_signal_surface`, `read_tool_result`, `reasoning_classify`, `recommend_escalation`, `record_hypothesis_sample`, `register_custom_role`, `register_hypothesis`, `remove_process_watch`, `request_codex_skeleton`, `resolve_prediction`, `scan_crisis_markers`, `search`, `search_chat_history`, `search_sessions`, `set_process_watch_enabled`, `smart_outline`, `synthesize_arc`, `test_retry_policy`, `tick_quality_summary`, `variant_performance`, `verification_status`, `verify_endpoint_responds`, `verify_file_contains`, `verify_service_active`
