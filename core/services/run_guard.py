"""Én fælles vagt: kører der et run i denne session lige nu?

Hvorfor ÉN vagt og ikke seks (13/10-2026)
-----------------------------------------
Der er seks uafhængige steder der starter baggrunds-runs — `wakeup_dispatcher`,
`scheduled_tasks`, `recurring_tasks`, `routine_trigger_adapters` (heartbeat),
`dreaming_session` og `inbox_idle_waker` — og hver især med sin EGEN vagt,
eller ingen. Det er ikke en detalje: `wakeup_dispatcher._active_turn_blocks`
læser `run_event_log`, som er **in-memory per proces**.

Daemonerne kører i jarvis-runtime (8011, `JARVIS_ENABLE_RUNTIME_SERVICES=1`);
desk'ens chat serveres af jarvis-api (8080, `=0`). En vagt i runtime-processen
kan derfor ikke se Bjørns tur, som kører i api-processen. Målt 13/10-2026:
`autonomous-af9f…` og `visible-4f70…` stod begge `running` i SAMME session
`chat-6f46…` med 31 sekunders mellemrum — den ene født mens den anden kørte.
Det var den dublet Bjørn så som «flere instanser af dig i samme session».

Kilden her er `in_flight_runs`, som ER delt: fil + flock, ejer =
`<pid>:<starttid>`. Både den synlige tur og de autonome runs skriver til den
allerede, så vagten kræver ingen ny bogføring — kun en læser, som ikke fandtes.

Grænsen: kun BAGGRUNDS-kilder rammes
------------------------------------
``BESKYTTEDE_ORIGINS`` er en positivliste. Et wakeup, en planlagt opgave eller
et heartbeat må vente på at sessionen bliver ledig; en Discord-besked Bjørn
selv sendte, eller et barn-agent-svar han venter på, må ikke. Kilden tages RÅ
(før `normalize_origin`), fordi `normalize_origin` kollapser ukendte navne til
"autonomous" — og "inbox" ville dermed blive uskelneligt fra et vilkårligt
autonomt run.

Self-safe: enhver fejl → ingen blokering. Et wakeup må ikke forsvinde, fordi
registret ikke kunne læses.
"""
from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

#: Baggrunds-kilder hvor vagten gælder. RÅ navne — se docstringen.
#:
#: BEVIDST UDE: continuation (`visible_runs_memory` sender ingen origin),
#: Discord/Telegram-svar, agent-resultat-levering (`agent_message_receipt`) og
#: `jarvisx_processes`. De er svar på noget Bjørn selv gjorde, og at blokere
#: dem ville tabe et svar han venter på. De har deres egne vagter, eller
#: ingen — det er en ÅBEN sag, ikke en påstand om at de er dækket.
BESKYTTEDE_ORIGINS: Final[frozenset[str]] = frozenset({
    "wakeup", "self-wakeup", "inbox", "scheduled", "recurring",
    "heartbeat", "heartbeat_runtime", "dream", "council",
})


def levende_run_i_session(session_id: str) -> str:
    """Run-id på et LEVENDE run i sessionen — cross-proces. "" hvis ingen.

    To kilder, i den rækkefølge de er præcise:

    1. ``run_event_log.active_run_for_session`` — samme proces, øjeblikkelig,
       og den eneste der kender et run der endnu ikke har nået journalen.
    2. ``in_flight_runs.levende_koersler`` — den DELTE journal. Det er den der
       fanger api-processens tur set fra runtime-processen, og det er hele
       grunden til at denne funktion findes.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return ""
    try:
        from core.services import run_event_log as rel

        rid = rel.active_run_for_session(sid)
        if rid:
            return str(rid)
    except Exception as exc:  # noqa: BLE001 — self-safe: gæt aldrig på et run
        logger.debug("run_guard: kunne ikke laese run-loggen for %s: %s", sid[:28], exc)
    try:
        from core.services import in_flight_runs as ifr

        poster = ifr.levende_koersler(session_id=sid)
        if poster:
            return str(poster[0].get("run_id") or "")
    except Exception as exc:  # noqa: BLE001 — self-safe, se ovenfor
        logger.debug("run_guard: kunne ikke laese registret for %s: %s", sid[:28], exc)
    return ""


def blokeringsgrund(origin: str, session_id: str) -> str:
    """Årsag hvis et nyt BAGGRUNDS-run ikke må starte her. "" = fri bane.

    Kaldes som pre-flight i run-starterne, FØR et run fødes. Er svaret ikke
    tomt, må runnet ikke starte: forpligtelsen bliver liggende i indbakken og
    tages i den kørende turs kontekst, eller når sessionen er ledig.
    """
    try:
        o = str(origin or "").strip().lower()
        if o not in BESKYTTEDE_ORIGINS:
            return ""
        rid = levende_run_i_session(session_id)
        if not rid:
            return ""
        return f"levende_run_i_session:{rid[:24]}"
    except Exception as exc:  # noqa: BLE001 — self-safe: hellere køre end tabe
        logger.debug("run_guard: vagten kunne ikke afgoeres: %s", exc)
        return ""


def parker_forpligtelse(
    *,
    origin: str,
    session_id: str,
    beskrivelse: str,
    kilde_id: str = "",
) -> dict[str, object]:
    """Læg en AFVIST forpligtelse i indbakken i stedet for at tabe den.

    ## Hullet (målt 14/10-2026)

    Begge run-startere loggede «forpligtelsen bliver i indbakken til sessionen
    er ledig» og `return`erede så — uden at skrive noget. Målt: nul nye
    `inbox_items` i vinduet, og `grep registrer_kilde` i
    `visible_autonomous_run.py` gav ét træf: en kommentar. Et afvist run
    forsvandt altså sporløst: hverken kørt eller lagt til side.

    Bjørn 14/10-2026: «istedet for at afvise burde de lande i indbox og så
    vælger inbox om du er i et run og du for den i prompten til næste runde
    eller idle vække dig». Det er præcis denne funktion.

    ## Hvorfor `bloker=True` og ikke `kraever_handling` alene

    `kraever_handling` udregnes i `registrer_kilde` som «ejer er Jarvis OG
    kildetypen står ikke i `IKKE_GATENDE_KILDETYPER`» — og `recurring` og
    `scheduled` står i den liste. En post med sin egen kildetype ville derfor
    få `kraever_handling=0`, ikke vække når Bjørn er idle, og først dukke op
    næste gang han selv skriver. `bloker=True` er den eksplicitte undtagelse
    (se `flag_fra_bruger`): den gater uanset kildetype, og
    `opret_eller_hent` giver den automatisk en 30-dages frist — så en afvist
    forpligtelse kan presse uden at kunne låse nogen fast for evigt.

    ## Samtalen følger med

    `session_id` skrives på posten, så `inbox_idle_waker._maal_session` kan
    vække DEN samtale forpligtelsen hørte til — ikke en `auto-*`-silo. Det er
    samme binding som `session_binding` bruger for urene.

    Self-safe: enhver fejl returnerer en fejl-status. En manglende post må
    aldrig kunne vælte den run-starter der kaldte os.
    """
    try:
        from core.services.inbox_state import _ejer_id, registrer_kilde
        from core.services.session_context_resolve import aktivt_run_id

        bruger = _ejer_id()
        if not bruger:
            return {"status": "fejl", "error": "ingen ejer-identitet"}
        kid = str(kilde_id or "").strip() or f"afvist-{origin}-{session_id[:12]}"
        # HVILKET RUN ER BEVISET? (19/10-2026)
        #
        # `aktivt_run_id("")` læser en ContextVar i DENNE proces. Det virker
        # når afvisningen sker i samme proces som det kørende run — men det er
        # netop ikke tilfældet her: rutinen fyrer i `jarvis-runtime` (8011),
        # mens Bjørns tur kører i `jarvis-api` (8080). Målt 19/10-2026: mid-
        # dagsmedicinen blev afvist korrekt, posten blev skrevet, og den stod
        # med `verificeret_ejer='ukendt'` — hverken gate eller vækning. En
        # tavs post er værre end ingen post, fordi loggen lovede det modsatte.
        #
        # Beviset FINDES: `levende_run_i_session` læser den DELTE journal
        # (`in_flight_runs`, fil + flock), som begge processer skriver til. Det
        # er samme kilde vagten selv brugte til at afvise — så vi genbruger
        # præcis det run-id den netop har set, frem for at gætte.
        _bevis = str(aktivt_run_id("") or "").strip() or levende_run_i_session(
            str(session_id or "")
        )
        return registrer_kilde(
            bruger_id=bruger,
            kildetype="afvist_run",
            kilde_id=kid,
            # Det KØRENDE run er beviset: `verificeret_jarvis_run` kræver at
            # run-id'et tilhører et run der kører nu. Er det tomt, falder posten
            # til `ukendt` — og så bærer `bloker` gatingen alene, hvilket målt
            # betyder at den hverken gater eller vækker.
            oprettende_run_id=_bevis,
            beskrivelse=beskrivelse[:400],
            bloker=True,
            session_id=str(session_id or ""),
        )
    except Exception as exc:  # noqa: BLE001 — self-safe: en post maa ikke vaelte starteren
        logger.warning("run_guard: kunne ikke parkere forpligtelsen: %s", exc)
        return {"status": "fejl", "error": str(exc)}
