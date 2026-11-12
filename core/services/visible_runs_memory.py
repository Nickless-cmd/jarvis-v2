"""Memory/continuity post-processing for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``
(8593 linjer god-fil). Ren KODE-FLYTNING — ingen logik-ændring. Funktionerne er
leaf-orkestratorer kaldt fra ``_stream_visible_run`` og re-eksporteres tilbage til
``visible_runs`` i bunden af den fil, så bare kald + test-monkeypatches fortsat virker.

Symboler der monkeypatches på ``visible_runs`` (fx ``start_autonomous_run``) refereres
via ``_vr.X`` (facade-seam) så patchen ses på kald-tidspunkt. Main-symboler bruges
KUN inde i funktions-kroppe (lazy), aldrig på modul-niveau → ingen import-cyklus.
"""

from __future__ import annotations

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus
from core.services.chat_sessions import recent_chat_tool_messages


_CONTINUATION_DELAY_SECONDS = 5.0


def _recent_internal_tool_context(session_id: str | None, *, limit: int = 6) -> str:
    if not session_id:
        return ""
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return ""
    lines: list[str] = []
    for item in messages[-limit:]:
        content = " ".join(str(item.get("content") or "").split()).strip()
        if not content:
            continue
        if len(content) > 300:
            content = content[:299].rstrip() + "…"
        lines.append(f"- {content}")
    if not lines:
        return ""
    return "\n".join(
        [
            "Recent internal tool results from this chat.",
            "These are Jarvis-only observations and are not visible user chat:",
            *lines,
        ]
    )


def _attention_fra_aktive_goals() -> dict[str, object] | None:
    """Fokus-feltet til kapslen — med forskellen paa «maalt tomt» og «ikke maalt».

    Maalt 10/11-2026: ``current_focus`` stod paa «Current goal: make stabilize
    workspace-search land visibly» mens ``runtime_goal_signals`` havde NULL
    aktive raekker. Kilden sendte en TOM dict, og ``capture_state`` merger over
    den forrige kapsel — saa «fersk og tom» betoed det samme som «behold den
    gamle». Kommentaren her paastod at feltet stod tomt; koden gjorde det
    modsatte, og det er den slags kommentar der holder fejlen i live.

    Derfor tre udfald, ikke to:

    * et signal     -> titlen, som foer
    * maalt, intet  -> ``None``-vaerdier, saa merge'en RYDDER feltet
    * ikke maalt    -> ``None`` (hele dict'en), saa kapslen arver. En fejlet
      maaling er ikke et bevis for at der intet fokus er; at rydde paa en
      fejl ville vaere den samme loegn, blot i den anden retning.
    """
    try:
        from core.services.continuity import MIN_FOCUS_CHARS
        from core.services.goal_signal_tracking import list_runtime_goal_signals

        for s in list_runtime_goal_signals(status="active", limit=3):
            titel = str(s.get("title") or s.get("goal_title") or "").strip()
            if len(titel) >= MIN_FOCUS_CHARS:
                return {
                    "active_goal_title": titel[:80],
                    "current_focus": titel[:80],
                }
    except Exception:
        import logging as _lg_fokus

        _lg_fokus.getLogger(__name__).warning(
            "fokus-udledning fejlede — kapslen arver sin forrige vaerdi",
            exc_info=True,
        )
        return None
    return {"active_goal_title": None, "current_focus": None}


def _goals_fra_aktive_maal() -> dict[str, object] | None:
    """Goals-sektionen til kapslen — maalt, ikke arvet.

    Maalt 10/11-2026: ``goals.active_goals`` og ``goals.recent_completions``
    blev vist i CONTINUITY-blokken, men ``live_update_after_turn`` sendte dem
    aldrig. ``list_active_goals()`` fandtes hele tiden i
    ``core/services/long_horizon_goals.py`` — den blev blot ikke kaldt herfra.

    Samme tre udfald som ``_attention_fra_aktive_goals``: maalt med maal,
    maalt tomt (saa merge'en rydder), ikke maalt (saa kapslen arver).
    """
    try:
        from core.services.long_horizon_goals import list_active_goals, list_all_goals

        aktive = list_active_goals(limit=5)
        maal = [
            {"title": str(g.get("title") or "").strip(), "id": g.get("goal_id")}
            for g in aktive
            if str(g.get("title") or "").strip()
        ]
        # 10/11-2026: her stod en haardkodet tom liste. Den var ikke en maaling
        # — den var en konstant der lignede et svar. ``list_all_goals`` har de
        # fuldfoerte maal (maalt: 7 i basen, nyeste 28/10), saa feltet kan
        # faktisk vise hvad der blev faerdigt i stedet for altid at vaere tomt.
        fuldfoerte = [
            {
                "title": str(g.get("title") or "").strip(),
                "completed_at": g.get("completed_at"),
            }
            for g in list_all_goals(limit=50)
            if g.get("status") == "completed" and str(g.get("title") or "").strip()
        ]
        fuldfoerte.sort(key=lambda g: str(g.get("completed_at") or ""), reverse=True)
        return {"active_goals": maal, "recent_completions": fuldfoerte[:3]}
    except Exception:
        import logging as _lg_maal

        _lg_maal.getLogger(__name__).warning(
            "goal-udledning fejlede — kapslen arver sin forrige vaerdi",
            exc_info=True,
        )
        return None


def _open_thread_fra_registry() -> dict[str, object] | None:
    """``open_thread`` til kapslen — fra den LEVENDE traad-registry.

    Maalt 10/11-2026: feltet blev vist som nutidstilstand uden nogen skriver.
    Den gamle kilde, ``cross_session_threads``, laeser en JSON-fil med 51
    traade der ALLE staar ``active`` og hvis nyeste er fra 27. maj — den er
    et arkiv der aldrig blev lukket, ikke en aaben traad. At vise den ville
    vaere praecis den loegn feltet blev fjernet for.

    ``runtime_thread_registry`` er den levende afloeser: en traad erklaeres
    med et SAT navn og lukkes med bevis. Er den tom, er svaret aerligt tomt.

    Samme tre udfald: maalt med traad, maalt tomt (rydder), ikke maalt (arver).
    """
    try:
        from core.runtime.db_runtime_executive_signals import list_runtime_threads

        aabne = list_runtime_threads(status="open", limit=1)
        if not aabne:
            return {"open_thread": None}
        navn = str(aabne[0].get("name") or "").strip()
        return {"open_thread": navn[:80] or None}
    except Exception:
        import logging as _lg_traad

        _lg_traad.getLogger(__name__).warning(
            "traad-udledning fejlede — kapslen arver sin forrige vaerdi",
            exc_info=True,
        )
        return None


def _relation_fra_turen(run: "_vr.VisibleRun") -> dict[str, object] | None:
    """``last_interaction_type`` til kapslen — fra den FLADE turen kom fra.

    Maalt 10/11-2026: feltet stod haardt paa «chat» fra ``_EMPTY_CAPSULE``.
    ``VisibleRun.surface`` baerer faktisk «desk», «mobil», «discord» eller
    «telegram» (sat af ``chat_stream_v2.py:511``), men den blev aldrig sendt
    til kapslen — og den gemmes ikke i ``visible_runs``, saa den kan kun
    laeses HER, mens turen er i live.

    Er ``surface`` tom (klienten sagde det ikke), er svaret ``None`` — ikke
    et gaet paa «chat». En tom flade er ikke det samme som en samtale.
    """
    flade = str(getattr(run, "surface", "") or "").strip().lower()
    if not flade:
        return {"last_interaction_type": None}
    return {"last_interaction_type": flade[:40]}


def _somatic_fra_sansearkivet() -> dict[str, object] | None:
    """Somatic-sektionen til kapslen — fra det der faktisk er sanset.

    Maalt 10/11-2026: alle tre viste noegler (``last_visual``, ``last_audio``,
    ``atmosphere``) var ``null``. ``sensory_archive.list_recent()`` har
    posterne — den blev blot aldrig kaldt fra capsule-vejen.

    Samme tre udfald: maalt indhold, maalt tomt (rydder), ikke maalt (arver).
    """
    tom = {"last_visual": None, "last_audio": None, "atmosphere": None}
    try:
        from core.services.sensory_archive import list_recent

        poster = list_recent(limit=1)
        if not poster:
            return tom
        nyeste = poster[0]
        indhold = str(nyeste.get("content") or "").strip()
        modalitet = str(nyeste.get("modality") or "").strip()
        if not indhold:
            return tom
        resultat: dict[str, object] = dict(tom)
        if modalitet == "visual":
            resultat["last_visual"] = indhold
        elif modalitet == "audio":
            resultat["last_audio"] = indhold
        elif modalitet in {"atmosphere", "mixed"}:
            resultat["atmosphere"] = indhold
        return resultat
    except Exception:
        import logging as _lg_sans

        _lg_sans.getLogger(__name__).warning(
            "somatic-udledning fejlede — kapslen arver sin forrige vaerdi",
            exc_info=True,
        )
        return None


def _run_memory_postprocess(run: "_vr.VisibleRun", assistant_text: str) -> None:
    if not run.session_id:
        return
    # Backstop for an explicit admission that a changed behavior has no test.
    # The preferred path is the structured flag_side_task call while the run
    # is live. This conservative scan only acts on one named source file and
    # never converts an unrelated red suite into a task.
    try:
        from core.services.inbox_state import _ejer_id
        from core.services.run_finding_accounting import audit_final_response
        owner = _ejer_id()
        run_user = str(getattr(run, "user_id", "") or "")
        if owner and (not run_user or run_user == owner):
            audit_final_response(
                run_id=run.run_id, session_id=run.session_id,
                text=assistant_text,
            )
    except Exception:
        import logging as _lg_findings
        _lg_findings.getLogger(__name__).warning(
            "run finding audit failed", exc_info=True)
    distillation_result: dict[str, object] | None = None
    consolidation_result: dict[str, object] | None = None
    errors: list[str] = []

    try:
        from core.services.session_distillation import (
            distill_session_carry,
        )

        distillation_result = distill_session_carry(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception as exc:
        errors.append(f"session_distillation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.session_distillation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    try:
        from core.services.end_of_run_memory_consolidation import (
            consolidate_run_memory,
        )

        consolidation_result = consolidate_run_memory(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
            internal_context=_vr._recent_internal_tool_context(run.session_id),
            human_user_message=not run.autonomous,
        )
    except Exception as exc:
        errors.append(f"end_of_run_consolidation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.end_of_run_consolidation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    # Generate session summary for cross-session continuity
    session_summary_text = ""
    try:
        from core.services.session_distillation import (
            generate_session_summary,
        )

        session_summary_text = generate_session_summary(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
            human_user_message=not run.autonomous,
        ) or ""
    except Exception as exc:
        errors.append(f"session_summary:{type(exc).__name__}:{exc}")

    # Cross-session threads: create or resume a thread for this session once
    # it has a meaningful title (not "New chat") and a summary. Uses session_id
    # as the de-dup key so we never open more than one thread per session.
    try:
        if session_summary_text:
            from core.services.chat_sessions import get_chat_session
            from core.services.cross_session_threads import (
                create_thread,
                list_threads,
                update_synopsis,
            )
            session_data = get_chat_session(run.session_id) or {}
            title = str(session_data.get("title") or "").strip()
            if title and title.lower() != "new chat":
                existing = [
                    t for t in list_threads()
                    if t.get("opened_in_session") == run.session_id
                ]
                if existing:
                    update_synopsis(existing[0]["thread_id"], session_summary_text[:500])
                else:
                    create_thread(
                        topic=title,
                        synopsis=session_summary_text[:500],
                        status="active",
                        opened_in_session=run.session_id,
                    )
    except Exception as exc:
        errors.append(f"cross_session_threads:{type(exc).__name__}:{exc}")

    # Continuity state capsule: persist after every turn
    try:
        from core.services.continuity import live_update_after_turn

        # Gather mood from mood_oscillator via continuity sync
        mood = {}
        try:
            from core.services.continuity import sync_capsule_mood
            synced = sync_capsule_mood()
            if synced:
                mood = synced
        except Exception:
            pass

        # Gather attention from active goals.
        #
        # 4/10-2026: her stod der «Focus: t» i CONTINUITY-blokken. Kaldet
        # hentede UDEN statusfilter, saa det nyeste signal vandt — og det
        # nyeste var en test-raekke fra 8. juli (goal_type='test', title='t').
        # Maalt i basen: 1744 signaler, ALLE 'archived', nul aktive. Et
        # fokus-felt der baerer eet bogstav er vaerre end et tomt felt.
        #
        # 10/11-2026: statusfilteret og laengde-vagten var paa plads, men
        # feltet stod STADIG med et foraeldet fokus — fordi en tom fersk dict
        # blev mergt ind over den forrige kapsel og derfor arvede den.
        # ``_attention_fra_aktive_goals`` skelner nu de tre udfald.
        attention = _attention_fra_aktive_goals()
        # 10/11-2026: ``open_thread`` blev vist som nutidstilstand uden nogen
        # skriver. Den hentes nu fra den levende traad-registry, og de to
        # dicts flettes — de har hver deres tre-udfalds-semantik.
        _traad = _open_thread_fra_registry()
        if _traad is not None:
            attention = {**(attention or {}), **_traad}

        # Gather recent activity
        recent_activity = {"last_tool_result_summary": assistant_text[:120]}
        try:
            from core.services.chat_sessions import recent_chat_tool_messages
            tool_msgs = recent_chat_tool_messages(run.session_id, limit=3)
            if tool_msgs:
                tools_used = []
                for tm in tool_msgs:
                    content = str(tm.get("content", "") or "")
                    name = str(tm.get("tool_name", "") or "")
                    if name:
                        tools_used.append(name)
                    elif "tool_use" in str(tm.get("role", "")):
                        tools_used.append(content.split("(")[0][:40])
                recent_activity["tools_used_recently"] = tools_used[:10]
        except Exception:
            pass

        live_update_after_turn(
            mood=mood or None,
            attention=attention or None,
            goals=_goals_fra_aktive_maal(),
            somatic=_somatic_fra_sansearkivet(),
            relation=_relation_fra_turen(run),
            recent_activity=recent_activity or None,
            session_id=run.session_id,
        )
    except Exception:
        # 4/10-2026: her stod der et bart «pass». Da jeg maalte om capsulen
        # blev skrevet efter hver tur, kunne journalen ikke skelne «blev ikke
        # kaldt» fra «fejlede tavst» — den var tom i BEGGE tilfaelde, og jeg
        # konkluderede forkert paa det. Skrive-vejen viste sig at virke.
        # Hullet var ikke desto mindre aegte: fejler forberedelsen (mood-sync,
        # attention, seneste aktivitet), forsvandt sporet helt. Samme moenster
        # som side-opgave-fejningen nedenfor bruger.
        import logging as _lg_cont

        _lg_cont.getLogger(__name__).warning(
            "continuity live_update-forberedelse fejlede efter run", exc_info=True)

    # En inaktiv arbejds-session flyttes tilbage til ventende. Tavshed er ikke
    # bevis for at opgaven er udført, så fejeren markerer den aldrig færdig.
    try:
        import logging as _lg_side
        from core.services.side_tasks import fej_faerdige
        _side = fej_faerdige()
        if _side.get("tilbage_til_venter"):
            # Modulet har ingen modul-logger; hentes lokalt frem for at
            # indfoere en global i en fil der klarer sig uden.
            _lg_side.getLogger(__name__).info(
                "side-opgaver tilbage til ventende efter run: %s", _side)
    except Exception:
        import logging as _lg_side2
        _lg_side2.getLogger(__name__).warning(
            "side-opgave-fejning fejlede efter run", exc_info=True)

    event_bus.publish(
        "memory.visible_run_postprocess_completed",
        {
            "session_id": run.session_id,
            "run_id": run.run_id,
            "distillation_ran": distillation_result is not None,
            "consolidation_ran": consolidation_result is not None,
            "errors": errors,
            "private_brain_count": (
                distillation_result or {}
            ).get("private_brain_count"),
            "workspace_memory_count": (
                distillation_result or {}
            ).get("workspace_memory_count"),
            "candidate_count": (
                consolidation_result or {}
            ).get("candidate_count"),
            "memory_updated": (
                consolidation_result or {}
            ).get("memory_updated"),
            "user_updated": (
                consolidation_result or {}
            ).get("user_updated"),
            "skipped_reason": (
                consolidation_result or {}
            ).get("skipped_reason"),
        },
    )


def _maybe_trigger_continuation(run: "_vr.VisibleRun", assistant_text: str) -> None:
    """If Jarvis stopped mid-task, trigger an autonomous-run
    that wakes him again with context.

    Guards:
    - Only for visible (non-autonomous) runs — prevents infinite continuation-loop
    - Only if session_id exists (we have somewhere to continue in)
    - Cooldown 45s per session (prevents spam)
    - Only on match with unfinished_intent.detect_unfinished_intent
    - Delay 5s before spawn so user can react first if they see the problem
    - Re-check at spawn: if new visible-run is active in session, abort
    """
    if run.autonomous:
        return  # autonomous runs spawner ikke continuations (loop-beskyttelse)
    if not run.session_id:
        return
    try:
        from core.services.unfinished_intent import (
            detect_unfinished_intent,
            is_in_cooldown,
            mark_triggered,
        )

        # Cooldown check BEFORE detection — saves work
        if is_in_cooldown(run.session_id):
            return

        intent = detect_unfinished_intent(assistant_text)
        if intent is None:
            return

        # Mark cooldown now so concurrent _post_process workers don't both fire
        mark_triggered(run.session_id)

        # Rodårsag 3 (side-02afb491ea, 13/11-2026): record_promise er flyttet ud
        # af continuation-stien — nu i _record_promise_from_run, kaldt fra
        # visible_runs.py UAFHÆNGIGT af dette. Før var registreringen bundet til
        # continuation: cooldown, spørgsmåls-guarden (rodårsag 2) og intent=None
        # gjorde at et løfte aldrig nåede ledgeren og Jarvis aldrig blev
        # konfronteret i næste prompt.

        # Publish for observability — Bjørn can see in Mission Control
        # how often detector fires
        try:
            event_bus.publish(
                "runtime.continuation_triggered",
                {
                    "run_id": run.run_id,
                    "session_id": run.session_id,
                    "pattern": intent.pattern,
                    "matched": intent.matched_text[:100],
                },
            )
        except Exception:
            pass

        # Snippet fra sidste paragraf (mere fokuseret end de sidste N tegn)
        text = assistant_text.strip()
        last_para = text.split("\n\n")[-1] if "\n\n" in text else text
        snippet = (last_para or text)[-400:].strip()

        continuation_message = (
            f"[auto-continuation after pause-pattern '{intent.pattern}'] "
            "You just wrote to the user:\n\n"
            f"---\n{snippet}\n---\n\n"
            "You stopped here — but the task isn't done. The user "
            "already green-lit it. Continue without waiting for a reply. "
            "If you're done, confirm it briefly."
        )

        # Delay spawn so user can react first if they see the problem before we do
        import threading as _threading
        def _delayed_spawn() -> None:
            try:
                import time as _time
                _time.sleep(_CONTINUATION_DELAY_SECONDS)
                # Re-check: if user sent a message in the meantime, then
                # abort — they took over.
                from core.services.visible_runs import _get_active_visible_run_state
                active = _get_active_visible_run_state()
                if active and active.get("session_id") == run.session_id:
                    # A new run is already active in this session — skip continuation
                    return
                # OVERLAP-VÆRNET (12/11-2026). Continuation var den ene af ti
                # startere der gik uden om `reserve_background_start`, så to
                # uafhængige startere kunne lande oven i hinanden i samme
                # samtale: den forrige kørsel var lige slut, og intet så den.
                # Reservationen er et OS-flock om check/start-sektionen, så
                # også en anden proces' start er synlig her.
                from core.services.background_start_reservation import (
                    reserve_background_start,
                )
                with reserve_background_start(run.session_id) as reservation:
                    if not reservation.acquired:
                        # Continuation er en bekvemmelighed, ikke et løfte:
                        # er der allerede nogen i samtalen, skal den ikke
                        # genforsøges — brugeren eller et andet run har taget
                        # over, og et ekstra run ville være præcis det
                        # «råb ind ad døren» værnene findes for at undgå.
                        import logging as _lg_vaern
                        _lg_vaern.getLogger(__name__).info(
                            "continuation afvist for %s: %s",
                            run.session_id[:28], reservation.reason,
                        )
                        return
                    _vr.start_autonomous_run(continuation_message, session_id=run.session_id,
                                             origin="continuation",
                                             # TILLADELSEN FØLGER SAMTALEN (12/11-2026).
                                             # En continuation er en fortsættelse af en tur
                                             # hvis niveau brugeren allerede har sat — den må
                                             # ikke læse et silo-niveau og rejse kort han ikke
                                             # sidder og svarer på.
                                             permission_session=run.session_id)
            except Exception:
                pass

        _threading.Thread(
            target=_delayed_spawn,
            name=f"continuation-{run.run_id[:12]}",
            daemon=True,
        ).start()
    except Exception:
        pass


def _record_promise_from_run(run: "_vr.VisibleRun", assistant_text: str) -> None:
    """Bjørn-gate (16. jun 2026), udkoblet fra continuation (rodårsag 3,
    side-02afb491ea 13/11-2026): registrér fremtids-løfter ("jeg gør det /
    jeg går i gang / jeg tjekker lige") så de rejses prominent i NÆSTE turs
    prompt og holder Jarvis ansvarlig. Fail-soft.

    Kører UAFHÆNGIGT af _maybe_trigger_continuation: cooldown, spørgsmåls-
    guarden og continuation-spawning afgør ikke længere om et løfte huskes.
    Registreringen bruger detect_promise_intent (rodårsag 2), så et løfte i en
    tekst der slutter med spørgsmål eller handoff registreres stadig.
    """
    if run.autonomous:
        return  # autonome runs skriver ikke til Bjørn — samme guard som continuation
    if not run.session_id:
        return
    try:
        from core.services.unfinished_intent import detect_promise_intent
        intent = detect_promise_intent(assistant_text)
        if intent is None:
            return
        from core.services.promise_ledger import record_promise
        record_promise(run.session_id, intent.matched_text)
    except Exception:
        pass
