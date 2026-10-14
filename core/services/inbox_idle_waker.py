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
    return False


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


def _start_run(tekst: str, *, session_id: str | None = None) -> None:
    """Start det autonome run. Adskilt, så testen kan bytte den ud ét sted."""
    from core.services.visible_autonomous_run import start_autonomous_run

    start_autonomous_run(tekst, session_id=session_id, origin="inbox")


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


def _dispatch_tekst(post: dict[str, Any]) -> tuple[str, str | None]:
    """(tekst, session) for det run vækningen skal starte.

    En SPRUNGT vækning bærer sin egen tekst og sin egen samtale: den skal køre
    med `direktiv_for` — den samme instruktion dispatcheren ville have givet —
    i den samtale den blev booket fra, ikke i en auto-session. Er kilden væk
    eller ikke læsbar, falder vi tilbage til det generiske direktiv; et run
    med den rigtige post er bedre end intet run.

    Gatende poster (den oprindelige klasse) er urørt: de bruger `_direktiv`.
    """
    from core.services.inbox_state import kan_dispatch

    if not post.get("kraever_handling") and kan_dispatch(post.get("kildetype")):
        if str(post.get("kildetype") or "") == "wakeup":
            rec = _wakeup_records().get(str(post.get("kilde_id") or ""))
            if rec:
                from core.services.self_wakeup import direktiv_for

                return direktiv_for(rec), (str(rec.get("session_id") or "").strip() or None)
    return _direktiv(post), None


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
    for post in poster[:MAKS_PR_RUNDE]:
        kilde_id = str(post.get("kilde_id") or post.get("id") or "")
        # Sporet skrives FØR run'et startes: kaster starten, må posten ikke stå
        # som vækket — så prøves den igen i næste runde.
        try:
            db_inbox.noter_vaekning(
                bruger_id=bruger_id, kilde_id=kilde_id, tur=_VAEKKET_AF)
        except Exception as exc:  # noqa: BLE001
            logger.debug("inbox_idle_waker: kunne ikke notere %s: %s", kilde_id, exc)
            continue
        tekst, session_id = _dispatch_tekst(post)
        try:
            _start_run(tekst, session_id=session_id)
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
