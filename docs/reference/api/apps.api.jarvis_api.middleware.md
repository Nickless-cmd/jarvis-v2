# `apps.api.jarvis_api.middleware` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/middleware/__init__.py`

_(no top-level classes or functions)_

## `apps/api/jarvis_api/middleware/anthropic_auth.py`
_x-api-key resolution + workspace binding for Anthropic-compat endpoint._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../apps/api/jarvis_api/middleware/anthropic_auth.py#L22) |
| function | `invalidate_cache` | `()` | — | [src](../../../apps/api/jarvis_api/middleware/anthropic_auth.py#L40) |
| function | `resolve_api_key` | `(api_key, *, dev_mode_open=…)` | Return {'user': str, 'workspace': str} or None for invalid keys. | [src](../../../apps/api/jarvis_api/middleware/anthropic_auth.py#L46) |
| function | `short_key_for_log` | `(api_key)` | Return first 4 chars + length suffix; never log full key. | [src](../../../apps/api/jarvis_api/middleware/anthropic_auth.py#L59) |

## `apps/api/jarvis_api/middleware/api_connection_nerve.py`
_API-forbindelses-nerve middleware — observerer HVER HTTP-request som metadata._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_client_ip` | `(request)` | Ægte klient-IP: første hop i X-Forwarded-For (bag Caddy), ellers direkte peer. | [src](../../../apps/api/jarvis_api/middleware/api_connection_nerve.py#L20) |
| class | `ApiConnectionNerveMiddleware` | `` | — | [src](../../../apps/api/jarvis_api/middleware/api_connection_nerve.py#L33) |
| method | `ApiConnectionNerveMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/api_connection_nerve.py#L34) |

## `apps/api/jarvis_api/middleware/internal_discord.py`
_Internal loopback endpoint for cross-process Discord dispatch._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DispatchRequest` | `` | — | [src](../../../apps/api/jarvis_api/middleware/internal_discord.py#L27) |
| function | `dispatch` | `(req, request)` | — | [src](../../../apps/api/jarvis_api/middleware/internal_discord.py#L33) |

## `apps/api/jarvis_api/middleware/jarvisx_user_routing.py`
_JarvisX user-routing + bearer-token auth middleware._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_public_path` | `(path)` | — | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L92) |
| function | `jarvisx_user_routing_middleware` | `(request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L104) |

## `apps/api/jarvis_api/middleware/security_headers.py`
_Security-headers + let-vægts rate-limiting middleware (spec §20)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_redirect_to_https` | `(*, scheme, x_forwarded_proto, client, path)` | Ren beslutning: skal denne request 301'es til HTTPS? (§20.1) | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L35) |
| class | `HttpsRedirectMiddleware` | `` | HTTP→HTTPS-redirect i-app (§20.1, lag 1) — uden at binde :80 (det ejer uvicorn). | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L49) |
| method | `HttpsRedirectMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L57) |
| class | `SecurityHeadersMiddleware` | `` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L69) |
| method | `SecurityHeadersMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L70) |
| function | `cors_allowed_origins` | `()` | CORS-origins fra env (§20.3). `JARVISX_CORS_ORIGINS` = komma-sepereret | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L79) |
| function | `_rate_limit_config` | `()` | (enabled, max_requests, window_seconds) fra env. Default FRA. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L89) |
| class | `SimpleRateLimitMiddleware` | `` | In-memory per-IP sliding-window rate limit. FRA medmindre env slår den til. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L103) |
| method | `SimpleRateLimitMiddleware.__init__` | `(self, app)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L106) |
| method | `SimpleRateLimitMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L110) |

