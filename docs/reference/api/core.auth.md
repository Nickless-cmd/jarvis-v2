# `core.auth` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/auth/__init__.py`

_(no top-level classes or functions)_

## `core/auth/copilot_oauth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_copilot_oauth_truth` | `(*, profile)` | — | [src](../../../core/auth/copilot_oauth.py#L22) |
| function | `save_copilot_oauth_credentials` | `(*, profile, credentials)` | — | [src](../../../core/auth/copilot_oauth.py#L65) |
| function | `get_copilot_oauth_credentials` | `(*, profile)` | — | [src](../../../core/auth/copilot_oauth.py#L75) |

## `core/auth/copilot_session.py`
_GitHub Copilot session-token exchange._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_oauth_access_token` | `(*, profile)` | — | [src](../../../core/auth/copilot_session.py#L33) |
| function | `_exchange_for_session` | `(oauth_token)` | — | [src](../../../core/auth/copilot_session.py#L47) |
| function | `get_copilot_session_token` | `(*, profile)` | Return a valid Copilot session bearer token, exchanging & caching as needed. | [src](../../../core/auth/copilot_session.py#L81) |
| function | `get_cached_session_endpoints` | `(*, profile)` | — | [src](../../../core/auth/copilot_session.py#L107) |
| function | `invalidate_session_cache` | `(*, profile=…)` | — | [src](../../../core/auth/copilot_session.py#L115) |

## `core/auth/openai_oauth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_openai_oauth_truth` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L40) |
| function | `load_openai_oauth_config` | `()` | — | [src](../../../core/auth/openai_oauth.py#L84) |
| function | `save_openai_oauth_config` | `(*, client_id, authorize_url=…, token_url=…, scopes=…, audience=…, redirect_base_url=…, callback_path=…)` | — | [src](../../../core/auth/openai_oauth.py#L111) |
| function | `get_openai_callback_url` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L142) |
| function | `build_openai_launch_intent` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L147) |
| function | `save_openai_callback` | `(*, profile, callback_url)` | — | [src](../../../core/auth/openai_oauth.py#L202) |
| function | `exchange_openai_callback_code` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L234) |
| function | `refresh_openai_access_token` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L267) |
| function | `get_openai_bearer_token` | `(*, profile, auto_reimport=…)` | — | [src](../../../core/auth/openai_oauth.py#L292) |
| function | `import_openai_codex_session` | `(*, profile)` | — | [src](../../../core/auth/openai_oauth.py#L321) |
| function | `_post_openai_token_request` | `(*, token_url, payload)` | — | [src](../../../core/auth/openai_oauth.py#L358) |
| function | `_jwt_claim` | `(token, key)` | — | [src](../../../core/auth/openai_oauth.py#L379) |
| function | `_jwt_expiry_iso` | `(token)` | — | [src](../../../core/auth/openai_oauth.py#L384) |
| function | `_decode_jwt_payload` | `(token)` | — | [src](../../../core/auth/openai_oauth.py#L392) |
| function | `_store_openai_token_response` | `(*, profile, credentials, token_data)` | — | [src](../../../core/auth/openai_oauth.py#L408) |
| function | `_generate_code_verifier` | `()` | — | [src](../../../core/auth/openai_oauth.py#L444) |
| function | `_pkce_code_challenge` | `(verifier)` | — | [src](../../../core/auth/openai_oauth.py#L448) |
| function | `_is_expired` | `(expires_at_raw)` | — | [src](../../../core/auth/openai_oauth.py#L453) |
| function | `execute_codex_responses` | `(*, message, model=…, profile=…, instructions=…, timeout=…)` | Execute a prompt via the Codex Responses API (chatgpt.com). | [src](../../../core/auth/openai_oauth.py#L479) |
| function | `codex_responses_health_check` | `(*, profile=…)` | Quick health check: verify Codex Responses API is reachable with valid auth. | [src](../../../core/auth/openai_oauth.py#L584) |

## `core/auth/profiles.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_auth_profile` | `(profile)` | — | [src](../../../core/auth/profiles.py#L14) |
| function | `list_auth_profiles` | `()` | — | [src](../../../core/auth/profiles.py#L35) |
| function | `save_provider_credentials` | `(*, profile, provider, credentials)` | — | [src](../../../core/auth/profiles.py#L53) |
| function | `get_provider_state` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L86) |
| function | `get_provider_state_view` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L94) |
| function | `get_provider_credentials` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L183) |
| function | `provider_has_real_credentials` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L197) |
| function | `get_provider_auth_material_kind` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L227) |
| function | `get_provider_oauth_state` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L260) |
| function | `get_provider_launch_result_state` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L297) |
| function | `get_provider_launch_freshness` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L320) |
| function | `get_provider_callback_validation_state` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L349) |
| function | `get_provider_exchange_readiness` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L374) |
| function | `get_provider_callback_intent_consistency` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L405) |
| function | `revoke_provider` | `(*, profile, provider)` | — | [src](../../../core/auth/profiles.py#L443) |
| function | `_profile_dir` | `(profile)` | — | [src](../../../core/auth/profiles.py#L460) |
| function | `_validate_provider` | `(provider)` | — | [src](../../../core/auth/profiles.py#L466) |
| function | `_read_json` | `(path)` | — | [src](../../../core/auth/profiles.py#L472) |
| function | `_existing_or_now` | `(path, key)` | — | [src](../../../core/auth/profiles.py#L476) |
| function | `_now` | `()` | — | [src](../../../core/auth/profiles.py#L483) |

