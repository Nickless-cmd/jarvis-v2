# `core.tools.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/nudge_broend_tools.py`
_Nudge-brønd tools — Jarvis inspicerer, sender og afviser nudges._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_nudge_inspect` | `(args)` | Vis pending nudges. | [src](../../../core/tools/nudge_broend_tools.py#L12) |
| function | `_exec_nudge_send` | `(args)` | Send en nudge via notify_user (webchat/Discord). | [src](../../../core/tools/nudge_broend_tools.py#L31) |
| function | `_exec_nudge_dismiss` | `(args)` | Afvis ét eller alle nudges. | [src](../../../core/tools/nudge_broend_tools.py#L87) |

## `core/tools/nudge_tools.py`
_Tools Jarvis uses to surface or dismiss pending nudges._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_list_pending_nudges` | `(args)` | — | [src](../../../core/tools/nudge_tools.py#L22) |
| function | `_exec_surface_nudge` | `(args)` | — | [src](../../../core/tools/nudge_tools.py#L31) |
| function | `_exec_dismiss_nudge` | `(args)` | — | [src](../../../core/tools/nudge_tools.py#L43) |

## `core/tools/operator_bash_session.py`
_operator_bash_session — vedvarende-FØLELSE bash-session på operatorens maskine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/tools/operator_bash_session.py#L26) |
| function | `_q` | `(s)` | — | [src](../../../core/tools/operator_bash_session.py#L30) |
| function | `_reap` | `()` | — | [src](../../../core/tools/operator_bash_session.py#L34) |
| function | `_extract_cwd` | `(out)` | Pluk cwd-markøren ud af stdout og fjern den fra det Jarvis ser. | [src](../../../core/tools/operator_bash_session.py#L41) |
| function | `_exec_operator_bash_session_open` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L52) |
| function | `_exec_operator_bash_session_run` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L65) |
| function | `_exec_operator_bash_session_close` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L111) |
| function | `_exec_operator_bash_session_list` | `(_args)` | — | [src](../../../core/tools/operator_bash_session.py#L127) |

## `core/tools/operator_tools.py`
_Operator-side tools — execute on operator's desktop via JarvisX bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bridge_call` | `(*, tool, args, user_id, timeout_s=…)` | Common dispatch helper. Raises RuntimeError on bridge failure. | [src](../../../core/tools/operator_tools.py#L23) |
| function | `operator_read_file_async` | `(*, path, user_id, timeout_s=…)` | Read a file from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L45) |
| function | `operator_read_file` | `(*, path, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L58) |
| function | `operator_write_file_async` | `(*, path, content, user_id, timeout_s=…)` | Write content to a file on the operator's desktop. Creates parents | [src](../../../core/tools/operator_tools.py#L65) |
| function | `operator_edit_file_async` | `(*, path, old_string, new_string, replace_all=…, user_id, timeout_s=…)` | Find/replace in a file on the operator's desktop. Returns | [src](../../../core/tools/operator_tools.py#L87) |
| function | `operator_glob_async` | `(*, pattern, cwd=…, max_results=…, user_id, timeout_s=…)` | Find files matching a glob pattern on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L117) |
| function | `operator_grep_async` | `(*, pattern, path=…, glob=…, case_insensitive=…, max_results=…, user_id, timeout_s=…)` | Search for regex pattern in files on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L144) |
| function | `operator_list_dir_async` | `(*, path, user_id, timeout_s=…)` | List directory contents on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L175) |
| function | `operator_webfetch_async` | `(*, url, method=…, headers=…, body=…, timeout_s=…, user_id)` | Fetch a URL from the operator's local network via the bridge. | [src](../../../core/tools/operator_tools.py#L196) |
| function | `operator_bash_async` | `(*, command, cwd=…, timeout_s=…, user_id, skip_approval=…)` | Run a shell command on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L232) |
| function | `operator_screenshot_async` | `(*, user_id, display_id=…, save_path=…, format=…, jpeg_quality=…, timeout_s=…)` | Capture a screenshot of the operator's desktop. | [src](../../../core/tools/operator_tools.py#L272) |
| function | `operator_open_url_async` | `(*, url, user_id, skip_approval=…, timeout_s=…)` | Open a URL in the operator s default browser. Returns {approved, opened, url}. | [src](../../../core/tools/operator_tools.py#L332) |
| function | `operator_launch_app_async` | `(*, path, user_id, args=…, cwd=…, skip_approval=…, timeout_s=…)` | Launch an installed app on the operator s machine. | [src](../../../core/tools/operator_tools.py#L352) |
| function | `operator_mouse_move_async` | `(*, x, y, user_id, smooth=…, timeout_s=…)` | Move the operator s mouse cursor to (x, y) screen coordinates. | [src](../../../core/tools/operator_tools.py#L389) |
| function | `operator_mouse_click_async` | `(*, user_id, button=…, double=…, x=…, y=…, timeout_s=…)` | Click the mouse on the operator s desktop, optionally moving first. | [src](../../../core/tools/operator_tools.py#L410) |
| function | `operator_mouse_position_async` | `(*, user_id, timeout_s=…)` | Get the current mouse cursor position on the operator s desktop. | [src](../../../core/tools/operator_tools.py#L437) |
| function | `operator_keyboard_type_async` | `(*, text, user_id, delay_ms=…, timeout_s=…)` | Type a string into the operator s currently focused window. | [src](../../../core/tools/operator_tools.py#L455) |
| function | `operator_keyboard_press_async` | `(*, keys, user_id, timeout_s=…)` | Press a single key or a hotkey combination on the operator s keyboard. | [src](../../../core/tools/operator_tools.py#L478) |
| function | `operator_screen_size_async` | `(*, user_id, timeout_s=…)` | Get the operator s primary display size in pixels. | [src](../../../core/tools/operator_tools.py#L504) |
| function | `operator_browser_open_async` | `(*, url, user_id, wait_until=…, timeout_ms=…, timeout_s=…)` | Navigate the browser session to URL. First call opens browser. | [src](../../../core/tools/operator_tools.py#L522) |
| function | `operator_browser_get_text_async` | `(*, user_id, selector=…, max_chars=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L536) |
| function | `operator_browser_get_links_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L549) |
| function | `operator_browser_click_async` | `(*, selector, user_id, wait_navigation=…, wait_for_selector=…, timeout_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L558) |
| function | `operator_browser_type_async` | `(*, selector, text, user_id, clear_first=…, delay_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L576) |
| function | `operator_browser_screenshot_async` | `(*, user_id, full_page=…, format=…, jpeg_quality=…, timeout_s=…)` | Screenshot the active browser page. Decoded to a Jarvis-side temp file. | [src](../../../core/tools/operator_tools.py#L594) |
| function | `operator_browser_evaluate_async` | `(*, script, user_id, skip_approval=…, timeout_s=…)` | Run JS in the page context. Requires approval unless skip_approval. | [src](../../../core/tools/operator_tools.py#L626) |
| function | `operator_browser_status_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L640) |
| function | `operator_browser_close_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L649) |
| function | `operator_clipboard_read_async` | `(*, user_id, timeout_s=…)` | Return current clipboard text from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L661) |
| function | `operator_clipboard_write_async` | `(*, text, user_id, timeout_s=…)` | Replace the operator's clipboard with the given text. | [src](../../../core/tools/operator_tools.py#L679) |
| function | `operator_list_windows_async` | `(*, user_id, timeout_s=…)` | List open windows on the operator's desktop. Returns {windows: [{title, id}]}. | [src](../../../core/tools/operator_tools.py#L698) |
| function | `operator_focus_window_async` | `(*, user_id, title_substring=…, handle=…, timeout_s=…)` | Bring a window to the foreground by title substring or handle/id. | [src](../../../core/tools/operator_tools.py#L716) |
| function | `operator_mouse_scroll_async` | `(*, direction, user_id, amount=…, timeout_s=…)` | Scroll the mouse wheel in the given direction. | [src](../../../core/tools/operator_tools.py#L741) |
| function | `operator_mouse_drag_async` | `(*, from_x, from_y, to_x, to_y, user_id, button=…, timeout_s=…)` | Drag the mouse from (from_x, from_y) to (to_x, to_y). | [src](../../../core/tools/operator_tools.py#L761) |
| function | `operator_list_processes_async` | `(*, user_id, filter=…, timeout_s=…)` | List running processes on the operator's machine. Returns {processes: [{pid, name, cpu, memMB}]}. | [src](../../../core/tools/operator_tools.py#L790) |
| function | `operator_kill_process_async` | `(*, pid, user_id, skip_approval=…, timeout_s=…)` | Kill a process by PID. Requires operator approval unless skip_approval=True. | [src](../../../core/tools/operator_tools.py#L812) |
| function | `operator_speak_async` | `(*, text, user_id, voice=…, rate=…, timeout_s=…)` | Say text aloud on the operator's machine via TTS (espeak-ng / SAPI). | [src](../../../core/tools/operator_tools.py#L832) |
| function | `operator_screenshot_window_async` | `(*, user_id, title_substring=…, handle=…, save_path=…, timeout_s=…)` | Capture a specific window on the operator's desktop. Returns base64 PNG or saves to path. | [src](../../../core/tools/operator_tools.py#L856) |
| function | `operator_find_image_async` | `(*, template_path, user_id, confidence=…, timeout_s=…)` | Template-match a small image inside the current screen. Returns {found, x, y, confidence}. | [src](../../../core/tools/operator_tools.py#L884) |
| function | `operator_ocr_region_async` | `(*, x, y, width, height, user_id, lang=…, timeout_s=…)` | Extract text from a screen region using Tesseract OCR. | [src](../../../core/tools/operator_tools.py#L904) |
| function | `operator_notify_async` | `(*, title, body, user_id, icon=…, timeout_s=…)` | Show an OS notification toast on the operator's machine via Electron Notification. | [src](../../../core/tools/operator_tools.py#L933) |
| function | `operator_watch_folder_async` | `(*, path, user_id, recursive=…, debounce_ms=…, timeout_s=…)` | Start watching a folder for changes on the operator's machine. Returns {watcher_id}. | [src](../../../core/tools/operator_tools.py#L957) |
| function | `operator_unwatch_folder_async` | `(*, watcher_id, user_id, timeout_s=…)` | Stop a folder watcher by watcher_id. Returns {stopped: true}. | [src](../../../core/tools/operator_tools.py#L975) |
| function | `operator_watch_events_async` | `(*, watcher_id, user_id, max=…, timeout_s=…)` | Poll buffered filesystem events for a watcher. Returns {events: [...]} and clears buffer. | [src](../../../core/tools/operator_tools.py#L991) |
| function | `operator_record_audio_async` | `(*, duration_s, user_id, output_path=…, device=…, skip_approval=…, timeout_s=…)` | Record N seconds of microphone audio on the operator's machine. Requires approval. | [src](../../../core/tools/operator_tools.py#L1011) |
| function | `operator_reminder_async` | `(*, when, message, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1042) |
| function | `operator_wakeup_async` | `(*, when, message=…, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1055) |
| function | `operator_scheduled_list_async` | `(*, user_id, kind=…, include_fired=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1070) |
| function | `operator_scheduled_cancel_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1083) |
| function | `operator_process_spawn_async` | `(*, cmd, user_id, cwd=…, label=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1096) |
| function | `operator_process_status_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1111) |
| function | `operator_process_output_async` | `(*, id, user_id, since_offset=…, max_bytes=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1121) |
| function | `operator_process_kill_async` | `(*, id, user_id, signal=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1133) |
| function | `operator_process_list_async` | `(*, user_id, include_finished=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1143) |
| function | `_op_sess_now` | `()` | — | [src](../../../core/tools/operator_tools.py#L1180) |
| function | `_op_sess_reap` | `()` | — | [src](../../../core/tools/operator_tools.py#L1184) |
| function | `_op_sess_owner_denied` | `()` | Denial reason if the caller is a real non-owner role, else None. | [src](../../../core/tools/operator_tools.py#L1192) |
| function | `_op_sess_user_id` | `(args)` | — | [src](../../../core/tools/operator_tools.py#L1208) |
| function | `_op_dispatch_bash` | `(command, *, user_id, cwd, timeout_s)` | Dispatch a command via the bridge with skip_approval=True (reuses the | [src](../../../core/tools/operator_tools.py#L1213) |
| function | `_exec_operator_session_open` | `(args)` | Open a persistent operator session. Owner-only. Probes the bridge with a | [src](../../../core/tools/operator_tools.py#L1227) |
| function | `_exec_operator_session_run` | `(args)` | Run a command in an operator session via the bridge WITHOUT an approval | [src](../../../core/tools/operator_tools.py#L1247) |
| function | `_exec_operator_session_close` | `(args)` | Close an operator session (owner-only). | [src](../../../core/tools/operator_tools.py#L1288) |

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

## `core/tools/py_source_guard.py`
_py_source_guard — vaern mod en tilbagevendende LLM-skrive-artefakt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `guard_py_escapes` | `(content, path)` | Returnér (evt. rettet content, advarsels-note eller None). Se modul-docstring. | [src](../../../core/tools/py_source_guard.py#L22) |

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
| function | `_canonicalize_workspace_target` | `(target)` | If target's basename is a canonical workspace file, force it to the | [src](../../../core/tools/simple_tools.py#L649) |
| function | `_emit_security_check` | `(hit, *, target)` | Self-safe audit-emit: et deny/destructive bæres nu med sit nummererede | [src](../../../core/tools/simple_tools.py#L745) |
| function | `classify_command` | `(command)` | Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L759) |
| function | `classify_file_write` | `(path)` | Classify a file write: 'auto', 'approval', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L848) |
| function | `execute_tool` | `(name, arguments)` | Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1). | [src](../../../core/tools/simple_tools.py#L870) |
| function | `_execute_tool_impl` | `(name, arguments)` | Execute a tool call and return the result. | [src](../../../core/tools/simple_tools.py#L943) |
| function | `execute_tool_force` | `(name, arguments)` | Execute tool bypassing approval checks. Only call for user-approved requests. | [src](../../../core/tools/simple_tools.py#L1083) |
| function | `_record_tool_outcome_memory` | `(name, arguments, result, *, mode)` | — | [src](../../../core/tools/simple_tools.py#L1164) |
| function | `_force_write_file` | `(args)` | Write file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1815) |
| function | `_force_edit_file` | `(args)` | Edit file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1839) |
| function | `_force_bash` | `(args)` | Run bash command bypassing approval (blocked still blocked). | [src](../../../core/tools/simple_tools.py#L1869) |
| function | `_force_operator_bash` | `(args)` | Kør operator_bash direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1901) |
| function | `_force_operator_open_url` | `(args)` | Åbn URL direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1906) |
| function | `_force_operator_launch_app` | `(args)` | Start program direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1911) |
| function | `_force_operator_browser_evaluate` | `(args)` | Kør browser-JavaScript direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1916) |
| function | `_force_operator_kill_process` | `(args)` | Afslut proces direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1921) |
| function | `_force_operator_record_audio` | `(args)` | Optag lyd direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1926) |
| function | `get_tool_definitions` | `(role=…, scope=…)` | Return Ollama-compatible tool definitions, filtered by role + scope. | [src](../../../core/tools/simple_tools.py#L1987) |
| function | `_verify_hint_for` | `(tool, result)` | Build a brief, contextual verify-hint to attach to a mutation's result. | [src](../../../core/tools/simple_tools.py#L2025) |
| function | `_json_safe_default` | `(o)` | json.dumps default= — GARANTERER at serialisering af et tool-resultat | [src](../../../core/tools/simple_tools.py#L2074) |
| function | `format_tool_result_for_model` | `(name, result)` | Format a tool result as text for the model's context. | [src](../../../core/tools/simple_tools.py#L2090) |

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
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _operator_user_id). | [src](../../../core/tools/simple_tools_native.py#L40) |
| function | `_operator_user_id` | `(args)` | Facade → simple_tools._operator_user_id (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_native.py#L46) |
| function | `_exec_list_initiatives` | `(_args)` | Return current initiative queue state. | [src](../../../core/tools/simple_tools_native.py#L51) |
| function | `_exec_push_initiative` | `(args)` | Push a new initiative to the queue. | [src](../../../core/tools/simple_tools_native.py#L105) |
| function | `_exec_read_model_config` | `(_args)` | Read the current model configuration for all runtime lanes. | [src](../../../core/tools/simple_tools_native.py#L131) |
| function | `_exec_read_mood` | `(_args)` | Read current affective/mood state. | [src](../../../core/tools/simple_tools_native.py#L188) |
| function | `_exec_adjust_mood` | `(args)` | Adjust affective parameters in the personality vector. | [src](../../../core/tools/simple_tools_native.py#L239) |
| function | `_exec_resurface_old_memory` | `(args)` | Pick a stale MEMORY.md heading and return it for the model to consider. | [src](../../../core/tools/simple_tools_native.py#L311) |
| function | `_exec_memory_graph_query` | `(args)` | Look up an entity in the memory graph and return its relations. | [src](../../../core/tools/simple_tools_native.py#L337) |
| function | `_exec_search_memory` | `(args)` | Semantic search across workspace memory files. | [src](../../../core/tools/simple_tools_native.py#L369) |
| function | `_exec_propose_source_edit` | `(args)` | File a source-edit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L413) |
| function | `_exec_propose_git_commit` | `(args)` | File a git-commit autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L488) |
| function | `_exec_approve_proposal` | `(args)` | Approve and execute a pending autonomy proposal. | [src](../../../core/tools/simple_tools_native.py#L564) |
| function | `_exec_list_proposals` | `(_args)` | List pending autonomy proposals. | [src](../../../core/tools/simple_tools_native.py#L590) |
| function | `_exec_schedule_task` | `(args)` | Schedule a task to fire after delay_minutes. | [src](../../../core/tools/simple_tools_native.py#L619) |
| function | `_exec_list_scheduled_tasks` | `(_args)` | List scheduled tasks (pending + recently fired). | [src](../../../core/tools/simple_tools_native.py#L646) |
| function | `_exec_cancel_task` | `(args)` | Cancel a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L678) |
| function | `_exec_edit_task` | `(args)` | Edit a pending scheduled task. | [src](../../../core/tools/simple_tools_native.py#L693) |
| function | `_exec_read_chronicles` | `(args)` | Return recent cognitive chronicle entries. | [src](../../../core/tools/simple_tools_native.py#L714) |
| function | `_exec_read_dreams` | `(args)` | Return active dream hypothesis signals and adoption candidates. | [src](../../../core/tools/simple_tools_native.py#L760) |
| function | `_exec_notify_user` | `(args)` | Push a proactive message to webchat, Discord, or both. | [src](../../../core/tools/simple_tools_native.py#L826) |
| function | `_exec_read_self_state` | `(_args)` | Return Jarvis's current internal cadence/emotional state. | [src](../../../core/tools/simple_tools_native.py#L885) |
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L971) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1016) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1040) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1061) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1078) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1095) |
| function | `_exec_send_ntfy` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1135) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1151) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json. | [src](../../../core/tools/simple_tools_native.py#L1166) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1210) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1244) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1438) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1508) |
| function | `_exec_convene_council` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1625) |
| function | `_exec_quick_council_check` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1685) |
| function | `_exec_spawn_agent_task` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1722) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1770) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1796) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1820) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1852) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L1867) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1872) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L1886) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1891) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1897) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L1917) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1922) |
| function | `_exec_recall_council_conclusions` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1962) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L1991) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2062) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2092) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2120) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2148) |
| function | `_exec_look_around` | `(args)` | Take a webcam snapshot now and describe what's there via VLM. | [src](../../../core/tools/simple_tools_native.py#L2172) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2201) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2254) |
| function | `_json_safe_cell` | `(v)` | Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8 | [src](../../../core/tools/simple_tools_native.py#L2267) |
| function | `_exec_db_query` | `(args)` | Run a read-only SELECT query against Jarvis' database. | [src](../../../core/tools/simple_tools_native.py#L2286) |
| function | `_exec_compact_context_session` | `(session_id)` | Run session compact for session_id. Returns CompactResult or None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2349) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2381) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2400) |
| function | `_exec_publish_file` | `(args)` | Copy or create a file in ~/.jarvis-v2/files/ and return a download URL. | [src](../../../core/tools/simple_tools_native.py#L2421) |
| function | `_tool_load_more_tools` | `(arguments)` | Resolve which tools to add to the next round. Logs to DB + events. | [src](../../../core/tools/simple_tools_native.py#L2491) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2582) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2591) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2600) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2608) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2615) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2636) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2642) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2649) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2655) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2662) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2668) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2690) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2709) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2731) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2737) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2742) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2747) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2752) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2757) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2762) |

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
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L600) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L616) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L637) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L647) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L666) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L683) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L693) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L703) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L716) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L726) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L752) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L768) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L789) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L804) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L839) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L859) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L880) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L898) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L924) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L944) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L962) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L977) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L990) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1008) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1021) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1039) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1056) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1070) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1091) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1110) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1125) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1142) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1183) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1201) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1218) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1228) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1247) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1268) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1284) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1314) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1324) |

## `core/tools/simple_tools_web.py`
_Web/search/system-info tool executors for Jarvis' native lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_glob_to_regex` | `(pattern)` | Oversæt et glob-mønster (POSIX-relativt) til en regex med KORREKT sti-semantik: | [src](../../../core/tools/simple_tools_web.py#L55) |
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn). | [src](../../../core/tools/simple_tools_web.py#L76) |
| function | `_cached_web_search_fn` | `(*, query, max_results, fetch_fn)` | Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_web.py#L82) |
| function | `_exec_search` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L87) |
| function | `_exec_find_files` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L145) |
| function | `_get_or_open_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L239) |
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L263) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L269) |
| function | `_html_to_text` | `(raw)` | Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift). | [src](../../../core/tools/simple_tools_web.py#L382) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L420) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L481) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L492) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L502) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L537) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L544) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L554) |
| function | `_exec_get_weather` | `(args)` | Current weather via OpenWeatherMap. | [src](../../../core/tools/simple_tools_web.py#L566) |
| function | `_exec_get_exchange_rate` | `(args)` | Currency exchange rates via exchangerate.host. | [src](../../../core/tools/simple_tools_web.py#L600) |
| function | `_exec_get_news` | `(args)` | Recent news via NewsAPI. | [src](../../../core/tools/simple_tools_web.py#L627) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L663) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L762) |
| function | `_exec_wolfram_query` | `(args)` | Precise answers via Wolfram Alpha Short Answers API. | [src](../../../core/tools/simple_tools_web.py#L832) |

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
| function | `_exec_smart_compact` | `(args)` | Compact context with a smarter prompt that preserves decisions/facts. | [src](../../../core/tools/smart_compact_tools.py#L60) |
| function | `_exec_context_size_check` | `(args)` | Estimate current context size and advise whether compaction is needed. | [src](../../../core/tools/smart_compact_tools.py#L114) |

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

