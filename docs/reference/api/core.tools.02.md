# `core.tools.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/kaldt_vaerktoej.py`
_`call_loaded_tool` — en transport, ikke en udfører._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pak_ud` | `(navn, argumenter)` | Oversæt et dispatcher-kald til det ægte kald. Alt andet går uændret igennem. | [src](../../../core/tools/kaldt_vaerktoej.py#L76) |

## `core/tools/kommando_beskrivelse.py`
_Jarvis' egen beskrivelse af en kommando — linjen i klienterne._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(s)` | — | [src](../../../core/tools/kommando_beskrivelse.py#L55) |
| function | `brugbar_beskrivelse` | `(beskrivelse, kommando=…)` | Beskrivelsen hvis den kan stå som linjen, ellers `""`. | [src](../../../core/tools/kommando_beskrivelse.py#L59) |

## `core/tools/load_more_tools.py`
_Lazy tool schema loader for visible-lane tool pruning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_name` | `(tool_def)` | — | [src](../../../core/tools/load_more_tools.py#L10) |
| function | `_tool_load_more_tools` | `(arguments)` | Resolve tools to add to the next round and return their full schemas. | [src](../../../core/tools/load_more_tools.py#L15) |

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
| function | `_read_memory` | `()` | — | [src](../../../core/tools/memory_tools.py#L69) |
| function | `_parse_headings` | `(text)` | — | [src](../../../core/tools/memory_tools.py#L76) |
| function | `_normalize` | `(heading)` | — | [src](../../../core/tools/memory_tools.py#L80) |
| function | `_exec_memory_check_duplicate` | `(args)` | — | [src](../../../core/tools/memory_tools.py#L84) |
| function | `_exec_memory_upsert_section` | `(args)` | Write or update a section in MEMORY.md. Replaces existing section if heading matches. | [src](../../../core/tools/memory_tools.py#L121) |
| function | `_exec_memory_list_headings` | `(args)` | — | [src](../../../core/tools/memory_tools.py#L186) |
| function | `_exec_memory_consolidate` | `(args)` | Find fuzzy-overlapping sections in MEMORY.md and propose/execute merges. | [src](../../../core/tools/memory_tools.py#L196) |

## `core/tools/memory_topic_tools.py`
_Kuraterede memory-topic-tools (spec 2026-07-10 Spec B)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_read_memory_topic` | `(args)` | Læs en kurateret memory-topic-fil (pull, LLM-led). Scoped til aktuel bruger. | [src](../../../core/tools/memory_topic_tools.py#L12) |
| function | `_exec_write_memory_topic` | `(args)` | Skriv/opdatér en kurateret memory-topic (streng bekraeftelse). Scoped til bruger. | [src](../../../core/tools/memory_topic_tools.py#L22) |

## `core/tools/mermaid_tool.py`
_`render_mermaid` — et diagram der også når telefonen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_generated_dir` | `()` | Samme mappe som `openrouter_image` skriver i — den er allerede synlig. | [src](../../../core/tools/mermaid_tool.py#L70) |
| function | `_svg_til_png` | `(svg)` | SVG → PNG med rsvg-convert. Rejser RuntimeError med en brugbar årsag. | [src](../../../core/tools/mermaid_tool.py#L86) |
| function | `_exec_render_mermaid` | `(args)` | Mermaid-kilde → PNG i tråden, så diagrammet også ses på mobilen. | [src](../../../core/tools/mermaid_tool.py#L148) |

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

## `core/tools/openrouter_image_tools.py`
_OpenRouter billed-generering — Gemini tegner, diffusion maler (målt 12/9-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_credentials` | `()` | Returnér (api_key, profil). Læses fra auth-laget — aldrig hardkodet. | [src](../../../core/tools/openrouter_image_tools.py#L83) |
| function | `_generated_dir` | `()` | — | [src](../../../core/tools/openrouter_image_tools.py#L126) |
| function | `_clamp` | `(value, lo, hi)` | — | [src](../../../core/tools/openrouter_image_tools.py#L131) |
| function | `_safe_filename` | `(prompt, gen_id, ext)` | — | [src](../../../core/tools/openrouter_image_tools.py#L135) |
| function | `_write_sidecar` | `(image_path, metadata)` | — | [src](../../../core/tools/openrouter_image_tools.py#L143) |
| function | `_as_reference` | `(source)` | Gør en sti/URL/data-URL til et ``input_references``-element. | [src](../../../core/tools/openrouter_image_tools.py#L153) |
| function | `_report_cost` | `(usage, *, model, run_id=…)` | Bogfør den FAKTISKE pris fra OpenRouter. Returnerer cost_usd. | [src](../../../core/tools/openrouter_image_tools.py#L188) |
| function | `_post` | `(body, *, timeout=…)` | Ét POST til billed-endpointet. Kaster aldrig — returnerer fejl-dict. | [src](../../../core/tools/openrouter_image_tools.py#L229) |
| function | `_save_images` | `(data, *, prompt, model, gen_id, save_dir=…, ekstra=…)` | Dekodér, gem og registrér billederne fra et svar. Delt af begge veje. | [src](../../../core/tools/openrouter_image_tools.py#L267) |
| function | `generate_image` | `(*, prompt, model=…, aspect_ratio=…, resolution=…, quality=…, output_format=…, n=…, seed=…, references=…, save_dir=…, timeout=…)` | Generér (eller redigér) et billede via OpenRouter. Betalt — se cost_usd. | [src](../../../core/tools/openrouter_image_tools.py#L398) |
| function | `edit_image` | `(*, reference, prompt, model=…, aspect_ratio=…, resolution=…, n=…, seed=…, save_dir=…, timeout=…)` | Redigér et eksisterende billede: reference + instruktion → nyt billede. | [src](../../../core/tools/openrouter_image_tools.py#L461) |
| function | `_haeng_paa_turen` | `(args, result)` | Læg det genererede billede på turen, så klienten kan vise det i tråden. | [src](../../../core/tools/openrouter_image_tools.py#L492) |
| function | `_exec_openrouter_image` | `(args)` | — | [src](../../../core/tools/openrouter_image_tools.py#L530) |
| function | `_exec_openrouter_image_edit` | `(args)` | — | [src](../../../core/tools/openrouter_image_tools.py#L563) |

## `core/tools/operator_background.py`
_Baggrunds-shells paa operatoerens maskine — paritet med jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_new_id` | `()` | — | [src](../../../core/tools/operator_background.py#L35) |
| function | `_valid` | `(shell_id)` | Kun vores egne id'er. Uden det kunne et id smugle sti-fragmenter ind i | [src](../../../core/tools/operator_background.py#L39) |
| function | `start_async` | `(*, command, user_id, cwd=…, titel=…, timeout_s=…)` | Start en loesrevet baggrunds-shell. Returnerer {shell_id, pid}. | [src](../../../core/tools/operator_background.py#L45) |
| function | `read_async` | `(*, shell_id, user_id, since=…, timeout_s=…)` | Laes NYT output siden byte-offset `since`. | [src](../../../core/tools/operator_background.py#L103) |
| function | `kill_async` | `(*, shell_id, user_id, timeout_s=…)` | Draeb en baggrunds-shell. Idempotent: en allerede doed shell er ikke en fejl. | [src](../../../core/tools/operator_background.py#L143) |

## `core/tools/operator_bash_session.py`
_operator_bash_session — vedvarende-FØLELSE bash-session på operatorens maskine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/tools/operator_bash_session.py#L26) |
| function | `_q` | `(s)` | — | [src](../../../core/tools/operator_bash_session.py#L30) |
| function | `_reap` | `()` | — | [src](../../../core/tools/operator_bash_session.py#L34) |
| function | `_extract_cwd` | `(out)` | Pluk cwd-markøren ud af stdout og fjern den fra det Jarvis ser. | [src](../../../core/tools/operator_bash_session.py#L41) |
| function | `_exec_operator_bash_session_open` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L52) |
| function | `_exec_operator_bash_session_run` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L66) |
| function | `_render_text` | `(inner)` | Læsbart output som en `text`-nøgle — og dét er ikke kosmetik. | [src](../../../core/tools/operator_bash_session.py#L123) |
| function | `_exec_operator_bash_session_close` | `(args)` | — | [src](../../../core/tools/operator_bash_session.py#L162) |
| function | `_exec_operator_bash_session_list` | `(_args)` | — | [src](../../../core/tools/operator_bash_session.py#L178) |

## `core/tools/operator_tools.py`
_Operator-side tools — execute on operator's desktop via JarvisX bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_workspace_scoped_args` | `(payload, workspace_root)` | — | [src](../../../core/tools/operator_tools.py#L26) |
| function | `_bridge_call` | `(*, tool, args, user_id, timeout_s=…)` | Common dispatch helper. Raises RuntimeError on bridge failure. | [src](../../../core/tools/operator_tools.py#L34) |
| function | `operator_read_file_async` | `(*, path, user_id, workspace_root=…, timeout_s=…)` | Read a file from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L56) |
| function | `operator_read_file` | `(*, path, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L70) |
| function | `operator_write_file_async` | `(*, path, content, user_id, timeout_s=…)` | Write content to a file on the operator's desktop. Creates parents | [src](../../../core/tools/operator_tools.py#L77) |
| function | `operator_file_snapshot_async` | `(*, path, user_id, timeout_s=…)` | Read a bounded text snapshot or an explicit missing-file marker. | [src](../../../core/tools/operator_tools.py#L96) |
| function | `operator_remove_file_async` | `(*, path, user_id, expected_sha256, expected_mode, timeout_s=…)` | Remove only a newly created file matching its last observed fingerprint. | [src](../../../core/tools/operator_tools.py#L104) |
| function | `operator_edit_file_async` | `(*, path, old_string, new_string, replace_all=…, user_id, timeout_s=…)` | Find/replace in a file on the operator's desktop. Returns | [src](../../../core/tools/operator_tools.py#L120) |
| function | `operator_multi_edit_async` | `(*, path, edits, user_id, timeout_s=…)` | Flere redigeringer i ÉN fil, ét bro-kald. Findes ikke i jarvis-code's | [src](../../../core/tools/operator_tools.py#L175) |
| function | `operator_multi_edit` | `(*, path, edits, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L229) |
| function | `operator_glob_async` | `(*, pattern, cwd=…, max_results=…, user_id, workspace_root=…, timeout_s=…)` | Find files matching a glob pattern on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L238) |
| function | `operator_grep_async` | `(*, pattern, path=…, glob=…, case_insensitive=…, max_results=…, user_id, workspace_root=…, timeout_s=…)` | Search for regex pattern in files on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L266) |
| function | `operator_list_dir_async` | `(*, path, user_id, workspace_root=…, timeout_s=…)` | List directory contents on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L298) |
| function | `operator_webfetch_async` | `(*, url, method=…, headers=…, body=…, timeout_s=…, user_id)` | Fetch a URL from the operator's local network via the bridge. | [src](../../../core/tools/operator_tools.py#L320) |
| function | `operator_bash_async` | `(*, command, cwd=…, timeout_s=…, user_id, skip_approval=…)` | Run a shell command on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L356) |
| function | `operator_screenshot_async` | `(*, user_id, display_id=…, save_path=…, format=…, jpeg_quality=…, timeout_s=…)` | Capture a screenshot of the operator's desktop. | [src](../../../core/tools/operator_tools.py#L396) |
| function | `operator_open_url_async` | `(*, url, user_id, skip_approval=…, timeout_s=…)` | Open a URL in the operator s default browser. Returns {approved, opened, url}. | [src](../../../core/tools/operator_tools.py#L456) |
| function | `operator_launch_app_async` | `(*, path, user_id, args=…, cwd=…, skip_approval=…, timeout_s=…)` | Launch an installed app on the operator s machine. | [src](../../../core/tools/operator_tools.py#L476) |
| function | `operator_mouse_move_async` | `(*, x, y, user_id, smooth=…, timeout_s=…)` | Move the operator s mouse cursor to (x, y) screen coordinates. | [src](../../../core/tools/operator_tools.py#L513) |
| function | `operator_mouse_click_async` | `(*, user_id, button=…, double=…, x=…, y=…, timeout_s=…)` | Click the mouse on the operator s desktop, optionally moving first. | [src](../../../core/tools/operator_tools.py#L534) |
| function | `operator_mouse_position_async` | `(*, user_id, timeout_s=…)` | Get the current mouse cursor position on the operator s desktop. | [src](../../../core/tools/operator_tools.py#L561) |
| function | `operator_keyboard_type_async` | `(*, text, user_id, delay_ms=…, timeout_s=…)` | Type a string into the operator s currently focused window. | [src](../../../core/tools/operator_tools.py#L579) |
| function | `operator_keyboard_press_async` | `(*, keys, user_id, timeout_s=…)` | Press a single key or a hotkey combination on the operator s keyboard. | [src](../../../core/tools/operator_tools.py#L602) |
| function | `operator_screen_size_async` | `(*, user_id, timeout_s=…)` | Get the operator s primary display size in pixels. | [src](../../../core/tools/operator_tools.py#L628) |
| function | `operator_browser_open_async` | `(*, url, user_id, wait_until=…, timeout_ms=…, timeout_s=…)` | Navigate the browser session to URL. First call opens browser. | [src](../../../core/tools/operator_tools.py#L646) |
| function | `operator_browser_get_text_async` | `(*, user_id, selector=…, max_chars=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L660) |
| function | `operator_browser_get_links_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L673) |
| function | `operator_browser_click_async` | `(*, selector, user_id, wait_navigation=…, wait_for_selector=…, timeout_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L682) |
| function | `operator_browser_type_async` | `(*, selector, text, user_id, clear_first=…, delay_ms=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L700) |
| function | `operator_browser_screenshot_async` | `(*, user_id, full_page=…, format=…, jpeg_quality=…, timeout_s=…)` | Screenshot the active browser page. Decoded to a Jarvis-side temp file. | [src](../../../core/tools/operator_tools.py#L718) |
| function | `operator_browser_evaluate_async` | `(*, script, user_id, skip_approval=…, timeout_s=…)` | Run JS in the page context. Requires approval unless skip_approval. | [src](../../../core/tools/operator_tools.py#L750) |
| function | `operator_browser_status_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L764) |
| function | `operator_browser_close_async` | `(*, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L773) |
| function | `operator_clipboard_read_async` | `(*, user_id, timeout_s=…)` | Return current clipboard text from the operator's desktop. | [src](../../../core/tools/operator_tools.py#L785) |
| function | `operator_clipboard_write_async` | `(*, text, user_id, timeout_s=…)` | Replace the operator's clipboard with the given text. | [src](../../../core/tools/operator_tools.py#L803) |
| function | `operator_list_windows_async` | `(*, user_id, timeout_s=…)` | List open windows on the operator's desktop. Returns {windows: [{title, id}]}. | [src](../../../core/tools/operator_tools.py#L822) |
| function | `operator_focus_window_async` | `(*, user_id, title_substring=…, handle=…, timeout_s=…)` | Bring a window to the foreground by title substring or handle/id. | [src](../../../core/tools/operator_tools.py#L840) |
| function | `operator_mouse_scroll_async` | `(*, direction, user_id, amount=…, timeout_s=…)` | Scroll the mouse wheel in the given direction. | [src](../../../core/tools/operator_tools.py#L865) |
| function | `operator_mouse_drag_async` | `(*, from_x, from_y, to_x, to_y, user_id, button=…, timeout_s=…)` | Drag the mouse from (from_x, from_y) to (to_x, to_y). | [src](../../../core/tools/operator_tools.py#L885) |
| function | `operator_list_processes_async` | `(*, user_id, filter=…, timeout_s=…)` | List running processes on the operator's machine. Returns {processes: [{pid, name, cpu, memMB}]}. | [src](../../../core/tools/operator_tools.py#L914) |
| function | `operator_kill_process_async` | `(*, pid, user_id, skip_approval=…, timeout_s=…)` | Kill a process by PID. Requires operator approval unless skip_approval=True. | [src](../../../core/tools/operator_tools.py#L936) |
| function | `operator_speak_async` | `(*, text, user_id, voice=…, rate=…, timeout_s=…)` | Say text aloud on the operator's machine via TTS (espeak-ng / SAPI). | [src](../../../core/tools/operator_tools.py#L956) |
| function | `operator_screenshot_window_async` | `(*, user_id, title_substring=…, handle=…, save_path=…, timeout_s=…)` | Capture a specific window on the operator's desktop. | [src](../../../core/tools/operator_tools.py#L980) |
| function | `operator_find_image_async` | `(*, template_path, user_id, confidence=…, timeout_s=…)` | Template-match a small image inside the current screen. Returns {found, x, y, confidence}. | [src](../../../core/tools/operator_tools.py#L1047) |
| function | `operator_ocr_region_async` | `(*, x, y, width, height, user_id, lang=…, timeout_s=…)` | Extract text from a screen region using Tesseract OCR. | [src](../../../core/tools/operator_tools.py#L1067) |
| function | `operator_notify_async` | `(*, title, body, user_id, icon=…, timeout_s=…)` | Show an OS notification toast on the operator's machine via Electron Notification. | [src](../../../core/tools/operator_tools.py#L1096) |
| function | `operator_watch_folder_async` | `(*, path, user_id, recursive=…, debounce_ms=…, timeout_s=…)` | Start watching a folder for changes on the operator's machine. Returns {watcher_id}. | [src](../../../core/tools/operator_tools.py#L1120) |
| function | `operator_unwatch_folder_async` | `(*, watcher_id, user_id, timeout_s=…)` | Stop a folder watcher by watcher_id. Returns {stopped: true}. | [src](../../../core/tools/operator_tools.py#L1138) |
| function | `operator_watch_events_async` | `(*, watcher_id, user_id, max=…, timeout_s=…)` | Poll buffered filesystem events for a watcher. Returns {events: [...]} and clears buffer. | [src](../../../core/tools/operator_tools.py#L1154) |
| function | `operator_record_audio_async` | `(*, duration_s, user_id, output_path=…, device=…, skip_approval=…, timeout_s=…)` | Record N seconds of microphone audio on the operator's machine. Requires approval. | [src](../../../core/tools/operator_tools.py#L1174) |
| function | `operator_reminder_async` | `(*, when, message, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1205) |
| function | `operator_wakeup_async` | `(*, when, message=…, title=…, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1218) |
| function | `operator_scheduled_list_async` | `(*, user_id, kind=…, include_fired=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1233) |
| function | `operator_scheduled_cancel_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1246) |
| function | `operator_process_spawn_async` | `(*, cmd, user_id, cwd=…, label=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1259) |
| function | `operator_process_status_async` | `(*, id, user_id, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1274) |
| function | `operator_process_output_async` | `(*, id, user_id, since_offset=…, max_bytes=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1284) |
| function | `operator_process_kill_async` | `(*, id, user_id, signal=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1296) |
| function | `operator_process_list_async` | `(*, user_id, include_finished=…, timeout_s=…)` | — | [src](../../../core/tools/operator_tools.py#L1306) |
| function | `_op_sess_now` | `()` | — | [src](../../../core/tools/operator_tools.py#L1343) |
| function | `_op_sess_reap` | `()` | — | [src](../../../core/tools/operator_tools.py#L1347) |
| function | `_op_sess_owner_denied` | `()` | Denial reason if the caller is a real non-owner role, else None. | [src](../../../core/tools/operator_tools.py#L1355) |
| function | `_op_sess_user_id` | `(args)` | — | [src](../../../core/tools/operator_tools.py#L1371) |
| function | `_op_dispatch_bash` | `(command, *, user_id, cwd, timeout_s)` | Dispatch a command via the bridge with skip_approval=True (reuses the | [src](../../../core/tools/operator_tools.py#L1376) |
| function | `_exec_operator_session_open` | `(args)` | Open a persistent operator session. Owner-only. Probes the bridge with a | [src](../../../core/tools/operator_tools.py#L1390) |
| function | `_exec_operator_session_run` | `(args)` | Run a command in an operator session via the bridge WITHOUT an approval | [src](../../../core/tools/operator_tools.py#L1410) |
| function | `_exec_operator_session_close` | `(args)` | Close an operator session (owner-only). | [src](../../../core/tools/operator_tools.py#L1451) |

## `core/tools/owner_approval.py`
_Ejer-godkendelse — «Bjørn har set PRÆCIS denne kommando og sagt ja»._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ejer_godkendt_kald` | `()` | Marker at DETTE kald bærer en menneskelig godkendelse. | [src](../../../core/tools/owner_approval.py#L51) |
| function | `er_ejer_godkendt` | `()` | Har et menneske godkendt præcis dette kald? | [src](../../../core/tools/owner_approval.py#L66) |

## `core/tools/pause_and_ask_tools.py`
_pause_and_ask — structured clarification prompts mid-run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_pause_and_ask` | `(args)` | — | [src](../../../core/tools/pause_and_ask_tools.py#L28) |

## `core/tools/phone_adb.py`
_ADB over Wi-Fi — ægte skal på telefonen, uden om broen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_adb_sti` | `()` | — | [src](../../../core/tools/phone_adb.py#L43) |
| function | `_adresse` | `(args=…)` | Telefonens ``host:port``. Argument slår config, config slår ingenting. | [src](../../../core/tools/phone_adb.py#L47) |
| function | `_koer_adb` | `(argv, *, timeout_s=…)` | Kør adb og returnér resultatet. Kaster aldrig — fejl er data. | [src](../../../core/tools/phone_adb.py#L59) |
| function | `_forbundet` | `(adresse)` | Står telefonen som ``device`` (ikke ``offline``/``unauthorized``) i adb? | [src](../../../core/tools/phone_adb.py#L87) |
| function | `_exec_phone_adb_status` | `(args)` | Hvad adb ser lige nu. Ændrer intet, kræver derfor ingen godkendelse. | [src](../../../core/tools/phone_adb.py#L102) |
| function | `_exec_phone_adb_connect` | `(args)` | Forbind til telefonen. Kræver at der er parret én gang først. | [src](../../../core/tools/phone_adb.py#L116) |
| function | `_exec_phone_adb_pair` | `(args)` | Par med telefonen. Koden kommer fra Bjørn og gemmes ikke. | [src](../../../core/tools/phone_adb.py#L133) |
| function | `_exec_phone_adb_shell` | `(args)` | Kør en kommando på telefonen. **Kræver godkendelse.** | [src](../../../core/tools/phone_adb.py#L159) |
| function | `_exec_phone_adb_screenshot` | `(args)` | Tag et skærmbillede af telefonen og gem det på runtime-maskinen. | [src](../../../core/tools/phone_adb.py#L186) |
| function | `_f` | `(navn, beskrivelse, properties, required)` | — | [src](../../../core/tools/phone_adb.py#L242) |
| function | `_force_phone_adb_shell` | `(args)` | Koer kommandoen direkte efter chat-godkendelse. | [src](../../../core/tools/phone_adb.py#L292) |
| function | `_force_phone_adb_screenshot` | `(args)` | Tag skaermbilledet direkte efter chat-godkendelse. | [src](../../../core/tools/phone_adb.py#L297) |

## `core/tools/phone_tools.py`
_Telefon-vaerktoejer — Jarvis' organer paa Bjoerns telefon._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_phone_call` | `(*, tool, args, user_id, timeout_s=…)` | Send et kald til telefonen. Kaster ``RuntimeError`` med en LAESELIG grund. | [src](../../../core/tools/phone_tools.py#L47) |
| function | `phone_photo_async` | `(*, user_id, kamera=…, gem_sti=…, timeout_s=…)` | Tag et billede. **Kraever at appen er i forgrunden** — kameraet kan ikke | [src](../../../core/tools/phone_tools.py#L112) |
| function | `phone_location_async` | `(*, user_id, noejagtighed=…, timeout_s=…)` | Hvor telefonen er. Virker ogsaa i baggrunden. | [src](../../../core/tools/phone_tools.py#L126) |
| function | `phone_record_audio_async` | `(*, user_id, sekunder=…, timeout_s=…)` | Optag lyd fra mikrofonen. Virker ogsaa i baggrunden. | [src](../../../core/tools/phone_tools.py#L139) |
| function | `phone_speak_async` | `(*, user_id, tekst, sprog=…, timeout_s=…)` | Sig noget hoejt gennem telefonens hoejttaler. | [src](../../../core/tools/phone_tools.py#L160) |
| function | `phone_bubble_async` | `(*, user_id, tekst, timeout_s=…)` | Vis noget i den flydende boble oven paa andre apps. | [src](../../../core/tools/phone_tools.py#L173) |
| function | `phone_read_file_async` | `(*, user_id, sti, timeout_s=…)` | Laes en fil i appens eget omraade paa telefonen. | [src](../../../core/tools/phone_tools.py#L187) |
| function | `phone_write_file_async` | `(*, user_id, sti, indhold, timeout_s=…)` | Skriv en fil i appens eget omraade paa telefonen. | [src](../../../core/tools/phone_tools.py#L198) |
| function | `phone_list_files_async` | `(*, user_id, sti=…, timeout_s=…)` | Hvad ligger der i appens omraade. | [src](../../../core/tools/phone_tools.py#L210) |
| function | `phone_share_async` | `(*, user_id, tekst=…, sti=…, timeout_s=…)` | Send noget videre til en anden app via delings-arket. | [src](../../../core/tools/phone_tools.py#L221) |
| function | `phone_clipboard_read_async` | `(*, user_id, timeout_s=…)` | Hvad der ligger i telefonens udklipsholder. | [src](../../../core/tools/phone_tools.py#L237) |
| function | `phone_clipboard_write_async` | `(*, user_id, tekst, timeout_s=…)` | Laeg noget i telefonens udklipsholder. | [src](../../../core/tools/phone_tools.py#L247) |
| function | `_f` | `(navn, beskrivelse, properties, required)` | — | [src](../../../core/tools/phone_tools.py#L268) |
| function | `_bruger` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L332) |
| function | `_koer` | `(coro_fn, *, tool_name, timeout_s)` | — | [src](../../../core/tools/phone_tools.py#L337) |
| function | `_exec_phone_photo` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L342) |
| function | `_exec_phone_location` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L350) |
| function | `_exec_phone_record_audio` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L357) |
| function | `_exec_phone_speak` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L365) |
| function | `_exec_phone_bubble` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L373) |
| function | `_exec_phone_read_file` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L379) |
| function | `_exec_phone_write_file` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L385) |
| function | `_exec_phone_list_files` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L393) |
| function | `_exec_phone_share` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L399) |
| function | `_exec_phone_clipboard_read` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L407) |
| function | `_exec_phone_clipboard_write` | `(args)` | — | [src](../../../core/tools/phone_tools.py#L413) |

## `core/tools/plan_revise_tool.py`
_Plan revision tool — revise_plan._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_revise_plan` | `(args)` | Tool handler for revise_plan. | [src](../../../core/tools/plan_revise_tool.py#L27) |

## `core/tools/pollinations_tools.py`
_Pollinations.ai tools — free, no-auth image + video generation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_api_key` | `()` | Read pollinations API key from runtime.json (never hardcoded). | [src](../../../core/tools/pollinations_tools.py#L83) |
| function | `_auth_headers` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L95) |
| function | `_generated_dir` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L103) |
| function | `_video_dir` | `()` | — | [src](../../../core/tools/pollinations_tools.py#L108) |
| function | `_clamp` | `(value, lo, hi)` | — | [src](../../../core/tools/pollinations_tools.py#L113) |
| function | `_safe_filename` | `(prompt, gen_id, ext)` | — | [src](../../../core/tools/pollinations_tools.py#L117) |
| function | `_write_sidecar` | `(image_path, metadata)` | — | [src](../../../core/tools/pollinations_tools.py#L126) |
| function | `generate_image` | `(*, prompt, model=…, width=…, height=…, seed=…, nologo=…, enhance=…, save_dir=…)` | Fetch an image from Pollinations and save to disk. Returns result dict. | [src](../../../core/tools/pollinations_tools.py#L135) |
| function | `_exec_pollinations_image` | `(args)` | — | [src](../../../core/tools/pollinations_tools.py#L248) |
| function | `generate_video` | `(*, prompt, model=…, duration=…, aspect_ratio=…, audio=…, image_url=…, save_dir=…)` | Generate a video via pollinations.ai. Requires pollinations_api_key | [src](../../../core/tools/pollinations_tools.py#L331) |
| function | `_hent_video` | `(*, url, model, prompt, save_dir=…)` | Hent, gem og beskriv en video. Faelles for generering og redigering. | [src](../../../core/tools/pollinations_tools.py#L373) |
| function | `_registrer_video` | `(result, args, *, hvad=…)` | Goer videoen synlig: registrér den, og laeg den paa turen. | [src](../../../core/tools/pollinations_tools.py#L458) |
| function | `edit_video` | `(*, prompt, video_url, model=…, duration=…, aspect_ratio=…, audio=…)` | Lav en NY video ud fra en eksisterende + en instruktion. | [src](../../../core/tools/pollinations_tools.py#L506) |
| function | `_exec_pollinations_video_edit` | `(args)` | — | [src](../../../core/tools/pollinations_tools.py#L571) |
| function | `_exec_pollinations_video` | `(args)` | — | [src](../../../core/tools/pollinations_tools.py#L595) |

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

## `core/tools/publish_file_tool.py`
_`publish_file` — udskilt enhed, og nu per bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_publish_file` | `(args)` | Copy or create a file in ~/.jarvis-v2/files/ and return a download URL. | [src](../../../core/tools/publish_file_tool.py#L36) |

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
| function | `_exec_list_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L69) |
| function | `_exec_cancel_recurring` | `(args)` | — | [src](../../../core/tools/recurring_scheduler_tools.py#L85) |
| function | `_exec_set_recurring_channel` | `(args)` | Sæt leverings-kanal på en recurring task (notif-routing spec §3.5). | [src](../../../core/tools/recurring_scheduler_tools.py#L223) |
| function | `_exec_set_recurring_weekdays` | `(args)` | Begræns en recurring task til bestemte ugedage. | [src](../../../core/tools/recurring_scheduler_tools.py#L243) |

## `core/tools/restart_self_tools.py`
_restart_self tool — fire-and-forget service restart that survives process death._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_aktive_koersler` | `(graense=…)` | Hvilke synlige koersler LEVER lige nu? | [src](../../../core/tools/restart_self_tools.py#L92) |
| function | `_exec_restart_self` | `(args)` | — | [src](../../../core/tools/restart_self_tools.py#L145) |
| function | `_wait_for_gateway_connected` | `(max_wait=…, interval=…)` | Vent på at Discord gateway er connected efter restart. | [src](../../../core/tools/restart_self_tools.py#L265) |
| function | `_send_discord_restart_msg` | `(base_msg)` | Send restart-bekræftelse til Bjørn via Discord DM. | [src](../../../core/tools/restart_self_tools.py#L291) |
| function | `_try_fallback_channels` | `(base_msg)` | Forsøg at sende restart-bekræftelse via Telegram eller ntfy som fallback. | [src](../../../core/tools/restart_self_tools.py#L312) |
| function | `_claim_restart_file` | `()` | Atomic claim af restart-confirmation-fil — kun én uvicorn worker vinder. | [src](../../../core/tools/restart_self_tools.py#L348) |
| function | `send_pending_restart_confirmation` | `()` | On startup, check for a pending restart confirmation file and send it. | [src](../../../core/tools/restart_self_tools.py#L379) |

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

