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

## `apps/api/jarvis_api/middleware/internal_loopback.py`
_Delt loopback-vagt for /api/internal-ruterne — som DEPENDENCY, ikke som kropskode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `require_loopback` | `(request)` | Rejs 403 hvis kaldet ikke er et ægte, lokalt IPC-kald. | [src](../../../apps/api/jarvis_api/middleware/internal_loopback.py#L41) |

## `apps/api/jarvis_api/middleware/jarvisx_user_routing.py`
_JarvisX user-routing + bearer-token auth middleware._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_log_auth_afvisning` | `(grund, request, raw_auth=…)` | Sig HVORFOR en 401 skete — én gang i minuttet pr. klient og grund. | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L50) |
| function | `_er_lokal_afsender` | `(request)` | Kom kaldet fra loopback eller vores eget net? | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L178) |
| function | `_er_ui_skal` | `(path)` | — | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L202) |
| function | `_er_offentlig_ui_skal` | `(request)` | Lad en fjern PWA hente HTML, JS og CSS uden at åbne data eller maps. | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L206) |
| function | `_is_public_path` | `(path)` | — | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L219) |
| function | `_er_signeret_filhentning` | `(request)` | Er dette en GET af én fil med en gyldig, levende signatur? | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L231) |
| function | `jarvisx_user_routing_middleware` | `(request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/jarvisx_user_routing.py#L289) |

## `apps/api/jarvis_api/middleware/security_headers.py`
_Security-headers + let-vægts rate-limiting middleware (spec §20)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_redirect_to_https` | `(*, scheme, x_forwarded_proto, client, path)` | Ren beslutning: skal denne request 301'es til HTTPS? (§20.1) | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L44) |
| class | `HttpsRedirectMiddleware` | `` | HTTP→HTTPS-redirect i-app (§20.1, lag 1) — uden at binde :80 (det ejer uvicorn). | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L58) |
| method | `HttpsRedirectMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L66) |
| class | `SecurityHeadersMiddleware` | `` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L78) |
| method | `SecurityHeadersMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L79) |
| function | `cors_allowed_origins` | `()` | CORS-origins fra env (§20.3). `JARVISX_CORS_ORIGINS` = komma-sepereret | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L88) |
| function | `_rate_limit_config` | `()` | (enabled, max_requests, window_seconds) fra env. Default TIL. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L98) |
| function | `_authenticated_rate_limit_max` | `()` | Loft for en gyldigt autentificeret app-klient. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L118) |
| function | `_authenticated_subject` | `(request)` | Verificeret token-subjekt, ellers tom streng (aldrig header-tillid). | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L130) |
| function | `_effektiv_klient_ip` | `(request)` | Den IP der skal tælles på — ikke den socket uvicorn ser. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L149) |
| function | `_er_lokal_adresse` | `(ip)` | Loopback/privat/link-local = husets egne klienter. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L175) |
| class | `SimpleRateLimitMiddleware` | `` | In-memory sliding-window limit for public IPs and verified app users. | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L189) |
| method | `SimpleRateLimitMiddleware.__init__` | `(self, app)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L192) |
| method | `SimpleRateLimitMiddleware.dispatch` | `(self, request, call_next)` | — | [src](../../../apps/api/jarvis_api/middleware/security_headers.py#L196) |

