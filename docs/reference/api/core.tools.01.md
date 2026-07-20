# `core.tools.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/__init__.py`

_(no top-level classes or functions)_

## `core/tools/agent_todo_tools.py`
_Tool wrappers for the per-session todo tracker (agent_todos)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session_id_arg` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L15) |
| function | `_exec_todo_list` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L20) |
| function | `_exec_todo_set` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L25) |
| function | `_exec_todo_add` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L32) |
| function | `_exec_todo_update_status` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L36) |
| function | `_exec_todo_remove` | `(args)` | — | [src](../../../core/tools/agent_todo_tools.py#L44) |

## `core/tools/app_control_tool.py`
_request_app_action tool (spec 2026-06-15) — Jarvis foreslår mode/permission-skift._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_request_app_action` | `(args)` | — | [src](../../../core/tools/app_control_tool.py#L25) |
| function | `_exec_open_ui_panel` | `(args)` | — | [src](../../../core/tools/app_control_tool.py#L51) |
| function | `build_app_action_event` | `(result, *, user_message, session_id)` | Ren helper: hvis et tool-resultat bærer en app_action-markør, byg payloaden | [src](../../../core/tools/app_control_tool.py#L85) |

## `core/tools/auto_ensure_tests.py`
_Auto-ensure tests — Layer 2 of the Agentic Test Enforcement._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_core_file` | `(file_path)` | True if file is under core/ and is a .py file worth testing. | [src](../../../core/tools/auto_ensure_tests.py#L33) |
| function | `_expected_test_path` | `(core_path)` | Map core/foo/bar.py → tests/test_bar.py. | [src](../../../core/tools/auto_ensure_tests.py#L48) |
| function | `_infer_imports` | `(core_path)` | Try to infer the top-level imports needed for a test skeleton. | [src](../../../core/tools/auto_ensure_tests.py#L56) |
| function | `_generate_skeleton` | `(core_path)` | Generate a minimal but runnable test skeleton for a core module. | [src](../../../core/tools/auto_ensure_tests.py#L119) |
| function | `_run_pytest` | `(test_path)` | Run pytest on a single test file.  Returns CompletedProcess. | [src](../../../core/tools/auto_ensure_tests.py#L152) |
| function | `auto_ensure_tests` | `(changed_path)` | Main entry point. | [src](../../../core/tools/auto_ensure_tests.py#L174) |
| function | `_count_tests` | `(pytest_stdout)` | Extract the 'X passed' summary from pytest output. | [src](../../../core/tools/auto_ensure_tests.py#L235) |

## `core/tools/bash_session.py`
_Persistent bash sessions — Jarvis' one-shot bash forced him to restart his_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Session` | `` | — | [src](../../../core/tools/bash_session.py#L66) |
| method | `_Session.__init__` | `(self, session_id)` | — | [src](../../../core/tools/bash_session.py#L67) |
| method | `_Session._drain_pending` | `(self, timeout)` | — | [src](../../../core/tools/bash_session.py#L103) |
| method | `_Session.alive` | `(self)` | — | [src](../../../core/tools/bash_session.py#L114) |
| method | `_Session.run` | `(self, command, timeout=…)` | — | [src](../../../core/tools/bash_session.py#L121) |
| method | `_Session.close` | `(self)` | — | [src](../../../core/tools/bash_session.py#L185) |
| function | `_decode` | `(buf)` | — | [src](../../../core/tools/bash_session.py#L204) |
| function | `_daemon_main` | `()` | Singleton bash-session daemon. Listens on the Unix socket, owns sessions. | [src](../../../core/tools/bash_session.py#L216) |
| function | `_send` | `(client, payload)` | — | [src](../../../core/tools/bash_session.py#L367) |
| function | `_ensure_daemon_running` | `()` | Return True if a reachable daemon exists. Spawn one if not. | [src](../../../core/tools/bash_session.py#L379) |
| function | `_spawn_daemon` | `()` | Fork a detached daemon process running _daemon_main(). | [src](../../../core/tools/bash_session.py#L415) |
| function | `_ping_daemon` | `()` | — | [src](../../../core/tools/bash_session.py#L431) |
| function | `_client_call` | `(payload, timeout=…)` | — | [src](../../../core/tools/bash_session.py#L451) |
| function | `_exec_bash_session_open` | `(args)` | — | [src](../../../core/tools/bash_session.py#L482) |
| function | `_exec_bash_session_run` | `(args)` | — | [src](../../../core/tools/bash_session.py#L486) |
| function | `_exec_bash_session_close` | `(args)` | — | [src](../../../core/tools/bash_session.py#L504) |
| function | `_exec_bash_session_list` | `(_args)` | — | [src](../../../core/tools/bash_session.py#L511) |

## `core/tools/brain_write_gate.py`
_HARD gate for user-initiated writes to Jarvis' brain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_brain_write_allowed` | `(name, *, role)` | True if a user-initiated call to `name` is permitted for `role`. | [src](../../../core/tools/brain_write_gate.py#L13) |

## `core/tools/browser_tools.py`
_Browser control tools for Jarvis — Playwright-backed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_update_status` | `(status, *, url=…, title=…)` | — | [src](../../../core/tools/browser_tools.py#L33) |
| function | `_exec_browser_navigate` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L162) |
| function | `_exec_browser_read` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L183) |
| function | `_exec_browser_click` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L208) |
| function | `_exec_browser_type` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L226) |
| function | `_exec_browser_submit` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L244) |
| function | `_exec_browser_screenshot` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L263) |
| function | `_exec_browser_find_tabs` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L278) |
| function | `_exec_browser_switch_tab` | `(args)` | — | [src](../../../core/tools/browser_tools.py#L296) |

## `core/tools/calendar_tools.py`
_Calendar tools — Google Calendar with .ics fallback._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_runtime_key` | `(key)` | — | [src](../../../core/tools/calendar_tools.py#L12) |
| function | `_get_gcal_service` | `()` | Build Google Calendar service from credentials in runtime.json. | [src](../../../core/tools/calendar_tools.py#L23) |
| function | `_gcal_list_events` | `(days_ahead)` | — | [src](../../../core/tools/calendar_tools.py#L38) |
| function | `_gcal_create_event` | `(title, start_dt, end_dt)` | — | [src](../../../core/tools/calendar_tools.py#L67) |
| function | `_gcal_delete_event` | `(event_id)` | — | [src](../../../core/tools/calendar_tools.py#L85) |
| function | `_ics_list_events` | `(days_ahead)` | — | [src](../../../core/tools/calendar_tools.py#L98) |
| function | `_ics_create_event` | `(title, start_dt, end_dt)` | — | [src](../../../core/tools/calendar_tools.py#L131) |
| function | `_ics_delete_event` | `(event_id)` | — | [src](../../../core/tools/calendar_tools.py#L155) |
| function | `_exec_list_events` | `(args)` | — | [src](../../../core/tools/calendar_tools.py#L180) |
| function | `_exec_create_event` | `(args)` | — | [src](../../../core/tools/calendar_tools.py#L202) |
| function | `_exec_delete_event` | `(args)` | — | [src](../../../core/tools/calendar_tools.py#L232) |

## `core/tools/central_query_tool.py`
_`central_query` — Jarvis' direkte adgang til Den Intelligente Central (pull on-demand)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_envelope` | `(status, action, data, error, source, t0, **meta_extra)` | — | [src](../../../core/tools/central_query_tool.py#L31) |
| function | `_paginate` | `(items, offset, limit)` | Returnér en side + pagina-meta. ALDRIG trunkér en linje midt over: vi dropper | [src](../../../core/tools/central_query_tool.py#L39) |
| function | `_nerve_klass` | `(nerve)` | NerveSpec.klass for en nerve (til sikker toggle). Defaulter SECURITY-SIKKERT: | [src](../../../core/tools/central_query_tool.py#L57) |
| function | `central_query` | `(args)` | Eneste indgang. Returnerer ALTID en envelope (status ok/error). Kaster aldrig. | [src](../../../core/tools/central_query_tool.py#L75) |

## `core/tools/code_navigation_tools.py`
_Symbol find / find usages — regex-based v1._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ext_patterns` | `(extensions)` | Return (patterns, ripgrep --type-add args, ripgrep -t args). | [src](../../../core/tools/code_navigation_tools.py#L72) |
| function | `_scope_dir` | `()` | — | [src](../../../core/tools/code_navigation_tools.py#L94) |
| function | `_ripgrep_available` | `()` | — | [src](../../../core/tools/code_navigation_tools.py#L102) |
| function | `_run_rg` | `(patterns, symbol, scope, extra_args)` | — | [src](../../../core/tools/code_navigation_tools.py#L106) |
| function | `_exec_find_symbol` | `(args)` | — | [src](../../../core/tools/code_navigation_tools.py#L146) |
| function | `_exec_find_usages` | `(args)` | — | [src](../../../core/tools/code_navigation_tools.py#L189) |
| function | `_classify` | `(snippet)` | — | [src](../../../core/tools/code_navigation_tools.py#L248) |

## `core/tools/coding_lane_tools.py`
_Coding lane tools — Niveau 1 skeleton dispatcher._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_request_codex_skeleton` | `(args)` | Byg et skeleton/plan for en opgave via coding lane (Codex). | [src](../../../core/tools/coding_lane_tools.py#L18) |

## `core/tools/comfyui_tools.py`
_ComfyUI integration tools for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_comfy_get` | `(path, *, host=…)` | GET from ComfyUI API, return parsed JSON. | [src](../../../core/tools/comfyui_tools.py#L29) |
| function | `_comfy_post` | `(path, data, *, host=…)` | POST JSON to ComfyUI API, return parsed JSON. | [src](../../../core/tools/comfyui_tools.py#L42) |
| function | `_exec_comfyui_status` | `(args)` | Get ComfyUI system stats and queue status. | [src](../../../core/tools/comfyui_tools.py#L67) |
| function | `_exec_comfyui_workflow` | `(args)` | Submit a ComfyUI workflow for execution. | [src](../../../core/tools/comfyui_tools.py#L86) |
| function | `_exec_comfyui_history` | `(args)` | Get ComfyUI execution history. | [src](../../../core/tools/comfyui_tools.py#L118) |
| function | `_exec_comfyui_objects` | `(args)` | List available ComfyUI node types / models. | [src](../../../core/tools/comfyui_tools.py#L148) |

## `core/tools/companion_push_tools.py`
_Tool: send_push_notification — proaktiv push til brugerens companion (mobil/desktop)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_send_push_notification` | `(args)` | — | [src](../../../core/tools/companion_push_tools.py#L41) |

## `core/tools/composites_tools.py`
_Composite tools interface — self-extension for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_composite_propose` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L21) |
| function | `_exec_composite_list` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L48) |
| function | `_exec_composite_get` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L62) |
| function | `_exec_composite_invoke` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L72) |
| function | `_exec_composite_approve` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L82) |
| function | `_exec_composite_revoke` | `(args)` | — | [src](../../../core/tools/composites_tools.py#L98) |

## `core/tools/copilot_tool_pruning.py`
_Contextual tool pruning for GitHub Copilot / OpenAI-compatible providers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_tool_usage` | `(tool_name)` | Record a tool call timestamp for recent-usage boost. Best-effort. | [src](../../../core/tools/copilot_tool_pruning.py#L180) |
| function | `_recent_tool_counts` | `()` | — | [src](../../../core/tools/copilot_tool_pruning.py#L186) |
| function | `_keyword_score_for_categories` | `(user_message)` | Return {tool_name: keyword_score} based on category keyword hits. | [src](../../../core/tools/copilot_tool_pruning.py#L196) |
| function | `select_tools_for_copilot` | `(tools, *, user_message=…, session_id=…, max_tools=…, stable_only=…)` | Return at most ``max_tools`` tool definitions, prioritised for this call. | [src](../../../core/tools/copilot_tool_pruning.py#L212) |
| function | `_stable_idx` | `(name)` | Deterministic tiebreak — lexicographic by name. | [src](../../../core/tools/copilot_tool_pruning.py#L292) |
| function | `select_tools_for_visible` | `(tools, *, user_message=…, session_id=…, max_tools=…)` | Provider-neutral pruning wrapper for the visible lane. | [src](../../../core/tools/copilot_tool_pruning.py#L297) |

## `core/tools/counterfactual_tools.py`
_Counterfactual reflection tools — read-only exposition._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_row_to_dict` | `(row)` | Convert a sqlite Row to a plain dict, decoding the JSON fields. | [src](../../../core/tools/counterfactual_tools.py#L32) |
| function | `_exec_list_counterfactuals` | `(args)` | List recent counterfactuals with optional filters. | [src](../../../core/tools/counterfactual_tools.py#L45) |
| function | `_exec_read_counterfactual` | `(args)` | Read a single counterfactual by cf_id, with its bound prediction status. | [src](../../../core/tools/counterfactual_tools.py#L136) |
| function | `_exec_counterfactual_summary` | `(args)` | Aggregate stats across recent counterfactuals — useful for self-review. | [src](../../../core/tools/counterfactual_tools.py#L202) |

## `core/tools/curiosity_tools.py`
_Curiosity-budget tools — Phase 1 (AGI track #6 Åben udforskning)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_curiosity_wrap` | `(*, action, args, underlying_call, underlying_args)` | Common path for all 9 curiosity-tool wrappers. | [src](../../../core/tools/curiosity_tools.py#L37) |
| function | `_direct_list_skills` | `(_args)` | List skill files in workspace/skills/. Read-only, lightweight. | [src](../../../core/tools/curiosity_tools.py#L105) |
| function | `_direct_list_tools` | `(_args)` | Return all currently-registered tool names + descriptions. | [src](../../../core/tools/curiosity_tools.py#L122) |
| function | `_direct_search_events` | `(args)` | SELECT from events table — read-only, parameterised, bounded. | [src](../../../core/tools/curiosity_tools.py#L137) |
| function | `_exec_curiosity_search_memory` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L176) |
| function | `_exec_curiosity_read_chronicles` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L186) |
| function | `_exec_curiosity_read_dreams` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L196) |
| function | `_exec_curiosity_read_model_config` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L206) |
| function | `_exec_curiosity_read_mood` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L216) |
| function | `_exec_curiosity_list_skills` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L226) |
| function | `_exec_curiosity_list_tools` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L235) |
| function | `_exec_curiosity_search_events` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L244) |
| function | `_exec_curiosity_search_sessions` | `(args)` | — | [src](../../../core/tools/curiosity_tools.py#L257) |
| function | `_make_def` | `(name, description, extra_props, required)` | — | [src](../../../core/tools/curiosity_tools.py#L293) |

## `core/tools/daemon_alert_tools.py`
_Daemon health alert — detects inactive/crashed daemons and sends notifications._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_alert_state` | `()` | — | [src](../../../core/tools/daemon_alert_tools.py#L14) |
| function | `_save_alert_state` | `(data)` | — | [src](../../../core/tools/daemon_alert_tools.py#L21) |
| function | `_hours_since` | `(iso_str)` | — | [src](../../../core/tools/daemon_alert_tools.py#L26) |
| function | `_exec_daemon_health_alert` | `(args)` | — | [src](../../../core/tools/daemon_alert_tools.py#L38) |
| function | `_exec_daemon_alert_status` | `(args)` | Show when each daemon was last alerted. | [src](../../../core/tools/daemon_alert_tools.py#L118) |
| function | `_exec_restart_overdue_daemons` | `(args)` | Restart daemons that have been overdue for more than threshold_minutes. | [src](../../../core/tools/daemon_alert_tools.py#L133) |

## `core/tools/decisions_tools.py`
_Behavioral decisions tools — Jarvis-facing closure of reflection→behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_decision_create` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L19) |
| function | `_exec_decision_review` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L40) |
| function | `_exec_decision_list` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L63) |
| function | `_exec_decision_get` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L85) |
| function | `_exec_decision_revoke` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L102) |

## `core/tools/file_tools_exec.py`
_Fil-tool executors (read_file / write_file / edit_file / read_tool_result /_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ws_read_text` | `(path)` | Læs encryption-aware (member .enc transparent). None hvis intet findes. | [src](../../../core/tools/file_tools_exec.py#L22) |
| function | `_ws_write_text` | `(path, content)` | Skriv encryption-aware (member → .enc når ENCRYPT_ON_WRITE on). | [src](../../../core/tools/file_tools_exec.py#L28) |
| function | `_ws_path_exists` | `(path)` | Eksistens encryption-aware: plaintext eller member .enc. | [src](../../../core/tools/file_tools_exec.py#L34) |
| function | `_record_active_file` | `(path, op, args)` | Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path`, så | [src](../../../core/tools/file_tools_exec.py#L42) |
| function | `_exec_read_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L53) |
| function | `_exec_read_tool_result` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L95) |
| function | `_exec_read_self_docs` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L115) |
| function | `_exec_write_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L131) |
| function | `_exec_edit_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L182) |

## `core/tools/forgetting_tools.py`
_Forgetting tools — Lag 11 self-track._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_release_memory` | `(args)` | Hard-delete a memory and leave an absence-marker. | [src](../../../core/tools/forgetting_tools.py#L15) |

## `core/tools/geolocation_tools.py`
_Native geolocation-tools til Jarvis — geocode, reverse-geocode, routing,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_http_get_json` | `(url, *, timeout=…, data=…)` | GET (eller POST hvis data) JSON med Jarvis User-Agent. Kaster ved fejl. | [src](../../../core/tools/geolocation_tools.py#L32) |
| function | `_throttle_nominatim` | `()` | — | [src](../../../core/tools/geolocation_tools.py#L39) |
| function | `geocode` | `(address)` | — | [src](../../../core/tools/geolocation_tools.py#L48) |
| function | `reverse_geocode` | `(lat, lon)` | — | [src](../../../core/tools/geolocation_tools.py#L70) |
| function | `_resolve_point` | `(point)` | Accepter enten 'adresse'-streng eller [lat, lon] / {lat,lon}. | [src](../../../core/tools/geolocation_tools.py#L99) |
| function | `route_directions` | `(from_, to, profile=…)` | — | [src](../../../core/tools/geolocation_tools.py#L118) |
| function | `_haversine_m` | `(lat1, lon1, lat2, lon2)` | — | [src](../../../core/tools/geolocation_tools.py#L173) |
| function | `nearby_search` | `(lat, lon, query, radius=…)` | — | [src](../../../core/tools/geolocation_tools.py#L182) |
| function | `_ip_location` | `()` | — | [src](../../../core/tools/geolocation_tools.py#L222) |
| function | `geolocation_lookup` | `(user_id=…)` | Find en brugers nuværende lokation. Læser delt presence-lokation først; | [src](../../../core/tools/geolocation_tools.py#L235) |
| function | `exec_geolocation_lookup` | `(args)` | — | [src](../../../core/tools/geolocation_tools.py#L261) |
| function | `exec_geocode` | `(args)` | — | [src](../../../core/tools/geolocation_tools.py#L272) |
| function | `exec_reverse_geocode` | `(args)` | — | [src](../../../core/tools/geolocation_tools.py#L276) |
| function | `exec_route_directions` | `(args)` | — | [src](../../../core/tools/geolocation_tools.py#L280) |
| function | `exec_nearby_search` | `(args)` | — | [src](../../../core/tools/geolocation_tools.py#L284) |

## `core/tools/github_tools.py`
_Git introspection tools — operates on the Jarvis v2 repo._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git` | `(args, cwd=…)` | — | [src](../../../core/tools/github_tools.py#L11) |
| function | `_exec_git_log` | `(args)` | — | [src](../../../core/tools/github_tools.py#L22) |
| function | `_exec_git_diff` | `(args)` | — | [src](../../../core/tools/github_tools.py#L32) |
| function | `_exec_git_status` | `(args)` | — | [src](../../../core/tools/github_tools.py#L46) |
| function | `_exec_git_branch` | `(args)` | — | [src](../../../core/tools/github_tools.py#L54) |
| function | `_exec_git_blame` | `(args)` | — | [src](../../../core/tools/github_tools.py#L65) |

## `core/tools/goals_tools.py`
_Long-horizon goals tools — Jarvis-facing CRUD for persistent goals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_tags` | `(raw)` | — | [src](../../../core/tools/goals_tools.py#L18) |
| function | `_exec_goal_create` | `(args)` | — | [src](../../../core/tools/goals_tools.py#L30) |
| function | `_exec_goal_update` | `(args)` | — | [src](../../../core/tools/goals_tools.py#L55) |
| function | `_exec_goal_list` | `(args)` | — | [src](../../../core/tools/goals_tools.py#L86) |
| function | `_exec_goal_get` | `(args)` | — | [src](../../../core/tools/goals_tools.py#L108) |

## `core/tools/health_monitor_tools.py`
_API health monitor tools — Jarvis can watch services and be notified of outages._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/tools/health_monitor_tools.py#L21) |
| function | `_save` | `(data)` | — | [src](../../../core/tools/health_monitor_tools.py#L28) |
| function | `_ping` | `(url, expected_status=…, timeout=…)` | — | [src](../../../core/tools/health_monitor_tools.py#L33) |
| function | `_record_check` | `(name, result)` | — | [src](../../../core/tools/health_monitor_tools.py#L62) |
| function | `_exec_health_check` | `(args)` | — | [src](../../../core/tools/health_monitor_tools.py#L79) |
| function | `_exec_health_register` | `(args)` | — | [src](../../../core/tools/health_monitor_tools.py#L115) |
| function | `_exec_health_status` | `(args)` | — | [src](../../../core/tools/health_monitor_tools.py#L139) |
| function | `_exec_health_history` | `(args)` | — | [src](../../../core/tools/health_monitor_tools.py#L169) |

## `core/tools/hf_inference_tools.py`
_Hugging Face Inference API tools — free-tier text-to-video + fallback image gen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hf_token` | `()` | Read HF token from runtime.json (never hardcoded). | [src](../../../core/tools/hf_inference_tools.py#L43) |
| function | `_auth_headers` | `()` | — | [src](../../../core/tools/hf_inference_tools.py#L55) |
| function | `_video_dir` | `()` | — | [src](../../../core/tools/hf_inference_tools.py#L66) |
| function | `_safe_filename` | `(prompt, gen_id, ext)` | — | [src](../../../core/tools/hf_inference_tools.py#L71) |
| function | `_write_sidecar` | `(path, metadata)` | — | [src](../../../core/tools/hf_inference_tools.py#L79) |
| function | `generate_video` | `(*, prompt, model=…, num_frames=…, guidance_scale=…, negative_prompt=…, num_inference_steps=…, seed=…, save_dir=…)` | Generate a video via HF serverless inference API. | [src](../../../core/tools/hf_inference_tools.py#L88) |
| function | `_exec_hf_text_to_video` | `(args)` | — | [src](../../../core/tools/hf_inference_tools.py#L221) |
| function | `_read_audio_bytes` | `(source)` | Read audio from a local path or HTTP(S) URL. Returns raw bytes. | [src](../../../core/tools/hf_inference_tools.py#L283) |
| function | `transcribe_audio` | `(*, audio_source, model=…, return_timestamps=…, language=…)` | Transcribe audio via HF Whisper. audio_source can be file path or URL. | [src](../../../core/tools/hf_inference_tools.py#L295) |
| function | `_exec_hf_transcribe_audio` | `(args)` | — | [src](../../../core/tools/hf_inference_tools.py#L391) |
| function | `semantic_similarity` | `(*, source, candidates, model=…)` | Compute cosine similarity between source and each candidate via HF. | [src](../../../core/tools/hf_inference_tools.py#L426) |
| function | `_exec_hf_embed` | `(args)` | Semantic similarity via HF sentence-similarity pipeline. | [src](../../../core/tools/hf_inference_tools.py#L503) |
| function | `zero_shot_classify` | `(*, text, labels, model=…, multi_label=…)` | Classify text against provided candidate labels via MNLI. | [src](../../../core/tools/hf_inference_tools.py#L552) |
| function | `_exec_hf_zero_shot_classify` | `(args)` | — | [src](../../../core/tools/hf_inference_tools.py#L620) |
| function | `_image_to_data_url` | `(source)` | Convert file path / URL / raw-bytes path to a data URL for VLM input. | [src](../../../core/tools/hf_inference_tools.py#L652) |
| function | `vision_analyze` | `(*, image_source, prompt=…, model=…, max_tokens=…)` | Analyze an image via a vision-language model. image_source = path or URL. | [src](../../../core/tools/hf_inference_tools.py#L666) |
| function | `_exec_hf_vision_analyze` | `(args)` | — | [src](../../../core/tools/hf_inference_tools.py#L729) |

## `core/tools/identity_pin_tools.py`
_Identity-pinning — pin a snippet from chronicle/MILESTONES/letters as_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/tools/identity_pin_tools.py#L39) |
| class | `IdentityPin` | `` | — | [src](../../../core/tools/identity_pin_tools.py#L44) |
| class | `IdentityPinsState` | `` | — | [src](../../../core/tools/identity_pin_tools.py#L54) |
| method | `IdentityPinsState.to_dict` | `(self)` | — | [src](../../../core/tools/identity_pin_tools.py#L58) |
| function | `_load` | `()` | — | [src](../../../core/tools/identity_pin_tools.py#L65) |
| function | `_save` | `(state)` | — | [src](../../../core/tools/identity_pin_tools.py#L78) |
| function | `list_pins` | `()` | — | [src](../../../core/tools/identity_pin_tools.py#L87) |
| function | `add_pin` | `(*, title, content, source=…, pinned_by=…)` | — | [src](../../../core/tools/identity_pin_tools.py#L92) |
| function | `remove_pin` | `(pin_id)` | — | [src](../../../core/tools/identity_pin_tools.py#L118) |
| function | `awareness_section` | `()` | Render the pin store as a prompt-awareness block. Used by | [src](../../../core/tools/identity_pin_tools.py#L129) |
| function | `_exec_pin_identity` | `(args)` | — | [src](../../../core/tools/identity_pin_tools.py#L145) |
| function | `_exec_list_identity_pins` | `(_args)` | — | [src](../../../core/tools/identity_pin_tools.py#L154) |
| function | `_exec_unpin_identity` | `(args)` | — | [src](../../../core/tools/identity_pin_tools.py#L158) |

## `core/tools/identity_sketch_tools.py`
_Tools for Persistent Identity Sketch — read and update._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_read_identity_sketch` | `(args)` | — | [src](../../../core/tools/identity_sketch_tools.py#L12) |
| function | `_exec_update_identity_sketch` | `(args)` | — | [src](../../../core/tools/identity_sketch_tools.py#L33) |

## `core/tools/jarvis_brain_tools.py`
_Visible Jarvis' værktøjer til hjernen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/tools/jarvis_brain_tools.py#L131) |
| function | `_day_key` | `(now)` | — | [src](../../../core/tools/jarvis_brain_tools.py#L135) |
| function | `_get_caps` | `()` | Read caps from RuntimeSettings if available, else defaults. | [src](../../../core/tools/jarvis_brain_tools.py#L139) |
| function | `_exec_remember_this` | `(args)` | Executor for remember_this tool. | [src](../../../core/tools/jarvis_brain_tools.py#L157) |
| function | `_exec_search_jarvis_brain` | `(args)` | Executor for search_jarvis_brain tool. | [src](../../../core/tools/jarvis_brain_tools.py#L187) |
| function | `_exec_read_brain_entry` | `(args)` | Executor for read_brain_entry tool. | [src](../../../core/tools/jarvis_brain_tools.py#L199) |
| function | `_exec_archive_brain_entry` | `(args)` | Executor for archive_brain_entry tool. | [src](../../../core/tools/jarvis_brain_tools.py#L204) |
| function | `_exec_adopt_brain_proposal` | `(args)` | Executor for adopt_brain_proposal tool. | [src](../../../core/tools/jarvis_brain_tools.py#L212) |
| function | `_exec_discard_brain_proposal` | `(args)` | Executor for discard_brain_proposal tool. | [src](../../../core/tools/jarvis_brain_tools.py#L220) |
| function | `remember_this` | `(*, kind, title, content, visibility, domain, session_id, turn_id, related=…, tags=…, source_url=…, source_chronicle=…, importance=…)` | Skriv en post i Jarvis' egen hjerne. | [src](../../../core/tools/jarvis_brain_tools.py#L233) |
| function | `search_jarvis_brain` | `(*, query, session_visibility_ceiling=…, kinds=…, limit=…, domain=…, tags=…, include_archived=…)` | Søg Jarvis' egen hjerne. Returnerer excerpts; brug read_brain_entry for fuld content. | [src](../../../core/tools/jarvis_brain_tools.py#L308) |
| function | `read_brain_entry` | `(entry_id)` | Hent fuld content for én brain entry. | [src](../../../core/tools/jarvis_brain_tools.py#L381) |
| function | `archive_brain_entry` | `(entry_id, *, reason=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/tools/jarvis_brain_tools.py#L408) |
| function | `adopt_brain_proposal` | `(proposal_id, edits=…)` | Flyt en pending proposal til den rigtige kind/-mappe og stempel som visible_jarvis. | [src](../../../core/tools/jarvis_brain_tools.py#L420) |
| function | `discard_brain_proposal` | `(proposal_id, *, reason=…)` | Slet en pending proposal og log reason. | [src](../../../core/tools/jarvis_brain_tools.py#L496) |

## `core/tools/jc_tool_catalog.py`
_Single source of truth for what jarvis-code (jc) presents as tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `alias_for` | `(name)` | runtime_ alias for a colliding tool name. | [src](../../../core/tools/jc_tool_catalog.py#L30) |
| function | `unalias` | `(name)` | Strip the runtime_ prefix iff it maps to a colliding tool; else unchanged. | [src](../../../core/tools/jc_tool_catalog.py#L35) |
| function | `is_runtime_alias` | `(name)` | True only for runtime_<one-of-the-four-colliding-tools>. | [src](../../../core/tools/jc_tool_catalog.py#L42) |
| function | `execution_location` | `(name)` | Hvor et tool med DETTE præsenterede navn eksekverer: | [src](../../../core/tools/jc_tool_catalog.py#L59) |
| function | `execution_map` | `(defs)` | Kortlæg en liste af tool-defs → {navn: execution_location}. Muterer IKKE | [src](../../../core/tools/jc_tool_catalog.py#L74) |
| function | `build_jc_catalog_text` | `()` | Jarvis-code-SPECIFIK toolbox-forklaring til prompten (Bjørn: der manglede en | [src](../../../core/tools/jc_tool_catalog.py#L95) |
| function | `_def_name` | `(d)` | — | [src](../../../core/tools/jc_tool_catalog.py#L120) |
| function | `_all_native_defs` | `(role)` | Full native tool defs for a role. Wrapped as a module function for test injection. | [src](../../../core/tools/jc_tool_catalog.py#L124) |
| function | `build_jc_catalog` | `(*, role, unlocked)` | Native-side tool defs jc should present (WITHOUT the 8 local client tools — | [src](../../../core/tools/jc_tool_catalog.py#L130) |

## `core/tools/mail_tools.py`
_Mail tools for Jarvis — jarvis@srvlab.dk_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_mail_config` | `()` | — | [src](../../../core/tools/mail_tools.py#L24) |
| function | `_exec_send_mail` | `(args)` | Send an email from jarvis@srvlab.dk. | [src](../../../core/tools/mail_tools.py#L27) |
| function | `_exec_read_mail` | `(args)` | Read recent emails from jarvis@srvlab.dk inbox. | [src](../../../core/tools/mail_tools.py#L70) |

## `core/tools/math_tools.py`
_Precise math and unit conversion tools using sympy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_calculate` | `(args)` | — | [src](../../../core/tools/math_tools.py#L37) |
| function | `_exec_unit_convert` | `(args)` | — | [src](../../../core/tools/math_tools.py#L50) |
| function | `_exec_percentage` | `(args)` | — | [src](../../../core/tools/math_tools.py#L80) |

## `core/tools/memory_tools.py`
_Memory duplicate-check and safe-write tools for MEMORY.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_memory_uid` | `(user_id=…)` | Hvilken brugers MEMORY.md skal vi røre. Best-effort: | [src](../../../core/tools/memory_tools.py#L11) |
| function | `_memory_md` | `(user_id=…)` | Brugerens MEMORY.md (workspace) — IKKE shared. Fald tilbage til shared | [src](../../../core/tools/memory_tools.py#L36) |
| function | `_read_memory` | `()` | — | [src](../../../core/tools/memory_tools.py#L53) |
| function | `_parse_headings` | `(text)` | — | [src](../../../core/tools/memory_tools.py#L60) |
| function | `_normalize` | `(heading)` | — | [src](../../../core/tools/memory_tools.py#L64) |
| function | `_exec_memory_check_duplicate` | `(args)` | — | [src](../../../core/tools/memory_tools.py#L68) |
| function | `_exec_memory_upsert_section` | `(args)` | Write or update a section in MEMORY.md. Replaces existing section if heading matches. | [src](../../../core/tools/memory_tools.py#L105) |
| function | `_exec_memory_list_headings` | `(args)` | — | [src](../../../core/tools/memory_tools.py#L179) |
| function | `_exec_memory_consolidate` | `(args)` | Find fuzzy-overlapping sections in MEMORY.md and propose/execute merges. | [src](../../../core/tools/memory_tools.py#L189) |

## `core/tools/memory_topic_tools.py`
_Kuraterede memory-topic-tools (spec 2026-07-10 Spec B)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_read_memory_topic` | `(args)` | Læs en kurateret memory-topic-fil (pull, LLM-led). Scoped til aktuel bruger. | [src](../../../core/tools/memory_topic_tools.py#L12) |
| function | `_exec_write_memory_topic` | `(args)` | Skriv/opdatér en kurateret memory-topic (streng bekraeftelse). Scoped til bruger. | [src](../../../core/tools/memory_topic_tools.py#L22) |

## `core/tools/meta_learning_tools.py`
_Meta-læring tools — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_phase1_enabled` | `()` | — | [src](../../../core/tools/meta_learning_tools.py#L23) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/tools/meta_learning_tools.py#L30) |
| function | `_exec_read_learning_memo` | `(args)` | Read full memo and acknowledge it. | [src](../../../core/tools/meta_learning_tools.py#L38) |
| function | `_exec_list_learning_memos` | `(args)` | — | [src](../../../core/tools/meta_learning_tools.py#L73) |
| function | `_exec_register_hypothesis` | `(args)` | Promote a memo hypothesis_candidate to an active tracked hypothesis. | [src](../../../core/tools/meta_learning_tools.py#L136) |
| function | `_exec_record_hypothesis_sample` | `(args)` | — | [src](../../../core/tools/meta_learning_tools.py#L154) |

## `core/tools/mic_listen_tool.py`
_Mic listen tool — Jarvis hears the room when he actively chooses to._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize_for_match` | `(text)` | Lowercase + replace punctuation with spaces + collapse whitespace. | [src](../../../core/tools/mic_listen_tool.py#L54) |
| function | `detect_trigger` | `(text)` | Return the action_key of a trigger matched in text, or None. | [src](../../../core/tools/mic_listen_tool.py#L66) |
| function | `_strip_trigger` | `(text, action_key)` | Remove the matched trigger phrase from the transcript so the remainder | [src](../../../core/tools/mic_listen_tool.py#L78) |
| function | `_route_trigger` | `(action_key, transcript, metadata)` | Route a detected trigger to the appropriate downstream system. | [src](../../../core/tools/mic_listen_tool.py#L102) |
| function | `_parec_binary` | `()` | — | [src](../../../core/tools/mic_listen_tool.py#L171) |
| function | `_recording_dir` | `()` | — | [src](../../../core/tools/mic_listen_tool.py#L178) |
| function | `_capture_parec` | `(duration)` | Capture from Logitech via parec. Returns raw s16le mono 16kHz bytes. | [src](../../../core/tools/mic_listen_tool.py#L185) |
| function | `_capture_sounddevice` | `(duration)` | Fallback capture via sounddevice (default input device). | [src](../../../core/tools/mic_listen_tool.py#L207) |
| function | `_capture_audio` | `(duration)` | Try parec first (NOS X500), then sounddevice fallback. | [src](../../../core/tools/mic_listen_tool.py#L225) |
| function | `_write_wav` | `(raw_pcm, path)` | Wrap raw s16le mono 16kHz bytes as a WAV file. | [src](../../../core/tools/mic_listen_tool.py#L236) |
| function | `_transcribe_hf` | `(wav_path, language)` | — | [src](../../../core/tools/mic_listen_tool.py#L247) |
| function | `_transcribe_local` | `(raw_pcm, language)` | — | [src](../../../core/tools/mic_listen_tool.py#L259) |
| function | `listen_and_transcribe` | `(*, duration=…, backend=…, language=…, save_recording=…)` | Active mic listen. Captures audio, transcribes, returns text. | [src](../../../core/tools/mic_listen_tool.py#L273) |
| function | `_exec_mic_listen` | `(args)` | — | [src](../../../core/tools/mic_listen_tool.py#L406) |

## `core/tools/monitor_tools.py`
_Tool wrappers for pinned monitor streams (monitor_streams)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_monitor_open` | `(args)` | — | [src](../../../core/tools/monitor_tools.py#L13) |
| function | `_exec_monitor_close` | `(args)` | — | [src](../../../core/tools/monitor_tools.py#L22) |
| function | `_exec_monitor_list` | `(args)` | — | [src](../../../core/tools/monitor_tools.py#L29) |

## `core/tools/native_tool_gate.py`
_Native-tool lås/lås-op — en runtime allowlist Bjørn styrer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `disabled_tools` | `()` | Sættet af låste native tool-navne. Fail-open → tom mængde. | [src](../../../core/tools/native_tool_gate.py#L16) |
| function | `is_disabled` | `(name)` | — | [src](../../../core/tools/native_tool_gate.py#L26) |
| function | `set_tool_disabled` | `(name, disabled)` | Lås (disabled=True) eller lås-op (False) et native tool. Returnerer det nye sæt. | [src](../../../core/tools/native_tool_gate.py#L30) |

## `core/tools/notification_tools.py`
_Native tools til notifikations-præferencer (notif-routing spec §4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_uid` | `(args)` | — | [src](../../../core/tools/notification_tools.py#L12) |
| function | `exec_get_notification_preferences` | `(args)` | — | [src](../../../core/tools/notification_tools.py#L23) |
| function | `exec_set_notification_preferences` | `(args)` | Args (alle valgfri): global, briefing, reminder, reach_out, team_invite, | [src](../../../core/tools/notification_tools.py#L36) |

## `core/tools/notify_out_tools.py`
_Unified outgoing notification pipeline — ntfy, Discord, Slack, generic webhooks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/tools/notify_out_tools.py#L14) |
| function | `_save` | `(data)` | — | [src](../../../core/tools/notify_out_tools.py#L21) |
| function | `_send_ntfy` | `(message, title, priority)` | — | [src](../../../core/tools/notify_out_tools.py#L28) |
| function | `_send_discord` | `(url, message, title)` | — | [src](../../../core/tools/notify_out_tools.py#L36) |
| function | `_send_slack` | `(url, message, title)` | — | [src](../../../core/tools/notify_out_tools.py#L49) |
| function | `_send_generic` | `(url, message, title, extra)` | — | [src](../../../core/tools/notify_out_tools.py#L63) |
| function | `_dispatch` | `(channel_cfg, message, title, priority)` | — | [src](../../../core/tools/notify_out_tools.py#L80) |
| function | `_exec_notify_out` | `(args)` | — | [src](../../../core/tools/notify_out_tools.py#L97) |
| function | `_exec_notify_channel_add` | `(args)` | — | [src](../../../core/tools/notify_out_tools.py#L133) |
| function | `_exec_notify_channel_list` | `(args)` | — | [src](../../../core/tools/notify_out_tools.py#L157) |
| function | `_exec_notify_channel_delete` | `(args)` | — | [src](../../../core/tools/notify_out_tools.py#L168) |

