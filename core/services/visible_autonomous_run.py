"""Autonome (heartbeat-startede) synlige runs: starter og observation.

Boy Scout-udskillelse (2026-10-07) fra ``core/services/visible_runs.py`` (7.539 linjer): den naermeste
sammenhaengende enhed ved aendringen i ``_stream_visible_run`` - starteren af et autonomt run
(``start_autonomous_run``) og dets udfaldsobservation (``_observe_autonomous_run``). Koden er uaendret bortset fra
at navne der bor i ``visible_runs`` (``VisibleRun``, ``event_bus``, ``load_settings``, ``_stream_visible_run``,
``get_last_visible_run_outcome``) slaas op paa ``visible_runs`` ved KALDET, saa monkeypatches paa det modul
(``monkeypatch.setattr(visible_runs, "load_settings", ...)``) virker som foer. ``visible_runs`` re-eksporterer
begge symboler under de gamle navne.
"""
from __future__ import annotations

import logging
from uuid import uuid4

import core.services.visible_runs as _vr  # noqa: E402  (cirkulaer-sikkert: kun brugt ved kald)

logger = logging.getLogger(__name__)


def _observe_autonomous_run(*, run, session_id: str, outcome: str,
                            frames: int = 0, error: str = "") -> None:
    """#10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den
    Intelligente Central. Før fangede INGEN cluster en autonom run der fejlede/loopede/brændte
    tokens — ingen trace, ingen flag. Nu observe pr. run-udfald. Self-safe. Phase B/C (gradering
    + akkumuleret deterministisk læring pr. run-type) er den adaptive del — bygges bevidst senere."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "autonomous", "nerve": "autonomous_run",
            "run_id": getattr(run, "run_id", ""), "session_id": str(session_id or ""),
            "provider": getattr(run, "provider", ""), "model": getattr(run, "model", ""),
            "outcome": outcome, "frames": int(frames or 0),
            "error": str(error or "")[:160],
        })
    except Exception:
        pass
    # Selv-awareness: Jarvis er ellers BLIND for sine egne autonome runs medmindre
    # han aktivt leder. Drop en nudge i brønden (→ outbound_nudges → hans prompt-
    # awareness) så han bliver bevidst når et run slutter — hvad det gjorde, status,
    # fejl-id (run_id) og en review-invitation. Fejl/afbrud ALTID; completed kun når
    # der faktisk skete noget (frames>0), så trivielle ticks ikke oversvømmer brønden.
    # Redesign 4. sep 2026: "run færdig" er TELEMETRI (event + Central), ikke en
    # besked til Bjørn — 89 % af brøndens 506 nudges/uge var denne linje, 0 blev
    # sendt. Kun fejl/afbrud bliver en proaktiv kandidat (medium → digest når
    # Bjørn har været væk), leveret af proactivity_bridge.
    try:
        _focus = str(getattr(run, "user_message", "") or "")[:160]
        _rid = str(getattr(run, "run_id", "") or "")
        try:
            from core.eventbus.bus import event_bus as _eb_ar
            _eb_ar.publish("runtime.autonomous_run_finished", {
                "run_id": _rid, "outcome": str(outcome or ""), "frames": int(frames or 0),
                "error": str(error or "")[:200], "focus": _focus,
            })
        except Exception:
            pass
        if outcome == "failed":
            _msg = (f"Autonom run ✗ FEJLET [err_id={_rid}]: {_focus} — "
                    f"{str(error or 'ukendt fejl')[:120]} — reviewe?")
        elif outcome in ("interrupted", "looped", "burned"):
            _msg = f"Autonom run ⏸ {outcome} [id={_rid}]: {_focus} — reviewe?"
        else:
            _msg = ""
        if _msg:
            from core.services.proactive_candidates import add_candidate
            add_candidate(source="autonomous_run", kind="autonomous_run_failure",
                          text=_msg, priority="medium")
    except Exception:
        pass
    # #3 supervision: vurdér runnet (korrelér + fang løgn/loop/forbindelsesfejl) + flag.
    try:
        from core.services.autonomous_supervisor import supervise
        supervise(getattr(run, "run_id", ""), outcome, error=str(error or ""))
    except Exception:
        pass


def start_autonomous_run(message: str, session_id: str | None = None, follow: bool = False,
                         origin: str | None = None) -> None:
    """Trigger an autonomous (heartbeat-initiated) visible run in a background thread.

    The run executes the visible model with tools available, persists results to
    the given session (or the dedicated autonomous session), and auto-denies any
    tool that requires user approval (no user is present). Fire-and-forget.

    follow=True: publicér runnets v2-SSE-frames til run_follow-bufferen, så
    jarvis-desk kan token-streame dem live via /chat/sessions/{id}/follow (i
    stedet for at "dumpe" beskeden ind når den er færdig). Bruges af
    operator_wakeup_fired (kører i api-processen → samme proces som follow-
    endpointet → in-memory buffer virker).
    """
    import threading

    # Rotér pr. oprindelse+dag (2026-07-06): et autonomt run uden eksplicit session
    # lander IKKE længere i den ene udødelige "Autonomous"-silo (8373 beskeder, kontekst-
    # fejl, usynlig), men i en afgrænset, kategoriseret `auto-{origin}-{dato}`-session.
    # Eksplicit session_id (discord/telegram/continuation) vinder altid — uændret.
    _origin = None
    if not (session_id or "").strip():
        try:
            from core.services.autonomous_sessions import (
                normalize_origin,
                resolve_autonomous_session,
            )
            _origin = normalize_origin(origin)
            resolved_session = resolve_autonomous_session(_origin)
        except Exception:
            # fail-safe: hvis rotationen svigter, brug et dato-stemplet fallback frem for
            # at genoplive den udødelige silo.
            from core.services.chat_sessions import create_chat_session
            resolved_session = create_chat_session(title="Autonomous")["id"]
    else:
        resolved_session = session_id.strip()

    # Spec D / D1-konsument (første ægte autoritet): når Centralen EJER agendaen (flag ON), kommer et
    # retningsløst autonomt runs RETNING fra Centralens valgte næste-intention — Jarvis handler på SIN
    # EGEN dagsorden, ikke en generisk check-in. Fylder KUN tomrummet (eksplicit besked vinder altid).
    # Default OFF → uændret. Self-safe.
    if not (message or "").strip():
        try:
            from core.services.central_agenda import authoritative_next_intention
            _intent = authoritative_next_intention()
            if _intent and _intent.get("text"):
                message = str(_intent["text"])
        except Exception:
            pass

    settings = _vr.load_settings()
    # Bjørn-regel (2026-07-16): den BETALTE deepseek.com-API er KUN til visible lane.
    # Autonome/baggrunds-runs kører på baggrunds-modellen (default ollama/
    # deepseek-v4.1-flash:cloud). resolve_autonomous_model honorerer stadig lært præference
    # + eksplorations-armen OVENPÅ baggrunds-basen, men hard-guarder mod at lande på den
    # betalte deepseek-provider (lukkede også HTTP-400 ':cloud'-tag-til-deepseek.com-lækken).
    from core.services.central_router_adapt import resolve_autonomous_model as _resolve_auto
    _auto_provider, _auto_model = _resolve_auto(
        autonomous_provider=settings.autonomous_model_provider,
        autonomous_model=settings.autonomous_model_name)

    # MODEL-PARRET SKAL OGSAA TJEKKES HER (10/9-2026). `resolve_safe` blev
    # bygget da `ollama/glm-5.2` viste sig at give 162 tomme svar ud af 162 —
    # men den blev kun koblet paa `start_visible_run`. Den AUTONOME sti gik
    # udenom, og det er praecis dér de tomme koersler kom fra. Fundet fordi
    # afregnings-skyggen blev ved med at melde uenighed paa netop det par.
    #
    # Forskellen fra den synlige sti: her er der INGEN at vise en fejl til.
    # Kan parret ikke afgoeres, beholdes det oprindelige og det siges hoejt —
    # at afvise ville lukke autonomt arbejde helt ned paa en tvivl.
    try:
        from core.services.model_pair_resolver import resolve_safe as _resolve_par
        _p2, _m2, _problem = _resolve_par(_auto_provider, _auto_model)
        if _problem:
            logger.warning("autonomt model-par uafklaret (%s/%s): %s — beholder "
                           "parret", _auto_provider, _auto_model, _problem)
        else:
            if (_p2, _m2) != (_auto_provider, _auto_model):
                logger.info("autonomt model-par oversat: %s/%s -> %s/%s",
                            _auto_provider, _auto_model, _p2, _m2)
            _auto_provider, _auto_model = _p2, _m2
    except Exception:
        logger.warning("autonomt model-par-tjek fejlede — lader parret gaa",
                       exc_info=True)
    run = _vr.VisibleRun(
        run_id=f"autonomous-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=_auto_provider,
        model=_auto_model,
        user_message=(message or "").strip() or "Autonomous heartbeat check-in",
        session_id=resolved_session,
        autonomous=True,
        origin=_origin,
    )
    _vr.event_bus.publish(
        "runtime.autonomous_run_started",
        {
            "run_id": run.run_id,
            "session_id": resolved_session,
            "provider": run.provider,
            "model": run.model,
            "focus": run.user_message[:200],
            "origin": _origin or "autonomous",
            # run_closure_gate bruger dette til at skelne autonome nat-runs
            # (ingen bruger til stede) fra synlige chats — auto-commit af
            # efterladte ændringer må KUN ske når ingen sidder og kigger.
            "autonomous": bool(run.autonomous),
        },
    )
    # Lag 2 — gør den autonome historie synlig for Centralen (og dermed Jarvis' egen
    # proprioception + Central-CLI). Egress-frit: kun oprindelse + liveness, intet indhold.
    try:
        from core.services.central_core import central as _central_auto
        _central_auto().observe({
            "cluster": "autonomous", "nerve": "autonomous_history",
            "kind": "run_started", "origin": _origin or "autonomous",
            "session_id": resolved_session, "run_id": run.run_id,
        })
    except Exception:
        pass

    def _in_thread() -> None:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        consumed_frames = 0
        failed = False
        try:
            async def _consume() -> None:
                nonlocal consumed_frames
                if follow:
                    # Tee runnets frames som v2 → run_follow-buffer (desk-streaming).
                    from core.services.run_follow import (
                        begin_follow,
                        end_follow,
                        publish_follow_frame,
                    )
                    from core.services.visible_runs_sse_v2 import translate_to_v2
                    begin_follow(resolved_session, run.run_id)
                    try:
                        async for frame in translate_to_v2(
                            _vr._stream_visible_run(run),
                            run_id=run.run_id, model=run.model, provider=run.provider,
                            lane=run.lane, session_id=resolved_session,
                            ping_interval_s=10.0,
                        ):
                            consumed_frames += 1
                            publish_follow_frame(resolved_session, frame)
                    finally:
                        end_follow(resolved_session)
                else:
                    async for _ in _vr._stream_visible_run(run):
                        consumed_frames += 1

            loop.run_until_complete(_consume())
        except Exception as exc:
            failed = True
            _vr.event_bus.publish(
                "runtime.autonomous_run_failed",
                {
                    "run_id": run.run_id,
                    "session_id": resolved_session,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "error": str(exc)[:500],
                    "consumed_frames": consumed_frames,
                },
            )
            _observe_autonomous_run(run=run, session_id=resolved_session,
                                    outcome="failed", frames=consumed_frames, error=str(exc))
        finally:
            if not failed:
                outcome = _vr.get_last_visible_run_outcome() or {}
                interrupted = (
                    str(outcome.get("run_id") or "") == run.run_id
                    and str(outcome.get("status") or "") == "interrupted"
                )
                if interrupted:
                    _vr.event_bus.publish(
                        "runtime.autonomous_run_interrupted",
                        {
                            "run_id": run.run_id,
                            "session_id": resolved_session,
                            "provider": run.provider,
                            "model": run.model,
                            "focus": run.user_message[:200],
                            "error": str(outcome.get("error") or "")[:500],
                            "consumed_frames": consumed_frames,
                        },
                    )
                    _observe_autonomous_run(run=run, session_id=resolved_session,
                                            outcome="interrupted", frames=consumed_frames,
                                            error=str(outcome.get("error") or ""))
                    loop.close()
                    return
                _vr.event_bus.publish(
                    "runtime.autonomous_run_completed",
                    {
                        "run_id": run.run_id,
                        "session_id": resolved_session,
                        "provider": run.provider,
                        "model": run.model,
                        "focus": run.user_message[:200],
                        "consumed_frames": consumed_frames,
                        # run_closure_gate: samme flag som started-eventen —
                        # se kommentar der.
                        "autonomous": bool(run.autonomous),
                    },
                )
                _observe_autonomous_run(run=run, session_id=resolved_session,
                                        outcome="completed", frames=consumed_frames)
            loop.close()

    # EJEREN BINDES HVIS INGEN ER BUNDET (24/9-2026).
    #
    # Kopieringen nedenfor er korrekt — den har altid virket. Problemet var at
    # der intet var at kopiere: `dreaming_session` fyrer fra sin egen daemon-
    # traad uden nogen bundet identitet, og saa skrives turens beskeder med tom
    # `user_id`. Sessionslisten kan kun vise en session hvis mindst én besked
    # baerer den spoergendes id (privatlivs-vaernet mod at se andres samtaler),
    # saa de sessioner var usynlige for Bjoern. For evigt.
    #
    # Maalt paa CT105 24/9-2026:
    #
    #     auto-recurring-   8859 beskeder   user_id = 1246415163603816499  <- ses
    #     auto-dream-       3468 beskeder   user_id = tom                  <- ses ikke
    #     auto-heartbeat-   2287 beskeder   user_id = tom                  <- ses ikke
    #     auto-wakeup-      2779 beskeder   user_id = tom                  <- ses ikke
    #
    # `auto-recurring` er den eneste der virker, og kun fordi `scheduled_tasks`
    # selv binder `user_context` foer den fyrer. Derfor hoerer bindingen HER, i
    # den faelles tragt, og ikke hos hver kalder — ellers mangler den naeste
    # oprindelse den igen.
    #
    # `bind_context_if_unset` roerer ikke en eksplicit binding, saa et run
    # discord_gateway har bundet til Michelle forbliver hendes.
    _ejer_token = None
    try:
        from core.identity.owner_resolver import owner_user_id
        from core.identity.workspace_context import bind_context_if_unset
        _ejer = owner_user_id()
        if _ejer:
            _ejer_token = bind_context_if_unset(user_id=_ejer)
    except Exception:
        logger.warning("autonomt run: kunne ikke binde ejeren — turen bliver "
                       "usynlig i sessionslisten", exc_info=True)

    # Propagate ContextVars (workspace_name, user_id) into the new thread.
    # threading.Thread does NOT inherit context by default — without this
    # all downstream code would see default workspace regardless of what
    # discord_gateway bound. This is the pivot for multi-user to work.
    import contextvars as _ctxvars
    _ctx = _ctxvars.copy_context()
    # Kopien er taget; kalderens egen kontekst maa ikke baere bindingen videre.
    if _ejer_token is not None:
        try:
            from core.identity.workspace_context import reset_context
            reset_context(_ejer_token)
        except Exception:
            logger.warning("kunne ikke rulle ejer-bindingen tilbage", exc_info=True)
    threading.Thread(
        target=lambda: _ctx.run(_in_thread),
        name="jarvis-autonomous-run",
        daemon=True,
    ).start()
