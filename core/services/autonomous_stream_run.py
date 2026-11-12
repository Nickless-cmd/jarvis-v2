"""PENSIONERET — den autonome startvej er `visible_autonomous_run.start_autonomous_run`.

MÅLT 12/11-2026: `start_autonomous_stream_run` importeres IKKE i produktionen.
`grep -rn "import.*autonomous_stream_run" --include=*.py core/ apps/` giver nul
hits uden for modulet selv, og der findes ingen dynamisk reference (ingen
`getattr`, `importlib` eller registry-streng peger på den). Kun tests kalder den:
`tests/test_autonomous_stream_run.py`, `tests/e2e/test_wakeup_guard_e2e.py`,
`tests/test_autonomi_koordinering_fem_steps.py` og `tests/test_wakeup_dispatch_trace.py`.

Den LEVENDE vej er `core.services.visible_autonomous_run.start_autonomous_run`,
som har 13 produktionskaldere (session_spawn, inbox_idle_waker, recurring_tasks,
dreaming_session, discord_gateway, telegram_gateway, jarvisx_processes m.fl.).

Modulet bliver stående fordi testene dækker adfærd der stadig gælder
(permissions-arv, `auto-*`-siloer), men ni produktions-kommentarer henviser til
det som om det er en aktiv startvej — og det får en læser til at bygge
begrundelser på en vej der ikke kører. Det skete i commit 841723595.
Ret kommentaren dér, ikke koden her, hvis du finder flere.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _trust_for_session(session_id: str) -> bool:
    """Samtalens tilladelses-niveau — fail-closed til `ask`.

    Kørslen skal fortsætte som samtalen allerede er sat (Bjørn 21/10-2026).
    Kan niveauet ikke læses, arves intet: en tvivl skal koste et spørgsmål,
    ikke en mutation.
    """
    try:
        from core.services.session_permission import trust_for_session

        return bool(trust_for_session(session_id))
    except Exception:  # noqa: BLE001 — en læsefejl må ikke åbne adgang
        logger.debug("kunne ikke læse permissions for %s", session_id, exc_info=True)
        return False


def _trust_for_autonomous(session_id: str) -> bool:
    """Arv for et AUTONOMT run — en silo låner ejerens niveau (9/11-2026).

    Se `session_permission.trust_for_autonomous`: en `auto-*`-silo er født
    `ask` og har ingen bruger bag sig, så dens eget svar er meningsløst.
    Fail-closed til `ask`.
    """
    try:
        from core.services.session_permission import trust_for_autonomous

        return bool(trust_for_autonomous(session_id))
    except Exception:  # noqa: BLE001 — en læsefejl må ikke åbne adgang
        logger.debug("kunne ikke læse autonom-permissions for %s",
                     session_id, exc_info=True)
        return False


def start_autonomous_stream_run(
    message: str,
    *,
    session_id: str | None,
    origin: str = "autonomous",
    task_id: str = "",
    permission_session: str | None = None,
) -> None:
    """Start autonomous work and relay its v2 frames through ``run_event_log``.

    Governance jobs, including wakeup dispatch, run in the API process. Registering
    before the worker starts makes the run immediately visible to ``/active-runs``
    and attachable through ``/sessions/{id}/live``.

    ``permission_session`` er hvor tilladelses-niveauet læses fra, når det ikke
    er ``session_id``. En vækning lander i en `auto-*`-silo (som er født `ask`),
    men blev BOOKET i Bjørns samtale — og det er den samtales niveau, han gav
    (målt 9/11-2026: alle hans vækninger bærer `chat-52d75bf…` = `trust`, mens
    siloen stod `ask`, så hver vækning rejste et kort han ikke sad og svarede
    på). Tom = samme session som før; adfærden er uændret for alle andre.
    """
    import contextvars
    import threading
    from uuid import uuid4

    import core.services.visible_runs as vr
    from core.services.autonomous_frame_relay import AutonomousFrameRelay
    from core.services.central_router_adapt import resolve_autonomous_model

    sid = (session_id or "").strip()
    if not sid:
        from core.services.autonomous_sessions import (
            normalize_origin,
            resolve_autonomous_session,
        )

        sid = resolve_autonomous_session(normalize_origin(origin))

    # FÆLLES CROSS-PROCES-VAGT (13/10-2026). Se `core/services/run_guard.py`.
    # Denne sti er wakeup-dispatcherens — den der fyrede sit eget run mens
    # Bjørn var midt i en tur, fordi vagten spurgte en PROCES-LOKAL log.
    try:
        from core.services.run_guard import blokeringsgrund

        _vagt = blokeringsgrund(str(origin or ""), sid)
    except Exception:  # noqa: BLE001 — self-safe: kan vagten ikke laeses, starter runnet
        _vagt = ""
    if _vagt:
        logger.info(
            "autonomt stream-run afvist af run-guarden: %s (session=%s origin=%s)",
            _vagt, sid[:24], origin,
        )
        # Samme hul som i `visible_autonomous_run` (målt 14/10-2026): afvisningen
        # loggede og returnerede uden at skrive noget. Forpligtelsen lægges nu i
        # indbakken med sin samtale, så den ikke forsvinder sporløst.
        try:
            from core.services.run_guard import parker_forpligtelse

            parker_forpligtelse(
                origin=str(origin or ""),
                session_id=sid,
                beskrivelse=str(message or "")[:400],
            )
        except Exception:  # noqa: BLE001 — self-safe
            logger.debug("autonomous_stream_run: kunne ikke parkere forpligtelsen",
                         exc_info=True)
        return

    settings = vr.load_settings()
    provider, model = resolve_autonomous_model(
        autonomous_provider=settings.autonomous_model_provider,
        autonomous_model=settings.autonomous_model_name,
    )
    # SAMTALENS MODEL (12/11-2026): samme regel som `start_autonomous_run`, og samme
    # funktion — to veje må ikke kunne svare forskelligt om hvilken model en vækning får.
    from core.services.visible_autonomous_run import _samtalens_model

    provider, model = _samtalens_model(sid, provider, model)
    # PRE-FLIGHT GUT-GATE (12/10-2026). Samme beslutningspunkt som i `start_autonomous_run`:
    # gaten skal kunne stoppe runnet FØR det fødes. Fail-open — kan gaten ikke kaldes,
    # starter runnet som før.
    try:
        from core.services.gut_engine import preflight_allows
    except Exception:  # gaten er rådgivende — kan den ikke importeres, starter runnet
        preflight_allows = None  # type: ignore[assignment]
    if preflight_allows is not None and not preflight_allows(message):
        logger.info("autonomt stream-run stoppet af gut-gaten (pre-flight): %s",
                    (message or "")[:80])
        return

    # EJEREN PÅ RUN-OBJEKTET (8/11-2026). Samme fejl som i
    # `visible_autonomous_run.start_autonomous_run`, målt her 20:40Z: vækningens
    # dispatcher binder brugeren med `set_context` FØR dette kald, men funktionen
    # læste den aldrig. Derfor blev `visible_runs.user_id` tom og
    # `in_flight_runs` skrev `force_user_id: ""` — og `verificeret_jarvis_run`
    # afviser netop den form («er den tom, er der intet bevis»). En vækning
    # kunne derfor ALDRIG lægge sin rapport i ownerens indbakke.
    #
    # Rækkefølgen er bevidst: den BUNDNE bruger vinder (en vækning for Michelle
    # skal forblive hendes), og først derefter ejeren som fallback.
    _ejer = ""
    try:
        from core.identity.workspace_context import current_user_id

        _ejer = str(current_user_id() or "").strip()
    except Exception:  # noqa: BLE001 — kan konteksten ikke læses, prøver vi ejeren
        logger.debug("autonomt stream-run: kunne ikke læse bundet bruger", exc_info=True)
    if not _ejer:
        try:
            from core.identity.owner_resolver import owner_user_id

            _ejer = str(owner_user_id() or "").strip()
        except Exception:  # noqa: BLE001 — uden ejer kører runnet, men kan ikke rapportere
            logger.warning("autonomt stream-run: kunne ikke afgøre ejeren — "
                           "rapporten kan ikke leveres i indbakken")

    run = vr.VisibleRun(
        run_id=f"autonomous-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=provider,
        model=model,
        user_message=(message or "").strip() or "Autonomous heartbeat check-in",
        session_id=sid,
        autonomous=True,
        user_id=_ejer,
        trust_all=(
            _trust_for_session(_pk) if (_pk := str(permission_session or "").strip())
            else _trust_for_autonomous(sid)
        ),
        # PERMISSIONS-ARVEN (21/10-2026, Bjørn: «wakeups skal arve sessions
        # permissions»). Niveauet læses fra samtalen selv, så en vækning i en
        # `trust`-samtale fortsætter med fuld adgang i stedet for at rejse et
        # godkendelses-kort som ingen sad og svarede på. `ask` er uændret.
        #
        # KILDEN ER ``permission_session``, ikke ``sid`` (9/11-2026). Arven var
        # rigtig i sin hensigt men læste den forkerte række: en vækning lander i
        # `auto-wakeup-…`/`auto-heartbeat-…`, som er en SYSTEM-SILO født `ask`.
        # Målt: alle Bjørns vækninger bærer `chat-52d75bf…` = `trust`, mens
        # siloen stod `ask` — så hver enkelt rejste et kort han ikke sad og
        # svarede på. Dispatcheren sender nu vækningens oprindelses-samtale her.
        # Oprindelsen SKAL med på run-objektet (målt 10/10-2026): uden den læste
        # `set_run_identity` en tom origin, og self-wakeup faldt tilbage til
        # bund-sættet i stedet for sit eget. Samme felt som start_autonomous_run.
        origin=origin,
    )

    # KAEDE-STEMPLET (14/10-2026). Samme begrundelse som i
    # `visible_autonomous_run.start_autonomous_run`: foer stemplede kun
    # `detached_run`, saa en fortsaettelse ad denne vej (wakeup-dispatcheren,
    # self-wakeup) fik en frisk post paa forsoeg 0. Skrives synkront FOER
    # traaden og FOER `mark_started`, som arver tallet fra posten.
    #
    # OPRINDELSEN afgoer om der stemples i det hele taget: `wakeup` tager en
    # forpligtelse op, men `agent-completion` goer ikke — en agent der melder
    # tilbage er et FRISKT arbejde, ikke et led i en anden opgaves kaede.
    try:
        from core.services.in_flight_runs import stempl_aktiv_kaede

        stempl_aktiv_kaede(run_id=run.run_id, session_id=sid, origin=origin,
                           task_id=task_id)
    except Exception:  # noqa: BLE001 — self-safe: et manglende stempel maa ikke dræbe runnet
        logger.debug("kunne ikke stemple kaeden paa %s", run.run_id, exc_info=True)

    # SPORET SKRIVES FØR TRÅDEN (målt 12/9-2026). Runnet kører i en daemon-tråd,
    # så et genstart midt i turen dræbte tråden uden at efterlade noget som
    # helst: ingen række i `visible_runs`, ingen in-flight-post. Dispatcheren
    # havde sat `dispatched: True` (fordi tråden STARTEDE), men der kom aldrig et
    # svar — og forskellen kunne kun ses ved at grave i event-loggen i hånden.
    # Begge spor skrives derfor her, synkront i api-processen, så de findes fra
    # første sekund uanset hvad der sker med tråden bagefter.
    try:
        from core.services import in_flight_runs as _ifr
        _ifr.mark_started(
            run_id=run.run_id,
            session_id=sid,
            user_message=run.user_message,
            kind="autonomous",
            provider=run.provider,
            model=run.model,
            # Journalen er den `verificeret_jarvis_run` slår op i. Uden ejeren
            # her er run-objektets user_id uden betydning for rapport-stien.
            force_user_id=_ejer,
        )
    except Exception:
        # SPORET MÅ IKKE FORSVINDE I TAVSHED (20/9-2026). To autonome kørsler
        # fra 20:43 stod `running` i `visible_runs` men fandtes IKKE i
        # journalen — og så kan reconcilerens præcise ejer-regel
        # (`list_running_orphans`, som spørger om ejerens pid) aldrig se dem.
        # Tilbage er kun den svage «fravær»-regel, der først slår til efter
        # seks timer. Rækkerne lå og løj om at være i live imens.
        #
        # Hvorfor den fejlede er sandsynligvis målbart: journalen var vokset
        # til 521 KB, hver mutation skriver HELE filen under en flock, og kl.
        # 20:43 lå iowait på 51 % fordi der blev installeret 5,9 GB pakker.
        # Men det er en formodning — det eneste vi VED er at ingen fik det at
        # vide. Det er der rettet.
        logger.warning("autonomous-run %s: kunne ikke skrive in-flight-sporet",
                       run.run_id, exc_info=True)
    try:
        from core.services.visible_runs_outcomes import persist_visible_run_start
        persist_visible_run_start(run)
    except Exception:
        # Den anden halvdel af sporet. Falder DEN, står kørslen omvendt kun i
        # journalen — og så ved Mission Control intet om den.
        logger.warning("autonomous-run %s: kunne ikke skrive visible_runs-raekken",
                       run.run_id, exc_info=True)

    frame_relay = AutonomousFrameRelay(
        run_id=run.run_id,
        session_id=sid,
        legacy_follow=True,
    )
    frame_relay.register()
    vr.event_bus.publish(
        "runtime.autonomous_run_started",
        {
            "run_id": run.run_id,
            "session_id": sid,
            "provider": run.provider,
            "model": run.model,
            "focus": run.user_message[:200],
            "origin": origin,
            "autonomous": True,
        },
    )
    try:
        from core.services.central_core import central

        central().observe({
            "cluster": "autonomous",
            "nerve": "autonomous_history",
            "kind": "run_started",
            "origin": origin,
            "session_id": sid,
            "run_id": run.run_id,
        })
    except Exception:
        pass

    def _in_thread() -> None:
        import asyncio

        from core.services.visible_runs_sse_v2 import translate_to_v2

        loop = asyncio.new_event_loop()
        consumed_frames = 0
        failed = False

        async def _consume() -> None:
            nonlocal consumed_frames
            generator = translate_to_v2(
                vr._stream_visible_run(run),
                run_id=run.run_id,
                model=run.model,
                provider=run.provider,
                lane=run.lane,
                session_id=sid,
                ping_interval_s=5.0,
            )
            try:
                async for frame in generator:
                    consumed_frames += 1
                    frame_relay.publish(frame)
            finally:
                try:
                    await generator.aclose()
                except Exception:
                    pass

        try:
            loop.run_until_complete(_consume())
        except Exception as exc:
            failed = True
            vr.event_bus.publish(
                "runtime.autonomous_run_failed",
                {
                    "run_id": run.run_id,
                    "session_id": sid,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "error": str(exc)[:500],
                    "consumed_frames": consumed_frames,
                },
            )
            vr._observe_autonomous_run(
                run=run,
                session_id=sid,
                outcome="failed",
                frames=consumed_frames,
                error=str(exc),
            )
        finally:
            frame_relay.finish()
            try:
                state = vr._get_active_visible_run_state() or {}
                if str(state.get("session_id") or "") == sid:
                    vr._set_active_visible_run({})
            except Exception:
                pass
            if not failed:
                outcome = vr.get_last_visible_run_outcome() or {}
                interrupted = (
                    str(outcome.get("run_id") or "") == run.run_id
                    and str(outcome.get("status") or "") == "interrupted"
                )
                status = "interrupted" if interrupted else "completed"
                payload = {
                    "run_id": run.run_id,
                    "session_id": sid,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "consumed_frames": consumed_frames,
                }
                if interrupted:
                    payload["error"] = str(outcome.get("error") or "")[:500]
                else:
                    payload["autonomous"] = True
                vr.event_bus.publish(f"runtime.autonomous_run_{status}", payload)
                vr._observe_autonomous_run(
                    run=run,
                    session_id=sid,
                    outcome=status,
                    frames=consumed_frames,
                    error=str(outcome.get("error") or "") if interrupted else "",
                )
            loop.close()

    context = contextvars.copy_context()
    threading.Thread(
        target=lambda: context.run(_in_thread),
        name="jarvis-autonomous-stream-run",
        daemon=True,
    ).start()
