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
from datetime import UTC, datetime
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
    if kildetype in ("ci_alarm", "vaekning"):
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
    """Kører der et run lige nu? Sensorfejl blokerer konservativt en vækning.

    Guarden er `wakeup_dispatcher._active_turn_blocks`, som tjekker BÅDE et
    levende run i sessionen (via run-loggen) OG karantænen efter Bjørns seneste
    besked. Den er genbrugt frem for kopieret: to definitioner af «nogen taler
    nu» driver fra hinanden, og så bliver det ene filter stille virkningsløst.
    """
    try:
        from core.identity.owner_resolver import resolve_owner_target_session

        session = resolve_owner_target_session() or ""
        return _session_er_aktiv(session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_idle_waker: kunne ikke afgoere aktiv-tilstand: %s", exc)
        return True


def _session_er_aktiv(session_id: str) -> bool:
    """Tjek den konkrete målsamtale, ikke kun ejerens aktuelle standardsession.

    En inbox-post kan bære sin egen session.  Preflight-tjekket brugte tidligere
    ejerens resolver før posten var valgt; derefter kunne ``_maal_session`` pege
    på en anden, netop aktiv samtale.  Sådan landede wake-4b2bdb004f midt i en
    synlig tur 3/11-2026.  Sensorfejl er konservativt en blokering her.
    """
    if not str(session_id or "").strip():
        return True
    try:
        from core.services.wakeup_dispatcher import _active_turn_blocks

        # KUN et levende run (Bjørn 12/11-2026). Tidskarantænerne efter hans og
        # min sidste besked kaldte en rolig samtale «aktiv» og holdt en vækning
        # tilbage i minutter uden at nogen skrev eller noget kørte.
        return bool(_active_turn_blocks(str(session_id), karantaene=False))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "inbox_idle_waker: kunne ikke afgoere maal-sessionens aktivitet: %s",
            exc,
        )
        return True


#: Hvor længe en post må vente på en ledig samtale, før den KRÆVES læst.
#: Bjørn 12/11-2026: «hvis du er aktiv lægge den markeret i inbox og forlange
#: du læser den». Uden denne grænse stod en fyrede vækning hvis run ikke kunne
#: startes som `kraever_handling=0` — hverken kørt eller krævet.
KRAEV_ALDER_MIN = 5


def _alder_minutter(
    post: dict[str, Any], *, nu: "datetime | None" = None,
) -> float | None:
    """Hvor længe posten har været AKTUEL — ikke hvor længe rækken har eksisteret.

    En vækning får sin indbakke-række ved BOOKINGEN, så `created_at` kan være
    timer ældre end det øjeblik hun fyrer. Måler vi på den, ville hver planlagt
    vækning være «gammel» i samme sekund hun fyrer og blive krævet med det
    samme — også når samtalen blev fri igen om ti sekunder. For en vækning
    tælles derfor fra `fire_at`; for alle andre kilder fra `created_at`.

    `None` = alderen kan ikke bestemmes (manglende eller ulaesbar tidsstempel).
    Kalderen behandler det som «for ung»: et gæt må ikke gøre en post gatende.
    """
    raa = ""
    if str(post.get("kildetype") or "") == "wakeup":
        rec = _wakeup_records().get(str(post.get("kilde_id") or ""))
        if rec:
            raa = str(rec.get("fire_at") or "")
    if not raa:
        raa = str(post.get("created_at") or "")
    if not raa:
        return None
    try:
        sat = datetime.fromisoformat(raa)
    except (TypeError, ValueError):  # noqa: BLE001 — ukendt alder er et svar, ikke en fejl: et gæt maa ikke goere posten gatende
        return None
    if sat.tzinfo is None:
        sat = sat.replace(tzinfo=UTC)
    return ((nu or datetime.now(UTC)) - sat).total_seconds() / 60.0


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


def _start_run(
    tekst: str,
    *,
    session_id: str,
    user_id: str,
    task_id: str = "",
    permission_session: str = "",
    origin: str = "",
    max_tool_calls: int = 0,
    max_seconds: float = 0.0,
    tool_scope: str = "",
    kilde_id: str = "",
    kildetype: str = "",
) -> bool | None:
    """Start det autonome run i den samtale posten hører til. Adskilt, så
    testen kan bytte den ud ét sted.

    `session_id` er PÅKRÆVET: et run uden en samtale ville falde tilbage til
    `auto-{origin}-{dato}` — den silo vækkeren netop ikke må skabe.

    `kilde_id`/`kildetype` er postens adresse. De bruges KUN til afregningen:
    når runnet er terminalt, kvitteres posten automatisk (12/11-2026), så en
    vækning ikke bliver stående uforbrugt fordi jeg glemte at kalde
    `inbox_done`. Er de tomme, springes afregningen over — et run uden en post
    skal ikke kunne lukke noget tilfældigt.

    Returnerer starterens svar: `False` = run-guarden eller gut-gaten afviste
    det TAVST, og posten må ikke stå som vækket. `None` bevares for kaldere og
    tests der bytter funktionen ud uden at returnere noget — tvivlen skal falde
    ud til fordel for at have startet, ikke til at rulle et rigtigt run tilbage.
    """
    from core.services.background_start_reservation import reserve_background_start
    from core.services.visible_autonomous_run import start_autonomous_run

    # Hold den fælles cross-process reservation gennem både det sidste
    # active-run-tjek og den synkrone registrering i starteren. Dermed kan
    # side-opgave-vækkeren ikke passere samme vindue samtidig. Sensorfejl er
    # en afvisning her; posten får sit vækkespor rullet tilbage af kalderen.
    with reserve_background_start(session_id) as reservation:
        if not reservation.acquired:
            logger.info(
                "inbox_idle_waker: start afvist for %s: %s",
                session_id[:28], reservation.reason,
            )
            return False
        # ARBEJDSRUMMET SKAL MED (11/11-2026). Da `wakeup_dispatcher` blev
        # flyttet herind, fulgte dens `set_context(...)`-kald IKKE med — og
        # `start_autonomous_run` arver blot ContextVars fra den tråd der
        # kalder. Uden dette led kører en vækning booket i Michelles
        # arbejdsrum i Bjørns, og runnet ser den forkerte hukommelse. Fejlen
        # er tavs: runnet starter og svarer som om intet er galt.
        # `workspace_dir()` er husets hybrid-resolver (legacy + SQLite).
        # Fejler den, vækker vi alligevel — men vi LOGGER tabet, så det kan
        # måles frem for at være usynligt.
        token = None
        if str(user_id or "").strip():
            try:
                from core.identity.workspace_context import set_context
                from core.runtime.workspace_paths import workspace_dir

                ws = workspace_dir(str(user_id)).name
                token = set_context(
                    workspace_name=ws, user_id=str(user_id), user_display_name=""
                )
            except Exception as exc:  # noqa: BLE001 — se kommentaren ovenfor
                logger.warning(
                    "inbox_idle_waker: kunne ikke binde arbejdsrum for %s: %s",
                    str(user_id)[:28], exc,
                )
        def _bind_start(
            *, visible_run_id: str, session_id: str = "", **_: Any,
        ) -> None:
            """Skriv bindingen paa posten og paa rutine-raekken, hvis der er en.

            `bind_visible_run` er en no-op naar `task_id` ikke matcher et
            koerende rutine-run, saa den kaldes uden at spoerge foerst.

            POSTEN BINDES OGSAA (12/11-2026). Uden det kan man ikke svare paa
            hvad en vaekning kostede: `costs` baerer `run_id`, men posten bar
            intet run-id, og et tidsvindue paa 120 s rammer ogsaa runs posten
            ikke startede. Bindingen er det eneste sted koblingen findes.
            """
            if str(kilde_id or "").strip():
                try:
                    from core.runtime import db_inbox

                    db_inbox.noter_leveret_til_run(
                        bruger_id=str(user_id or ""),
                        kilde_id=str(kilde_id),
                        run_id=str(visible_run_id or ""),
                        session_id=str(session_id or ""),
                    )
                except Exception as exc:  # noqa: BLE001 — binding maa aldrig vaelte en vaekning
                    # Ikke tavst: et tabt spor goer kroneloftet blindt, og det
                    # skal kunne maales i loggen i stedet for at vaere usynligt.
                    logger.warning(
                        "inbox_idle_waker: kunne ikke binde posten %s til run: %s",
                        kilde_id, exc,
                    )
            try:
                from core.runtime import db_routines

                db_routines.bind_visible_run(
                    str(task_id or ""), visible_run_id=str(visible_run_id),
                    session_id=str(session_id or ""),
                )
            except Exception:  # noqa: BLE001 — binding maa aldrig vaelte en vaekning
                logger.debug(
                    "inbox_idle_waker: kunne ikke binde rutine-run", exc_info=True,
                )

        def _afregn_post(
            *, outcome: str, visible_run_id: str = "", error: str = "", **_: Any,
        ) -> None:
            """Kvittér posten når dens run er terminalt (12/11-2026).

            Bjørns krav: enten kvitterer jeg, eller systemet gør det
            automatisk. Uden dette stod en vækning hvis run var færdigt
            tilbage som `fired`/uforbrugt — og `kandidater()` springer poster
            med et vækkespor over, så den kunne hverken rejses igen eller
            lukkes af nogen anden. Den stod fast i visningen for evigt.

            Kun poster med en adresse afregnes. Fejler skrivningen, logges
            det: et run der sluttede er stadig sandt, og et manglende
            kvitteringsforsøg må ikke kunne vælte afslutningen.
            """
            if not str(kilde_id or "").strip():
                return
            try:
                from core.services.inbox_state import afslut_efter_run

                afslut_efter_run(
                    str(user_id or ""), str(kilde_id),
                    udfald=str(outcome or ""), run_id=str(visible_run_id or ""),
                    error=str(error or ""),
                )
            except Exception as exc:  # noqa: BLE001 — se docstringen
                logger.warning(
                    "inbox_idle_waker: kunne ikke afregne %s/%s efter run (%s): %s",
                    kildetype, kilde_id, outcome, exc,
                )

        try:
            return start_autonomous_run(
                tekst,
                session_id=session_id,
                # Bevar kildens herkomst; "inbox" er kun fallback for en post
                # skrevet før feltet fandtes.
                origin=str(origin or "").strip() or "inbox",
                force_user_id=str(user_id or ""),
                # Vækningen fortsætter den forpligtelse den blev booket som —
                # ellers starter et løsrevet run uden bånd til opgaven.
                task_id=str(task_id or ""),
                # Adgangsniveauet læses fra den samtale vækningen blev BOOKET
                # i, ikke fra den silo runnet lander i (målt 9/11-2026).
                permission_session=str(permission_session or ""),
                # BINDINGEN (11/11-2026). Er postens `task_id` et rutine-run,
                # skrives det visible run-id paa rutine-raekken med det samme.
                # Afregningen kan dermed laeses som TILSTAND af reconcileren i
                # stedet for at vaere en closure der ikke kan krydse en
                # procesgraense — og uden den requeuede reconcileren et claim
                # hvis run maaske netop lykkedes, saa rutinen koerte IGEN.
                started_callback=_bind_start,
                # AFREGNINGEN (12/11-2026): posten kvitteres når runnet er
                # terminalt — færdig, fejlet eller pauset. Se `_afregn_post`.
                completion_callback=_afregn_post,
                # BUDGETTET (11/11-2026). Kilden satte et loft da den bookede
                # vækningen; uden at føre det videre kører runnet uden grænse.
                # `0` betyder «intet loft» og sendes derfor kun videre når
                # kilden faktisk satte en grænse.
                **({"max_tool_calls": int(max_tool_calls)}
                   if int(max_tool_calls or 0) > 0 else {}),
                **({"max_seconds": float(max_seconds)}
                   if float(max_seconds or 0.0) > 0 else {}),
                **({"tool_scope": str(tool_scope)}
                   if str(tool_scope or "").strip() else {}),
            )
        finally:
            if token is not None:
                from core.identity.workspace_context import reset_context

                reset_context(token)


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

    # En gateway-vækning bærer sin EGEN instruktion i beskrivelsen — det er
    # kildens tekst, ikke et generisk «du har en post»-direktiv.
    if str(post.get("kildetype") or "") == "vaekning":
        tekst = str(post.get("beskrivelse") or "").strip()
        if tekst:
            return tekst
    if not post.get("kraever_handling") and kan_dispatch(post.get("kildetype")):
        if str(post.get("kildetype") or "") == "wakeup":
            rec = _wakeup_records().get(str(post.get("kilde_id") or ""))
            if rec:
                from core.services.self_wakeup import direktiv_for

                return direktiv_for(rec)
    return _direktiv(post)


def _publicer_vaekning_startet(post: dict[str, Any], kilde_id: str) -> None:
    """Udgiv `self_wakeup.dispatched` NÅR runnet er startet — ikke før.

    Eventet hed indtil 12/11-2026 `dispatched` allerede ved afleveringen til
    indbakken (nu `queued`, i `wakeup_dispatcher`). Målt: 18:15:39 vs. et run der
    startede 18:22:20. Her ved vi det faktisk: starteren har ikke afvist.
    Self-safe: observabilitet må ikke kunne vælte polleren.
    """
    # Afkodningen af `vaek-wakeup:<id>` bor i `wake_gateway`, som EJER
    # formatet. Den lå her som en lokal konstant indtil 12/11-2026, hvor den
    # samme afkodning skulle bruges i `inbox_state._luk_kilden` — to steder,
    # ét format, ingen ejer.
    from core.services.wake_gateway import wakeup_id_fra_vaekning

    wakeup_id = wakeup_id_fra_vaekning(kilde_id)
    if not wakeup_id:
        return
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("self_wakeup.dispatched", {
            "wakeup_id": wakeup_id,
            "kilde_id": kilde_id,
            "session_id": str(post.get("session_id") or ""),
            "origin": str(post.get("origin") or ""),
        })
    except Exception as exc:  # noqa: BLE001
        logger.debug("inbox_idle_waker: kunne ikke udgive dispatched for %s: %s",
                     kilde_id, exc)


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
        # Det første tjek ligger før vi kender postens adresse og kan derfor
        # have undersøgt en anden session.  Genkontrollér den faktiske adresse
        # før vækkesporet skrives; en aktiv samtale må hverken afbrydes eller
        # få posten brændt af som allerede vækket.
        if _session_er_aktiv(session_id):
            # ── TRE GRENE, IKKE ÉN (Bjørn 12/11-2026) ──────────────────────
            #
            # «inbox skal vurdere om der gået X min uden du eller jeg ikk har
            # skrevet hvis det er et ældre wakeup, men hvis det er et wakeup du
            # mangler sår bør inbox starte den med det samme eller hvis du er
            # aktiv lægge den markeret i inbox og forlange du læserne.»
            #
            # FØR: en aktiv samtale betød `continue` — og en fyrede vækning
            # hvis run ikke kunne startes stod tilbage som `kraever_handling=0`,
            # hverken kørt eller krævet. Målt 12/11-2026: wake-b1f4f73cf9
            # fyrede 17:55:43 og var stadig ubesvaret fordi samtalen var aktiv
            # 61 sekunder senere. Guarden havde ret i at vente; fejlen var at
            # der ikke fandtes en anden udgang.
            #
            # NU: en post der har ventet længere end KRAEV_ALDER_MIN gøres
            # gatende. Så tvinger den eksisterende inbox-gate mig til at læse
            # hende i næste tur — uden en ny mekanisme, med samme regel som
            # enhver anden forpligtelse jeg selv har oprettet.
            alder = _alder_minutter(post)
            if alder is not None and alder >= KRAEV_ALDER_MIN:
                try:
                    r = db_inbox.kraev_laesning(
                        bruger_id=bruger_id, kilde_id=kilde_id)
                    logger.info(
                        "inbox_idle_waker: %s/%s har ventet %.0f min paa en "
                        "aktiv samtale — kraever laesning (%s)",
                        post.get("kildetype"), kilde_id, alder,
                        r.get("status"),
                    )
                except Exception as exc:  # noqa: BLE001 — maa ikke vaelte polleren
                    logger.warning(
                        "inbox_idle_waker: kunne ikke kraeve %s laest: %s",
                        kilde_id, exc,
                    )
            else:
                logger.info(
                    "inbox_idle_waker: maal-session %s er aktiv — posten venter "
                    "(alder %s min)",
                    session_id[:28],
                    "?" if alder is None else f"{alder:.0f}",
                )
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
            startet = _start_run(
                tekst,
                session_id=session_id,
                user_id=bruger_id,
                task_id=str(post.get("task_id") or ""),
                permission_session=str(post.get("permission_session") or ""),
                # HERKOMSTEN (11/11-2026). Kilden skrev hvad slags run den
                # bad om (dream, heartbeat, scheduled …). Uden den blev alt
                # "inbox", og telemetrien kunne ikke skelne dem.
                origin=str(post.get("origin") or ""),
                # BUDGETTET (11/11-2026). Kilden satte loftet da den bookede
                # vækningen; posten bærer det, og her føres det videre.
                max_tool_calls=int(post.get("max_tool_calls") or 0),
                max_seconds=float(post.get("max_seconds") or 0.0),
                tool_scope=str(post.get("tool_scope") or ""),
                # POSTENS ADRESSE (12/11-2026). Runnet skal kunne kvittere
                # præcis den post det blev født af — ellers kan det ikke
                # afregne sig selv, og posten bliver stående.
                kilde_id=kilde_id,
                kildetype=str(post.get("kildetype") or ""),
            )
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
            _publicer_vaekning_startet(post, kilde_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("inbox_idle_waker: kunne ikke starte run for %s: %s",
                           kilde_id, exc)
            # Rul sporet tilbage, så posten proeves igen.
            try:
                db_inbox.nulstil_vaekning(bruger_id=bruger_id, kilde_id=kilde_id)
            except Exception:  # noqa: BLE001 — sporet er sat; en fejlet rollback maa ikke vaelte polleren
                pass

    return {"status": "ok", "vaekket": vaekket}
