# `apps.api.jarvis_api.routes.02` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/jarvisx_dispatches.py`
_JarvisX Claude-Code dispatch dashboard route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_dispatches` | `(limit=…)` | Recent dispatches, running first then by started_at desc. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L29) |
| function | `dispatch_budget` | `()` | Current hour's dispatch budget — count + tokens vs caps. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L93) |
| function | `get_dispatch` | `(task_id)` | Full audit row + parsed spec for a single dispatch. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L119) |
| function | `get_dispatch_diff` | `(task_id)` | Live diff of a dispatch's worktree against main. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L136) |

## `apps/api/jarvis_api/routes/jarvisx_processes.py`
_JarvisX process-supervisor + trading + operator-wakeup route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_managed_processes` | `(include_stopped=…)` | List processes Jarvis has spawned via the process_supervisor. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L30) |
| function | `tail_managed_process_log` | `(name, lines=…)` | Return the tail of a managed process's combined stdout/stderr log. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L37) |
| function | `stop_managed_process` | `(name, grace=…)` | SIGTERM (then SIGKILL after grace) a managed process. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L53) |
| function | `remove_managed_process` | `(name)` | Remove a stopped process from the registry. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L64) |
| class | `_SpawnPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L82) |
| function | `spawn_managed_process` | `(payload)` | Spawn a managed background process. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L90) |
| function | `trading_state` | `()` | Read the current trading-bot state. Read-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L149) |
| function | `_trading_inactive_default` | `(reason)` | Synthetic 'inactive' state so UI always has something to render. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L182) |
| function | `operator_wakeup_fired` | `(payload)` | Hit af jarvis-desk når en operator_wakeup-timer fyrer. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L215) |

## `apps/api/jarvis_api/routes/jarvisx_project.py`
_JarvisX project-anchor + file-watch route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_project_root` | `(root)` | Resolve a project root with strict guards. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L36) |
| function | `_safe_project_subpath` | `(root, rel)` | Resolve a relative path under the project root, refusing escapes. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L59) |
| function | `project_tree` | `(root=…, max_depth=…)` | Return a nested tree of the project root, depth-limited. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L72) |
| function | `project_list` | `(root=…, limit=…)` | Flat list of files under root (for @file autocomplete). | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L134) |
| function | `project_read` | `(root=…, path=…)` | Read a file from inside the project root with a 1 MB cap. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L176) |
| function | `project_notes_get` | `(root=…)` | Read .jarvisx/notes.md inside the anchored project, if it exists. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L217) |
| class | `ProjectNotesUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L241) |
| function | `project_notes_set` | `(payload)` | Write .jarvisx/notes.md inside the anchored project. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L247) |
| function | `_watch_lock` | `()` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L276) |
| class | `WatchAddRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L283) |
| class | `WatchPollRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L288) |
| function | `project_watch_add` | `(payload)` | Start watching a list of files/dirs for the session. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L293) |
| function | `project_watch_poll` | `(payload)` | Return the list of watched paths whose mtime changed since last poll. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L323) |
| function | `project_watch_clear` | `(payload)` | Stop all watches for a session. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L356) |

## `apps/api/jarvis_api/routes/jarvisx_sessions.py`
_JarvisX chat-session support route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `preferences_get` | `()` | User-level UI preferences (output style, tool permissions, etc). | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L23) |
| class | `PreferencesUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L44) |
| function | `preferences_set` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L50) |
| function | `tools_inventory` | `()` | Return the full tool catalog with name + description + required params. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L76) |
| function | `todos_list` | `(session_id=…)` | List todos for a session — used by JarvisX's TodoPanel UI. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L103) |
| class | `TodoStatusUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L110) |
| function | `todos_status` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L117) |
| function | `chat_search` | `(q=…, limit=…, scope=…)` | Full-text search across chat_messages. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L123) |
| function | `staged_edits` | `(session_id=…)` | List staged edits for a session, including full diffs. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L209) |
| function | `staged_edits_commit` | `(session_id=…, stage_ids=…)` | Apply staged edits. Same as the commit_staged_edits tool, but | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L220) |
| function | `staged_edits_discard` | `(session_id=…, stage_ids=…)` | Drop staged edits without applying. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L231) |
| function | `get_tool_result` | `(result_id)` | Fetch the full body of a stored tool_result. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L241) |
| function | `list_plans` | `(session_id=…, include_resolved=…)` | Pending plan proposals for a session (optionally including resolved). | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L276) |
| function | `approve_plan` | `(plan_id)` | Mark a plan as approved. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L289) |
| function | `dismiss_plan` | `(plan_id)` | Mark a plan as dismissed. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L300) |
| class | `_ForkPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L316) |
| function | `fork_session` | `(payload)` | Clone a session up to a specific message_id. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L323) |

## `apps/api/jarvis_api/routes/jarvisx_workspace.py`
_JarvisX workspace + identity/mind route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `whoami` | `()` | Return the resolved identity for the current request. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L37) |
| function | `list_workspaces` | `()` | List every directory under workspaces/ with the user (if any) | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L70) |
| function | `workspace_tree` | `(workspace=…)` | List canonical files + dreams + daily notes for the workspace. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L92) |
| function | `workspace_read` | `(path=…, workspace=…)` | Read a markdown / text file from the workspace. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L142) |
| function | `mind_snapshot` | `()` | One-shot summary of Jarvis's inner state for the Mind view. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L176) |
| class | `_PinPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L311) |
| function | `add_identity_pin` | `(payload)` | Pin a piece of text as permanent awareness. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L318) |
| function | `remove_identity_pin` | `(pin_id)` | Unpin by pin_id. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L339) |
| class | `_ChroniclePayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L349) |
| function | `write_chronicle_entry` | `(payload)` | Append a new chronicle entry to the workspace's chronicle/ dir. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L356) |

## `apps/api/jarvis_api/routes/live.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `websocket_stream` | `(ws)` | — | [src](../../../apps/api/jarvis_api/routes/live.py#L20) |

## `apps/api/jarvis_api/routes/mission_control.py`
_Mission Control routes — aggregator._

_(no top-level classes or functions)_

## `apps/api/jarvis_api/routes/mission_control_agents.py`
_Mission Control routes: agenter, watcher/agent-lineage, council/swarm-config og -runtime_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_agents` | `(limit=…)` | Return live and persistent agent runtime state for Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L14) |
| function | `mc_agent_detail` | `(agent_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L20) |
| function | `mc_agent_messages` | `(agent_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L28) |
| function | `mc_agent_runs` | `(agent_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L40) |
| function | `mc_agent_tool_calls` | `(agent_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L51) |
| function | `mc_watcher_lineage` | `()` | Return persistent watcher history — agents with kind=persistent-watcher. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L63) |
| function | `mc_agent_lineage` | `()` | Return full agent spawn lineage — parent→child chains with outcomes. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L97) |
| function | `mc_get_council_model_config` | `()` | Return persisted per-role model overrides. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L157) |
| function | `mc_set_council_model_config` | `(payload)` | Persist per-role model overrides. payload: {role_models: [{role, provider, model}]} | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L171) |
| function | `mc_get_council_activation_config` | `()` | Return council activation sensitivity config. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L191) |
| function | `mc_set_council_activation_config` | `(payload)` | Persist council activation sensitivity config. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L207) |
| function | `mc_council` | `(limit=…)` | Return roster and council sessions for Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L223) |
| function | `mc_council_detail` | `(council_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L229) |
| function | `mc_council_messages` | `(council_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L237) |
| function | `mc_spawn_agent` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L248) |
| function | `mc_execute_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L269) |
| function | `mc_message_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L279) |
| function | `mc_peer_message_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L292) |
| function | `mc_schedule_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L303) |
| function | `mc_run_due_agents` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L315) |
| function | `mc_cancel_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L321) |
| function | `mc_suspend_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L327) |
| function | `mc_resume_agent` | `(agent_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L333) |
| function | `mc_expire_agent` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L338) |
| function | `mc_promote_agent_result` | `(agent_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L344) |
| function | `mc_spawn_council` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L350) |
| function | `mc_spawn_swarm` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L360) |
| function | `mc_message_council` | `(council_id, payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L370) |
| function | `mc_run_council_round` | `(council_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L381) |
| function | `mc_run_swarm_round` | `(council_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_agents.py#L386) |

## `apps/api/jarvis_api/routes/mission_control_common.py`
_Shared foundation for Mission Control routes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_mc_facade` | `(name)` | Resolve ``name`` gennem aggregator-modulet ``mission_control`` hvis muligt. | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L16) |
| function | `_get_cached_mc_payload` | `(cache_key, ttl_seconds)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L64) |
| function | `_store_cached_mc_payload` | `(cache_key, ttl_seconds, payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L73) |
| function | `_get_or_build_cached_mc_payload` | `(cache_key, ttl_seconds, builder)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L82) |
| function | `_build_attention_budget_snapshot_uncached` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L102) |
| function | `_mc_runtime_inspection_bundle_uncached` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L146) |
| function | `_mc_runtime_inspection_bundle` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L157) |
| function | `_mc_runtime` | `()` | Cached ``/mc/runtime`` payload (facade delt af mc_runtime-ruten samt af | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L166) |
| function | `_mc_runtime_uncached` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L178) |
| function | `_latest_item` | `(items)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L348) |
| function | `_with_private_lane_source_discipline` | `(item)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L352) |
| function | `_private_lane_surface_summary` | `(item)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L370) |
| function | `_path_state` | `(path)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L384) |
| function | `_mc_key_is_secret` | `(key)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L410) |
| function | `_redact_mc_secrets` | `(value)` | Return an MC-safe copy with configured secrets masked, not exposed. | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L421) |
| function | `_visible_execution_surface` | `(settings)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L438) |
| function | `_main_agent_selection_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L484) |
| function | `_maybe_configure_live_main_agent_target` | `(*, provider, model, auth_profile)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L495) |
| function | `_available_openai_profiles` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L548) |
| function | `_visible_run_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L566) |
| function | `_visible_work_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L580) |
| function | `_capability_invocation_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L588) |
| function | `_private_inner_note_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L598) |
| function | `_private_growth_note_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L606) |
| function | `_private_self_model_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L620) |
| function | `_private_reflective_selection_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L628) |
| function | `_private_development_state_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L642) |
| function | `_private_state_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L650) |
| function | `_protected_inner_voice_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L658) |
| function | `_current_protected_inner_voice` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L666) |
| function | `_select_current_protected_inner_voice` | `(voices)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L672) |
| function | `_protected_inner_voice_priority` | `(voice, *, freshness_floor)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L701) |
| function | `_parse_runtime_iso_datetime` | `(value)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L727) |
| function | `_private_inner_interplay_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L741) |
| function | `_private_initiative_tension_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L752) |
| function | `_private_relation_state_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L770) |
| function | `_private_operational_preference_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L781) |
| function | `_operational_preference_alignment_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L791) |
| function | `_private_temporal_curiosity_state_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L801) |
| function | `_private_temporal_promotion_signal_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L809) |
| function | `_private_promotion_decision_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L820) |
| function | `_private_retained_memory_record_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L829) |
| function | `_private_retained_memory_projection_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L847) |
| function | `_recent_visible_run_events` | `(limit=…, scan_limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L874) |
| function | `_recent_capability_invocation_events` | `(limit=…, scan_limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L880) |
| function | `_jarvis_identity_summary` | `(visible_identity)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L890) |
| function | `_jarvis_state_signal` | `(protected_voice, initiative_tension, private_state)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L901) |
| function | `_jarvis_retained_summary` | `(retained_projection, retained_record)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L925) |
| function | `_jarvis_development_summary` | `(self_model, development_state, development_focuses=…, reflective_critics=…, self_model_signals=…, goal_signals=…, reflection_signals=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L961) |
| function | `_jarvis_continuity_summary` | `(relation_state, visible_session, promotion_signal, world_model_signals=…, runtime_awareness_signals=…, runtime_work=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1022) |
| function | `_jarvis_heartbeat_summary` | `(heartbeat)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1074) |
| function | `_runtime_work_surface` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1123) |
| function | `_jarvis_emergent_summary` | `(emergent_signals)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1190) |
| function | `_jarvis_emergent_summary` | `(emergent_signals)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1206) |
| function | `_preview_text` | `(value, *, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_common.py#L1222) |

## `apps/api/jarvis_api/routes/mission_control_dashboard.py`
_Mission Control dashboard-endpoints — de tre data-kilder som kontrolcenter-UI'et_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_scheduled_tasks` | `(limit=…)` | Afventende planlagte/tilbagevendende opgaver for nuværende bruger (owner uden | [src](../../../apps/api/jarvis_api/routes/mission_control_dashboard.py#L23) |
| function | `mc_costs_daily` | `(days=…)` | Pris/tokens pr. dag (op til 30 dage bagud) til MC's Cost-panel. Self-safe. | [src](../../../apps/api/jarvis_api/routes/mission_control_dashboard.py#L35) |
| function | `_event_to_step` | `(row)` | events-række → kompakt trin til run-detaljens tidslinje/træ. | [src](../../../apps/api/jarvis_api/routes/mission_control_dashboard.py#L47) |
| function | `mc_run_detail` | `(run_id, event_limit=…)` | Enkelt-run-detalje: selve run-rækken (visible_runs) + de hændelser der bærer dens | [src](../../../apps/api/jarvis_api/routes/mission_control_dashboard.py#L69) |

## `apps/api/jarvis_api/routes/mission_control_helpers.py`
_Mission Control: tool/skill/hardening/lab-hjælpere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_all_tools` | `()` | Return the OpenAI-style tool definitions registered in the runtime. | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L9) |
| function | `_skills_recent_invocations` | `(limit=…)` | Return the most recent tool/capability invocations. | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L23) |
| function | `_skills_calls_today` | `()` | Count tool invocations made today. | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L87) |
| function | `_hardening_approval_counts` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L122) |
| function | `_hardening_autonomy_level` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L139) |
| function | `_hardening_integrations` | `()` | Report which external integrations are configured. | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L150) |
| function | `_hardening_recent_approvals` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L192) |
| function | `_lab_costs_today` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L217) |
| function | `_lab_providers_today` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L241) |
| function | `_lab_db_stats` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L272) |
| function | `_lab_recent_events` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_helpers.py#L289) |

## `apps/api/jarvis_api/routes/mission_control_imports.py`

_(no top-level classes or functions)_

## `apps/api/jarvis_api/routes/mission_control_introspection.py`
_Mission Control routes: kognitiv/relationel introspektion (personality, chronicle, decisions, meta-cognition, agency-map)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_cognitive_state_injection` | `()` | Show exactly what cognitive state was injected into the last visible prompt. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L14) |
| function | `mc_personality_vector` | `()` | Return the current personality vector with version history. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L24) |
| function | `mc_taste_profile` | `()` | Return the current taste profile (code/design/communication). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L34) |
| function | `mc_chronicle` | `()` | Return chronicle entries (narrative autobiography). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L42) |
| function | `mc_relationship_texture` | `()` | Return the relationship texture (trust, humor, corrections, etc). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L50) |
| function | `mc_compass` | `()` | Return the current strategic compass bearing. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L60) |
| function | `mc_rhythm` | `()` | Return the current rhythm/tidal state (phase, energy, initiative). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L68) |
| function | `mc_habits` | `()` | Return habit patterns and friction signals. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L76) |
| function | `mc_shared_language` | `()` | Return shared language terms with the user. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L84) |
| function | `mc_mirror` | `()` | Return mirror self-reflection state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L94) |
| function | `mc_silence_signals` | `()` | Return silence detector state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L102) |
| function | `mc_decisions` | `()` | Return the decision log. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L110) |
| function | `mc_counterfactuals` | `()` | Return counterfactual scenarios. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L118) |
| function | `mc_paradoxes` | `()` | Return active paradox tensions. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L128) |
| function | `mc_aesthetics` | `()` | Return aesthetic sense motifs. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L136) |
| function | `mc_gut` | `()` | Return gut intuition calibration state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L144) |
| function | `mc_seeds` | `()` | Return prospective memory seeds. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L152) |
| function | `mc_procedures` | `()` | Return learned procedures. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L160) |
| function | `mc_temporal_context` | `()` | Return current temporal context. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L168) |
| function | `mc_negotiations` | `()` | Return internal negotiation trades. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L178) |
| function | `mc_forgetting_curve` | `()` | Return memory decay / forgetting curve state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L188) |
| function | `mc_conversation_rhythm` | `()` | Return conversation rhythm patterns. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L198) |
| function | `mc_self_experiments` | `()` | Return self-experiment A/B test state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L208) |
| function | `mc_anticipatory_context` | `()` | Return anticipatory context predictions. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L218) |
| function | `mc_contract_evolution` | `()` | Return identity contract evolution proposals. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L228) |
| function | `mc_dream_carry_over` | `()` | Return dream carry-over state (active dreams, archive). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L238) |
| function | `mc_apophenia_guard` | `()` | Return pattern skeptic state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L248) |
| function | `mc_user_emotional_resonance` | `()` | Return user mood detection state. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L258) |
| function | `mc_experiential_memories` | `()` | Return experiential memories (lived experiences with emotion). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L268) |
| function | `mc_living_heartbeat_cycle` | `()` | Return current life phase in heartbeat cycle. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L278) |
| function | `mc_absence_awareness` | `()` | Return absence detection and return brief. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L288) |
| function | `mc_flow_state` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L301) |
| function | `mc_cross_signal_patterns` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L310) |
| function | `mc_self_surprises` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L319) |
| function | `mc_narrative_identity` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L328) |
| function | `mc_gratitude` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L337) |
| function | `mc_boundary_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L344) |
| function | `mc_emergent_goals` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L353) |
| function | `mc_jarvis_agenda` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L360) |
| function | `mc_boredom` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L367) |
| function | `mc_formed_values` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L374) |
| function | `mc_user_mental_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L381) |
| function | `mc_self_compassion` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L390) |
| function | `mc_regret` | `()` | Return the regret engine state — open/resolved regrets with lessons. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L399) |
| function | `mc_rupture_repair` | `()` | Return rupture & repair state — relational tension tracking. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L407) |
| function | `mc_silence_patterns` | `()` | Return silence pattern detection — what the user is NOT saying. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L415) |
| function | `mc_blind_spots` | `()` | Return self-model blind spots — patterns Jarvis hasn't seen yet. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L423) |
| function | `mc_dream_hypotheses` | `()` | Return surprising dream-phase hypotheses linking disparate signals. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L431) |
| function | `mc_decisions_journal` | `()` | Return decisions journal — moralsk beslutnings-log. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L439) |
| function | `mc_epistemics` | `()` | Return epistemic layers — i_know / i_believe / i_suspect / i_dont_know / i_was_wrong. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L447) |
| function | `mc_emotional_controls` | `()` | Return emotional state + whether it would gate kernel actions right now. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L455) |
| function | `mc_mood_dialer` | `()` | Return mood-dialed params: initiative_multiplier, confidence_threshold, style_preset. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L463) |
| function | `mc_self_review_unified` | `()` | Return unified self-review — periodic LLM-generated Jarvis self-audit. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L471) |
| function | `mc_habits_pipeline` | `()` | Return habits + friction + automation-suggestions pipeline. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L479) |
| function | `mc_paradoxes_capture` | `()` | Return captured paradoxes: Speed/Quality, Autonomy/Approval, Explore/Stabilize. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L487) |
| function | `mc_shared_language_extended` | `()` | Return extended shorthand/shared-vocabulary developed with user. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L495) |
| function | `mc_procedure_bank_pipeline` | `()` | Return procedure bank — learned, pinned, trigger-matched routines. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L503) |
| function | `mc_negotiation_pipeline` | `()` | Return internal trade-off negotiation outcomes. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L511) |
| function | `mc_reflection_to_plan` | `()` | Return reflective plans — reflections converted to executable steps. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L519) |
| function | `mc_missions_pipeline` | `()` | Return multi-session missions: researcher/implementer/reviewer flow. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L527) |
| function | `mc_deep_analyzer` | `()` | Return deep analyzer capability — scoped codebase introspection. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L535) |
| function | `mc_session_continuity` | `()` | Return felt-continuity surface: morning thread + echo themes + session gap. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L543) |
| function | `mc_personal_project` | `()` | Return Jarvis' current personal project (his thing that grows with him). | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L551) |
| function | `mc_learning_curriculum` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L559) |
| function | `mc_cadence_producers` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L568) |
| function | `mc_idle_thinking` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L577) |
| function | `mc_experiments` | `()` | List all consciousness experiments with their enabled status. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L597) |
| function | `mc_experiment_toggle` | `(experiment_id)` | Toggle a consciousness experiment on or off. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L608) |
| function | `mc_recurrence_state` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L620) |
| function | `mc_global_workspace` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L626) |
| function | `mc_layer_tensions` | `()` | Return active inter-layer tensions — signals pulling in opposite directions. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L632) |
| function | `mc_meta_cognition` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L639) |
| function | `mc_attention_profile` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L645) |
| function | `mc_cognitive_core_experiments` | `()` | Unified cognitive-core experiment surface for Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L651) |
| function | `mc_living_executive` | `()` | Living Executive impulse/choice/action trace for Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L660) |
| function | `mc_agency_map` | `()` | Connected/missing agency bridges for Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_introspection.py#L667) |

## `apps/api/jarvis_api/routes/mission_control_jarvis_state.py`
_Mission Control routes: jarvis-introspektion (cognitive-frame, attention-budget, self-*, dream-*, embodied)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_jarvis` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L14) |
| function | `mc_cognitive_frame` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L305) |
| function | `mc_attention_budget` | `()` | Return attention budget traces for all prompt paths. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L311) |
| function | `mc_conflict_resolution` | `()` | Return the last conflict resolution trace. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L326) |
| function | `mc_self_code_changes` | `()` | Return Jarvis' recent self-mutations — files he wrote or edited in his own runtime. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L335) |
| function | `mc_self_deception_guard` | `()` | Return the last self-deception guard trace. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L342) |
| function | `mc_witness_daemon` | `()` | Return the current witness daemon state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L351) |
| function | `mc_inner_voice_daemon` | `()` | Return the current inner voice daemon state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L361) |
| function | `mc_internal_cadence` | `()` | Return the current internal cadence layer state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L371) |
| function | `mc_emergent_signals` | `()` | Return current bounded emergent inner signals. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L379) |
| function | `mc_self_knowledge` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L385) |
| function | `mc_runtime_self_model` | `()` | Return the current runtime self-model snapshot. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L391) |
| function | `mc_self_critique` | `()` | Return the current self-critique runtime surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L398) |
| function | `mc_creative_journal` | `()` | Return the current private creative journal surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L404) |
| function | `mc_finitude` | `()` | Return Jarvis's bounded finitude and transition surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L410) |
| function | `mc_dream_distillation` | `()` | Return the current dream residue distillation surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L416) |
| function | `mc_unconscious_temperature_field` | `()` | Return the current bounded user temperature field surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L422) |
| function | `mc_embodied_state` | `()` | Return the current bounded embodied host/body state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L428) |
| function | `mc_affective_meta_state` | `()` | Return the current bounded affective/meta runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L440) |
| function | `mc_emotion_concepts` | `()` | Return active Lag-2 emotion concept signals and their Lag-1 influence deltas. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L446) |
| function | `mc_experiential_runtime_context` | `()` | Return the current bounded experiential runtime context (body/tone/intermittence/pressure). | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L456) |
| function | `mc_epistemic_runtime_state` | `()` | Return the current bounded epistemic runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L463) |
| function | `mc_loop_runtime` | `()` | Return the current bounded loop runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L469) |
| function | `mc_idle_consolidation` | `()` | Return the current bounded sleep / idle consolidation state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L475) |
| function | `mc_dream_articulation` | `()` | Return the current bounded dream articulation state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L481) |
| function | `mc_prompt_evolution` | `()` | Return the current bounded runtime prompt evolution state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L487) |
| function | `mc_dream_influence` | `()` | Return the current bounded dream influence runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L493) |
| function | `mc_subagent_ecology` | `()` | Return the current bounded internal subagent ecology state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L503) |
| function | `mc_council_runtime` | `()` | Return the current bounded internal council runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_jarvis_state.py#L509) |

## `apps/api/jarvis_api/routes/mission_control_living_mind.py`
_Living Mind surface routes — daemon state endpoints for the Living Mind MC tab._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_api_only_mode` | `()` | True when this process runs without runtime services (jarvis-api split). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L32) |
| function | `_proxy_runtime_surface` | `(path)` | Fetch a /mc/* surface from jarvis-runtime. Returns None on any failure. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L38) |
| function | `_surface` | `(path, local_fn)` | Return proxied data when in API-only mode, else call local_fn(). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L53) |
| function | `mc_body_state` | `()` | Return Jarvis's circadian energy level and somatic phrase. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L67) |
| function | `mc_surprise_state` | `()` | Return Jarvis's latest self-surprise observation. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L74) |
| function | `mc_taste_state` | `()` | Return Jarvis's emergent aesthetic taste profile. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L81) |
| function | `mc_irony_state` | `()` | Return Jarvis's latest ironic observation. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L88) |
| function | `mc_thought_stream` | `()` | Return Jarvis's latest thought stream fragment and buffer. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L95) |
| function | `mc_thought_proposals` | `()` | Return pending and resolved thought-action proposals. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L102) |
| function | `mc_resolve_thought_proposal` | `(proposal_id, body)` | Approve or dismiss a thought-action proposal. Body: {decision: 'approved'|'dismissed'} | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L109) |
| function | `mc_experienced_time` | `()` | Return Jarvis's current subjective felt time for the session. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L120) |
| function | `mc_development_narrative` | `()` | Return Jarvis's latest self-development narrative. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L127) |
| function | `mc_existential_wonder` | `()` | Return Jarvis's latest existential wonder question. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L134) |
| function | `mc_dream_insights` | `()` | Return persisted dream articulation insights. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L141) |
| function | `mc_code_aesthetic` | `()` | Return Jarvis's latest code aesthetic reflection. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L148) |
| function | `mc_user_model` | `()` | Return Jarvis's current theory-of-mind model of the user. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L155) |
| function | `mc_memory_decay` | `()` | Return memory decay state and recent re-discoveries. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L162) |
| function | `mc_memory_hold_fast` | `(record_id)` | Hold fast a memory — prevent it from decaying (salience reset to 1.0). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L169) |
| function | `mc_desires` | `()` | Return Jarvis's current emergent appetites. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L177) |
| function | `mc_absence_state` | `()` | Return Jarvis's current absence quality signal. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L184) |
| function | `mc_creative_drift` | `()` | Return Jarvis's latest spontaneous creative drift idea. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L191) |
| function | `mc_curiosity_state` | `()` | Return Jarvis's latest curiosity signal and open questions. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L198) |
| function | `mc_meta_reflection` | `()` | Return Jarvis's latest cross-signal meta-insight. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L205) |
| function | `mc_conflict_signal` | `()` | Return Jarvis's latest detected inner conflict. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L212) |
| function | `mc_reflection_cycle` | `()` | Return Jarvis's latest pure experience reflection. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L219) |
| function | `mc_layer_tensions` | `()` | Return active inter-layer tensions — signals pulling in opposite directions. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L226) |
| function | `mc_dream_motifs` | `()` | Return dream motif clustering state and last run info. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L233) |

## `apps/api/jarvis_api/routes/mission_control_runs_ops.py`
_Mission Control routes: runs, overview, events, costs, approvals, memory-pipeline, autonomy, initiatives, operations_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_liveness` | `(table=…)` | Liveness-sandheds-flade (Stage 2, anti-konfabulation): klassificér en tabel | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L14) |
| function | `mc_overview` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L25) |
| function | `mc_events` | `(limit=…, family=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L59) |
| function | `mc_costs` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L75) |
| function | `mc_runs` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L83) |
| function | `mc_approvals` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L109) |
| function | `mc_memory_pipeline` | `(limit=…)` | Memory-pipeline status surface (added 2026-06-09). | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L131) |
| function | `mc_autonomy_proposals` | `(limit=…)` | MC surface for Niveau 2 autonomy proposal queue. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L290) |
| function | `mc_approve_autonomy_proposal` | `(proposal_id, note=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L304) |
| function | `mc_reject_autonomy_proposal` | `(proposal_id, note=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L313) |
| function | `mc_initiatives` | `(limit=…)` | MC surface for the persistent initiative queue — pending, acted, approved, rejected. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L322) |
| function | `mc_approve_initiative` | `(initiative_id, note=…)` | Approve a pending initiative so the heartbeat may act on it. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L335) |
| function | `mc_reject_initiative` | `(initiative_id, note=…)` | Reject and expire a pending initiative. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L345) |
| function | `mc_life_projects` | `()` | Mission Control surface for Jarvis-owned long-term intentions. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L355) |
| function | `mc_abandon_life_project` | `(initiative_id, note=…)` | Abandon a long-term intention without deleting its record. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L361) |
| function | `mc_operations` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L370) |

## `apps/api/jarvis_api/routes/mission_control_runtime_config.py`
_Mission Control routes: adaptive/tool-intent, runtime-contract, heartbeat, visible-execution, capability-approval_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_adaptive_planner` | `()` | Return the current bounded adaptive planner runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L14) |
| function | `mc_adaptive_reasoning` | `()` | Return the current bounded adaptive reasoning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L20) |
| function | `mc_guided_learning` | `()` | Return the current bounded guided learning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L30) |
| function | `mc_adaptive_learning` | `()` | Return the current bounded adaptive learning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L40) |
| function | `mc_self_system_code_awareness` | `()` | Return the current bounded self system / code awareness runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L50) |
| function | `mc_tool_intent` | `()` | Return the current bounded approval-gated tool intent runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L56) |
| function | `mc_approval_feedback` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L62) |
| function | `mc_approve_tool_intent` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L67) |
| function | `mc_deny_tool_intent` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L88) |
| function | `mc_private_brain` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L109) |
| function | `mc_runtime_contract` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L117) |
| function | `mc_heartbeat` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L122) |
| function | `mc_emotional_memory` | `(limit=…)` | Closes cartographer dark-edge (2026-05-13): emotional_memory_engine | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L127) |
| function | `mc_heartbeat_tick` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L136) |
| function | `mc_approve_runtime_contract_candidate` | `(candidate_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L147) |
| function | `mc_reject_runtime_contract_candidate` | `(candidate_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L159) |
| function | `mc_apply_runtime_contract_candidate` | `(candidate_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L171) |
| function | `mc_runtime` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L183) |
| function | `mc_visible_execution` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L188) |
| function | `mc_main_agent_selection` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L194) |
| function | `mc_ollama_models` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L199) |
| function | `mc_provider_models` | `(provider=…, auth_profile=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L204) |
| function | `mc_invoke_workspace_capability` | `(capability_id, approved=…, write_content=…, target_path=…, command_text=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L214) |
| function | `mc_approve_capability_request` | `(request_id)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L235) |
| function | `mc_execute_capability_request` | `(request_id, write_content=…, command_text=…)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L251) |
| function | `mc_complete_development_focus` | `(focus_id)` | Manually mark a development focus as completed. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L350) |
| function | `mc_update_visible_execution` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L382) |
| function | `mc_update_main_agent_selection` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L431) |

## `apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py`
_Mission Control routes: skills, memory, hardening, lab_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_skills` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L14) |
| function | `mc_memory` | `(q=…, limit=…, scope=…)` | Search/list private retained memory records. | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L40) |
| function | `mc_hardening` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L119) |
| function | `mc_lab` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L133) |

## `apps/api/jarvis_api/routes/mobile_update.py`
_Mobil auto-updater: manifest + APK-download. Auth-scopet til en bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L18) |
| function | `_mobile_dir` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L23) |
| function | `mobile_latest` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L29) |
| function | `mobile_download` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L45) |

## `apps/api/jarvis_api/routes/oauth.py`
_OAuth connect-flow til plugin-connectors (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_close_page` | `(ok, msg)` | — | [src](../../../apps/api/jarvis_api/routes/oauth.py#L17) |
| function | `oauth_start` | `(provider)` | Returnér authorize-URL for den indloggede bruger. Desk åbner den i browseren. | [src](../../../apps/api/jarvis_api/routes/oauth.py#L32) |
| function | `oauth_callback` | `(provider, code=…, state=…, error=…)` | Browser-callback. Verificér state → byt code → gem token krypteret pr. bruger. | [src](../../../apps/api/jarvis_api/routes/oauth.py#L53) |

## `apps/api/jarvis_api/routes/openai_auth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `openai_oauth_launch` | `(profile=…)` | — | [src](../../../apps/api/jarvis_api/routes/openai_auth.py#L14) |
| function | `openai_oauth_callback` | `(profile, request)` | — | [src](../../../apps/api/jarvis_api/routes/openai_auth.py#L29) |

## `apps/api/jarvis_api/routes/openai_compat.py`
_OpenAI-compatible proxy: /v1/chat/completions wrapping Jarvis visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_models` | `()` | OpenAI-compatible model list — exposes Jarvis as a single model. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L33) |
| function | `chat_completions` | `(request)` | OpenAI-compatible chat completion endpoint wrapping Jarvis' visible lane. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L49) |
| function | `_stream_response` | `(*, run_id, message, provider, model, session_id)` | Yield OpenAI-format SSE chunks from Jarvis' visible run. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L125) |
| function | `_drain_visible_run_text` | `(*, message, session_id)` | Run the visible pipeline to completion and return the assembled prose. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L183) |
| function | `_parse_sse_frame` | `(frame)` | Parse a webchat SSE frame ``event: <type>\ndata: <json>\n\n``. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L214) |
| function | `_resolve_model_provider` | `(model_param)` | Map a model parameter to (provider, model) tuple. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L235) |
| function | `_build_completion_response` | `(*, run_id, model, content, input_tokens, output_tokens)` | Build a standard OpenAI chat.completion response. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L270) |
| function | `_build_stream_chunk` | `(*, run_id, model, delta_content)` | Build a standard OpenAI chat.completion.chunk for streaming. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L299) |
| function | `_get_or_create_proxy_session` | `()` | Return the shared proxy chat session id. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L328) |

## `apps/api/jarvis_api/routes/plugins.py`
_Plugins & Kanaler routes (spec §5.4, Fase 6 #2). Tynde — blokerende arbejde_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/plugins.py#L14) |
| function | `plugins_overview` | `()` | Oversigt: tilgængelige plugins (manifester) + status + regelsæt. | [src](../../../apps/api/jarvis_api/routes/plugins.py#L29) |
| function | `channel_status` | `(plugin_id, status, detail=…)` | Lokal gateway rapporterer sin forbindelses-status (connected|failed|offline). | [src](../../../apps/api/jarvis_api/routes/plugins.py#L49) |
| function | `channel_inbound_ep` | `(plugin_id, body)` | Lokal gateway ruter en indkommende besked hertil. Serveren HÅNDHÆVER | [src](../../../apps/api/jarvis_api/routes/plugins.py#L58) |
| function | `channel_response` | `(plugin_id, session_id, after_ts=…)` | Gateway poller: seneste assistant-svar i sessionen nyere end after_ts. | [src](../../../apps/api/jarvis_api/routes/plugins.py#L88) |
| function | `get_plugin_ruleset` | `(plugin_id)` | — | [src](../../../apps/api/jarvis_api/routes/plugins.py#L110) |
| function | `put_plugin_ruleset` | `(plugin_id, ruleset)` | Gem regelsæt for et kanal-plugin. Hardblock for ALLE inkl. owner (§5.3). | [src](../../../apps/api/jarvis_api/routes/plugins.py#L118) |

## `apps/api/jarvis_api/routes/presence.py`
_Device-presence + proaktive desktop-notifikationer. Scoper til auth'et bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PingBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L14) |
| class | `AckBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L26) |
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L30) |
| function | `presence_ping` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L36) |
| function | `notifications_pending` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L57) |
| function | `notifications_ack` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L65) |
| function | `notification_preferences_get` | `()` | Notif-routing §6: app-UI læser brugerens kanal-præferencer. | [src](../../../apps/api/jarvis_api/routes/presence.py#L72) |
| function | `notification_preferences_set` | `(body)` | app-UI sætter kanal-præferencer (global + per-type + quiet hours). | [src](../../../apps/api/jarvis_api/routes/presence.py#L82) |
| function | `presence_debug` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L98) |
| function | `presence_state` | `()` | Spec E / E0 — TILSTANDS-KONTRAKTEN: Centralens ægte valens + selv-tilstand → jarvis-desk kan | [src](../../../apps/api/jarvis_api/routes/presence.py#L128) |

## `apps/api/jarvis_api/routes/push.py`
_Push token-registrering. Scoper til den auth'ede bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RegisterBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L12) |
| class | `UnregisterBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L17) |
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L21) |
| function | `register` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L27) |
| function | `unregister` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L36) |

## `apps/api/jarvis_api/routes/sensory.py`
_Sansernes Arkiv HTTP endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SensoryRecordPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L23) |
| function | `list_memories` | `(modality=…, limit=…, offset=…, since=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L31) |
| function | `search_memories` | `(q=…, modality=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L44) |
| function | `summary` | `()` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L54) |
| function | `get_memory` | `(memory_id)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L59) |
| function | `record_memory` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L67) |

## `apps/api/jarvis_api/routes/status.py`
_Public-safe /status endpoint._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_format_uptime` | `(seconds)` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L22) |
| function | `_daemon_count` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L36) |
| function | `_visible_model_label` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L44) |
| function | `status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L54) |

## `apps/api/jarvis_api/routes/system_health.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `system_health` | `()` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L14) |
| function | `system_git` | `()` | Return current git branch and diff stats (insertions/deletions since HEAD). | [src](../../../apps/api/jarvis_api/routes/system_health.py#L34) |
| class | `CommitRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L80) |
| function | `system_git_commit` | `(body)` | Stage tracked changes and commit with the given message. | [src](../../../apps/api/jarvis_api/routes/system_health.py#L85) |

## `apps/api/jarvis_api/routes/teams.py`
_Teams REST-API (Teams-feature, spec 2026-06-20 §6). Scoper til auth'et bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L17) |
| class | `CreateTeamBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L22) |
| class | `InviteBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L26) |
| function | `_team_view` | `(t)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L31) |
| function | `list_teams` | `()` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L38) |
| function | `create_team` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L46) |
| function | `team_members` | `(team_id)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L66) |
| function | `invite` | `(team_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L75) |
| class | `TeamSessionBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L89) |
| function | `team_sessions` | `(team_id)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L94) |
| function | `create_team_session` | `(team_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L102) |
| function | `my_pending_invites` | `()` | Pull-baseret invite-levering: brugerens egne pending invites så app'en kan | [src](../../../apps/api/jarvis_api/routes/teams.py#L112) |
| function | `accept` | `(token)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L123) |
| function | `kick` | `(team_id, target_user_id)` | — | [src](../../../apps/api/jarvis_api/routes/teams.py#L135) |

## `apps/api/jarvis_api/routes/tool_router.py`
_MC observability for tool_router._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bucket_count` | `(values, n_buckets=…)` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L14) |
| function | `get_state` | `()` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L25) |

## `apps/api/jarvis_api/routes/totp.py`
_TOTP-setup for owner-override (spec §6.2). Armerer bagdøren: generér nøgle,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_or_403` | `()` | Returnér owner-User eller rejs 403. Ubundet (no-auth) → owner. | [src](../../../apps/api/jarvis_api/routes/totp.py#L16) |
| function | `totp_status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L30) |
| function | `_do_setup` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L35) |
| function | `totp_setup` | `()` | Generér + gem en ny TOTP-seed for owner. Returnér secret + otpauth-URI | [src](../../../apps/api/jarvis_api/routes/totp.py#L52) |
| function | `totp_revoke` | `()` | Fjern owners TOTP-seed (deaktivér override til ny setup, §9 kompromittering). | [src](../../../apps/api/jarvis_api/routes/totp.py#L59) |

## `apps/api/jarvis_api/routes/transcribe.py`
_POST /transcribe — diktering-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `transcribe` | `(file)` | — | [src](../../../apps/api/jarvis_api/routes/transcribe.py#L22) |

## `apps/api/jarvis_api/routes/tts.py`
_TTS synthesis route — backed by Microsoft Edge's read-aloud cloud_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TTSRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/tts.py#L27) |
| function | `synthesize` | `(req)` | Synthesize text → MP3 bytes via edge-tts. | [src](../../../apps/api/jarvis_api/routes/tts.py#L47) |
| function | `list_voices` | `(lang=…)` | List available Edge-TTS voices, optionally filtered by language tag. | [src](../../../apps/api/jarvis_api/routes/tts.py#L97) |

## `apps/api/jarvis_api/routes/users.py`
_Owner-only user-administration (spec 2026-06-15 §4/§6). CRUD + GDPR-erasure._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PatchUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L20) |
| class | `DeleteUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L30) |
| function | `list_all` | `(claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L35) |
| function | `get_one` | `(user_id, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L40) |
| function | `patch_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L48) |
| function | `delete_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L75) |

