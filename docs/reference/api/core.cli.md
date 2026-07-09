# `core.cli` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/cli/__init__.py`

_(no top-level classes or functions)_

## `core/cli/capability_commands.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cmd_invoke_capability` | `(args)` | — | [src](../../../core/cli/capability_commands.py#L16) |
| function | `cmd_approve_capability_request` | `(args)` | — | [src](../../../core/cli/capability_commands.py#L36) |
| function | `cmd_execute_capability_request` | `(args)` | — | [src](../../../core/cli/capability_commands.py#L54) |
| function | `invoke_capability_truth` | `(capability_id, *, approved=…)` | — | [src](../../../core/cli/capability_commands.py#L72) |
| function | `approve_capability_request_truth` | `(request_id)` | — | [src](../../../core/cli/capability_commands.py#L92) |
| function | `execute_capability_request_truth` | `(request_id)` | — | [src](../../../core/cli/capability_commands.py#L110) |

## `core/cli/copilot_auth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_github_copilot_client_id` | `()` | — | [src](../../../core/cli/copilot_auth.py#L39) |
| function | `_save_github_copilot_client_id` | `(client_id)` | — | [src](../../../core/cli/copilot_auth.py#L60) |
| function | `cmd_copilot_auth_status` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L84) |
| function | `cmd_configure_copilot_client_id` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L118) |
| function | `cmd_start_copilot_device_flow` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L143) |
| function | `cmd_poll_copilot_token_exchange` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L221) |
| function | `_request_github_device_code` | `()` | — | [src](../../../core/cli/copilot_auth.py#L355) |
| function | `_poll_github_token_exchange` | `(*, device_code, interval)` | — | [src](../../../core/cli/copilot_auth.py#L386) |
| function | `cmd_set_copilot_auth_state` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L449) |
| function | `cmd_start_copilot_oauth_launch_intent` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L559) |
| function | `cmd_launch_copilot_oauth_browser` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L607) |
| function | `cmd_reset_copilot_oauth_launch` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L675) |
| function | `cmd_intake_copilot_oauth_callback` | `(args)` | — | [src](../../../core/cli/copilot_auth.py#L734) |
| function | `_load_provider_credentials_for_action` | `(*, profile, action)` | — | [src](../../../core/cli/copilot_auth.py#L797) |

## `core/cli/http_fallback.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `fetch_visible_run_via_api` | `()` | — | [src](../../../core/cli/http_fallback.py#L10) |
| function | `cancel_visible_run_via_api` | `(run_id)` | — | [src](../../../core/cli/http_fallback.py#L17) |
| function | `request_json` | `(method, path, payload=…)` | — | [src](../../../core/cli/http_fallback.py#L24) |
| function | `http_error_detail` | `(body)` | — | [src](../../../core/cli/http_fallback.py#L55) |

## `core/cli/openai_auth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cmd_openai_auth_status` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L34) |
| function | `cmd_configure_openai_oauth_client` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L52) |
| function | `cmd_start_openai_oauth_launch_intent` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L67) |
| function | `cmd_launch_openai_oauth_browser` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L90) |
| function | `cmd_reset_openai_oauth_launch` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L136) |
| function | `cmd_intake_openai_oauth_callback` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L156) |
| function | `cmd_exchange_openai_oauth_code` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L179) |
| function | `cmd_refresh_openai_oauth_token` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L201) |
| function | `cmd_revoke_openai_oauth` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L221) |
| function | `cmd_print_openai_callback_url` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L240) |
| function | `cmd_import_openai_codex_session` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L257) |
| function | `cmd_await_openai_oauth_callback` | `(args)` | — | [src](../../../core/cli/openai_auth.py#L280) |

## `core/cli/provider_config.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cmd_configure_provider` | `(args)` | — | [src](../../../core/cli/provider_config.py#L28) |
| function | `cmd_configure_coding_lane` | `(args)` | — | [src](../../../core/cli/provider_config.py#L53) |
| function | `cmd_configure_copilot_coding_lane` | `(args)` | — | [src](../../../core/cli/provider_config.py#L84) |
| function | `cmd_configure_openai_oauth_coding_lane` | `(args)` | — | [src](../../../core/cli/provider_config.py#L115) |
| function | `cmd_configure_codex_cli_coding_lane` | `(args)` | — | [src](../../../core/cli/provider_config.py#L148) |
| function | `cmd_configure_local_lane` | `(args)` | — | [src](../../../core/cli/provider_config.py#L180) |
| function | `cmd_select_main_agent` | `(args)` | — | [src](../../../core/cli/provider_config.py#L213) |
| function | `cmd_configure_cheap_provider` | `(args)` | — | [src](../../../core/cli/provider_config.py#L222) |
| function | `cmd_cheap_lane_status` | `(_)` | — | [src](../../../core/cli/provider_config.py#L264) |
| function | `cmd_list_provider_models` | `(args)` | — | [src](../../../core/cli/provider_config.py#L270) |
| function | `cmd_test_provider` | `(args)` | — | [src](../../../core/cli/provider_config.py#L286) |
| function | `cmd_cheap_lane_smoke` | `(args)` | — | [src](../../../core/cli/provider_config.py#L320) |
| function | `cmd_list_cheap_providers` | `(_)` | — | [src](../../../core/cli/provider_config.py#L332) |

## `core/cli/visible_output.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `visible_execution_section` | `(visible_execution, source, api_unavailable)` | — | [src](../../../core/cli/visible_output.py#L4) |
| function | `visible_run_section` | `(visible_run, source, api_unavailable)` | — | [src](../../../core/cli/visible_output.py#L37) |
| function | `capability_invocation_section` | `(capability_invocation, source, api_unavailable)` | — | [src](../../../core/cli/visible_output.py#L56) |
| function | `normalize_visible_authority` | `(authority)` | — | [src](../../../core/cli/visible_output.py#L76) |
| function | `normalize_visible_readiness` | `(readiness)` | — | [src](../../../core/cli/visible_output.py#L85) |
| function | `normalize_visible_identity` | `(visible_identity)` | — | [src](../../../core/cli/visible_output.py#L102) |
| function | `normalize_visible_work` | `(visible_work)` | — | [src](../../../core/cli/visible_output.py#L115) |
| function | `normalize_visible_work_units` | `(items)` | — | [src](../../../core/cli/visible_output.py#L136) |
| function | `normalize_visible_work_notes` | `(items)` | — | [src](../../../core/cli/visible_output.py#L153) |
| function | `normalize_visible_work_surface` | `(visible_work_surface)` | — | [src](../../../core/cli/visible_output.py#L172) |
| function | `normalize_visible_selected_work_surface` | `(visible_selected_work_surface)` | — | [src](../../../core/cli/visible_output.py#L193) |
| function | `normalize_visible_selected_work_item` | `(visible_selected_work_item)` | — | [src](../../../core/cli/visible_output.py#L220) |
| function | `normalize_visible_continuity` | `(visible_continuity)` | — | [src](../../../core/cli/visible_output.py#L247) |
| function | `normalize_visible_session_continuity` | `(visible_session_continuity)` | — | [src](../../../core/cli/visible_output.py#L262) |
| function | `normalize_visible_capability_continuity` | `(visible_capability_continuity)` | — | [src](../../../core/cli/visible_output.py#L288) |
| function | `normalize_active_run` | `(active_run)` | — | [src](../../../core/cli/visible_output.py#L306) |
| function | `normalize_last_outcome` | `(last_outcome)` | — | [src](../../../core/cli/visible_output.py#L319) |
| function | `normalize_capability_invocation` | `(last_invocation)` | — | [src](../../../core/cli/visible_output.py#L334) |
| function | `normalize_persisted_capability_invocations` | `(items)` | — | [src](../../../core/cli/visible_output.py#L351) |
| function | `normalize_approval_requests` | `(items)` | — | [src](../../../core/cli/visible_output.py#L374) |
| function | `normalize_approval` | `(approval)` | — | [src](../../../core/cli/visible_output.py#L398) |
| function | `normalize_visible_capability_use` | `(last_capability_use)` | — | [src](../../../core/cli/visible_output.py#L409) |
| function | `normalize_persisted_recent_runs` | `(items)` | — | [src](../../../core/cli/visible_output.py#L427) |

