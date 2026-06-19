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


def start_or_attach_user_run(
    *,
    message: str,
    session_id: str,
    nudge_enabled: bool = True,
    **kw,
) -> tuple[str, bool]:
    """Single-flight pr. session for server-autoritative runs.

    Jarvis' visible-run-motor er single-flight pr. session (active-run-singleton
    + nudge-interception). To SAMTIDIGE detached runs i samme session klobber
    hinandens slot → begge fejler (det første run = 0 frames, bliver aldrig done;
    verificeret rod-årsag 2026-06-19). run_event_log er den pålidelige autoritet
    fordi ``create()`` er synkron og registrerer FØR det ~14s prompt-assembly —
    modsat active-run-slotten der først sættes sent og derfor har et race-vindue.

    Hvis sessionen allerede har et LIVE detached run: spawn IKKE et nyt. Injicér
    beskeden som high-importance nudge (så Jarvis ser den når den kørende tur
    fortsætter) og returnér det kørende run_id — klienten abonnerer da på det
    igangværende svar. Ellers start et frisk run.

    Returnerer ``(run_id, attached)`` hvor ``attached`` er True hvis vi hægtede os
    på et eksisterende run i stedet for at starte et nyt.
    """
    import core.services.run_event_log as rel

    sid = (session_id or "").strip()
    existing = rel.active_run_for_session(sid)
    if existing and rel.is_live(existing):
        if nudge_enabled:
            try:
                from core.services.outbound_nudges import push_nudge
                push_nudge(
                    source="user_midway_followup",
                    kind="other",
                    message=(message or "").strip(),
                    importance="high",
                    parent_session_id=sid,
                    parent_message_id=existing,
                )
            except Exception:
                pass
        return existing, True

    run_id = start_user_run_detached(message=message, session_id=session_id, **kw)
    return run_id, False
