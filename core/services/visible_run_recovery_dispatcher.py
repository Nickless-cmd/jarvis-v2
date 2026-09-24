"""Én ejer af fortsættelsen — en forladt opgave genoptages præcis én gang.

Opgave 4 i planen for varig genoptagelse.

Før kunne en fortsættelse starte to steder fra: den detachede kørsels egen
afslutning og boot-forligeren. To veje til samme handling betyder enten to
kørsler for samme opgave, eller ingen — afhængigt af hvem der nåede først.

Her er reglerne:

* **Kun API-processen dispatcher.** Runtime-processen må gerne forlige og
  skrive, men den må ikke starte en synlig fortsættelse; ellers ville begge
  processer gøre det efter en genstart.
* **Et krav, ikke et kig.** `claim_due_recovery` er atomisk og flytter posten
  til `running` med en ny generation og et lejemål. To dispatchere kan derfor
  ikke tage den samme opgave, og en dispatcher der dør, giver den fra sig når
  lejemålet udløber.
* **En mislykket start giver kravet tilbage.** Ellers ville opgaven stå som
  «kørende» hos en kørsel der aldrig blev til noget, indtil lejemålet udløb.
"""
from __future__ import annotations

import logging
import os
import threading

from core.services import in_flight_runs

logger = logging.getLogger("uvicorn.error")

#: Hvor længe et krav holder uden fornyelse. Længere end en almindelig
#: opstart, kortere end en menneskelig tålmodighed.
LEASE_SECONDS = 120.0
#: Hvor ofte der kigges efter forfaldne opgaver når intet vækker os.
TICK_SECONDS = 5.0
#: Hvor længe der ventes før en opgave prøves igen efter en mislykket start.
BACKOFF_SECONDS = 30.0
#: Loft over ventetiden mellem udskydelser. En samtale kan være optaget længe;
#: uden loftet ville en eksponentiel backoff gøre en fri samtale til et kvarters
#: venten, med det ville vi banke på hvert 30. sekund i timevis.
MAX_UDSKYDELSE_SECONDS = 300.0


def _udskydelses_backoff(tidligere: int) -> float:
    """Vent længere for hver gang samtalen var optaget — men aldrig i det uendelige."""
    return min(MAX_UDSKYDELSE_SECONDS, BACKOFF_SECONDS * (2 ** max(0, int(tidligere))))

_vaekker = threading.Event()
_stop = threading.Event()
_traad: threading.Thread | None = None
_laas = threading.Lock()


def _er_runtime_processen() -> bool:
    """Runtime-processen dispatcher ikke. Den må forlige, ikke starte."""
    raw = str(os.getenv("JARVIS_ENABLE_RUNTIME_SERVICES", "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _besked_fra(record: dict[str, object]) -> str:
    """Den oprindelige anmodning — det er DEN opgaven handler om."""
    # `original_request` er journalens eget navn (mark_started); de øvrige er
    # der for ældre poster og for en opgave der kun har et resumé.
    for felt in ("original_request", "user_message", "original_message", "excerpt", "summary"):
        value = str(record.get(felt) or "").strip()
        if value:
            return value
    return "Fortsæt hvor du slap."


def recover_due_once(*, owner: str | None = None) -> dict[str, object]:
    """Tag ÉN forfalden opgave og start dens fortsættelse.

    Returnerer hvad der skete, så kalderen (og testene) kan se forskel på
    «ingenting forfaldt», «startet» og «kunne ikke startes».
    """
    ejer = str(owner or in_flight_runs.current_owner())
    try:
        krav = in_flight_runs.claim_due_recovery(owner=ejer, lease_seconds=LEASE_SECONDS)
    except Exception:
        logger.warning("recovery-dispatcher: kunne ikke tage et krav", exc_info=True)
        return {"started": 0, "released": 0, "claimed": "", "error": "claim-failed"}
    if not krav:
        return {"started": 0, "released": 0, "claimed": ""}

    task_id = str(krav.get("task_id") or krav.get("run_id") or "")
    generation = int(krav.get("recovery_generation") or 0)
    session_id = str(krav.get("session_id") or "")
    if not session_id:
        # Uden en samtale er der ingen at fortsætte for. Giv kravet fra dig
        # frem for at starte noget der lander et tilfældigt sted.
        in_flight_runs.release_recovery_claim(
            task_id, generation, owner=ejer, reason="ingen session",
            retry_after_s=BACKOFF_SECONDS)
        return {"started": 0, "released": 1, "claimed": task_id, "error": "no-session"}

    besked = _besked_fra(krav)
    # SIDSTE SLUTRUNDE (opgave 3/4). Er genoptagelserne brugt op, beder
    # journalen om en AFSLUTNING — ikke om mere arbejde. Uden dette fik den
    # samme besked som en almindelig fortsættelse og kunne bruge sin sidste
    # runde på at grave videre i stedet for at svare.
    if str(krav.get("recovery_mode") or "") == "final_synthesis":
        besked = (
            "Din sidste runde: du har ikke flere forsøg. Svar på det du ved nu "
            "— sammenfat hvad du nåede, og sig tydeligt hvad der IKKE blev "
            f"gjort. Start ikke nyt arbejde.\n\nOpgaven var:\n{besked}"
        )
    # Hvad brugeren nåede at skrive imens hører til opgaven — ikke til det
    # segment der døde. Uden dette ville hans tilføjelse være tabt.
    koe = [str(x).strip() for x in (krav.get("pending_steers") or []) if str(x).strip()]
    if koe:
        besked = besked + "\n\nBrugeren tilføjede imens:\n- " + "\n- ".join(koe)
    # ÉN KØRSEL AD GANGEN I EN SAMTALE (Bjørn 20/9-2026).
    #
    # «I hans og mine sessioner sker det ofte at han har 3 eller flere runs
    # kørende samtidig … i en session med en bruger må han aldrig kunne køre
    # flere sideløbende runs.»
    #
    # Single-flight bor i `start_or_attach_user_run`, og dispatcheren her går
    # uden om den — den kalder `start_user_run_detached` direkte. Det stod
    # endda skrevet i detached_run som en bemærkning, uden at nogen så hvad
    # det kostede: målt 20/9 lå der 456 afbrudte kørsler i køen, 189 af dem i
    # ÉN samtale. Efter en genstart spawnede fire fortsættelser på to
    # sekunder, og to af dem lavede prompt-assembly i samme sekund i samme
    # session — hver med sit eget godkendelses-kort han ikke kunne se.
    #
    # Kravet er durabelt: giver vi det tilbage, er fortsættelsen ikke tabt.
    # Den tages næste gang samtalen er fri. Dispatcheren kører i API-processen
    # — samme proces som brugerens egne ture — så opslaget er pålideligt.
    try:
        from core.services import run_event_log as _rel
        levende = _rel.active_run_for_session(session_id)
    except Exception:
        levende = None   # kan vi ikke se efter, blokerer vi ikke
    if levende:
        # `attempted=False`: vi tog kravet for at kunne SE sessionen, ikke for
        # at starte noget. Talte udskydelsen som et forsøg, brændte halvandet
        # minuts optaget samtale hele budgettet — og opgaven blev aldrig hentet
        # (12 poster målt sådan på CT105 24/9-2026).
        in_flight_runs.release_recovery_claim(
            task_id, generation, owner=ejer, reason="samtalen har et levende run",
            retry_after_s=_udskydelses_backoff(int(krav.get("recovery_deferrals") or 0)),
            attempted=False)
        logger.info("recovery-dispatcher: %s udskudt — %s kører stadig i %s",
                    task_id[:24], str(levende)[:24], session_id[:28])
        return {"started": 0, "released": 1, "claimed": task_id, "error": "session-optaget"}

    try:
        from core.services.visible_runs_sections.detached_run import start_user_run_detached
        run_id = start_user_run_detached(
            message=besked,
            session_id=session_id,
            provider_override=str(krav.get("provider") or ""),
            model_override=str(krav.get("model") or ""),
            recovery_task_id=task_id,
            recovery_generation=generation,
            recovery_attempt=int(krav.get("recovery_attempt") or 0),
        )
    except Exception as exc:
        in_flight_runs.release_recovery_claim(
            task_id, generation, owner=ejer, reason=str(exc)[:160],
            retry_after_s=BACKOFF_SECONDS)
        logger.warning("recovery-dispatcher: start fejlede for %s — kravet er givet "
                       "tilbage", task_id, exc_info=True)
        return {"started": 0, "released": 1, "claimed": task_id, "error": str(exc)[:160]}

    logger.info("recovery-dispatcher: genoptog %s som run %s (generation %d)",
                task_id, run_id, generation)
    return {"started": 1, "released": 0, "claimed": task_id, "run_id": str(run_id),
            "generation": generation}


def signal_recovery_dispatcher() -> None:
    """Væk dispatcheren nu — kaldes lige efter en durabel afregning."""
    _vaekker.set()


def _loop() -> None:
    while not _stop.is_set():
        try:
            while recover_due_once().get("started"):
                # Flere forfaldne opgaver: tag dem, men én ad gangen, så hver
                # start kan nå at fejle for sig selv.
                if _stop.is_set():
                    return
        except Exception:
            logger.warning("recovery-dispatcher: tick fejlede", exc_info=True)
        _vaekker.wait(TICK_SECONDS)
        _vaekker.clear()


def start_recovery_dispatcher() -> bool:
    """Start dispatcheren. `False` = den kører ikke her (og skal ikke)."""
    global _traad
    if _er_runtime_processen():
        logger.info("recovery-dispatcher: springes over i runtime-processen")
        return False
    with _laas:
        if _traad is not None and _traad.is_alive():
            return True
        _stop.clear()
        _traad = threading.Thread(target=_loop, name="visible-recovery-dispatcher",
                                  daemon=True)
        _traad.start()
    logger.info("recovery-dispatcher: startet")
    return True


def stop_recovery_dispatcher() -> None:
    """Stop uden at starte nyt arbejde. En nedlukning afregner, den dispatcher ikke."""
    global _traad
    _stop.set()
    _vaekker.set()
    with _laas:
        traad, _traad = _traad, None
    if traad is not None and traad.is_alive():
        traad.join(timeout=2.0)
