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
    run_id: str | None = None,
    local_tool_exec: bool = False,
) -> str:
    """Start et server-autoritativt run. Returnerer run_id (klienten abonnerer
    via run_event_log gennem /chat/stream/v2 eller /chat/runs/{id}/subscribe)."""
    import contextvars as _ctxvars
    import threading

    import core.services.run_event_log as rel
    from core.services.visible_runs import start_visible_run
    from core.services.visible_runs_sse_v2 import translate_to_v2

    sid = (session_id or "").strip()
    if not run_id:
        run_id = f"visible-{uuid4().hex}"
        rel.create(run_id, sid)  # synkront FØR retur → straks synlig i live_run_ids
    # ellers: run_id er allerede claimet+oprettet atomisk af claim_or_create

    legacy_iter = start_visible_run(
        message=message,
        session_id=session_id,
        approval_mode=approval_mode,
        thinking_mode=thinking_mode,
        force_user_id=force_user_id,
        tool_scope=tool_scope,
        provider_override=provider_override,
        model_override=model_override,
        local_tool_exec=local_tool_exec,
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
                # Ryd den globale active-visible-run-singleton for DENNE session.
                # Den detached-sti er nu single-flight via run_event_log
                # (claim_or_create), men start_visible_run's gamle globale slot
                # bliver IKKE ryddet pålideligt: translate_to_v2 breaker på 'done'
                # uden at udtømme legacy_iter, så _stream_visible_run's finally
                # (unregister) aldrig kører — slottet bliver hængende "active".
                # Næste besked inden for 120s ramte så den gamle midway-nudge-
                # interception (nudge_system_enabled defaulter True) → _midway_ack
                # → TOM stream → desktop "Forbindelse afbrudt" (rod-årsag fundet
                # 2026-06-19). Single-flight garanterer at intet andet run for
                # sessionen er aktivt når dette run er done → sikkert at rydde.
                try:
                    from core.services.visible_runs import (
                        _get_active_visible_run_state,
                        _set_active_visible_run,
                    )
                    _st = _get_active_visible_run_state() or {}
                    if str(_st.get("session_id") or "") == sid:
                        _set_active_visible_run({})
                except Exception:
                    pass
                try:
                    from core.services.push_dispatcher import on_run_done
                    on_run_done(run_id)
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
    # ATOMISK claim (rod-fix mod rapid-resend-race): find-eller-opret under laas.
    claimed, is_new = rel.claim_or_create(sid)
    if not is_new:
        if nudge_enabled:
            try:
                from core.services.outbound_nudges import push_nudge
                push_nudge(
                    source="user_midway_followup",
                    kind="other",
                    message=(message or "").strip(),
                    importance="high",
                    parent_session_id=sid,
                    # Korrelér nudgen til det LIVE run vi hægtede os på. Før refererede
                    # dette en udefineret `existing` → NameError slugt af bare-except →
                    # nudgen mistede sin parent-reference. `claimed` er run_id'et
                    # claim_or_create returnerede (det kørende run).
                    parent_message_id=claimed,
                )
            except Exception:
                pass
        return claimed, True

    run_id = start_user_run_detached(message=message, session_id=session_id, run_id=claimed, **kw)
    return run_id, False
