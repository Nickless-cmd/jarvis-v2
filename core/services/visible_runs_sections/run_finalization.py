"""Hvad der skal ske NÅR et visible run er slut — samlet ét sted.

Boy Scout-udtrækning (2026-08-20): `visible_runs.py` er 7.055 linjer, og
run-afslutningens sideeffekter lå spredt. Denne enhed samler dem, så der
findes ÉT svar på "hvad køres ved run-slut" i stedet for et kald pr. gren.

## Bug'en der gjorde udtrækningen nødvendig

`_advance_tool_lifecycle` blev kaldt PRÆCIS ét sted (visible_runs.py:4574),
inde i den agentiske followup-gren. Men `_persist_session_assistant_message`
kaldes fra otte forskellige steder — den simple ikke-agentiske gren (~5226),
afbrudt-grenen (~5364) og fire fejlstier. Alle ture der afsluttede ad de veje
avancerede **aldrig** cold_floor.

Målt live 20. aug 2026 på Bjørns session: floor stod på 104207 fra kl. 18:05,
mens otte afsluttede runs (18:23-18:31) ikke flyttede den. Manuelt kald gav
straks 104207 → 104311, hvilket flyttede 61 tool-results fra warm til cold og
sparede 3.641 tokens i hver eneste prompt derefter.

Diagnosen kom fra Codex, som forudsagde både det nye floor-tal (104311) og
effekten (92 → 31 warm) korrekt før verifikation.

## Hvorfor finally-blokken

`_post_process`-tråden startes fra en `finally`, som ALLE runs når — completed,
failed, interrupted og cancelled. Det er den eneste sti med den garanti.
`evaluate_and_advance` er idempotent (floor'en beregnes fra beskederne, ikke
inkrementelt), så et ekstra kald fra den gamle gren er harmløst.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def advance_tool_lifecycle(session_id: str) -> None:
    """Ryk tool-result cold_floor frem (spec 2026-07-16). Self-safe.

    Idempotent: `evaluate_and_advance` udleder floor'en fra sessionens beskeder
    med hysterese, så gentagne kald i samme tilstand er no-ops. Må ALDRIG kaste
    — en fejl her må ikke vælte run-afslutningen.
    """
    if not session_id:
        return
    try:
        from core.context.tool_result_lifecycle import evaluate_and_advance
        evaluate_and_advance(session_id)
    except Exception:
        pass


def status_for_run(run_id: str) -> str:
    """Koerslens status, eller "" hvis den ikke findes.

    MAA IKKE fange DB-fejl. Task 2 blev ramt af praecis dét: `approval_runtime.
    state()` havde en indre `except Exception: return None`, saa en utilgaengelig
    database blev til en VAERDI der ikke kunne skelnes fra «kortet er afgjort» —
    og hydreringen lukkede raekken. En kort nedetid tommede hele feeden, tavst.

    Reglen der foelger: en hydrerings-hjaelper returnerer kun en vaerdi naar den
    VED noget. Kan den ikke spoerge, skal undtagelsen forplante sig op til
    `_hydrer`s eget net, som markerer raekken foraeldet i stedet for at lukke den.

    Laesningen laa foer inline i opmaerksomhed.py. Feeden skal ogsaa bruge
    den, og to steder der laeser samme tabel paa hver sin maade er den slags
    der skrider fra hinanden.
    """
    from core.runtime.db import connect
    with connect() as conn:
        raekke = conn.execute(
            "SELECT status FROM visible_runs WHERE run_id = ?", (run_id,)).fetchone()
    return str(raekke[0] or "") if raekke else ""


def finalize_run(session_id: str, *, status: str) -> None:
    """Kaldes fra run-afslutningens finally — uanset hvordan runnet endte.

    Kun `completed` avancerer lifecycle: et afbrudt run kan have efterladt
    halve tool-exchanges, og at fryse dem til cold-stubs ville tabe kontekst
    Jarvis stadig har brug for i den næste tur.
    """
    if status == "completed":
        advance_tool_lifecycle(session_id)


def finalize_in_flight(
    *, run_id: str, session_id: str, status: str, error: str = "",
) -> None:
    """Resolve durable recovery state without erasing resumable work."""
    from core.services.in_flight_runs import settle_recovering, settle_terminal

    if status in {"interrupted", "recovering"}:
        reason = error or status
        settle_recovering(run_id, reason=reason, summary=reason)
    else:
        terminal = status if status in {"completed", "cancelled", "failed_terminal"} else "failed_terminal"
        settle_terminal(run_id, status=terminal, reason=error or terminal)

    # Feeden (spec 2026-09-21). Fejler den, skal koerslen stadig afsluttes:
    # afslutningen er den vigtige del.
    try:
        from core.services import notifikations_emittere
        from core.services.visible_runs_sections.run_finalization import _ejer_og_titel
        ejer, titel = _ejer_og_titel(session_id)
        if ejer:
            if status in ("failed", "failed_terminal", "interrupted"):
                notifikations_emittere.paa_koersel_fejlet(
                    run_id, user_id=ejer, session_id=session_id, titel=titel)
            elif status == "completed":
                notifikations_emittere.paa_koersel_faerdig(
                    run_id, user_id=ejer, session_id=session_id, titel=titel)
    except Exception:
        _log.warning("koersel %s naaede ikke feeden", run_id, exc_info=True)


def _ejer_og_titel(session_id: str) -> tuple[str, str]:
    """(ejer, samtale-titel).

    To ting maalt paa skemaet 21/9-2026, som planens foerste udkast tog fejl af:
    noeglen hedder `session_id` (`id` er et autoincrement-HELTAL), og der findes
    INGEN `user_id`-kolonne — samtaler er ikke bruger-scopede. Ejeren afgoeres
    derfor som i godkendelses-stien (`visible_runs._godkendelses_ejer`): den
    kaldende brugers id hvis der er et, ellers husets ejer.

    Fanger IKKE DB-fejl. Kalderen har sit eget net og logger — men en fejl her
    betyder at DEN notifikation er tabt for altid, for run-raekker har ingen
    afstemning som godkendelser har. Kendt graense, ikke en overset.
    """
    from core.identity.workspace_context import current_user_id
    from core.runtime.db import connect
    from core.services.notifikations_emittere import _owner_id

    uid = str(current_user_id() or "").strip() or (_owner_id() or "")
    with connect() as conn:
        raekke = conn.execute(
            "SELECT title FROM chat_sessions WHERE session_id = ?",
            (session_id,)).fetchone()
    return uid, (str(raekke[0]) if raekke and raekke[0] else "samtalen")
