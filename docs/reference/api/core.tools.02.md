# `core.tools.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/tools/operator_background.py`
_Baggrunds-shells paa operatoerens maskine — paritet med jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_new_id` | `()` | — | [src](../../../core/tools/operator_background.py#L35) |
| function | `_valid` | `(shell_id)` | Kun vores egne id'er. Uden det kunne et id smugle sti-fragmenter ind i | [src](../../../core/tools/operator_background.py#L39) |
| function | `start_async` | `(*, command, user_id, cwd=…, timeout_s=…)` | Start en loesrevet baggrunds-shell. Returnerer {shell_id, pid}. | [src](../../../core/tools/operator_background.py#L45) |
| function | `read_async` | `(*, shell_id, user_id, since=…, timeout_s=…)` | Laes NYT output siden byte-offset `since`. | [src](../../../core/tools/operator_background.py#L73) |
| function | `kill_async` | `(*, shell_id, user_id, timeout_s=…)` | Draeb en baggrunds-shell. Idempotent: en allerede doed shell er ikke en fejl. | [src](../../../core/tools/operator_background.py#L113) |

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
| function | `_render_text` | `(inner)` | Læsbart output som en `text`-nøgle — og dét er ikke kosmetik. | [src](../../../core/tools/operator_bash_session.py#L119) |
| function | `_exec_operator_bash_session_close` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L158) |
| function | `_exec_operator_bash_session_list` | `(_args)` | — | [src](../../../core/tools/operator_bash_session.py#L174) |

## `core/tools/operator_tools.py`
_Operator-side tools — execute on operator's desktop via JarvisX bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bridge_call` | `(*, tool, args, user_id, timeout_s=…)` | Common dispatch helper. Raises RuntimeError on bridge failure. | [src](../../../core/tools/operator_tools.py#L23) |
| function | `operator_read_file_async` | `(*, path, user_id, timeout_s=…)` | Read a file from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L45) |
| function | `operator_read_file` | `(*, path, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L58) |
| function | `operator_write_file_async` | `(*, path, content, user_id, timeout_s=…)` | Write content to a file on the operator's desktop. Creates parents | [src](../../../core/tools/operator_tools.py#L65) |
| function | `operator_edit_file_async` | `(*, path, old_string, new_string, replace_all=…, user_id, timeout_s=…)` | Find/replace in a file on the operator's desktop. Returns | [src](../../../core/tools/operator_tools.py#L87) |
| function | `operator_multi_edit_async` | `(*, path, edits, user_id, timeout_s=…)` | Flere redigeringer i ÉN fil, ét bro-kald. Findes ikke i jarvis-code's | [src](../../../core/tools/operator_tools.py#L142) |
| function | `operator_multi_edit` | `(*, path, edits, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L196) |
| function | `operator_glob_async` | `(*, pattern, cwd=…, max_results=…, user_id, timeout_s=…)` | Find files matching a glob pattern on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L205) |
| function | `operator_grep_async` | `(*, pattern, path=…, glob=…, case_insensitive=…, max_results=…, user_id, timeout_s=…)` | Search for regex pattern in files on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L232) |
| function | `operator_list_dir_async` | `(*, path, user_id, timeout_s=…)` | List directory contents on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L263) |
| function | `operator_webfetch_async` | `(*, url, method=…, headers=…, body=…, timeout_s=…, user_id)` | Fetch a URL from the operator's local network via the bridge. | [src](../../../core/tools/operator_tools.py#L284) |
| function | `operator_bash_async` | `(*, command, cwd=…, timeout_s=…, user_id, skip_approval=…)` | Run a shell command on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L320) |
| function | `operator_screenshot_async` | `(*, user_id, display_id=…, save_path=…, format=…, jpeg_quality=…, timeout_s=…)` | Capture a screenshot of the operator's desktop. | [src](../../../core/tools/operator_tools.py#L360) |
| function | `operator_open_url_async` | `(*, url, user_id, skip_approval=…, timeout_s=…)` | Open a URL in the operator s default browser. Returns {approved, opened, url}. | [src](../../../core/tools/operator_tools.py#L420) |
| function | `operator_launch_app_async` | `(*, path, user_id, args=…, cwd=…, skip_approval=…, timeout_s=…)` | Launch an installed app on the operator s machine. | [src](../../../core/tools/operator_tools.py#L440) |
| function | `operator_mouse_move_async` | `(*, x, y, user_id, smooth=…, timeout_s=…)` | Move the operator s mouse cursor to (x, y) screen coordinates. | [src](../../../core/tools/operator_tools.py#L477) |
| function | `operator_mouse_click_async` | `(*, user_id, button=…, double=…, x=…, y=…, timeout_s=…)` | Click the mouse on the operator s desktop, optionally moving first. | [src](../../../core/tools/operator_tools.py#L498) |
| function | `operator_mouse_position_async` | `(*, user_id, timeout_s=…)` | Get the current mouse cursor position on the operator s desktop. | [src](../../../core/tools/operator_tools.py#L525) |
| function | `operator_keyboard_type_async` | `(*, text, user_id, delay_ms=…, timeout_s=…)` | Type a string into the operator s currently focused window. | [src](../../../core/tools/operator_tools.py#L543) |
| function | `operator_keyboard_press_async` | `(*, keys, user_id, timeout_s=…)` | Press a single key or a hotkey combination on the operator s keyboard. | [src](../../../core/tools/operator_tools.py#L566) |
| function | `operator_screen_size_async` | `(*, user_id, timeout_s=…)` | Get the operator s primary display size in pixels. | [src](../../../core/tools/operator_tools.py#L592) |
| function | `operator_browser_open_async` | `(*, url, user_id, wait_until=…, timeout_ms=…, timeout_s=…)` | Navigate the browser session to URL. First call opens browser. | [src](../../../core/tools/operator_tools.py#L610) |
| function | `operator_browser_get_text_async` | `(*, user_id, selector=…, max_chars=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L624) |
| function | `operator_browser_get_links_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L637) |
| function | `operator_browser_click_async` | `(*, selector, user_id, wait_navigation=…, wait_for_selector=…, timeout_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L646) |
| function | `operator_browser_type_async` | `(*, selector, text, user_id, clear_first=…, delay_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L664) |
| function | `operator_browser_screenshot_async` | `(*, user_id, full_page=…, format=…, jpeg_quality=…, timeout_s=…)` | Screenshot the active browser page. Decoded to a Jarvis-side temp file. | [src](../../../core/tools/operator_tools.py#L682) |
| function | `operator_browser_evaluate_async` | `(*, script, user_id, skip_approval=…, timeout_s=…)` | Run JS in the page context. Requires approval unless skip_approval. | [src](../../../core/tools/operator_tools.py#L714) |
| function | `operator_browser_status_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L728) |
| function | `operator_browser_close_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L737) |
| function | `operator_clipboard_read_async` | `(*, user_id, timeout_s=…)` | Return current clipboard text from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L749) |
| function | `operator_clipboard_write_async` | `(*, text, user_id, timeout_s=…)` | Replace the operator's clipboard with the given text. | [src](../../../core/tools/operator_tools.py#L767) |
| function | `operator_list_windows_async` | `(*, user_id, timeout_s=…)` | List open windows on the operator's desktop. Returns {windows: [{title, id}]}. | [src](../../../core/tools/operator_tools.py#L786) |
| function | `operator_focus_window_async` | `(*, user_id, title_substring=…, handle=…, timeout_s=…)` | Bring a window to the foreground by title substring or handle/id. | [src](../../../core/tools/operator_tools.py#L804) |
| function | `operator_mouse_scroll_async` | `(*, direction, user_id, amount=…, timeout_s=…)` | Scroll the mouse wheel in the given direction. | [src](../../../core/tools/operator_tools.py#L829) |
| function | `operator_mouse_drag_async` | `(*, from_x, from_y, to_x, to_y, user_id, button=…, timeout_s=…)` | Drag the mouse from (from_x, from_y) to (to_x, to_y). | [src](../../../core/tools/operator_tools.py#L849) |
| function | `operator_list_processes_async` | `(*, user_id, filter=…, timeout_s=…)` | List running processes on the operator's machine. Returns {processes: [{pid, name, cpu, memMB}]}. | [src](../../../core/tools/operator_tools.py#L878) |
| function | `operator_kill_process_async` | `(*, pid, user_id, skip_approval=…, timeout_s=…)` | Kill a process by PID. Requires operator approval unless skip_approval=True. | [src](../../../core/tools/operator_tools.py#L900) |
| function | `operator_speak_async` | `(*, text, user_id, voice=…, rate=…, timeout_s=…)` | Say text aloud on the operator's machine via TTS (espeak-ng / SAPI). | [src](../../../core/tools/operator_tools.py#L920) |
| function | `operator_screenshot_window_async` | `(*, user_id, title_substring=…, handle=…, save_path=…, timeout_s=…)` | Capture a specific window on the operator's desktop. Returns base64 PNG or saves to path. | [src](../../../core/tools/operator_tools.py#L944) |
| function | `operator_find_image_async` | `(*, template_path, user_id, confidence=…, timeout_s=…)` | Template-match a small image inside the current screen. Returns {found, x, y, confidence}. | [src](../../../core/tools/operator_tools.py#L972) |
| function | `operator_ocr_region_async` | `(*, x, y, width, height, user_id, lang=…, timeout_s=…)` | Extract text from a screen region using Tesseract OCR. | [src](../../../core/tools/operator_tools.py#L992) |
| function | `operator_notify_async` | `(*, title, body, user_id, icon=…, timeout_s=…)` | Show an OS notification toast on the operator's machine via Electron Notification. | [src](../../../core/tools/operator_tools.py#L1021) |
| function | `operator_watch_folder_async` | `(*, path, user_id, recursive=…, debounce_ms=…, timeout_s=…)` | Start watching a folder for changes on the operator's machine. Returns {watcher_id}. | [src](../../../core/tools/operator_tools.py#L1045) |
| function | `operator_unwatch_folder_async` | `(*, watcher_id, user_id, timeout_s=…)` | Stop a folder watcher by watcher_id. Returns {stopped: true}. | [src](../../../core/tools/operator_tools.py#L1063) |
| function | `operator_watch_events_async` | `(*, watcher_id, user_id, max=…, timeout_s=…)` | Poll buffered filesystem events for a watcher. Returns {events: [...]} and clears buffer. | [src](../../../core/tools/operator_tools.py#L1079) |
| function | `operator_record_audio_async` | `(*, duration_s, user_id, output_path=…, device=…, skip_approval=…, timeout_s=…)` | Record N seconds of microphone audio on the operator's machine. Requires approval. | [src](../../../core/tools/operator_tools.py#L1099) |
| function | `operator_reminder_async` | `(*, when, message, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1130) |
| function | `operator_wakeup_async` | `(*, when, message=…, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1143) |
| function | `operator_scheduled_list_async` | `(*, user_id, kind=…, include_fired=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1158) |
| function | `operator_scheduled_cancel_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1171) |
| function | `operator_process_spawn_async` | `(*, cmd, user_id, cwd=…, label=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1184) |
| function | `operator_process_status_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1199) |
| function | `operator_process_output_async` | `(*, id, user_id, since_offset=…, max_bytes=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1209) |
| function | `operator_process_kill_async` | `(*, id, user_id, signal=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1221) |
| function | `operator_process_list_async` | `(*, user_id, include_finished=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1231) |
| function | `_op_sess_now` | `()` | — | [src](../../../core/tools/operator_tools.py#L1268) |
| function | `_op_sess_reap` | `()` | — | [src](../../../core/tools/operator_tools.py#L1272) |
| function | `_op_sess_owner_denied` | `()` | Denial reason if the caller is a real non-owner role, else None. | [src](../../../core/tools/operator_tools.py#L1280) |
| function | `_op_sess_user_id` | `(args)` | — | [src](../../../core/tools/operator_tools.py#L1296) |
| function | `_op_dispatch_bash` | `(command, *, user_id, cwd, timeout_s)` | Dispatch a command via the bridge with skip_approval=True (reuses the | [src](../../../core/tools/operator_tools.py#L1301) |
| function | `_exec_operator_session_open` | `(args)` | Open a persistent operator session. Owner-only. Probes the bridge with a | [src](../../../core/tools/operator_tools.py#L1315) |
| function | `_exec_operator_session_run` | `(args)` | Run a command in an operator session via the bridge WITHOUT an approval | [src](../../../core/tools/operator_tools.py#L1335) |
| function | `_exec_operator_session_close` | `(args)` | Close an operator session (owner-only). | [src](../../../core/tools/operator_tools.py#L1376) |

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
| function | `_keyword_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L103) |
| function | `_embed_query` | `(text)` | Embed text via Ollama. Returns None if unavailable. | [src](../../../core/tools/session_search.py#L144) |
| function | `_cosine_similarity` | `(a, b)` | — | [src](../../../core/tools/session_search.py#L163) |
| function | `_semantic_search` | `(query, *, channel, since, until, limit, user_id=…)` | — | [src](../../../core/tools/session_search.py#L173) |
| function | `_merge_results` | `(keyword_results, semantic_results, limit)` | — | [src](../../../core/tools/session_search.py#L230) |
| function | `exec_search_sessions` | `(args)` | — | [src](../../../core/tools/session_search.py#L254) |

## `core/tools/simple_tools.py`
_Simple, general-purpose tools for Jarvis visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `canonical_identity_file_path` | `(name)` | Den ENE fil `name` bor i — samme opslag som prompten bruger til at LÆSE. | [src](../../../core/tools/simple_tools.py#L642) |
| function | `_canonicalize_workspace_target` | `(target)` | If target's basename is a canonical workspace file, force it to the | [src](../../../core/tools/simple_tools.py#L671) |
| function | `_emit_security_check` | `(hit, *, target)` | Self-safe audit-emit: et deny/destructive bæres nu med sit nummererede | [src](../../../core/tools/simple_tools.py#L767) |
| function | `classify_command` | `(command)` | Classify a shell command: 'auto', 'approval', 'destructive', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L781) |
| function | `classify_file_write` | `(path)` | Classify a file write: 'auto', 'approval', or 'blocked'. | [src](../../../core/tools/simple_tools.py#L870) |
| function | `execute_tool` | `(name, arguments)` | Execute a tool call — Tools-cluster (Den Intelligente Central, Phase 1). | [src](../../../core/tools/simple_tools.py#L892) |
| function | `_execute_tool_impl` | `(name, arguments)` | Execute a tool call and return the result. | [src](../../../core/tools/simple_tools.py#L965) |
| function | `execute_tool_force` | `(name, arguments)` | Execute tool bypassing approval checks. Only call for user-approved requests. | [src](../../../core/tools/simple_tools.py#L1105) |
| function | `_record_tool_outcome_memory` | `(name, arguments, result, *, mode)` | — | [src](../../../core/tools/simple_tools.py#L1186) |
| function | `_force_write_file` | `(args)` | Write file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1843) |
| function | `_force_edit_file` | `(args)` | Edit file bypassing approval (blocked paths still blocked). | [src](../../../core/tools/simple_tools.py#L1867) |
| function | `_force_bash` | `(args)` | Run bash command bypassing approval (blocked still blocked). | [src](../../../core/tools/simple_tools.py#L1897) |
| function | `_force_operator_bash` | `(args)` | Kør operator_bash direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1930) |
| function | `_force_operator_open_url` | `(args)` | Åbn URL direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1935) |
| function | `_force_operator_launch_app` | `(args)` | Start program direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1940) |
| function | `_force_operator_browser_evaluate` | `(args)` | Kør browser-JavaScript direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1945) |
| function | `_force_operator_kill_process` | `(args)` | Afslut proces direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1950) |
| function | `_force_operator_record_audio` | `(args)` | Optag lyd direkte efter chat-godkendelse. | [src](../../../core/tools/simple_tools.py#L1955) |
| function | `get_tool_definitions` | `(role=…, scope=…)` | Return Ollama-compatible tool definitions, filtered by role + scope. | [src](../../../core/tools/simple_tools.py#L2016) |
| function | `_verify_hint_for` | `(tool, result)` | Build a brief, contextual verify-hint to attach to a mutation's result. | [src](../../../core/tools/simple_tools.py#L2054) |
| function | `_json_safe_default` | `(o)` | json.dumps default= — GARANTERER at serialisering af et tool-resultat | [src](../../../core/tools/simple_tools.py#L2103) |
| function | `format_tool_result_for_model` | `(name, result, *, clip=…)` | Format a tool result as text for the model's context. | [src](../../../core/tools/simple_tools.py#L2119) |

## `core/tools/simple_tools_definitions.py`
_Tool definitions catalog for Jarvis' visible-lane tools._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_til_openai_form` | `(td)` | Anthropic-formet definition → OpenAI-formet. Andet passerer urørt. | [src](../../../core/tools/simple_tools_definitions.py#L3482) |
| function | `_ensret_tool_definitions` | `(defs)` | — | [src](../../../core/tools/simple_tools_definitions.py#L3499) |

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
| function | `_exec_read_self_state` | `(_args)` | Return Jarvis's current internal cadence/emotional state. | [src](../../../core/tools/simple_tools_native.py#L883) |
| function | `_exec_heartbeat_status` | `(_args)` | Return heartbeat scheduler status and recent tick history. | [src](../../../core/tools/simple_tools_native.py#L969) |
| function | `_exec_trigger_heartbeat_tick` | `(_args)` | Trigger an on-demand heartbeat tick. | [src](../../../core/tools/simple_tools_native.py#L1014) |
| function | `_exec_send_telegram_message` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1038) |
| function | `_exec_read_attachment` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1059) |
| function | `_exec_list_attachments` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1101) |
| function | `_exec_query_why` | `(args)` | Query the causal graph for why an event happened. | [src](../../../core/tools/simple_tools_native.py#L1118) |
| function | `_exec_send_ntfy` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1158) |
| function | `_exec_send_webchat_message` | `(args)` | Inject a message into the active webchat session. | [src](../../../core/tools/simple_tools_native.py#L1174) |
| function | `_exec_send_discord_dm` | `(args)` | Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json. | [src](../../../core/tools/simple_tools_native.py#L1189) |
| function | `_exec_discord_status` | `(_args)` | Return Discord gateway connection state and activity summary. | [src](../../../core/tools/simple_tools_native.py#L1233) |
| function | `_exec_discord_channel` | `(args)` | Interact with Discord guild channels: search, fetch, or send. | [src](../../../core/tools/simple_tools_native.py#L1267) |
| function | `_exec_search_chat_history` | `(args)` | Search previous chat sessions for messages matching a query. | [src](../../../core/tools/simple_tools_native.py#L1461) |
| function | `_exec_home_assistant` | `(args)` | Control and read Home Assistant devices via REST API. | [src](../../../core/tools/simple_tools_native.py#L1531) |
| function | `_exec_convene_council` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1648) |
| function | `_exec_quick_council_check` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1708) |
| function | `_exec_spawn_agent_task` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1745) |
| function | `_exec_explore` | `(args)` | Bred, laese-kun undersoegelse — ét spoergsmaal ind, fund ud. | [src](../../../core/tools/simple_tools_native.py#L1801) |
| function | `_exec_send_message_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1874) |
| function | `_exec_list_agents` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1903) |
| function | `_exec_relay_to_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1927) |
| function | `_exec_cancel_agent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1962) |
| function | `_exec_daemon_status` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L1977) |
| function | `_exec_control_daemon` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L1986) |
| function | `_exec_list_signal_surfaces` | `(_args)` | — | [src](../../../core/tools/simple_tools_native.py#L2000) |
| function | `_exec_read_signal_surface` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2005) |
| function | `_exec_eventbus_recent` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2011) |
| function | `_is_sensitive_setting` | `(key)` | — | [src](../../../core/tools/simple_tools_native.py#L2032) |
| function | `_exec_update_setting` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2037) |
| function | `_exec_recall_council_conclusions` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2077) |
| function | `_exec_internal_api` | `(args)` | Call Jarvis' own internal API (same-process HTTP, no external auth). | [src](../../../core/tools/simple_tools_native.py#L2106) |
| function | `_exec_my_project_status` | `(args)` | Return your current personal project state, including any pending proposal. | [src](../../../core/tools/simple_tools_native.py#L2177) |
| function | `_exec_my_project_journal_write` | `(args)` | Write a journal entry in your current personal project. No approval needed. | [src](../../../core/tools/simple_tools_native.py#L2207) |
| function | `_exec_my_project_accept_proposal` | `(args)` | Accept the latest pending proposal as your personal project. | [src](../../../core/tools/simple_tools_native.py#L2235) |
| function | `_exec_my_project_declare` | `(args)` | Freely declare a new personal project (bypassing proposal flow). | [src](../../../core/tools/simple_tools_native.py#L2263) |
| function | `_exec_look_around` | `(args)` | Look through one of the house cameras now and describe what's there. | [src](../../../core/tools/simple_tools_native.py#L2287) |
| function | `_exec_deep_analyze` | `(args)` | Run scoped deep analysis of the codebase. | [src](../../../core/tools/simple_tools_native.py#L2320) |
| function | `_exec_central_query` | `(args)` | Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool — | [src](../../../core/tools/simple_tools_native.py#L2373) |
| function | `_exec_interlanguage_protocol` | `(args)` | Eksportér inter-sprog-protokollen (designets fase 5 — bæring ved modelskift). | [src](../../../core/tools/simple_tools_native.py#L2386) |
| function | `_json_safe_cell` | `(v)` | Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8 | [src](../../../core/tools/simple_tools_native.py#L2401) |
| function | `_exec_db_query` | `(args)` | Run a read-only SELECT query against Jarvis' database. | [src](../../../core/tools/simple_tools_native.py#L2420) |
| function | `_exec_compact_context_session` | `(session_id)` | Run session compact for session_id. Returns CompactResult or None (monkeypatchable). | [src](../../../core/tools/simple_tools_native.py#L2486) |
| function | `_exec_compact_context` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2518) |
| function | `_exec_queue_followup` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2537) |
| function | `_exec_publish_file` | `(args)` | Copy or create a file in ~/.jarvis-v2/files/ and return a download URL. | [src](../../../core/tools/simple_tools_native.py#L2558) |
| function | `_exec_github_list_issues` | `(args)` | List GitHub-issues via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2626) |
| function | `_exec_github_list_prs` | `(args)` | List GitHub pull requests via brugerens EGEN connector-token (Spor A). | [src](../../../core/tools/simple_tools_native.py#L2635) |
| function | `_exec_gmail_search` | `(args)` | Søg i brugerens Gmail via deres EGEN Google-connector-token. | [src](../../../core/tools/simple_tools_native.py#L2644) |
| function | `_exec_gmail_list` | `(args)` | List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token. | [src](../../../core/tools/simple_tools_native.py#L2652) |
| function | `_exec_gmail_send` | `(args)` | Send mail på brugerens vegne — bag approval-kort (som operator-tools). | [src](../../../core/tools/simple_tools_native.py#L2659) |
| function | `_exec_calendar_list_events` | `(args)` | List kommende begivenheder i brugerens primære Google Calendar. | [src](../../../core/tools/simple_tools_native.py#L2680) |
| function | `_exec_drive_search` | `(args)` | Søg/list filer i brugerens Google Drive. | [src](../../../core/tools/simple_tools_native.py#L2686) |
| function | `_exec_docs_read` | `(args)` | Læs tekst fra et Google Docs-dokument. | [src](../../../core/tools/simple_tools_native.py#L2693) |
| function | `_exec_sheets_read` | `(args)` | Læs celler fra et Google Sheets-regneark. | [src](../../../core/tools/simple_tools_native.py#L2699) |
| function | `_exec_slides_read` | `(args)` | Læs titler og tekst fra et Google Slides-show. | [src](../../../core/tools/simple_tools_native.py#L2706) |
| function | `_exec_calendar_create_event` | `(args)` | Opret kalender-aftale — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2712) |
| function | `_exec_docs_append` | `(args)` | Tilføj tekst til et Google-dokument — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2734) |
| function | `_exec_sheets_write` | `(args)` | Skriv celler i et Google Sheets-regneark — bag approval-kort. | [src](../../../core/tools/simple_tools_native.py#L2753) |
| function | `_exec_pdf_read` | `(args)` | Læs/ekstraher tekst fra en PDF (sti eller URL). | [src](../../../core/tools/simple_tools_native.py#L2775) |
| function | `_exec_note_add` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2781) |
| function | `_exec_note_list` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2786) |
| function | `_exec_note_search` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2791) |
| function | `_exec_note_delete` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2796) |
| function | `_exec_hf_search_models` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2801) |
| function | `_exec_hf_model_info` | `(args)` | — | [src](../../../core/tools/simple_tools_native.py#L2806) |

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
| function | `_exec_operator_run_in_background` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L406) |
| function | `_exec_operator_bash_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L431) |
| function | `_exec_operator_kill_shell` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L444) |
| function | `_exec_operator_multi_edit` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L456) |
| function | `_exec_operator_glob` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L505) |
| function | `_exec_operator_grep` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L523) |
| function | `_exec_operator_list_dir` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L544) |
| function | `_exec_operator_webfetch` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L556) |
| function | `_exec_operator_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L577) |
| function | `_exec_operator_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L602) |
| function | `_exec_operator_open_url` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L623) |
| function | `_exec_operator_launch_app` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L654) |
| function | `_exec_operator_mouse_move` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L699) |
| function | `_exec_operator_mouse_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L715) |
| function | `_exec_operator_mouse_position` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L736) |
| function | `_exec_operator_keyboard_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L746) |
| function | `_exec_operator_keyboard_press` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L765) |
| function | `_exec_operator_screen_size` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L782) |
| function | `_exec_operator_clipboard_read` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L792) |
| function | `_exec_operator_clipboard_write` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L802) |
| function | `_exec_operator_list_windows` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L815) |
| function | `_exec_operator_focus_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L825) |
| function | `_exec_operator_mouse_scroll` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L851) |
| function | `_exec_operator_mouse_drag` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L867) |
| function | `_exec_operator_list_processes` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L888) |
| function | `_exec_operator_kill_process` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L903) |
| function | `_exec_operator_speak` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L938) |
| function | `_exec_operator_screenshot_window` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L958) |
| function | `_exec_operator_find_image` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L979) |
| function | `_exec_operator_ocr_region` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L997) |
| function | `_exec_operator_reminder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1023) |
| function | `_exec_operator_wakeup` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1043) |
| function | `_exec_operator_scheduled_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1061) |
| function | `_exec_operator_scheduled_cancel` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1076) |
| function | `_exec_operator_process_spawn` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1089) |
| function | `_exec_operator_process_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1107) |
| function | `_exec_operator_process_output` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1120) |
| function | `_exec_operator_process_kill` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1138) |
| function | `_exec_operator_process_list` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1155) |
| function | `_exec_operator_notify` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1169) |
| function | `_exec_operator_watch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1190) |
| function | `_exec_operator_unwatch_folder` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1209) |
| function | `_exec_operator_watch_events` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1224) |
| function | `_exec_operator_record_audio` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1241) |
| function | `_exec_operator_browser_open` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1282) |
| function | `_exec_operator_browser_get_text` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1300) |
| function | `_exec_operator_browser_get_links` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1317) |
| function | `_exec_operator_browser_click` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1327) |
| function | `_exec_operator_browser_type` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1346) |
| function | `_exec_operator_browser_screenshot` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1367) |
| function | `_exec_operator_browser_evaluate` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1383) |
| function | `_exec_operator_browser_status` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1413) |
| function | `_exec_operator_browser_close` | `(args)` | — | [src](../../../core/tools/simple_tools_operator.py#L1423) |

## `core/tools/simple_tools_web.py`
_Web/search/system-info tool executors for Jarvis' native lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_glob_to_regex` | `(pattern)` | Oversæt et glob-mønster (POSIX-relativt) til en regex med KORREKT sti-semantik: | [src](../../../core/tools/simple_tools_web.py#L63) |
| function | `_st` | `()` | Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn). | [src](../../../core/tools/simple_tools_web.py#L84) |
| function | `_cached_web_search_fn` | `(*, query, max_results, fetch_fn)` | Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm). | [src](../../../core/tools/simple_tools_web.py#L90) |
| function | `_exec_search` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L95) |
| function | `_exec_find_files` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L191) |
| function | `_get_or_open_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L286) |
| function | `_reset_default_bash_session` | `()` | — | [src](../../../core/tools/simple_tools_web.py#L310) |
| function | `_exec_bash` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L316) |
| function | `_html_to_text` | `(raw)` | Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift). | [src](../../../core/tools/simple_tools_web.py#L477) |
| function | `_egress_blokeret` | `(url)` | Fejl-svaret hvis destinationen er intern, ellers None. | [src](../../../core/tools/simple_tools_web.py#L515) |
| class | `_RevaliderendeRedirect` | `` | Stopper en omdirigering mod et internt maal, hop for hop. | [src](../../../core/tools/simple_tools_web.py#L547) |
| method | `_RevaliderendeRedirect.redirect_request` | `(self, req, fp, code, msg, headers, newurl)` | — | [src](../../../core/tools/simple_tools_web.py#L550) |
| function | `_hent_side` | `(url)` | Hent en side med redirect-revalidering og kort cache. | [src](../../../core/tools/simple_tools_web.py#L565) |
| function | `_exec_web_fetch` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L583) |
| function | `_exec_web_scrape` | `(args)` | — | [src](../../../core/tools/simple_tools_web.py#L646) |
| function | `_read_api_key` | `(key)` | Read an API key directly from runtime.json. | [src](../../../core/tools/simple_tools_web.py#L661) |
| function | `_fetch_tavily` | `(query, max_results)` | Raw Tavily API call — no caching. | [src](../../../core/tools/simple_tools_web.py#L671) |
| function | `_cached_web_search_fn_impl` | `(*, query, max_results, fetch_fn)` | Wrapper so tests can monkeypatch the cache layer (real impl). | [src](../../../core/tools/simple_tools_web.py#L706) |
| function | `_exec_web_search` | `(args)` | Web search via Tavily API with result caching. | [src](../../../core/tools/simple_tools_web.py#L713) |
| function | `_read_user_location` | `()` | Read Location from the live workspace USER.md. | [src](../../../core/tools/simple_tools_web.py#L723) |
| function | `_exec_get_weather` | `(args)` | Current weather via OpenWeatherMap. | [src](../../../core/tools/simple_tools_web.py#L735) |
| function | `_exec_get_exchange_rate` | `(args)` | Currency exchange rates via exchangerate.host. | [src](../../../core/tools/simple_tools_web.py#L769) |
| function | `_exec_get_news` | `(args)` | Recent news via NewsAPI. | [src](../../../core/tools/simple_tools_web.py#L796) |
| function | `_exec_analyze_image` | `(args)` | Analyze an image using a vision-capable model via Ollama. | [src](../../../core/tools/simple_tools_web.py#L832) |
| function | `_exec_read_archive` | `(args)` | List or extract a zip / tar / rar archive. | [src](../../../core/tools/simple_tools_web.py#L952) |
| function | `_exec_wolfram_query` | `(args)` | Precise answers via Wolfram Alpha Short Answers API. | [src](../../../core/tools/simple_tools_web.py#L1022) |

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
| function | `_skill_summary` | `(result, *, max_chars=…)` | — | [src](../../../core/tools/skill_gate_tool.py#L92) |
| function | `_exec_skill_gate` | `(args)` | Pre-action gate: match user query to installed skills, invoke if relevant. | [src](../../../core/tools/skill_gate_tool.py#L106) |

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

