# `core.tools.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/__init__.py`

_(no top-level classes or functions)_

## `core/tools/agent_contract_tools.py`
_Modelvendte agent-vaerktoejer over agent-contract-v1 (leverance F2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fn` | `(name, description, properties, required)` | — | [src](../../../core/tools/agent_contract_tools.py#L33) |
| function | `contract_tool_names_advertised` | `()` | De navne der skal fastnaeles i Jarvis' flade - tom naar kapabiliteten er slukket. | [src](../../../core/tools/agent_contract_tools.py#L116) |
| function | `hidden_contract_tools` | `()` | De rene kontrakt-vaerktoejer der SKAL skjules lige nu: alle naar motoren er slukket | [src](../../../core/tools/agent_contract_tools.py#L127) |
| function | `_principal` | `(args)` | (ejer, session, parent-run). Ejeren er den autentificerede kontekst - IKKE et argument. | [src](../../../core/tools/agent_contract_tools.py#L135) |
| function | `_svc` | `()` | — | [src](../../../core/tools/agent_contract_tools.py#L146) |
| function | `_exec_dispatch_agent` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L151) |
| function | `_exec_followup_agent` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L171) |
| function | `_exec_wait_agents` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L181) |
| function | `_exec_interrupt_agent` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L194) |
| function | `_exec_close_agent` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L201) |
| function | `_is_contract_bound` | `(agent_id, owner)` | — | [src](../../../core/tools/agent_contract_tools.py#L207) |
| function | `_exec_send_message_to_agent` | `(args)` | Kontrakt-udgaven for bundne agenter; den gamle (inline) for resten. | [src](../../../core/tools/agent_contract_tools.py#L215) |
| function | `_exec_list_agents` | `(args)` | Naar motoren er taendt: ejerens kontrakt-agenter (+ de gamle under `legacy`). | [src](../../../core/tools/agent_contract_tools.py#L227) |
| function | `_exec_integrate_agent_work` | `(args)` | — | [src](../../../core/tools/agent_contract_tools.py#L240) |

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

## `core/tools/agent_worktree_tools.py`
_Agent-kun-vaerktoejer til at skrive i agentens EGET worktree (agent-contract-v1 C5b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_worktree_for` | `(args)` | (worktree, fejl). Agenten og dens assignment slaas op af serveren. | [src](../../../core/tools/agent_worktree_tools.py#L44) |
| function | `_fail` | `(exc)` | — | [src](../../../core/tools/agent_worktree_tools.py#L61) |
| function | `_exec_wt_bash` | `(args)` | — | [src](../../../core/tools/agent_worktree_tools.py#L67) |
| function | `_exec_wt_write_file` | `(args)` | — | [src](../../../core/tools/agent_worktree_tools.py#L80) |

## `core/tools/app_control_tool.py`
_request_app_action tool (spec 2026-06-15) — Jarvis foreslår mode/permission-skift._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_request_app_action` | `(args)` | — | [src](../../../core/tools/app_control_tool.py#L25) |
| function | `_exec_open_ui_panel` | `(args)` | — | [src](../../../core/tools/app_control_tool.py#L51) |
| function | `build_app_action_event` | `(result, *, user_message, session_id)` | Ren helper: hvis et tool-resultat bærer en app_action-markør, byg payloaden | [src](../../../core/tools/app_control_tool.py#L85) |

## `core/tools/approval_rollout_gate.py`
_Et nyt godkendelses-vaerktoej maa ikke rulles ud foer broen baerer — K4._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `bridge_active` | `()` | Haandhaever godkendelses-broen — eller koerer den stadig i skygge? | [src](../../../core/tools/approval_rollout_gate.py#L53) |
| function | `may_advertise` | `(tool_name)` | Maa vaerktoejet annonceres til modellen? (ja/nej, grund). | [src](../../../core/tools/approval_rollout_gate.py#L67) |
| function | `blocked` | `()` | Hvilke vaerktoejer holdes tilbage lige nu? Tom liste er det normale. | [src](../../../core/tools/approval_rollout_gate.py#L89) |
| function | `debt` | `()` | Gaelden: godkendelses-vaerktoejer der lever paa den gamle inline-sti. | [src](../../../core/tools/approval_rollout_gate.py#L96) |

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
| class | `_Session` | `` | — | [src](../../../core/tools/bash_session.py#L74) |
| method | `_Session.__init__` | `(self, session_id)` | — | [src](../../../core/tools/bash_session.py#L75) |
| method | `_Session._drain_pending` | `(self, timeout)` | — | [src](../../../core/tools/bash_session.py#L133) |
| method | `_Session.alive` | `(self)` | — | [src](../../../core/tools/bash_session.py#L144) |
| method | `_Session._resync` | `(self, probe_timeout=…)` | Bryd shell'en ud af en hængende/continuation-tilstand og bekræft at den svarer. | [src](../../../core/tools/bash_session.py#L151) |
| method | `_Session.run` | `(self, command, timeout=…)` | — | [src](../../../core/tools/bash_session.py#L199) |
| method | `_Session.terminate` | `(self)` | Dræb shellen UDEN at tage sessionens lås. | [src](../../../core/tools/bash_session.py#L312) |
| method | `_Session.close` | `(self)` | Dræb shellen og luk pty'en. Vender tilbage selv om en kommando kører. | [src](../../../core/tools/bash_session.py#L336) |
| function | `_list_row` | `(sid, sess, now)` | Én række i `list`-svaret. | [src](../../../core/tools/bash_session.py#L360) |
| function | `_decode` | `(buf)` | — | [src](../../../core/tools/bash_session.py#L391) |
| function | `_daemon_main` | `()` | Singleton bash-session daemon. Listens on the Unix socket, owns sessions. | [src](../../../core/tools/bash_session.py#L403) |
| function | `_send` | `(client, payload)` | — | [src](../../../core/tools/bash_session.py#L575) |
| function | `_read_daemon_pid` | `()` | Læs daemonens PID fra pid-filen. None hvis den ikke findes/er ulaesbar. | [src](../../../core/tools/bash_session.py#L587) |
| function | `_pid_is_our_daemon` | `(pid)` | Kill-guard: kun en ÆGTE bash-session-daemon. En genbrugt PID må aldrig rammes. | [src](../../../core/tools/bash_session.py#L595) |
| function | `_kill_daemon` | `(pid)` | SIGTERM, derefter SIGKILL. Gør intet hvis PID'en ikke er vores daemon. | [src](../../../core/tools/bash_session.py#L606) |
| function | `_force_restart_daemon` | `()` | Dræb en hængende daemon og start en frisk. True hvis den svarer bagefter. | [src](../../../core/tools/bash_session.py#L628) |
| function | `_ensure_daemon_running` | `()` | Return True if a reachable daemon exists. Spawn one if not. | [src](../../../core/tools/bash_session.py#L647) |
| function | `_spawn_daemon` | `()` | Fork a detached daemon process running _daemon_main(). | [src](../../../core/tools/bash_session.py#L695) |
| function | `_ping_daemon` | `()` | — | [src](../../../core/tools/bash_session.py#L711) |
| function | `_client_call_once` | `(payload, timeout=…)` | Ét IPC-forsøg mod daemonen. Ingen selv-helbredelse — se _client_call. | [src](../../../core/tools/bash_session.py#L731) |
| function | `_client_call` | `(payload, timeout=…)` | Send ét kald til daemonen — og helbred den selv hvis den er hængt. | [src](../../../core/tools/bash_session.py#L758) |
| function | `_exec_bash_session_open` | `(args)` | — | [src](../../../core/tools/bash_session.py#L795) |
| function | `_open_arbejdssession` | `()` | Aabn den DELTE arbejds-shell — den `bash`-vaerktoejet genbruger. | [src](../../../core/tools/bash_session.py#L800) |
| function | `_exec_bash_session_run` | `(args)` | — | [src](../../../core/tools/bash_session.py#L810) |
| function | `_exec_bash_session_close` | `(args)` | — | [src](../../../core/tools/bash_session.py#L832) |
| function | `_exec_bash_session_list` | `(_args)` | — | [src](../../../core/tools/bash_session.py#L839) |

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
| function | `_incident_counts` | `(snap)` | Sande incident-tal til status-svaret. | [src](../../../core/tools/central_query_tool.py#L31) |
| function | `_envelope` | `(status, action, data, error, source, t0, **meta_extra)` | — | [src](../../../core/tools/central_query_tool.py#L59) |
| function | `_paginate` | `(items, offset, limit)` | Returnér en side + pagina-meta. ALDRIG trunkér en linje midt over: vi dropper | [src](../../../core/tools/central_query_tool.py#L67) |
| function | `_nerve_klass` | `(nerve)` | NerveSpec.klass for en nerve (til sikker toggle). Defaulter SECURITY-SIKKERT: | [src](../../../core/tools/central_query_tool.py#L85) |
| function | `central_query` | `(args)` | Eneste indgang. Returnerer ALTID en envelope (status ok/error). Kaster aldrig. | [src](../../../core/tools/central_query_tool.py#L103) |

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

## `core/tools/composer_suggest_tools.py`
_Jarvis' eget forslag i komponisten — den næste OPGAVE, i Bjørns ord._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_suggest_next_task` | `(args)` | — | [src](../../../core/tools/composer_suggest_tools.py#L44) |

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
| function | `record_tool_usage` | `(tool_name)` | Record a tool call timestamp for recent-usage boost. Best-effort. | [src](../../../core/tools/copilot_tool_pruning.py#L368) |
| function | `_recent_tool_counts` | `()` | — | [src](../../../core/tools/copilot_tool_pruning.py#L374) |
| function | `_keyword_score_for_categories` | `(user_message)` | Return {tool_name: keyword_score} based on category keyword hits. | [src](../../../core/tools/copilot_tool_pruning.py#L384) |
| function | `select_tools_for_copilot` | `(tools, *, user_message=…, session_id=…, max_tools=…, stable_only=…)` | Return at most ``max_tools`` tool definitions, prioritised for this call. | [src](../../../core/tools/copilot_tool_pruning.py#L400) |
| function | `agent_contract_pinned` | `()` | De syv agent-vaerktoejer, FASTE i Jarvis' flade naar motoren er taendt (§7.3). | [src](../../../core/tools/copilot_tool_pruning.py#L495) |
| function | `_faestn_kraevede` | `(selected_names, seen, by_name, max_tools, user_message)` | Saet de vaerktoejer ind der SKAL overleve kappen, og skaer resten. | [src](../../../core/tools/copilot_tool_pruning.py#L505) |
| function | `spor_skill_match` | `(user_message)` | Spor at et skill matchede. Fæstner INGENTING — og det er hele rettelsen. | [src](../../../core/tools/copilot_tool_pruning.py#L541) |
| function | `_stable_idx` | `(name)` | Deterministic tiebreak — lexicographic by name. | [src](../../../core/tools/copilot_tool_pruning.py#L595) |
| function | `select_tools_for_visible` | `(tools, *, user_message=…, session_id=…, max_tools=…)` | Provider-neutral pruning wrapper for the visible lane. | [src](../../../core/tools/copilot_tool_pruning.py#L600) |

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

## `core/tools/db_query_tool.py`
_`db_query` — laeseadgang til Jarvis' database, med skemaet i fejlen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_json_safe_cell` | `(v)` | Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8 | [src](../../../core/tools/db_query_tool.py#L46) |
| function | `_tabeller` | `(conn)` | — | [src](../../../core/tools/db_query_tool.py#L65) |
| function | `_kolonner` | `(conn, tabel)` | — | [src](../../../core/tools/db_query_tool.py#L72) |
| function | `skema_hint` | `(conn, fejl, sql)` | De navne der FINDES, givet en fejl om et navn der ikke gjorde. | [src](../../../core/tools/db_query_tool.py#L81) |
| function | `_exec_db_query` | `(args)` | Run a read-only SELECT query against Jarvis' database. | [src](../../../core/tools/db_query_tool.py#L129) |

## `core/tools/decisions_tools.py`
_Behavioral decisions tools — Jarvis-facing closure of reflection→behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_decision_create` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L19) |
| function | `_exec_decision_review` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L40) |
| function | `_exec_decision_list` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L63) |
| function | `_exec_decision_get` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L85) |
| function | `_exec_decision_update` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L102) |
| function | `_exec_decision_revoke` | `(args)` | — | [src](../../../core/tools/decisions_tools.py#L135) |

## `core/tools/desk_browser_tools.py`
_Jarvis' EGEN browser inde i desk — otte værktøjer over broen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bro` | `(*, tool, args, user_id, timeout_s)` | Kald desk-broen. Returnerer den UDPAKKEDE resultat-værdi. | [src](../../../core/tools/desk_browser_tools.py#L45) |
| function | `_koer` | `(tool, args, runtime_args, *, timeout_s)` | Fælles vej: find brugeren, kald broen i hoved-loopet, svar ærligt. | [src](../../../core/tools/desk_browser_tools.py#L54) |
| function | `_tab_id` | `(args)` | `tab_id` er valgfri; udelades den, rammer broen den AKTIVE fane. | [src](../../../core/tools/desk_browser_tools.py#L72) |
| function | `_vis_panelet` | `(runtime_args)` | Bed desk om at vise browser-panelet — uden at vente på svaret. | [src](../../../core/tools/desk_browser_tools.py#L83) |
| function | `_gem_billede` | `(resultat)` | Skriv broens base64-billede til en fil og svar med STIEN. | [src](../../../core/tools/desk_browser_tools.py#L106) |
| function | `_exec_jarvis_browser_open` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L135) |
| function | `_exec_jarvis_browser_navigate` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L145) |
| function | `_exec_jarvis_browser_read` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L153) |
| function | `_exec_jarvis_browser_click` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L163) |
| function | `_exec_jarvis_browser_type` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L172) |
| function | `_exec_jarvis_browser_screenshot` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L180) |
| function | `_exec_jarvis_browser_tabs` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L192) |
| function | `_exec_jarvis_browser_close` | `(args)` | — | [src](../../../core/tools/desk_browser_tools.py#L196) |
| function | `_nr` | `(desc)` | — | [src](../../../core/tools/desk_browser_tools.py#L207) |

## `core/tools/desk_view_tools.py`
_Jarvis styrer desk-vinduet indefra — Claude Desktops `ccd_view`-værktøjer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session` | `()` | — | [src](../../../core/tools/desk_view_tools.py#L31) |
| function | `_spoerg` | `(op, args)` | — | [src](../../../core/tools/desk_view_tools.py#L39) |
| function | `_runtime` | `(args)` | De `_`-nøgler runtime sprøjter ind (samtalens id) — skal med videre. | [src](../../../core/tools/desk_view_tools.py#L58) |
| function | `_exec_get_layout` | `(args)` | — | [src](../../../core/tools/desk_view_tools.py#L63) |
| function | `_exec_show_pane` | `(args)` | — | [src](../../../core/tools/desk_view_tools.py#L67) |
| function | `_exec_close_pane` | `(args)` | — | [src](../../../core/tools/desk_view_tools.py#L81) |

## `core/tools/file_tools_exec.py`
_Fil-tool executors (read_file / write_file / edit_file / read_tool_result /_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ws_read_text` | `(path)` | Læs encryption-aware (member .enc transparent). None hvis intet findes. | [src](../../../core/tools/file_tools_exec.py#L22) |
| function | `_ws_write_text` | `(path, content)` | Skriv encryption-aware (member → .enc når ENCRYPT_ON_WRITE on). | [src](../../../core/tools/file_tools_exec.py#L28) |
| function | `_ws_path_exists` | `(path)` | Eksistens encryption-aware: plaintext eller member .enc. | [src](../../../core/tools/file_tools_exec.py#L34) |
| function | `_record_active_file` | `(path, op, args)` | Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path`, så | [src](../../../core/tools/file_tools_exec.py#L42) |
| function | `_safe_readback` | `(path)` | Læs filen tilbage — selv-sikker. None = den kunne ikke læses. | [src](../../../core/tools/file_tools_exec.py#L73) |
| function | `_disk_readback` | `(path, *, start_line, span=…, mark=…)` | Nummereret udsnit af filen som den står på disken EFTER skrivningen. | [src](../../../core/tools/file_tools_exec.py#L86) |
| function | `_exec_read_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L112) |
| function | `_exec_read_tool_result` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L154) |
| function | `_exec_read_self_docs` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L177) |
| function | `_exec_write_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L193) |
| function | `linjetal` | `(gammel, ny, erstatninger)` | (tilføjet, fjernet) for én erstatning ganget op — git-diff-semantik. | [src](../../../core/tools/file_tools_exec.py#L280) |
| function | `_exec_edit_file` | `(args)` | — | [src](../../../core/tools/file_tools_exec.py#L312) |

## `core/tools/force_handlers.py`
_Force-handlere — værktøjer der kører EFTER et menneske har godkendt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_operator_bash` | `(args)` | Sen import: operator_bash_session traekker paa broen, som traekker paa | [src](../../../core/tools/force_handlers.py#L51) |
| function | `_exec_bash` | `(args)` | Facade → ``simple_tools._exec_bash`` (honorér test-patch-søm). | [src](../../../core/tools/force_handlers.py#L58) |
| function | `_canonicalize_workspace_target` | `(target)` | Sen import: bor i simple_tools, som importerer DENNE fil. En import paa | [src](../../../core/tools/force_handlers.py#L70) |
| function | `_force_write_file` | `(args)` | Write file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/force_handlers.py#L77) |
| function | `_force_edit_file` | `(args)` | Edit file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/force_handlers.py#L101) |
| function | `_force_bash` | `(args)` | Kør bash uden godkendelses-prompt. Blokerede kommandoer stoppes stadig. | [src](../../../core/tools/force_handlers.py#L131) |
| function | `_force_operator_bash` | `(args)` | Kør operator_bash direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L161) |
| function | `_force_operator_open_url` | `(args)` | Åbn URL direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L166) |
| function | `_force_stripe_create_issuing_card` | `(args)` | Opret kortet EFTER at Bjørn har sagt ja. Uden denne ville godkendelsen | [src](../../../core/tools/force_handlers.py#L180) |
| function | `_force_gmail_send` | `(args)` | Send mailen direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L187) |
| function | `_force_calendar_create_event` | `(args)` | Opret begivenheden direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L192) |
| function | `_force_docs_append` | `(args)` | Skriv i dokumentet direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L197) |
| function | `_force_sheets_write` | `(args)` | Skriv i regnearket direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L202) |
| function | `_force_operator_write_file` | `(args)` | Skriv filen paa operatoerens maskine direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L207) |
| function | `_force_operator_edit_file` | `(args)` | Redigér filen paa operatoerens maskine direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L212) |
| function | `_force_operator_launch_app` | `(args)` | Start program direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L217) |
| function | `_force_operator_browser_evaluate` | `(args)` | Kør browser-JavaScript direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L222) |
| function | `_force_operator_kill_process` | `(args)` | Afslut proces direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L227) |
| function | `_force_operator_record_audio` | `(args)` | Optag lyd direkte efter chat-godkendelse. | [src](../../../core/tools/force_handlers.py#L232) |

## `core/tools/forgetting_tools.py`
_Forgetting tools — Lag 11 self-track._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_release_memory` | `(args)` | Hard-delete a memory and leave an absence-marker. | [src](../../../core/tools/forgetting_tools.py#L15) |

## `core/tools/fuzzy_edit.py`
_Fuzzy tekst-match til fil-redigering — porteret fra jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exact_find` | `(content, old_text)` | All exact-match spans of old_text in content. [] if none. | [src](../../../core/tools/fuzzy_edit.py#L33) |
| function | `_whitespace_fuzzy_find` | `(content, old_text)` | Match old_text against content with ALL whitespace (on BOTH sides) | [src](../../../core/tools/fuzzy_edit.py#L48) |
| function | `_indent_insensitive_find` | `(content, old_text)` | Match old_text LINE-BY-LINE ignoring leading indent — each content | [src](../../../core/tools/fuzzy_edit.py#L81) |
| function | `_reapply_indent` | `(new_text, indent)` | Re-apply `indent` as a leading prefix on every non-blank line of | [src](../../../core/tools/fuzzy_edit.py#L109) |
| function | `_difflib_fuzzy_find` | `(content, old_text, threshold=…)` | Best-matching line-window in content vs. old_text, by | [src](../../../core/tools/fuzzy_edit.py#L126) |
| function | `resolve_edit` | `(content, old_text, new_text, replace_all=…)` | Loes et redigerings-oenske mod filens FAKTISKE indhold. | [src](../../../core/tools/fuzzy_edit.py#L159) |

## `core/tools/gate_override_tools.py`
_Gate-override-værktøj — Jarvis' eksplicitte svar på en gate der tog fejl._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_override_gate` | `(args)` | — | [src](../../../core/tools/gate_override_tools.py#L15) |
| function | `_exec_gate_override_status` | `(_args)` | — | [src](../../../core/tools/gate_override_tools.py#L30) |

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

## `core/tools/graf_tools.py`
_`vis_graf` — en graf der faktisk kan SES, i baade desk og mobil._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_graf_dir` | `()` | — | [src](../../../core/tools/graf_tools.py#L44) |
| function | `_exec_vis_graf` | `(args)` | Tegn en graf og laeg den i traaden. Kaster aldrig. | [src](../../../core/tools/graf_tools.py#L49) |

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

## `core/tools/inbox_tools.py`
_De tre indbakke-værktøjer: `inbox`, `inbox_done`, `inbox_drop`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger` | `()` | Den autentificerede bruger. Tom streng når ingen er bundet. | [src](../../../core/tools/inbox_tools.py#L107) |
| function | `_tekst` | `(v)` | Visningen som ÉN tekst. Tomme sektioner udelades helt. | [src](../../../core/tools/inbox_tools.py#L148) |
| function | `_exec_inbox` | `(arguments=…, **_kw)` | Hele visningen. Læser; skriver intet. | [src](../../../core/tools/inbox_tools.py#L170) |
| function | `_exec_inbox_done` | `(arguments=…, **_kw)` | — | [src](../../../core/tools/inbox_tools.py#L193) |
| function | `_exec_inbox_drop` | `(arguments=…, **_kw)` | — | [src](../../../core/tools/inbox_tools.py#L213) |

