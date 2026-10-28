"""Loopback-only endpoint serving the current process' run frame log."""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.services.jarvisx_bridge import (
    _INTERNAL_TOKEN_HEADER,
    internal_dispatch_token,
)
from core.services.run_stream_proxy import local_frame_generator

from apps.api.jarvis_api.middleware.internal_loopback import require_loopback

router = APIRouter(dependencies=[Depends(require_loopback)])
logger = logging.getLogger(__name__)
_LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}


@router.get("/api/internal/run-stream/{run_id}")
async def internal_run_stream(
    request: Request,
    run_id: str,
    from_idx: int = 0,
):
    client_host = request.client.host if request.client else None
    if client_host not in _LOCALHOST_HOSTS:
        logger.warning("internal-run-stream rejected non-localhost host=%s", client_host)
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if request.headers.get("x-forwarded-for") or request.headers.get("forwarded"):
        logger.warning("internal-run-stream rejected proxy-forwarded request")
        return JSONResponse({"error": "forbidden"}, status_code=403)

    expected = internal_dispatch_token()
    provided = request.headers.get(_INTERNAL_TOKEN_HEADER, "")
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        logger.warning("internal-run-stream rejected bad/missing token")
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    from core.services import run_event_log

    # Local lookup only. Never consult the cross-process locator here: doing so
    # could proxy back to the caller and create a forwarding loop.
    if run_event_log.session_for_run(run_id) is None:
        return JSONResponse({"error": "run_not_local"}, status_code=404)
    return StreamingResponse(
        local_frame_generator(run_id, from_idx),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Run-Id": run_id},
    )
