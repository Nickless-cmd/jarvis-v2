# `core.tools.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/tools/tiktok_content_tools.py`
_TikTok content generation tool — wraps jarvis_pollinations_pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_tiktok_generate_video` | `(args)` | — | [src](../../../core/tools/tiktok_content_tools.py#L21) |

## `core/tools/tiktok_tools.py`
_TikTok auto-uploader integration tools for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_tiktok_upload` | `(args)` | Upload a video to TikTok using tiktokautouploader. | [src](../../../core/tools/tiktok_tools.py#L38) |
| function | `_exec_tiktok_login` | `(args)` | Log into TikTok via headless browser using username + password. | [src](../../../core/tools/tiktok_tools.py#L114) |
| function | `_exec_tiktok_show` | `(args)` | List saved TikTok cookie profiles and available videos. | [src](../../../core/tools/tiktok_tools.py#L185) |
| function | `_get_display` | `()` | Return a DISPLAY value for browser operations. | [src](../../../core/tools/tiktok_tools.py#L217) |

## `core/tools/tool_scoping.py`
_Tool-scoping policy — hvilke værktøjer er tilgængelige pr. rolle og mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_local_execution_tool` | `(name)` | True hvis værktøjet kører lokalt i code mode (resultat forlader ikke maskinen). | [src](../../../core/tools/tool_scoping.py#L137) |
| function | `current_tool_scope` | `()` | Nuværende tool-scope ("chat" eller "" for ubegrænset). | [src](../../../core/tools/tool_scoping.py#L148) |
| function | `set_tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L153) |
| function | `reset_tool_scope` | `(token)` | — | [src](../../../core/tools/tool_scoping.py#L157) |
| function | `current_local_exec` | `()` | True når det aktive run er en jarvis-code Path B lokal-exec-tur. | [src](../../../core/tools/tool_scoping.py#L170) |
| function | `set_local_exec` | `(on)` | — | [src](../../../core/tools/tool_scoping.py#L175) |
| function | `tool_scope` | `(scope)` | — | [src](../../../core/tools/tool_scoping.py#L180) |
| function | `_owner_has_live_bridge` | `()` | True hvis der findes en levende desk-bro for nuværende bruger (presence, cross-proces). | [src](../../../core/tools/tool_scoping.py#L188) |
| function | `allowed_tool_names` | `(*, role, scope, all_names)` | Beregn det tilladte sæt tool-navne for (role, scope). | [src](../../../core/tools/tool_scoping.py#L202) |
| function | `is_tool_allowed` | `(*, role, scope, name)` | Må (role, scope) eksekvere værktøjet `name`? (Spor A — serverside håndhævelse.) | [src](../../../core/tools/tool_scoping.py#L248) |
| function | `_apply_computer_use_policy` | `(result)` | Computer-use-toggle (§4.7): fjern operator/computer-tools hvis brugeren har | [src](../../../core/tools/tool_scoping.py#L261) |
| function | `_fn_name` | `(td)` | — | [src](../../../core/tools/tool_scoping.py#L285) |
| function | `filter_tool_definitions` | `(defs, *, role, scope)` | Filtrér Ollama-tool-definitioner ned til det tilladte sæt for (role, scope). | [src](../../../core/tools/tool_scoping.py#L289) |

## `core/tools/ui_panel_tools.py`
_open_ui_panel-tool (spec §8.2, Fase 6 #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_open_ui_panel` | `(args)` | — | [src](../../../core/tools/ui_panel_tools.py#L23) |

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
| function | `load_workspace_capabilities` | `(name=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L138) |
| function | `build_ollama_tool_definitions` | `(name=…)` | Build Ollama-compatible tool definitions from workspace capabilities. | [src](../../../core/tools/workspace_capabilities.py#L341) |
| function | `resolve_tool_call_to_capability` | `(tool_name, arguments)` | Map an Ollama tool_call back to capability invocation parameters. | [src](../../../core/tools/workspace_capabilities.py#L373) |
| function | `invoke_workspace_capability` | `(capability_id, *, name=…, run_id=…, approved=…, write_content=…, target_path=…, command_text=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L397) |
| function | `get_capability_invocation_truth` | `()` | — | [src](../../../core/tools/workspace_capabilities.py#L549) |
| function | `_invoke_runnable_capability` | `(*, workspace_dir, section, summary, approved=…, write_content=…, target_path=…, command_text=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L558) |
| function | `classify_workspace_execution_mode` | `(execution_mode)` | — | [src](../../../core/tools/workspace_capabilities.py#L1864) |
| function | `_read_bounded_text` | `(path)` | — | [src](../../../core/tools/workspace_capabilities.py#L1964) |
| function | `_bounded_exec_output` | `(*, stdout, stderr)` | — | [src](../../../core/tools/workspace_capabilities.py#L1971) |
| function | `_run_bounded_command` | `(*, argv, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities.py#L1987) |
| function | `_run_bounded_shell_command` | `(*, command_text, workspace_dir)` | — | [src](../../../core/tools/workspace_capabilities.py#L2008) |
| function | `_search_file_matches` | `(path, query)` | — | [src](../../../core/tools/workspace_capabilities.py#L2029) |
| function | `_bounded_excerpt` | `(text, limit=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2049) |
| function | `_set_last_capability_invocation` | `(invocation, *, invoked_at, capability_id=…, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2056) |
| function | `_publish_capability_invocation_completed` | `(invocation, *, invoked_at, capability_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2094) |
| function | `_persist_capability_invocation` | `(invocation, *, invoked_at, finished_at, capability_id=…, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2123) |
| function | `_persist_capability_approval_request` | `(invocation, *, requested_at, run_id=…)` | — | [src](../../../core/tools/workspace_capabilities.py#L2177) |
| function | `_workspace_write_proposal_content` | `(*, summary, write_content)` | — | [src](../../../core/tools/workspace_capabilities.py#L2243) |
| function | `_now` | `()` | — | [src](../../../core/tools/workspace_capabilities.py#L2290) |

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

## `core/tools/worktree_tools.py`
_Git worktree primitive — let Jarvis experiment in isolation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_project_root` | `()` | — | [src](../../../core/tools/worktree_tools.py#L35) |
| function | `_is_git_repo` | `(path)` | — | [src](../../../core/tools/worktree_tools.py#L43) |
| function | `_git` | `(cwd, argv)` | — | [src](../../../core/tools/worktree_tools.py#L47) |
| function | `_safe_branch_name` | `(name)` | — | [src](../../../core/tools/worktree_tools.py#L57) |
| function | `_exec_worktree_create` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L63) |
| function | `_exec_worktree_list` | `(_args)` | — | [src](../../../core/tools/worktree_tools.py#L110) |
| function | `_exec_worktree_merge` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L146) |
| function | `_exec_worktree_discard` | `(args)` | — | [src](../../../core/tools/worktree_tools.py#L192) |

## `core/tools/world_model_tools.py`
_World Model tools — predict_outcome + resolve_prediction._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_exec_predict_outcome` | `(args)` | Record a falsifiable prediction. | [src](../../../core/tools/world_model_tools.py#L25) |
| function | `_exec_resolve_prediction` | `(args)` | Resolve an open prediction with a later observation. | [src](../../../core/tools/world_model_tools.py#L85) |

