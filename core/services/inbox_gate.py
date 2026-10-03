"""Indbakkens to-trins forudsætning i mutationspunktet.

Opgave 4 og 12 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

## To trin, fordi det var Bjørns form

> «først bede ham checke indbox, og hvis ignoreret eskalerer som den gør nu»

Første udkast af spec'en kollapsede det til øjeblikkelig blokering. Det var en
vurdering sat i stedet for hans form, og uden at sige det. To trin er bedre: den
høflige anmodning koster ingenting, og blokeringen fanger dem der ignorerer den.

```
TRIN 1  åben, verificeret Jarvis-post?  → ÉN kilde-mærket systemlinje.
        Mutationen slipper igennem. Påmindelsen noteres durabelt pr. post.
TRIN 2  nok leverede, ubesvarede påmindelser? → nægt DENNE mutation,
        med post-id'et nævnt. Frigives KUN af done/drop på dens poster.
```

## Hvorfor en EGEN forudsætning, ikke en gren i R2.5

`r2_5_haandhaevelse` holder ÉN procesglobal `_blok`, som frigives ved første
readback eller efter 10 minutter. Begge dele er forkert livscyklus for en åben
inbox-post:

* en inbox-post er **per bruger og per post**, ikke per proces — en procesglobal
  blok er usikker på tværs af brugere og workers;
* et readback frigiver ingenting her. Posten er stadig åben. Kunne et blik
  frigive den, var læsningen en formalitet, og vi var tilbage i banner
  blindness — bare med en blokering i stedet for en advarsel, hvilket er værre.

Det der DELES er mutations-klassifikationen og bagdørs-undtagelsen. Begge læses
fra `r2_5_haandhaevelse`, så der kun er ét sted der afgør hvad en mutation er.
To definitioner driver fra hinanden, og det er præcis hvordan et filter bliver
stille virkningsløst.

## Opgave 12: tælleren læser ÉN liste

Skill-gaten fejlede 3/10 fordi den læste `_a_tool_calls`, der bærer
transport-navnet `call_loaded_tool`, mens udpakningen til det ægte navn sker i
`core/tools/kaldt_vaerktoej.pak_ud`.

**Beslutningen (Opgave 12 trin 1): indbakke-gaten deler IKKE kilde med
skill-gaten.** De tæller forskellige ting: skill-gaten tæller *kald i turen*,
indbakke-gaten tæller *leverede påmindelser pr. post*. Den sidste er durabel i
`inbox_items.paamindelser` og skal overleve en procesgenstart — en turs
kald-liste kan ikke bære den.

Men gaten rammer samme fælde fra den anden side: den får et **værktøjsnavn**
ind, og et indpakket kald bærer transport-navnet. Derfor pakkes navnet ud
gennem den ENE definition (`kaldt_vaerktoej.pak_ud`) frem for at reimplementere
reglen her.

## Fald-retningen

DB-fejl ⇒ **slip igennem**, og log med bruger- og post-id. En mutation må ikke
blokeres på et gæt; en gate der blokerer når den ikke kan læse sin egen tilstand
er værre end ingen gate, fordi den ikke kan slås fri.
"""
from __future__ import annotations

import logging
from typing import Any, Final

from core.runtime import db_inbox

logger = logging.getLogger(__name__)

NERVE: Final[str] = "inbox_gate"


def _gate_tændt() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "inbox_gate_enabled", True))
    except Exception as exc:  # noqa: BLE001
        # Kan vi ikke læse kontakten, er gaten TÆNDT som standard — men det
        # skal ses. En gate der tavst slukkede sig selv er den fejlform
        # `vagten_var_groen_fordi_forudsaetningen_var_i_stykker` beskriver.
        logger.warning("inbox_gate: kunne ikke laese kontakten: %s", exc)
        return True


def _foer_blok() -> int:
    try:
        from core.runtime.settings import load_settings
        return max(1, int(getattr(load_settings(), "inbox_paamindelser_foer_blok", 2)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_gate: kunne ikke laese taersklen: %s", exc)
        return 2


def _aegte_kald(
    vaerktoejsnavn: str, argumenter: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    """Det ÆGTE navn OG de ægte argumenter, også ad en indpakket vej.

    **Begge dele, ikke kun navnet.** Det var den fælde jeg selv gik i først:
    jeg hentede det indre navn og sendte det videre med de YDRE argumenter. For
    et indpakket shell-kald ligger `command` i de INDRE argumenter, så
    `shell_command_is_mutating("")` ville svare False — og en muterende
    kommando ville slippe uhindret gennem gaten. Navn og argumenter hører
    sammen; de kan ikke skilles her.

    Én definition, importeret — ikke reimplementeret. Skill-gaten læste
    transport-navnet `call_loaded_tool` i timevis og fyrede på en forkert
    præmis; to kopier af udpakningen ville give samme fejl igen.
    """
    navn = str(vaerktoejsnavn or "")
    args = argumenter or {}
    try:
        from core.tools.kaldt_vaerktoej import pak_ud
        ud = pak_ud(navn, args)
    except Exception as exc:  # noqa: BLE001
        # Kan kaldet ikke pakkes ud, bliver transport-navnet staaende. Det er
        # status quo og fejler i den rigtige retning: en ukendt indpakning
        # bliver IKKE udnaevnt til en mutation den ikke er.
        logger.debug("inbox_gate: pak_ud(%r) fejlede: %s", navn[:40], exc)
        return navn, args
    if (isinstance(ud, tuple) and len(ud) == 2
            and isinstance(ud[0], str) and ud[0]):
        return ud[0], ud[1] if isinstance(ud[1], dict) else args
    # Svarede `pak_ud` noget andet end sin kontrakt, er det ikke et bevis paa
    # noget. Behold det vi kom med.
    logger.warning("inbox_gate: pak_ud svarede uventet: %r", type(ud).__name__)
    return navn, args


def _gatende_poster(bruger_id: str) -> list[dict[str, Any]] | None:
    """Åbne poster der MÅ gate. `None` = kunne ikke læses (fail-open).

    `None` og `[]` må ikke mappes sammen: en tom liste betyder «intet venter»,
    mens `None` betyder «jeg ved det ikke». Blev de ét, ville en DB-fejl se ud
    som en ren indbakke — og gaten var tavst slukket.
    """
    try:
        poster = db_inbox.liste(bruger_id=bruger_id, kun_aabne=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_gate: kunne ikke laese poster for %r — "
                       "mutationen SLIPPER igennem: %s", bruger_id, exc)
        return None
    return [p for p in poster
            if p.get("kraever_handling")
            and str(p.get("verificeret_ejer") or "") == db_inbox.EJER_JARVIS]


#: Husets ENE mærkning, importeret. Jeg skrev først min egen her, og det var
#: den samme fejl jeg lige havde advaret om i Opgave 12: to definitioner af
#: samme regel driver fra hinanden, og så bliver det ene filter stille
#: virkningsløst.
#:
#: `visible_run_guard_notices.SYSTEM_MAERKE` har de tre egenskaber der gør
#: formen virksom: den siger hvad den ER, hvad den IKKE er, og den **forbyder
#: eksplicit at læse den som samtykke**. Den sidste er vigtigst — uden den kan
#: en systembesked blive et «ja».
#:
#: Og den er allerede den tekst `fjern_menneske_noter` genkender, så en
#: mærkning herfra kan filtreres af de samme to lag.
def _system_maerke() -> str:
    try:
        from core.services.visible_run_guard_notices import SYSTEM_MAERKE
        return SYSTEM_MAERKE
    except Exception as exc:  # noqa: BLE001
        # Kan husets maerkning ikke hentes, maerker vi ALLIGEVEL — umaerket
        # tekst i jeg-form startede runder i Bjoerns navn, og det er den
        # vaerste af de to udfald. Men fejlen skal ses.
        logger.warning("inbox_gate: kunne ikke hente husets systemmaerke: %s", exc)
        return ("[SYSTEM — IKKE FRA BJØRN] Automatisk haendelse, IKKE en besked "
                "fra brugeren. Maa IKKE laeses som samtykke.")


def _spor(kind: str, payload: dict[str, Any]) -> None:
    """Publicér til eventbussen. Kaster aldrig.

    Sporet er ikke pynt: Opgave 7 skal kunne PARRE hændelser per post-id og
    bruger-id, og skelne `done`, `drop`, udløb, fail-open og DB-fejl. «released
    uden årsag» er ikke efterlevelse — og uden et spor pr. trin kan de to
    heed-rater ikke måles hver for sig. R2's punkt 2 ventede fra 13. juni på en
    måling der aldrig blev lavet, fordi tallene ikke blev skrevet nogen steder.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception as exc:  # noqa: BLE001
        # Telemetrien maa aldrig vaelte gaten. Men en bus der er nede goer hele
        # Opgave 7 blind, saa den skal kunne SES.
        logger.warning("inbox_gate: kunne ikke spore %s: %s", kind, exc)


def _varsel(poster: list[dict[str, Any]]) -> str:
    n = len(poster)
    ider = ", ".join(str(p["id"]) for p in poster[:3])
    mere = f" (+{n - 3} mere)" if n > 3 else ""
    return (f"{_system_maerke()}\n"
            f"{n} post(er) venter i indbakken: {ider}{mere} → kald `inbox`")


def _naegtelse(poster: list[dict[str, Any]], navn: str) -> str:
    linjer = [f"  {p['id']}  «{str(p.get('beskrivelse') or '')[:60]}»" for p in poster[:5]]
    return (f"{_system_maerke()}\n"
            f"`{navn}` er naegtet: {len(poster)} post(er) i indbakken har faaet "
            f"paamindelser uden at blive afgjort.\n" + "\n".join(linjer) +
            "\nLuk hver med `inbox_done(id)` eller `inbox_drop(id, reason)`. "
            "Et blik paa `inbox` frigiver ikke — afgoerelsen goer.")


def evaluer_inbox_mutation(
    bruger_id: str,
    vaerktoejsnavn: str,
    argumenter: dict[str, Any] | None = None,
    *,
    tur: str = "",
) -> dict[str, Any]:
    """Skal `vaerktoejsnavn` nægtes, eller skal der bare påmindes?

    Returnerer altid typet:
    `{"blokeret": bool, "poster": [id…], "varsel": str, "grund": str}`.

    `tur` er turens id (run_id) og bruges som påmindelsens idempotens-nøgle:
    højst ÉN påmindelse pr. post pr. tur. Uden den kunne en enkelt tur med
    mange mutationer tælle sig op til tærsklen alene og springe hele den
    høflige anmodning over — præcis den støj R2 blev kritiseret for.
    """
    tomt = {"blokeret": False, "poster": [], "varsel": "", "grund": ""}
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        # Ingen autentificeret bruger ⇒ ingen poster der kan gate. Blokerede vi
        # her, ville en ubundet kontekst (scripts, daemoner) kunne låse sig
        # selv ude af en flade de ikke engang har poster i.
        return {**tomt, "grund": "ingen bruger"}
    if not _gate_tændt():
        return {**tomt, "grund": "kontakt slukket"}

    from core.services.r2_5_haandhaevelse import er_bagdoer, er_mutation
    navn, args = _aegte_kald(vaerktoejsnavn, argumenter)
    # Bagdørene FØRST. `bash_session*` og `operator_bash_session*` er Bjørns
    # aftalte vej udenom systemet, og en inbox-post må ikke utilsigtet fjerne
    # den. `er_mutation` afviser dem også, men rækkefølgen gør hensigten
    # læsbar frem for at hvile på en anden funktions interne detalje.
    if er_bagdoer(navn):
        return {**tomt, "grund": "bagdoer"}
    if not er_mutation(navn, args):
        # Læse-værktøjer slipper ALTID igennem: han skal kunne komme fri, og
        # `inbox`/`inbox_done`/`inbox_drop` er selv læse/bogførings-kald.
        return {**tomt, "grund": "ikke en mutation"}

    poster = _gatende_poster(bruger_id)
    if poster is None:
        _spor("inbox_gate.fail_open", {"bruger_id": bruger_id, "tool_name": navn,
                                       "tur": tur, "aarsag": "db-fejl"})
        return {**tomt, "grund": "fail-open: kunne ikke laese indbakken"}
    if not poster:
        return {**tomt, "grund": "intet venter"}

    graense = _foer_blok()
    modne = [p for p in poster if int(p.get("paamindelser") or 0) >= graense]
    if modne:
        _spor("inbox_gate.blocked", {
            "bruger_id": bruger_id, "tool_name": navn, "tur": tur,
            "poster": [str(p["id"]) for p in modne],
            "graense": graense})
        return {"blokeret": True,
                "poster": [str(p["id"]) for p in modne],
                "varsel": _naegtelse(modne, navn),
                "grund": f"{len(modne)} post(er) med >= {graense} paamindelser"}

    # TRIN 1: påmind, men slip igennem. Tællingen sker KUN når påmindelsen
    # faktisk blev leveret — derfor noteres den her, i samme greb som varslet
    # dannes, og ikke når gaten blev spurgt.
    leveret: list[dict[str, Any]] = []
    for p in poster:
        r = db_inbox.noter_paamindelse(bruger_id=bruger_id, kilde_id=str(p["id"]),
                                       tur=tur or "ukendt-tur")
        if r.get("status") == "ok":
            leveret.append(p)
    if not leveret:
        # Alle poster havde allerede faaet deres paamindelse i DENNE tur.
        # Mutationen slipper igennem uden et nyt varsel — ellers ville samme
        # linje gentages i hver runde.
        return {**tomt, "poster": [str(p["id"]) for p in poster],
                "grund": "paamindet i denne tur"}
    _spor("inbox_gate.reminded", {
        "bruger_id": bruger_id, "poster": [str(p["id"]) for p in leveret],
        "tool_name": navn, "tur": tur,
        "paamindelser": {str(p["id"]): int(p.get("paamindelser") or 0) + 1
                         for p in leveret}})
    return {**tomt, "poster": [str(p["id"]) for p in leveret],
            "varsel": _varsel(leveret),
            "grund": f"trin 1: paamindede {len(leveret)} post(er)"}


__all__ = ["NERVE", "evaluer_inbox_mutation"]
