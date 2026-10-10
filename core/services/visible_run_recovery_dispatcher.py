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
    # Et fejl-resumé er ikke en brugerbesked og må ikke bruges som opgave.
    for felt in ("original_request", "user_message", "original_message", "excerpt"):
        value = str(record.get(felt) or "").strip()
        if value:
            return value
    return ""


def _luk_afloest_raekke(run_id: str, *, reason: str) -> None:
    """Luk den afløste kørsels EGEN række i `visible_runs`.

    Dispatcheren afregnede kun journal-posten (JSON), og det var hele hullet:
    målt 6/10-2026 stod `visible-bd1727a4` som `running` uden ét eneste
    `costs`-opslag mens dens fortsættelse `visible-3433cf05` kørte færdig.
    Rækken blev først lukket af `_ryd_visible_drift` 30 minutter senere, og
    indtil da blokerer den genstarts-vagten — altså hvert deploy.

    `stamp_visible_run_superseded` og IKKE `stamp_visible_run_interrupted`:
    den anden udsender `runtime.visible_run_interrupted`, og `living_executive`
    planlægger en self-wakeup på netop det event («Resume from interrupted
    visible run»). Herfra ville den altså bede om en genoptagelse af det der
    LIGE blev genoptaget — dobbelt-run'et gjort værre, ikke bedre. Den tavse er
    også den sande: rækken er afløst, ikke efterladt.

    Er rækken allerede terminal, er stemplet en no-op (dens WHERE kræver
    `recovering` eller `running`), så den må gerne kaldes igen.

    Importen af `visible_runs` FØRST er ikke pynt: `visible_runs_outcomes` er
    cirkulær, og uden den kaster den «cannot import name … from partially
    initialized module» — men kun nogle gange, afhængigt af hvad der i forvejen
    er importeret i processen. Samme fælde er dokumenteret i
    `session_boot_reconciler`.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return
    try:
        import core.services.visible_runs  # noqa: F401
        from core.services.visible_runs_outcomes import stamp_visible_run_superseded
        stamp_visible_run_superseded(rid, reason=reason)
    except Exception:
        # IKKE tavs. Netop den cirkulære import kan fejle, og uden loggen ville
        # rækken blive stående `running` uden at nogen kunne se hvornår
        # oprydningen holdt op med at virke.
        logger.warning(
            "recovery-dispatcher: kunne ikke lukke afloest raekke %s", rid[:24],
            exc_info=True)


def _samtalen_gik_videre(session_id: str, efter: str) -> bool:
    """Er brugeren gået videre, siden den her kørsel døde?

    Målt 3/10-2026: `visible-6d1c15e7` døde 13:24:48 uden at svare. Den blev
    genoptaget 13:43:31 — og en fortsættelse får HELE samtale-historikken med,
    så den svarede på Bjørns NYESTE besked, som en levende kørsel havde
    besvaret 26 sekunder før. Fra hans side: ét spørgsmål, to svar.

    `recover_due_once` havde kun ét værn — «kører der noget LIGE NU». Det
    spørgsmål er sandt i et kort vindue og falsk igen bagefter; det ser ikke at
    samtalen er gået videre imens posten ventede.

    Reglen: har brugeren skrevet noget NYT i denne samtale efter posten døde,
    er opgaven forladt. Det er ikke et tab — skrev han noget, findes der et
    nyere run der bærer hans spørgsmål, og det bliver genoptaget for sig selv
    hvis det også dør. Vi dropper kun det gamle.

    `datetime()` og ikke en rå streng-sammenligning: den læser både `+00:00` og
    `Z`, og giver NULL på et tidsstempel den ikke forstår — altså nul rækker,
    altså «nej, gå videre». Kan vi ikke læse basen, svarer vi også NEJ og
    genoptager: et run må aldrig dø tavst, så tvivlen falder ud til fordel for
    at prøve.
    """
    sid = str(session_id or "").strip()
    if not sid or not str(efter or "").strip():
        return False
    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                """
                SELECT COUNT(*) FROM chat_messages
                WHERE session_id = ?
                  AND role = 'user'
                  AND datetime(created_at) > datetime(?)
                """,
                (sid, str(efter)),
            ).fetchone()
    except Exception:
        logger.warning(
            "recovery-dispatcher: kunne ikke se om samtalen gik videre (%s) — genoptager",
            sid[:28], exc_info=True)
        return False
    return bool(raekke and int(raekke[0]) > 0)


def _runnet_har_svaret(run_id: str) -> bool:
    """Har kørslen SELV allerede svaret Bjørn?

    Søsteren til `_samtalen_gik_videre`, og den fanger en anden fejl: den anden
    spørger om BRUGEREN skrev nyt, denne om RUNNET selv svarede.

    Målt 10/10-2026: run `visible-9a64aa1d` skrev sit svar kl. 16:48:32 og blev
    stemplet `interrupted` ét sekund senere (`pending-tool-intent`). Bjørn skrev
    INTET imens — han ventede — så `_samtalen_gik_videre` var falsk, og
    dispatcheren genoptog tre sekunder senere. To svar på én besked.

    Kilden er `besked_run_kobling` og ikke `chat_messages`: den binder besked→run,
    så vi spørger præcist «skrev DETTE run en besked?». Et bredere filter (enhver
    assistant-besked i sessionen efter døden) ville også tælle hver proaktiv
    besked, morgenbrief og heartbeat-ping — og droppe genoptagelser Bjørn faktisk
    ventede på. Det var grænsen der standsede denne søster 3/10.
    """
    try:
        from core.services.besked_run_kobling import skrev_run
        return skrev_run(run_id)
    except Exception:
        logger.warning("recovery-dispatcher: kunne ikke afgoere om %s svarede",
                       str(run_id or "")[:24], exc_info=True)
        return False


def recover_due_once(*, owner: str | None = None) -> dict[str, object]:
    """Tag ÉN forfalden opgave og start dens fortsættelse.

    Returnerer hvad der skete, så kalderen (og testene) kan se forskel på
    «ingenting forfaldt», «startet» og «kunne ikke startes».
    """
    ejer = str(owner or in_flight_runs.current_owner())
    try:  # agent-contract-v1 (B2): en vaekning der blev fastlagt men ikke skrevet
        from core.runtime.db_agent_wait import materialize_pending_wakes
        materialize_pending_wakes()
    except Exception:
        logger.warning("recovery-dispatcher: kunne ikke tage agent-vaekninger op", exc_info=True)
    try:  # agent-contract-v1 (C2): udloebne worker-leases (atomisk claim; ufarligt at koere to steder)
        from core.services.agent_contract_service import supervise
        supervise()   # uafhaengigt af kapabilitets-flaget: accepteret arbejde supervisereres altid
    except Exception:
        logger.warning("recovery-dispatcher: agent-supervisor fejlede", exc_info=True)
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

    # ER SAMTALEN GÅET VIDERE? (3/10-2026)
    #
    # Kravet her er ikke «kører der noget nu» — det spørgsmål stilles nedenfor,
    # og det er kun sandt i det korte vindue hvor en tur faktisk kører. Det her
    # er historisk: skrev brugeren noget, EFTER posten døde?
    #
    # Uden det stod posten i kø i 19 minutter mens Bjørn og jeg talte sammen;
    # da samtalen endelig var fri, blev den genoptaget og svarede på hans
    # nyeste besked — som var besvaret for længst.
    #
    # `settle_terminal` og ikke `release_recovery_claim`: gav vi kravet tilbage,
    # ville næste tick tage det igen og droppe det igen, i det uendelige.
    # `cancelled` frem for `failed_terminal`, fordi `failed_terminal` sætter
    # `notice_pending` — og en forældet opgave skal ikke give Bjørn et varsel.
    # Første afbrydelse er grænsen for HELE opgaven. En senere retry kan dø
    # igen efter at brugeren skrev videre; dens nye settled_at må ikke få den
    # gamle opgave til at ligne noget, der stadig afventer et svar.
    if _samtalen_gik_videre(session_id, str(
        krav.get("first_interrupted_at") or krav.get("settled_at")
        or krav.get("interrupted_at") or ""
    )):
        try:
            in_flight_runs.settle_terminal(
                task_id, status="cancelled",
                reason="samtalen gik videre efter afbrydelsen",
                expected_generation=generation, expected_owner=ejer)
        except Exception:
            # Kunne vi ikke lukke den, må kravet ikke blive hængende hos os.
            logger.warning("recovery-dispatcher: kunne ikke lukke forældet opgave "
                           "%s — giver kravet tilbage", task_id[:24], exc_info=True)
            in_flight_runs.release_recovery_claim(
                task_id, generation, owner=ejer, reason="kunne ikke lukke forældet opgave",
                retry_after_s=BACKOFF_SECONDS)
            return {"started": 0, "released": 1, "claimed": task_id,
                    "error": "settle-fejlede"}
        _luk_afloest_raekke(task_id, reason="samtalen gik videre efter afbrydelsen")
        logger.info(
            "recovery-dispatcher: %s droppet — brugeren skrev nyt i %s efter kørslen døde",
            task_id[:24], session_id[:28])
        return {"started": 0, "released": 1, "claimed": task_id,
                "error": "samtalen-gik-videre"}

    # HAR KØRSLEN SELV SVARET? (10/10-2026)
    #
    # Søsteren til tjekket ovenfor, og den dækker et andet hul: brugeren behøver
    # ikke at have skrevet noget for at et run er færdigt. Målt 10/10 skrev
    # `visible-9a64aa1d` sit svar, blev stemplet `interrupted` ét sekund senere,
    # og blev genoptaget tre sekunder efter — Bjørn ventede, han skrev intet.
    #
    # Samme lukning som ovenfor: `settle_terminal` og ikke `release_recovery_claim`
    # (ellers tager næste tick kravet igen og dropper det igen), og `cancelled`
    # frem for `failed_terminal`, så en opgave der ER besvaret ikke giver et varsel.
    if _runnet_har_svaret(task_id):
        try:
            in_flight_runs.settle_terminal(
                task_id, status="cancelled",
                reason="kørslen svarede selv før den blev stemplet afbrudt",
                expected_generation=generation, expected_owner=ejer)
        except Exception:
            logger.warning("recovery-dispatcher: kunne ikke lukke besvaret opgave "
                           "%s — giver kravet tilbage", task_id[:24], exc_info=True)
            in_flight_runs.release_recovery_claim(
                task_id, generation, owner=ejer, reason="kunne ikke lukke besvaret opgave",
                retry_after_s=BACKOFF_SECONDS)
            return {"started": 0, "released": 1, "claimed": task_id,
                    "error": "settle-fejlede"}
        _luk_afloest_raekke(task_id, reason="kørslen svarede selv")
        logger.info("recovery-dispatcher: %s droppet — kørslen svarede selv i %s",
                    task_id[:24], session_id[:28])
        return {"started": 0, "released": 1, "claimed": task_id,
                "error": "koerslen-svarede-selv"}

    besked = _besked_fra(krav)
    if not besked:
        in_flight_runs.settle_terminal(
            task_id, status="cancelled", reason="recovery-original-request-missing",
            expected_generation=generation, expected_owner=ejer,
        )
        _luk_afloest_raekke(task_id, reason="oprindelig anmodning mangler")
        return {"started": 0, "released": 1, "claimed": task_id,
                "error": "missing-original-request"}
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
        from core.services.session_permission import hent_permission
        run_id = start_user_run_detached(
            message=besked,
            session_id=session_id,
            approval_mode=("trust" if str(krav.get("approval_mode") or
                                           hent_permission(session_id)) == "trust" else "ask"),
            thinking_mode=str(krav.get("thinking_mode") or "think"),
            tool_scope=str(krav.get("tool_scope") or ""),
            surface=str(krav.get("surface") or ""),
            force_user_id=str(krav.get("force_user_id") or "") or None,
            local_tool_exec=bool(krav.get("local_tool_exec")),
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

    # Først NU, hvor fortsættelsen er i luften. Lukkede vi rækken før starten
    # og starten fejlede, havde vi stemplet en opgave død som stadig skulle
    # tages igen — og `release_recovery_claim` ovenfor ville ikke kunne rulle
    # stemplet tilbage.
    _luk_afloest_raekke(task_id, reason=f"afloest af {str(run_id)[:40]}")
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
