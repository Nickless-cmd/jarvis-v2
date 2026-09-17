"""Detached (request-uafhængig) bruger-run → server-autoritativt via run_event_log.

Runnet kører i en baggrundstråd og tee'er sine v2-frames til run_event_log[run_id].
HTTP-forbindelser er bare abonnenter. Klient-disconnect aflyser IKKE runnet; det
kører færdigt, persisterer i DB og unregistrerer sig (via gen.aclose i finally).
Log keyed pr. RUN → ingen kollision mellem overlappende runs (A3's fejl elimineret).
"""
from __future__ import annotations

import logging
from uuid import uuid4


logger = logging.getLogger(__name__)


def start_user_run_detached(
    *,
    message: str,
    original_message: str | None = None,
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
    research_mode: bool = False,
) -> str:
    """Start et server-autoritativt run. Returnerer run_id (klienten abonnerer
    via run_event_log gennem /chat/stream/v2 eller /chat/runs/{id}/subscribe)."""
    import contextvars as _ctxvars
    import threading

    import core.services.run_event_log as rel
    from core.services.visible_runs_sse_v2 import translate_to_v2

    sid = (session_id or "").strip()
    if not run_id:
        run_id = f"visible-{uuid4().hex}"
        rel.create(run_id, sid)  # synkront FØR retur → straks synlig i live_run_ids
    # ellers: run_id er allerede claimet+oprettet atomisk af claim_or_create

    visible_args = {
        "message": message,
        "session_id": session_id,
        "approval_mode": approval_mode,
        "thinking_mode": thinking_mode,
        "force_user_id": force_user_id,
        "tool_scope": tool_scope,
        "provider_override": provider_override,
        "model_override": model_override,
        "local_tool_exec": local_tool_exec,
    }
    if research_mode:
        from core.services.research_orchestrator import research_enabled, stream_research_run
        legacy_iter = stream_research_run(
            original_query=original_message,
            visible_run_id=run_id,
            **visible_args,
        ) if research_enabled() else None
    else:
        legacy_iter = None
    if legacy_iter is None:
        from core.services.visible_runs import start_visible_run
        legacy_iter = start_visible_run(**visible_args)

    import time as _time
    _startet = _time.monotonic()
    # Ny tur: den forrige turs udfald maa ikke kunne arves (auto_continuation).
    try:
        from core.services.auto_continuation import glem_session_udfald
        glem_session_udfald(sid)
    except Exception:
        pass

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
            aliaseret = False
            try:
                async for frame in gen:
                    try:
                        rel.append(run_id, frame)
                    except Exception:
                        pass
                    # Runnets eget id kommer i system_event(kind=run) — det er
                    # det id klienten genoptager med. Se run_event_log._ALIASER.
                    if not aliaseret and '"run"' in frame and "system_event" in frame:
                        eget = rel.run_id_fra_ramme(frame)
                        if eget:
                            rel.alias(eget, run_id)
                            aliaseret = True
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
                # ── AUTO-FORTSAETTELSE ────────────────────────────────────
                # EFTER mark_done: single-flight ville ellers se dette run som
                # stadig levende og haenge fortsaettelsen paa det doede run.
                try:
                    _fortsaet_hvis_budgettet_loeb_toert(
                        run_id=run_id, sid=sid, startet=_startet,
                        visible_args=visible_args, eff_model=eff_model,
                        eff_provider=eff_provider, lane=lane,
                    )
                except Exception:
                    logger.exception("auto-fortsaettelse fejlede for %s", run_id)
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
        except BaseException:
            # DEN TAVSE SLUGER (Bjoern 13/9-2026). Her loeber HELE svaret. Foer
            # stod der `except Exception: mark_done()` og ikke ét ord mere — saa
            # naar noget gik galt herinde, fik brugeren 200 OK, en valgt udbyder,
            # et run-id, og derefter absolut stilhed. Ingen fejl, intet svar,
            # ingen raekke i visible_runs. Eneste udvej var at skrive «Forsæt» og
            # slaa terningen igen; maalt 24 gange paa ét doegn.
            #
            # `BaseException`, ikke `Exception`: en CancelledError herinde er
            # netop den slags der forsvandt sporloest.
            logger.exception(
                "detached-run KRAKKEDE run_id=%s session=%s — svaret naaede aldrig brugeren",
                run_id, sid,
            )
            # Og saa skal klienten VIDE det. Uden en terminal frame bliver
            # telefonen staaende i «arbejder» til den giver op af sig selv.
            try:
                rel.append(run_id, rel.synthetic_terminal_frame(
                    run_id, sid, reason="detached_run_crashed"))
            except Exception:
                logger.warning("kunne ikke sende terminal-frame for %s", run_id)
            try:
                rel.mark_done(run_id)
            except Exception:
                logger.warning("kunne ikke markere %s som done", run_id)
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
    if bool(kw.get("research_mode")):
        try:
            from core.services.research_store import active_for_session, add_steer
            active = active_for_session(sid)
            if active:
                add_steer(str(active["id"]), message)
                if str(active.get("tier") or "") == "orchestrated":
                    nudge_enabled = False
        except Exception:
            pass
    # En AEGTE brugerbesked nulstiller kaeden og markerer at han er paa
    # tasterne. Fortsaettelser gaar uden om denne funktion (de kalder
    # start_user_run_detached direkte), saa de taeller ikke med her.
    try:
        from core.services.auto_continuation import noter_brugerbesked
        noter_brugerbesked(sid)
    except Exception:
        pass
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


def _fortsaet_hvis_budgettet_loeb_toert(
    *, run_id: str, sid: str, startet: float,
    visible_args: dict, eff_model: str, eff_provider: str, lane: str,
) -> None:
    """Start en fortsættelse når terminal-policyen klassificerede segmentet
    som resumérbart.

    Beslutningen ligger i `auto_continuation.beslut`, som er ren og proevet fra
    alle kanter. Her er kun ledningen: hent kendsgerningerne, spoerg, og start.

    Grunden logges ALTID — ogsaa naar svaret er nej. En fortsaettelse der
    udebliver skal kunne forklares uden at laese koden.
    """
    from core.services import auto_continuation as ac

    try:
        from core.runtime.settings import load_settings
        _slaaet_til = bool(getattr(load_settings(), "auto_continuation_enabled", True))
    except Exception:
        _slaaet_til = True

    _exit_reason = ac.hent_udfald(run_id, sid)
    beslutning = ac.beslut(
        exit_reason=_exit_reason,
        slaaet_til=_slaaet_til,
        # Denne sti er brugerens; autonome runs kommer aldrig herigennem.
        autonom=False,
        kaede_nr=ac.kaede_nr(sid),
        bruger_skrev_imens=ac.bruger_skrev_efter(sid, startet),
    )
    if not beslutning.fortsaet:
        logger.info("auto-fortsaettelse NEJ run_id=%s: %s", run_id, beslutning.grund)
        return

    # A continuation spawned after SIGTERM inherits a process that is already
    # being torn down. It can only be cut off again, consume the chain limit,
    # and replace a useful checkpoint with noise. The durable checkpoint is
    # instead surfaced by the boot/session recovery path after restart.
    try:
        from core.runtime.process_lifecycle import lukker_ned
        if lukker_ned():
            logger.info(
                "auto-fortsaettelse UDSAT run_id=%s: processen lukker ned; "
                "checkpointet bevares til genoptagelse",
                run_id,
            )
            return
    except Exception:
        pass

    nr = ac.kaede_nr(sid) + 1
    ac.saet_kaede(sid, nr)
    logger.info("auto-fortsaettelse JA run_id=%s: %s", run_id, beslutning.grund)

    nye = dict(visible_args)
    nye["message"] = ac.fortsaettelses_besked(nr, reason=_exit_reason)
    nye.pop("session_id", None)
    start_user_run_detached(
        session_id=sid, eff_model=eff_model, eff_provider=eff_provider,
        lane=lane, **nye,
    )
