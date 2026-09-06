# Tool-kortlægning — 429 registrerede værktøjer

Kortlagt 6. september 2026 fra `TOOL_DEFINITIONS`-kæden krydset med `tool.completed`-events (5.717 events).

**Ofte brugt (≥30 gange): 19** · **Mellem (5–29): 27** · **Sjældent (1–4): 55** · **Aldrig brugt: 328**

## Ofte brugt — kernen (19)

- bash (2686)
- operator_bash (801)
- bash_session_run (363)
- read_file (237)
- db_query (227)
- search (141)
- edit_file (112)
- operator_bash_session_run (108)
- web_search (83)
- write_file (67)
- find_files (59)
- search_memory (58)
- verify_file_contains (49)
- remember_this (48)
- load_more_tools (47)
- web_fetch (43)
- central_query (38)
- record_sensory_memory (37)
- recall_memories (33)

## Mellem — bruges når det giver mening (27)

- bash_session_open (27)
- recall_sensory_memories (22)
- search_jarvis_brain (22)
- operator_bash_session_open (20)
- read_dreams (19)
- read_visual_memory (19)
- analyze_image (18)
- get_weather (16)
- memory_upsert_section (16)
- daemon_status (15)
- send_discord_dm (15)
- explore (11)
- home_assistant (11)
- mic_listen (11)
- look_around (10)
- read_model_config (10)
- operator_glob (9)
- read_self_state (8)
- get_news (7)
- read_tool_result (7)
- heartbeat_status (6)
- my_project_status (6)
- read_chronicles (6)
- nudge_inspect (5)
- operator_bash_session_list (5)
- operator_list_dir (5)
- operator_read_file (5)

## Sjældent — findes, men sjældent nødvendigt (55)

- list_self_wakeups (4)
- notify_user (4)
- operator_channel (4)
- operator_run_in_background (4)
- operator_screenshot_window (4)
- restart_self (4)
- set_flag (4)
- eventbus_recent (3)
- goal_list (3)
- nudge_dismiss (3)
- operator_write_file (3)
- read_memory_topic (3)
- bash_session_list (2)
- find_usages (2)
- geolocation_lookup (2)
- git_log (2)
- git_status (2)
- gmail_send (2)
- internal_api (2)
- list_initiatives (2)
- mark_wakeup_consumed (2)
- operator_bash_output (2)
- operator_grep (2)
- operator_screenshot (2)
- pause_and_ask (2)
- read_mood (2)
- todo_add (2)
- todo_list (2)
- browser_navigate (1)
- calendar_list_events (1)
- checkpoint (1)
- decision_create (1)
- dismiss_plan (1)
- drive_search (1)
- find_symbol (1)
- list_attachments (1)
- list_plans (1)
- mcp (1)
- memory_check_duplicate (1)
- memory_graph_query (1)
- my_project_journal_write (1)
- operator_browser_open (1)
- operator_browser_status (1)
- operator_record_audio (1)
- operator_reminder (1)
- schedule_self_wakeup (1)
- search_chat_history (1)
- semantic_search_code (1)
- send_ntfy (1)
- send_push_notification (1)
- skill_invoke (1)
- skill_suggest (1)
- spawn_agent_task (1)
- todo_remove (1)
- write_memory_topic (1)

## Aldrig brugt (328)

_Se domæne-grupperingen nedenfor — hele grupper er ubrugte, ikke spredte enkeltværktøjer._

## Aldrig brugt — grupperet efter domæne

### simple_tools_definitions.py (kerne) — 87 tools

- adjust_mood
- approve_proposal
- cancel_agent
- cancel_task
- compact_context
- control_daemon
- convene_council
- deep_analyze
- discord_channel
- discord_status
- edit_task
- geocode
- get_exchange_rate
- interlanguage_protocol
- list_agents
- list_proposals
- list_scheduled_tasks
- list_signal_surfaces
- my_project_accept_proposal
- my_project_declare
- nearby_search
- operator_browser_click
- operator_browser_close
- operator_browser_evaluate
- operator_browser_get_links
- operator_browser_get_text
- operator_browser_screenshot
- operator_browser_type
- operator_clipboard_read
- operator_clipboard_write
- operator_edit_file
- operator_find_image
- operator_focus_window
- operator_keyboard_press
- operator_keyboard_type
- operator_kill_process
- operator_kill_shell
- operator_launch_app
- operator_list_processes
- operator_list_windows
- operator_mouse_click
- operator_mouse_drag
- operator_mouse_move
- operator_mouse_position
- operator_mouse_scroll
- operator_multi_edit
- operator_notify
- operator_ocr_region
- operator_open_url
- operator_process_kill
- operator_process_list
- operator_process_output
- operator_process_spawn
- operator_process_status
- operator_scheduled_cancel
- operator_scheduled_list
- operator_screen_size
- operator_speak
- operator_unwatch_folder
- operator_wakeup
- operator_watch_events
- operator_watch_folder
- operator_webfetch
- propose_source_edit
- publish_file
- push_initiative
- query_why
- queue_followup
- quick_council_check
- read_archive
- read_attachment
- read_self_docs
- read_signal_surface
- recall_council_conclusions
- relay_to_agent
- resurface_old_memory
- reverse_geocode
- route_directions
- schedule_task
- send_message_to_agent
- send_telegram_message
- send_webchat_message
- task
- trigger_heartbeat_tick
- update_setting
- web_scrape
- wolfram_query

### skill_engine_tools.py — 9 tools

- propose_new_skill
- skill_create
- skill_delete
- skill_get
- skill_import
- skill_import_from_url
- skill_list
- skill_reload
- skill_search

### browser_tools.py — 7 tools

- browser_click
- browser_find_tabs
- browser_read
- browser_screenshot
- browser_submit
- browser_switch_tab
- browser_type

### google_connector.py — 6 tools

- calendar_create_event
- docs_append
- docs_read
- sheets_read
- sheets_write
- slides_read

### composites_tools.py — 6 tools

- composite_approve
- composite_get
- composite_invoke
- composite_list
- composite_propose
- composite_revoke

### process_tools.py — 6 tools

- disk_usage
- gpu_status
- memory_usage
- run_pytest
- service_status
- tail_log

### agent_skill_library.py — 5 tools

- append_skill_observation
- get_agent_skills
- list_skill_mutations
- list_skill_roles
- rollback_skill_mutation

### proactive_context_governor.py — 5 tools

- auto_compact_check
- auto_compact_run
- build_subagent_context
- list_context_versions
- recall_context_version

### staged_edits_tools.py — 5 tools

- commit_staged_edits
- discard_staged_edits
- list_staged_edits
- stage_edit_file
- stage_write_file

### hf_inference_tools.py — 5 tools

- hf_embed
- hf_text_to_video
- hf_transcribe_audio
- hf_vision_analyze
- hf_zero_shot_classify

### process_supervisor_tools.py — 5 tools

- process_list
- process_remove
- process_spawn
- process_stop
- process_tail

### webhook_tools.py — 5 tools

- webhook_delete
- webhook_list
- webhook_register
- webhook_send
- webhook_test

### side_tasks.py — 4 tools

- activate_side_task
- dismiss_side_task
- flag_side_task
- list_side_tasks

### process_watcher_tools.py — 4 tools

- add_process_watch
- list_process_watches
- remove_process_watch
- set_process_watch_enabled

### jarvis_brain_tools.py — 4 tools

- adopt_brain_proposal
- archive_brain_entry
- discard_brain_proposal
- read_brain_entry

### recurring_scheduler_tools.py — 4 tools

- cancel_recurring
- list_recurring
- schedule_recurring
- set_recurring_channel

### comfyui_tools.py — 4 tools

- comfyui_history
- comfyui_objects
- comfyui_status
- comfyui_workflow

### decisions_tools.py — 4 tools

- decision_get
- decision_list
- decision_review
- decision_revoke

### health_monitor_tools.py — 4 tools

- health_check
- health_history
- health_register
- health_status

### memory_hierarchy.py — 4 tools

- memory_cold_tier
- memory_hot_tier
- memory_warm_tier
- recall_before_act

### notes_connector.py — 4 tools

- note_add
- note_delete
- note_list
- note_search

### notify_out_tools.py — 4 tools

- notify_channel_add
- notify_channel_delete
- notify_channel_list
- notify_out

### stripe_tools.py — 4 tools

- stripe_balance
- stripe_create_issuing_card
- stripe_payouts
- stripe_transactions

### worktree_tools.py — 4 tools

- worktree_create
- worktree_discard
- worktree_list
- worktree_merge

### math_tools.py — 3 tools

- calculate
- percentage
- unit_convert

### state_flag_tools.py — 3 tools

- clear_flag
- get_flag
- list_flags

### agent_observation_compressor.py — 3 tools

- compress_agent_run
- get_agent_observation
- list_agent_observations

### experiment_runner.py — 3 tools

- conclude_prompt_experiment
- list_prompt_experiments
- start_prompt_experiment

### counterfactual_tools.py — 3 tools

- counterfactual_summary
- list_counterfactuals
- read_counterfactual

### calendar_tools.py — 3 tools

- create_event
- delete_event
- list_events

### daemon_alert_tools.py — 3 tools

- daemon_alert_status
- daemon_health_alert
- restart_overdue_daemons

### agent_self_evaluation.py — 3 tools

- decision_adherence_summary
- detect_stale_goals
- tick_quality_summary

### nudge_tools.py — 3 tools

- dismiss_nudge
- list_pending_nudges
- surface_nudge

### github_tools.py — 3 tools

- git_blame
- git_branch
- git_diff

### goals_tools.py — 3 tools

- goal_create
- goal_get
- goal_update

### identity_mutation_log.py — 3 tools

- identity_mutation_status
- list_identity_mutations
- rollback_identity_mutation

### identity_pin_tools.py — 3 tools

- list_identity_pins
- pin_identity
- unpin_identity

### monitor_tools.py — 3 tools

- monitor_close
- monitor_list
- monitor_open

### operator_tools.py — 3 tools

- operator_session_close
- operator_session_open
- operator_session_run

### agent_relay.py — 2 tools

- agent_relay_message
- agent_relay_to_role

### plan_proposals.py — 2 tools

- approve_plan
- propose_plan

### context_window_manager.py — 2 tools

- context_pressure
- manage_context_window

### smart_compact_tools.py — 2 tools

- context_size_check
- smart_compact

### notification_tools.py — 2 tools

- get_notification_preferences
- set_notification_preferences

### github_connector.py — 2 tools

- github_list_issues
- github_list_prs

### gmail_connector.py — 2 tools

- gmail_list
- gmail_search

### autonomous_goals.py — 2 tools

- goal_decompose
- goal_update_status

### heartbeat_phases.py — 2 tools

- heartbeat_sense
- phased_heartbeat_tick

### hf_connector.py — 2 tools

- hf_model_info
- hf_search_models

### role_registry.py — 2 tools

- list_agent_roles
- register_custom_role

### long_arc_synthesizer.py — 2 tools

- list_arcs
- synthesize_arc

### crisis_marker_detector.py — 2 tools

- list_crisis_markers
- scan_crisis_markers

### meta_learning_tools.py — 2 tools

- list_learning_memos
- read_learning_memo

### prompt_variant_tracker.py — 2 tools

- log_variant_outcome
- variant_performance

### memory_tools.py — 2 tools

- memory_consolidate
- memory_list_headings

### app_control_tool.py — 2 tools

- open_ui_panel
- request_app_action

### personality_drift.py — 2 tools

- personality_drift_check
- personality_drift_snapshot

### pollinations_tools.py — 2 tools

- pollinations_image
- pollinations_video

### world_model_tools.py — 2 tools

- predict_outcome
- resolve_prediction

### provider_health_check.py — 2 tools

- provider_health_check
- provider_health_status

### identity_sketch_tools.py — 2 tools

- read_identity_sketch
- update_identity_sketch

### mail_tools.py — 2 tools

- read_mail
- send_mail

### project_notes_tools.py — 2 tools

- read_project_notes
- update_project_notes

### agent_todo_tools.py — 2 tools

- todo_set
- todo_update_status

### verify_tools.py — 2 tools

- verify_endpoint_responds
- verify_service_active

### bash_session.py — 1 tools

- bash_session_close

### self_wakeup.py — 1 tools

- cancel_self_wakeup

### emotion_tagging.py — 1 tools

- capture_emotion_tag

### good_enough_gate.py — 1 tools

- check_good_enough

### surprise_detector.py — 1 tools

- check_surprises

### clarification_classifier.py — 1 tools

- classify_clarification

### cross_agent_memory.py — 1 tools

- cross_agent_recall

### delegation_advisor.py — 1 tools

- delegation_advisor

### wakeup_dispatcher.py — 1 tools

- dispatch_due_wakeups

### auto_improvement_proposer.py — 1 tools

- generate_improvement_proposals

### tool_pattern_miner.py — 1 tools

- mine_tool_patterns

### nudge_broend_tools.py — 1 tools

- nudge_send

### operator_bash_session.py — 1 tools

- operator_bash_session_close

### pdf_connector.py — 1 tools

- pdf_read

### identity_drift_proposer.py — 1 tools

- propose_identity_drift_update

### skill_chain_propose_tool.py — 1 tools

- propose_skill_chain

### reasoning_classifier.py — 1 tools

- reasoning_classify

### reasoning_store_tools.py — 1 tools

- recall_reasoning

### reasoning_escalation.py — 1 tools

- recommend_escalation

### forgetting_tools.py — 1 tools

- release_memory

### coding_lane_tools.py — 1 tools

- request_codex_skeleton

### plan_revise_tool.py — 1 tools

- revise_plan

### skill_chain_revise_tool.py — 1 tools

- revise_skill_chain

### screen_tool.py — 1 tools

- screen_control

### skill_chain_tool.py — 1 tools

- skill_chain

### skill_gate_tool.py — 1 tools

- skill_gate

### smart_outline.py — 1 tools

- smart_outline

### provider_retry_policy.py — 1 tools

- test_retry_policy

### memory_recall_engine.py — 1 tools

- unified_recall

### verification_gate.py — 1 tools

- verification_status

### voice_journal_tool.py — 1 tools

- voice_journal

### wake_word_tool.py — 1 tools

- wake_word
