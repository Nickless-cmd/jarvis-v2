"""Detached (request-uafhængig) bruger-run → live session-broadcast (A3).

Problem: i den oprindelige sti drev FastAPI's StreamingResponse-generator selve
runnet — så når en klient mistede forbindelsen (mobil baggrundede, skærm sov)
blev request-generatoren lukket, hvilket cancellede runnet server-side og
efterlod en zombie active_run-slot.

Fix: kør runnet i en BAGGRUNDSTRÅD der tee'er sine v2-SSE-frames til
run_follow-bufferen pr. session. `/chat/stream/v2` (og enhver anden klient)
*følger* så bare bufferen via run_follow. Klientens forbindelse driver ikke
længere runnet → disconnect aflyser det ikke; runnet kører færdigt, persisterer
sit svar og unregistrerer sig selv (zombie-slot kureret ved roden). En mobil der
vender tilbage re-attacher via GET /chat/sessions/{id}/follow og fanger op.

Nudge-sikkerhed: `start_visible_run` har en midway-nudge-guard (sender man en
besked mens et run kører, fødes den ind i det aktive run i stedet for at starte
et nyt). `begin_follow` NULSTILLER bufferen — det må KUN ske ved et ægte nyt
run. Vi bruger `has_active_follow(session_id)` som signal: er der allerede en
ikke-afsluttet follow-buffer, er et run i gang → behandl som nudge (nulstil
IKKE, tee IKKE — det aktive runs egen tråd ejer bufferen; vi driver bare
iteratoren så followup'en når Jarvis' bevidsthed).
"""
from __future__ import annotations


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
    """Start et bruger-run afkoblet fra request-forbindelsen. Returnerer
    session_id (klienten følger bufferen via run_follow). Fire-and-forget."""
    import contextvars as _ctxvars
    import threading

    from core.services.run_follow import (
        begin_follow,
        end_follow,
        has_active_follow,
        publish_follow_frame,
    )
    from core.services.visible_runs import start_visible_run
    from core.services.visible_runs_sse_v2 import translate_to_v2

    sid = (session_id or "").strip()

    # Ægte nyt run vs nudge: en aktiv (ikke-done) follow-buffer betyder at et run
    # allerede tee'er til denne session → nudge. Kun ved et ægte nyt run nulstiller
    # vi bufferen (synkront, FØR vi returnerer, så klientens follow-respons ser en
    # frisk, ikke-done buffer i stedet for at replaye et tidligere afsluttet svar).
    fresh = not has_active_follow(sid)
    if fresh:
        try:
            begin_follow(sid, "")
        except Exception:
            pass

    # Guard'en i start_visible_run kører her (stuck-clear + nudge-interception).
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
                run_id="",
                model=eff_model,
                provider=eff_provider,
                lane=lane,
                session_id=sid,
                ping_interval_s=5.0,
            )
            if fresh:
                try:
                    async for frame in gen:
                        try:
                            publish_follow_frame(sid, frame)
                        except Exception:
                            pass
                finally:
                    try:
                        end_follow(sid)
                    except Exception:
                        pass
            else:
                # Nudge: driv iteratoren (så followup'en injiceres i det aktive
                # run) men tee IKKE — det aktive runs tråd ejer bufferen.
                async for _frame in gen:
                    pass

        try:
            loop.run_until_complete(_consume())
        except Exception:
            # Sidste-udvej: hvis et ægte run dør hårdt, markér bufferen done så
            # følgende klienter ikke poller i det uendelige.
            if fresh:
                try:
                    end_follow(sid)
                except Exception:
                    pass
        finally:
            loop.close()

    # ContextVars (workspace_name, user_id) skal propageres ind i tråden — ellers
    # ser downstream-kode default-workspace uanset hvad routen bandt.
    _ctx = _ctxvars.copy_context()
    threading.Thread(
        target=lambda: _ctx.run(_in_thread),
        name="jarvis-user-run",
        daemon=True,
    ).start()

    return sid
