"""Active-run discovery and replayable SSE follow routes.

Extracted from :mod:`routes.chat` before changing cross-process delivery.  The
module deliberately preserves the existing behavior; owner routing and status
classification are layered onto this boundary in the next tasks.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from apps.api.jarvis_api.routes.chat_session_view import kraev_adgang
from core.services.run_stream_locator import (
    RunStreamLocation,
    active_locations,
    live_run_for_session,
    locate_run,
)
from core.services.run_stream_proxy import (
    local_frame_generator,
    proxy_owner_stream,
    stream_error,
)

router = APIRouter(prefix="/chat", tags=["chat"])


# 3/10-2026: loft for hvor laenge et AABENT run maa holde indikatoren taendt.
_AKTIVE_RUNS_ALDER_LOFT_S = 600.0

# Stilstands-loft for den DELTE journal (13/10-2026).
_JOURNAL_STILSTAND_LOFT_S = 1800.0


def _journal_sessions() -> list[dict]:
    """Sessioner med et levende run i den delte journal."""
    try:
        from core.services import in_flight_runs as _ifr

        return [
            {
                "session_id": str(record.get("session_id") or ""),
                "run_id": str(record.get("run_id") or ""),
                "status": "working",
            }
            for record in _ifr.levende_koersler(
                max_alder_s=_JOURNAL_STILSTAND_LOFT_S
            )
            if str(record.get("session_id") or "")
        ]
    except Exception:  # journal discovery is best-effort; active-runs remains available
        return []


@router.get("/active-runs")
def chat_active_runs() -> dict:
    """Sessioner med et aktivt visible-run lige nu."""
    from core.runtime.settings import load_settings
    from core.identity.session_access import maa_tilgaa_session

    authoritative = bool(load_settings().server_authoritative_runs)
    session_ids: list[str] = []
    sessions: list[dict] = []
    try:
        locations = active_locations(max_idle_s=_JOURNAL_STILSTAND_LOFT_S)
    except Exception:
        locations = []
    for location in locations:
        session_id = location.session_id
        if not session_id or session_id in session_ids:
            continue
        try:
            allowed = maa_tilgaa_session(session_id)
        except Exception:
            allowed = False
        if not allowed:
            continue
        session_ids.append(session_id)
        item = {
            "session_id": session_id,
            "run_id": location.run_id if authoritative else "",
            "status": "working",
        }
        if authoritative:
            try:
                from core.services.research_store import active_for_session

                research = active_for_session(session_id)
                if research:
                    item.update(
                        {
                            "research_run_id": str(research["id"]),
                            "research_status": str(research["status"]),
                            "research_tier": str(research["tier"]),
                        }
                    )
            except Exception:  # optional research enrichment must not hide the run
                pass
        sessions.append(item)
    return {"session_ids": session_ids, "sessions": sessions}


async def subscribe_authorized(
    location: RunStreamLocation,
    from_idx: int,
):
    """Authorize and resolve one stream without inventing completion."""
    if location.session_id:
        kraev_adgang(location.session_id)
    if location.local_available:
        return StreamingResponse(
            local_frame_generator(location.run_id, from_idx),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Run-Id": location.run_id},
        )
    if location.lifecycle == "running" and location.producer_process in {
        "api",
        "runtime",
    }:
        return await proxy_owner_stream(location, from_idx)
    if location.lifecycle == "running":
        raise stream_error(
            503,
            "stream_unavailable",
            retry_after=1,
            run_id=location.run_id,
        )
    if location.lifecycle in {"terminal", "stale_owner"}:
        raise stream_error(410, "stream_pruned", run_id=location.run_id)
    raise stream_error(404, "run_unknown", run_id=location.run_id)


@router.get("/runs/{run_id}/subscribe")
async def chat_run_subscribe(run_id: str, from_idx: int = 0):
    """Gen-abonner paa et server-autoritativt run fra et offset."""
    return await subscribe_authorized(locate_run(run_id), from_idx)


@router.get("/sessions/{session_id}/live")
async def chat_session_live(session_id: str):
    """Attach til sessionens aktive run fra offset nul."""
    from fastapi import Response

    kraev_adgang(session_id)
    location = live_run_for_session(session_id)
    if location is None:
        return Response(status_code=204)
    return await subscribe_authorized(location, 0)


@router.get("/sessions/{session_id}/follow")
async def chat_session_follow(session_id: str):
    """Token-stream det aktive autonome run i sessionen."""
    import asyncio

    from fastapi.responses import StreamingResponse

    import core.services.run_event_log as rel
    from core.services.run_follow import snapshot_from

    kraev_adgang(session_id)

    async def _gen():
        idx = 0
        empty_polls = 0
        saw_stop = False
        while True:
            frames, done, idx = snapshot_from(session_id, idx)
            for frame in frames:
                if "message_stop" in frame:
                    saw_stop = True
                yield frame
            if done:
                if not saw_stop:
                    run_id = rel.active_run_for_session(session_id) or ""
                    yield rel.synthetic_terminal_frame(
                        run_id, session_id, reason="run_done_no_stop"
                    )
                break
            if frames:
                empty_polls = 0
            else:
                empty_polls += 1
                if empty_polls > 150:
                    run_id = rel.active_run_for_session(session_id) or ""
                    yield rel.synthetic_terminal_frame(
                        run_id, session_id, reason="session_follow_idle"
                    )
                    break
            await asyncio.sleep(0.08)

    return StreamingResponse(_gen(), media_type="text/event-stream")
