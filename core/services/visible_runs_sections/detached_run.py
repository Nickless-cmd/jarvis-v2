"""Detached (request-uafhængig) bruger-run → server-autoritativt via run_event_log.

Runnet kører i en baggrundstråd og tee'er sine v2-frames til run_event_log[run_id].
HTTP-forbindelser er bare abonnenter. Klient-disconnect aflyser IKKE runnet; det
kører færdigt, persisterer i DB og unregistrerer sig (via gen.aclose i finally).
Log keyed pr. RUN → ingen kollision mellem overlappende runs (A3's fejl elimineret).
"""
from __future__ import annotations

from uuid import uuid4


def start_user_run_detached(
    *,
    message: str,
    session_id: str,
    approval_mode: str = "ask",
    thinking_mode: str = "think",
    force_user_id: str | None = None,
    tool_scope: str = "",
    provider_override: str = "",
    model_override: str = "",
    eff_model: str = "",
    eff_provider: str = "",
    lane: str = "",
) -> str:
    """Start et server-autoritativt run. Returnerer run_id (klienten abonnerer
    via run_event_log gennem /chat/stream/v2 eller /chat/runs/{id}/subscribe)."""
    import contextvars as _ctxvars
    import threading

    import core.services.run_event_log as rel
    from core.services.visible_runs import start_visible_run
    from core.services.visible_runs_sse_v2 import translate_to_v2

    run_id = f"visible-{uuid4().hex}"
    sid = (session_id or "").strip()
    rel.create(run_id, sid)  # synkront FØR retur → straks synlig i live_run_ids

    legacy_iter = start_visible_run(
        message=message,
        session_id=session_id,
        approval_mode=approval_mode,
        thinking_mode=thinking_mode,
        force_user_id=force_user_id,
        tool_scope=tool_scope,
        provider_override=provider_override,
        model_override=model_override,
    )

    def _in_thread() -> None:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()

        async def _consume() -> None:
            gen = translate_to_v2(
                legacy_iter,
                run_id=run_id,
                model=eff_model,
                provider=eff_provider,
                lane=lane,
                session_id=sid,
                ping_interval_s=5.0,
            )
            try:
                async for frame in gen:
                    try:
                        rel.append(run_id, frame)
                    except Exception:
                        pass
            finally:
                try:
                    await gen.aclose()  # -> _stream_visible_run finally -> unregister
                except Exception:
                    pass
                try:
                    rel.mark_done(run_id)
                except Exception:
                    pass
                try:
                    rel.prune()
                except Exception:
                    pass

        try:
            loop.run_until_complete(_consume())
        except Exception:
            try:
                rel.mark_done(run_id)
            except Exception:
                pass
        finally:
            loop.close()

    _ctx = _ctxvars.copy_context()
    threading.Thread(target=lambda: _ctx.run(_in_thread), name="jarvis-user-run", daemon=True).start()
    return run_id
