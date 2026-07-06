"""API-forbindelses-nerve middleware — observerer HVER HTTP-request som metadata.

Bjørn (6. jul): Jarvis skal kunne "se og mærke nye forbindelser via sin api ... hvilke ip,
session/user id, aktive, last aktiv. og fejl.. ikke privat samtaler."

GDPR: METADATA-ONLY. Vi rører ALDRIG request- eller response-body — kun ip/metode/sti/status/
latens/user/session/tid. Klient-IP tages fra X-Forwarded-For (API'et kører bag Caddy-proxy).

HÅRDT INVARIANT: self-safe. Nerven må ALDRIG kunne fejle et request — al registrering i
try/except, og en fejl i nerven propagerer aldrig til klienten.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def _client_ip(request: Request) -> str:
    """Ægte klient-IP: første hop i X-Forwarded-For (bag Caddy), ellers direkte peer."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    try:
        return request.client.host if request.client else "unknown"
    except Exception:
        return "unknown"


class ApiConnectionNerveMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        status = 0
        err_name = ""
        try:
            response = await call_next(request)
            status = int(getattr(response, "status_code", 0) or 0)
            return response
        except Exception as exc:
            # request fejlede i en indre lag → registrér som 500 m. exception-TYPE (ikke besked,
            # for ikke at lække indhold), og re-raise så fejl-håndteringen er uændret.
            status = 500
            err_name = type(exc).__name__
            raise
        finally:
            try:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                # user_id: sat af jarvisx_user_routing-middleware i scope-state (delt på tværs af lag)
                uid = ""
                try:
                    uid = str(getattr(request.state, "jarvis_user_id", "") or "")
                except Exception:
                    uid = ""
                sid = ""
                try:
                    sid = str(request.query_params.get("session_id") or "")
                except Exception:
                    sid = ""
                from core.services.api_connection_nerve import record
                record(
                    ip=_client_ip(request),
                    method=request.method,
                    path=request.url.path,
                    status=status,
                    latency_ms=latency_ms,
                    user_id=uid,
                    session_id=sid,
                    error=err_name,
                )
            except Exception:
                pass
