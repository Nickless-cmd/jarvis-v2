"""Indbakken skal kunne VÆKKE — ikke kun gate.

Bjørn 10/10-2026: «skal inbox kunne vække dig, på den hvis du ikk er i et
aktivt run?»

## Hullet (målt 10/10-2026)

`inbox_gate` blokerer kun mutationer INDE i et aktivt run. Intet starter et run
fordi en post findes. En `kraever_handling=1`-post uden dispatcher ventede
derfor til næste heartbeat eller Bjørns næste besked — og kun `wakeup`-typen
havde både en indbakke-række OG en dispatcher der starter et run.

En forpligtelse der kræver handling bør ikke kunne stå og vente på at nogen
tilfældigvis kører.

## Vækkeren er bevidst KONSERVATIV

  * **Kun gatende poster** — plus én eksplicit tredje klasse. `kraever_handling`
    + verificeret ejer er samme kandidat-regel som `inbox_gate` bruger: en
    informerende post må ikke starte et run. Dertil `KAN_DISPATCHES_KILDETYPER`
    (13/10-2026): en post der MÅ starte et run men ALDRIG må nægte en mutation
    — og kun når kilden selv melder den moden (`_er_moden`).
  * **Kun når INTET kører.** Guarden er `wakeup_dispatcher._active_turn_blocks`
    — genbrugt, ikke kopieret. To definitioner af «nogen taler nu» er præcis den
    drift der gav fire fejl i dette spor.
  * **Én vækning pr. post.** Ellers bliver hver poll-runde et nyt run, og det
    er en kæde der skriver i Bjørns chat. Sporet skrives i postens
    `sidste_vaekning_tur` FØR run'et startes.
  * **Self-safe.** Enhver fejl → ingen vækning, aldrig en væltet poller.

## Vækkeren har sit EGET spor (rettet 10/10-2026, målt i drift)

Første udgave skrev sit spor i `sidste_paamindelse_tur` — det felt `inbox_gate`
også skriver sit run-id i når den nægter en mutation. Målt i drift: med gatens
spor sat gav `kandidater()` **0** og `{'vaekket': 0, 'aarsag':
'ingen_kandidater'}`; nulstillede man sporet, gav den **1** og `vaekket: 1`.
Kun sporet skilte.

Konsekvensen var skarp: enhver post der havde fået bare én gate-påmindelse
kunne ALDRIG vække — og det er præcis de poster vækkeren findes for. Den var
virkningsløs for sit eget formål. Nu læser og skriver den `sidste_vaekning_tur`
via `db_inbox.noter_vaekning`/`nulstil_vaekning`, og gatens felt er urørt.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

#: Hvor mange poster én runde må vække. Ti åbne poster må ikke blive ti runs.
MAKS_PR_RUNDE = 2

#: Mærket der skrives i `sidste_vaekning_tur` når vækkeren har fyret.
#: Bevidst et FAST navn og ikke et run-id: det er vækkeren der har handlet,
#: og sporet skal kunne læses som netop det.
_VAEKKET_AF = "inbox-idle-waker"


def _wakeup_records() -> dict[str, dict[str, Any]]:
    """Fyrede, sprangte vækninger — nøglet på `wakeup_id`.

    Self-safe: kan kilden ikke læses, svarer vi TOMT. En vækning vi ikke
    kunne læse må ikke blive et run på et gæt — og et tomt svar betyder
    «ingen at løfte», ikke «løft alt».
    """
    try:
        from core.services import self_wakeup

        return {str(r.get("wakeup_id") or ""): r
                for r in self_wakeup.ventende_efter_skip()}
    except Exception as exc:  # noqa: BLE001
        logger.debug("inbox_idle_waker: kunne ikke laese sprangte vaekninger: %s", exc)
        return {}


def _er_moden(post: dict[str, Any], *, vaekninger: dict[str, dict[str, Any]]) -> bool:
    """Er en dispatchbar post MODEN — melder kilden selv at den er klar?

    Dette led er hele forskellen mellem «findes» og «skal køre». En væknings
    indbakke-post oprettes ved BOOKINGEN, ikke ved fyringen. Uden en
    modenheds-test ville vækkeren starte et run for en vækning der først fyrer
    i morgen — og den ville gøre det hver eneste poll-runde.
    """
    kildetype = str(post.get("kildetype") or "")
    if kildetype == "wakeup":
        return str(post.get("kilde_id") or "") in vaekninger
    # `ci_alarm` (15/10-2026): en CI-fejl er moden i det øjeblik den skrives —
    # den er ikke booket til en fremtidig fyring som en wakeup. Uden dette led
    # laa `kan_dispatch` alene til grund, men `_er_moden` sagde nej, og alarmen
    # ventede alligevel. Maalt: Bjørn sad i en aaben session og fik intet
    # signal da desk-release 0.6.237 fejlede.
    if kildetype == "ci_alarm":
        return True
    # `recurring` (19/10-2026): HELE todelingen af rutiner ligger her.
    #
    # Posten findes allerede når den når hit — `run_closure_gate` skrev den da
    # runnet sluttede. Spørgsmålet er kun om den må VÆKKE, og svaret er nej
    # medmindre opgaven er en SESSION-rutine. En baggrunds-rutine rapporterer
    # til indbakken og venter til nogen kigger; den må ikke trænge ind i en
    # samtale den ikke hører til. Det er præcis Bjørns valg ved oprettelsen.
    #
    # Er opgaven ukendt eller slettet, svarer `er_session_rutine` False, og
    # posten bliver liggende synlig uden at vække. Det er den rigtige retning:
    # en post vi ikke kan redegøre for må ikke starte et run.
    if kildetype == "recurring":
        from core.services.recurring_tasks import er_session_rutine

        task_id = _task_id_fra_kilde(str(post.get("kilde_id") or ""))
        return bool(task_id) and er_session_rutine(task_id)
    return False


#: `run_closure_gate` skriver `kilde_id` som `recurring-{task_id}-{run_id}`.
#: Task-id'er er `rec-` plus hex (målt på alle 13 levende). Run-id'er kan være
#: `autonomous-…`, `visible-…` eller `run_…`, så vi kan ikke bare splitte på
#: den sidste bindestreg — vi skal have fat i opgave-delen forrest.
_TASK_ID_RE = re.compile(r"^recurring-(rec-[0-9A-Za-z]+)-")


def _task_id_fra_kilde(kilde_id: str) -> str:
    """Udtræk opgave-id'et fra en recurring-posts `kilde_id`.

    Ukendt form → tom streng. Kalleren behandler det som «kan ikke redegøres
    for» og vækker ikke. Et gæt her ville vække et run på en post vi ikke
    forstår.
    """
    m = _TASK_ID_RE.match(str(kilde_id or "").strip())
    return m.group(1) if m else ""


def kandidater(bruger_id: str) -> list[dict[str, Any]]:
    """Åbne, gatende poster for brugeren — dem der må starte et run.

    Samme regel som `inbox_gate.evaluer_inbox_mutation` bruger for hvem der må
    gate: `kraever_handling` OG en verificeret ejer. `ukendt` og `huset` kan
    aldrig gate, og må derfor heller ikke vække.

    «Har jeg allerede vækket?» læses i `sidste_vaekning_tur` — vækkerens EGET
    felt. Den må ikke læse `sidste_paamindelse_tur`: gaten skriver sit run-id
    der når den nægter en mutation, og så ville enhver post der havde fået bare
    én gate-påmindelse blive permanent usynlig her. Det var målt i drift.
    """
    from core.runtime import db_inbox
    from core.services.inbox_state import kan_dispatch

    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return []
    poster = db_inbox.liste_aktiv(bruger_id=bruger_id)
    vaekninger: dict[str, dict[str, Any]] | None = None
    ud: list[dict[str, Any]] = []
    for p in poster:
        if str(p.get("sidste_vaekning_tur") or "").strip():
            continue
        if str(p.get("verificeret_ejer") or "") != db_inbox.EJER_JARVIS:
            continue
        # En wakeup-post findes allerede fra BOOKINGEN og kan som frisk,
        # verificeret Jarvis-post baere `kraever_handling=1`. Det generelle
        # opgaveflag maa derfor aldrig faa lov at omgaa kildens ur: efter en
        # genstart er samtalen idle, og polleren ville ellers loefte posten
        # straks, selv om dens `fire_at` stadig ligger i fremtiden.
        #
        # Kilden er autoritativ for wakeup-modenhed uanset postens flag. Andre
        # gatende typer (fx `afvist_run`) bevarer den generelle vej nedenfor.
        if str(p.get("kildetype") or "") == "wakeup":
            if vaekninger is None:
                vaekninger = _wakeup_records()
            if _er_moden(p, vaekninger=vaekninger):
                ud.append(p)
            continue
        if p.get("kraever_handling"):
            ud.append(p)
            continue
        # Den TREDJE klasse. Kilde-læsningen er DOVEN med vilje: en post der
        # ikke er dispatchbar må ikke koste et opslag i en anden kilde.
        if not kan_dispatch(p.get("kildetype")):
            continue
        if vaekninger is None:
            vaekninger = _wakeup_records()
        if _er_moden(p, vaekninger=vaekninger):
            ud.append(p)
    return ud


def _noget_koerer() -> bool:
    """Kører der et run lige nu? Self-safe → False (ingen blokering) ved fejl.

    Guarden er `wakeup_dispatcher._active_turn_blocks`, som tjekker BÅDE et
    levende run i sessionen (via run-loggen) OG karantænen efter Bjørns seneste
    besked. Den er genbrugt frem for kopieret: to definitioner af «nogen taler
    nu» driver fra hinanden, og så bliver det ene filter stille virkningsløst.
    """
    try:
        from core.services.wakeup_dispatcher import _active_turn_blocks
        from core.identity.owner_resolver import resolve_owner_target_session

        session = resolve_owner_target_session() or ""
        return bool(_active_turn_blocks(session))
    except Exception as exc:  # noqa: BLE001
        logger.debug("inbox_idle_waker: kunne ikke afgoere aktiv-tilstand: %s", exc)
        return False


def _maal_session(post: dict[str, Any]) -> str:
    """Hvilken SAMTALE hører denne post til?

    Vækkeren startede indtil 14/10-2026 et run i `auto-autonomous` for ALLE
    gatende poster: `_dispatch_tekst` gav `session=None`, og
    `normalize_origin("inbox")` kollapser ukendte navne til «autonomous».
    Resultatet var et run i en session ingen læser — Bjørn: «de bør vække den
    session de høre til».

    Rækkefølgen er den SAMME som wakeup-dispatcheren bruger
    (`pick_wakeup_run_target`) — ikke en kopi. To definitioner af «hvor skal
    dette lande» driver fra hinanden, og så bliver den ene stille virkningsløs:

      1. Vækningens egen samtale (en wakeup bærer sin session i recorden).
      2. Ejerens app-samtale — resolvert, og med guard mod eksterne kanaler
         (Discord/Telegram), så et app-run ikke re-engagerer en ekstern kanal.
      3. Tom streng ⇒ INGEN vækning. Et run uden en samtale er præcis den
         silo vi fjerner; posten venter hellere til næste runde.
    """
    from core.identity.owner_resolver import (
        resolve_owner_app_session,
        resolve_owner_target_session,
        session_is_external_channel,
    )
    from core.services.wakeup_dispatcher import pick_wakeup_run_target

    record_session = ""
    if str(post.get("kildetype") or "") == "wakeup":
        rec = _wakeup_records().get(str(post.get("kilde_id") or ""))
        if rec:
            record_session = str(rec.get("session_id") or "")
    # En post kan BÆRE sin samtale (19/10-2026). For en session-rutine er det
    # den mest præcise adresse der findes: opgaven blev bestilt i en bestemt
    # samtale, og posten blev skrevet med den samme. Uden dette led faldt den
    # til ejerens app-samtale — rigtigt i dag, men et gæt hvis han har flere.
    if not record_session:
        record_session = str(post.get("session_id") or "").strip()
    return pick_wakeup_run_target(
        channel="app",
        record_session=record_session,
        app_resolver=resolve_owner_app_session,
        owner_resolver=resolve_owner_target_session,
        is_external=session_is_external_channel,
    ) or ""


def _start_run(tekst: str, *, session_id: str) -> bool | None:
    """Start det autonome run i den samtale posten hører til. Adskilt, så
    testen kan bytte den ud ét sted.

    `session_id` er PÅKRÆVET: et run uden en samtale ville falde tilbage til
    `auto-{origin}-{dato}` — den silo vækkeren netop ikke må skabe.

    Returnerer starterens svar: `False` = run-guarden eller gut-gaten afviste
    det TAVST, og posten må ikke stå som vækket. `None` bevares for kaldere og
    tests der bytter funktionen ud uden at returnere noget — tvivlen skal falde
    ud til fordel for at have startet, ikke til at rulle et rigtigt run tilbage.
    """
    from core.services.visible_autonomous_run import start_autonomous_run

    return start_autonomous_run(tekst, session_id=session_id, origin="inbox")


def _direktiv(post: dict[str, Any]) -> str:
    kilde_id = str(post.get("kilde_id") or post.get("id") or "")
    kildetype = str(post.get("kildetype") or "")
    beskrivelse = str(post.get("beskrivelse") or "").strip()
    return (
        f"[INBOX VÆKKEDE — {kildetype}/{kilde_id}]\n"
        f"En post i din indbakke kræver handling og har ventet på dig:\n"
        f"{beskrivelse or '(ingen beskrivelse)'}\n\n"
        "UDFØR den nu med dine tools — beskriv den ikke bare. Er den løst, "
        f"så luk den med `inbox_done(id=\"{kilde_id}\")`. Kan den ikke løses "
        "nu, så sig kort hvorfor og lad den stå.\n"
        "RAPPORTÉR KUN hvis der er noget NYT Bjørn skal vide. Er posten "
        "allerede håndteret eller uændret, så luk den og afslut uden at skrive "
        "til ham."
    )


def _dispatch_tekst(post: dict[str, Any]) -> str:
    """Run-direktivet for posten.

    En SPRUNGT vækning bærer sin EGEN tekst: den skal køre med `direktiv_for`
    — den samme instruktion dispatcheren ville have givet. Er kilden væk
    eller ikke læsbar, falder vi tilbage til det generiske direktiv; et run
    med den rigtige post er bedre end intet run.

    HVOR runnet skal køre, er ikke denne funktions sag — det afgør
    `_maal_session` for ALLE poster. Indtil 14/10-2026 blandede de to spørgsmål
    sig her, og kun wakeup-typen fik et svar på det andet.
    """
    from core.services.inbox_state import kan_dispatch

    if not post.get("kraever_handling") and kan_dispatch(post.get("kildetype")):
        if str(post.get("kildetype") or "") == "wakeup":
            rec = _wakeup_records().get(str(post.get("kilde_id") or ""))
            if rec:
                from core.services.self_wakeup import direktiv_for

                return direktiv_for(rec)
    return _direktiv(post)


def vaek_paa_aabne_poster(*, bruger_id: str) -> dict[str, Any]:
    """Væk ét run for de øverste gatende poster — hvis intet kører.

    Returnerer altid `status="ok"` med et tal, også når intet blev gjort: en
    poller må kunne kalde den uden at skelne «intet at gøre» fra «fejl».
    """
    try:
        poster = kandidater(bruger_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_idle_waker: kunne ikke laese kandidater: %s", exc)
        return {"status": "ok", "vaekket": 0, "aarsag": "laesefejl"}

    if not poster:
        return {"status": "ok", "vaekket": 0, "aarsag": "ingen_kandidater"}

    if _noget_koerer():
        return {"status": "ok", "vaekket": 0, "aarsag": "aktivt_run"}

    from core.runtime import db_inbox

    vaekket = 0
    for indeks, post in enumerate(poster[:MAKS_PR_RUNDE]):
        # MELLEM-ITERATIONERNES TJEK (14/10-2026). Pre-loop-tjekket ovenfor ser
        # kun tilstanden FOER foerste start. Uden dette kunne to poster starte
        # to runs i samme runde — `MAKS_PR_RUNDE = 2` var et loft uden en vagt
        # undervejs. Den spoerger den SAMME cross-process-vagt som pre-checket.
        if indeks and _noget_koerer():
            break
        kilde_id = str(post.get("kilde_id") or post.get("id") or "")
        # HVOR skal runnet køre? En post uden en samtale vækkes IKKE — den
        # venter. Faldt den til `auto-{origin}-{dato}`, ville vi skabe præcis
        # den silo vækkeren findes for at undgå (målt frem til 14/10-2026).
        # Tjekket ligger FØR sporet: en post vi ikke vækker må ikke stå som
        # vækket og dermed være usynlig i næste runde.
        session_id = _maal_session(post)
        if not session_id:
            logger.info(
                "inbox_idle_waker: %s/%s har ingen samtale at vække i — venter",
                post.get("kildetype"), kilde_id)
            continue
        # Sporet skrives FØR run'et startes: kaster starten, må posten ikke stå
        # som vækket — så prøves den igen i næste runde.
        try:
            db_inbox.noter_vaekning(
                bruger_id=bruger_id, kilde_id=kilde_id, tur=_VAEKKET_AF)
        except Exception as exc:  # noqa: BLE001
            logger.debug("inbox_idle_waker: kunne ikke notere %s: %s", kilde_id, exc)
            continue
        tekst = _dispatch_tekst(post)
        try:
            startet = _start_run(tekst, session_id=session_id)
            # TAVS AFVISNING (14/10-2026). `start_autonomous_run` returnerede
            # foer `None` ogsaa naar run-guarden eller gut-gaten afviste — og
            # vaekkeren talte det som en vaekning. Posten stod som vaekket, mens
            # intet koerte, og naeste runde sprang den over. Nu rulles sporet
            # tilbage, saa posten venter i stedet for at forsvinde.
            if startet is False:
                try:
                    db_inbox.nulstil_vaekning(bruger_id=bruger_id, kilde_id=kilde_id)
                except Exception:  # noqa: BLE001 — sporet er sat; en fejlet rollback maa ikke vaelte polleren
                    pass
                logger.info(
                    "inbox_idle_waker: %s/%s blev afvist af starteren — posten venter",
                    post.get("kildetype"), kilde_id)
                continue
            vaekket += 1
            logger.info("inbox_idle_waker: vaekkede paa %s/%s", post.get("kildetype"), kilde_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("inbox_idle_waker: kunne ikke starte run for %s: %s",
                           kilde_id, exc)
            # Rul sporet tilbage, så posten proeves igen.
            try:
                db_inbox.nulstil_vaekning(bruger_id=bruger_id, kilde_id=kilde_id)
            except Exception:  # noqa: BLE001 — sporet er sat; en fejlet rollback maa ikke vaelte polleren
                pass

    return {"status": "ok", "vaekket": vaekket}
