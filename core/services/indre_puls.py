"""Hjertet må hverken stå stille eller løbe løbsk — og bøgerne skal passe.

24/9-2026 fandt jeg fire fejl på én dag. De var alle ægte, de varede alle i
dage eller måneder, og **ingen af dem sagde til**. Hver eneste blev fundet ved
at forespørge databasen i hånden:

===========================================  ==========  ==================
fejl                                         varighed    hvem sagde til
===========================================  ==========  ==================
12 kørsler døde, budgettet brændt            dage        ingen
0 release-notifikationer leveret             måneder     ingen
8534 autonome beskeder usynlige              måneder     ingen
hjerteslaget kørte 28x for hurtigt           måneder     ingen
===========================================  ==========  ==================

Drift betyder at man får det at vide UDEN at lede. Det er det der manglede.

## Hvorfor én vagt og ikke to

Jeg designede først en vagt mod *stoppede* ure, fordi det var det symptom jeg
lige havde set (humøret frosset på distress 1.0 i 4½ time). Samme dag leverede
systemet det modsatte: hjerteslaget tikkede 28 gange for hurtigt. **En vagt der
kun kender den ene retning ville have meldt «alt friskt» mens hjertet
galoperede** — et ur der tikker for tit er friskt efter enhver alders-måling.

Og afstemningen viste sig at være det samme problem set fra en anden vinkel. På
fire timer havde eventbussen 368 `heartbeat.phased_tick` mens bogen havde 3.
Et forhold på 122:1, i månedsvis, uden at noget sammenlignede de to tal. Det er
en puls målt to steder der ikke stemmer.

Derfor: én vagt, tre slags målinger, og afvigelse i BEGGE retninger er en fejl.

## Hvad den ikke gør

Den gætter ikke. En puls uden en erklæret kadence bliver ikke vogtet — det er
med vilje. En vagt der selv finder på hvad der er normalt, melder enten alt
eller intet.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_KVITTERINGS_NOEGLE = "indre_puls.meldte"


@dataclass(frozen=True, slots=True)
class Puls:
    """En tilstand der skal slå i en kendt takt.

    ``kilde`` bestemmer HVORDAN takten måles:

    * ``"kv"``    — alderen på en `runtime_state_kv`-nøgle. Kan kun se at noget
                    er stoppet; en KV-nøgle der skrives for tit ser ens ud.
    * ``"event"`` — antal `events`-rækker af en bestemt `kind` i et vindue.
                    Ser begge retninger.
    * ``"tabel"`` — antal rækker i en tabel i et vindue. Ser begge retninger.
    """

    navn: str
    kilde: str
    noegle: str
    kadence_s: float
    #: Stille når der er gået mere end kadence × dette uden et slag.
    for_langsom: float = 6.0
    #: Løbsk når der falder flere end forventet × dette slag i vinduet.
    for_hurtig: float = 4.0
    #: Kolonnen med tidsstempel (kun `tabel`).
    tidskolonne: str = "created_at"


@dataclass(frozen=True, slots=True)
class Afstemning:
    """To bøger over det samme arbejde. De skal stemme.

    Hjerteslaget havde 368 hændelser og 3 bogførte tik. Begge tal fandtes,
    begge var korrekte hver for sig, og ingen sammenlignede dem.
    """

    navn: str
    event_kind: str
    tabel: str
    tidskolonne: str = "started_at"
    #: Forventet forhold bogført/hændelser. 1.0 = én bogføring per hændelse.
    forventet: float = 1.0
    #: Meldes når forholdet afviger mere end denne faktor fra det forventede.
    tolerance: float = 4.0


#: Kadencerne er ERKLÆREDE, ikke gættede. Tallene kommer fra hvad koden selv
#: siger den gør — ikke fra hvad den tilfældigvis gjorde da jeg målte.
PULSE: tuple[Puls, ...] = (
    Puls("Hjerteslagets tik", "event", "heartbeat.phased_tick", 900.0),
    Puls("Humørets ur", "kv", "mood_oscillator.state", 900.0),
    Puls("Valens", "kv", "central_valence_state", 900.0),
    Puls("Somatisk krop", "kv", "somatic_runtime_body", 300.0),
    Puls("Selvtilstand", "kv", "central_self_state", 900.0),
    Puls("Driftsafvejning", "kv", "drive_arbitration_engine", 900.0),
    Puls("Endelighed", "kv", "finitude_runtime.state", 21600.0),
    Puls("Drømmemotiver", "kv", "dream_motif_daemon.state", 86400.0),
)

AFSTEMNINGER: tuple[Afstemning, ...] = (
    Afstemning("Hjerteslagets bogføring", "heartbeat.phased_tick",
               "heartbeat_runtime_ticks"),
)


def _nu() -> datetime:
    return datetime.now(UTC)


def _alder_af_kv(noegle: str) -> float | None:
    """Sekunder siden nøglen sidst blev skrevet. `None` = kan ikke aflæses."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                "SELECT updated_at FROM runtime_state_kv WHERE key = ?",
                (noegle,),
            ).fetchone()
        if not raekke or not raekke[0]:
            return None
        return max(0.0, (_nu() - datetime.fromisoformat(str(raekke[0]))).total_seconds())
    except Exception as exc:
        logger.debug("indre_puls: kunne ikke aflaese %s: %s", noegle, exc)
        return None


def _antal(tabel: str, tidskolonne: str, siden: datetime,
           hvor: tuple[str, object] | None = None) -> int | None:
    """Rækker i et vindue. `None` = kan ikke tælles (tabellen findes måske ikke)."""
    try:
        from core.runtime.db import connect
        sql = f"SELECT COUNT(*) FROM {tabel} WHERE {tidskolonne} > ?"  # noqa: S608
        args: list[object] = [siden.isoformat()]
        if hvor:
            sql += f" AND {hvor[0]} = ?"
            args.append(hvor[1])
        with connect() as conn:
            return int(conn.execute(sql, args).fetchone()[0])
    except Exception as exc:
        logger.debug("indre_puls: kunne ikke taelle %s: %s", tabel, exc)
        return None


def maal_puls(p: Puls, *, vindue_s: float | None = None) -> dict[str, object]:
    """Mål én puls. ``tilstand`` er "frisk", "stille", "loebsk" eller "ukendt"."""
    # Vinduet skal rumme flere forventede slag, ellers er ét manglende slag nok
    # til at raabe op. Fire kadencer er kort nok til at opdage hurtigt og langt
    # nok til at et enkelt udfald ikke taeller som en fejl.
    vindue = vindue_s if vindue_s is not None else max(p.kadence_s * 4, 300.0)
    ud: dict[str, object] = {"navn": p.navn, "noegle": p.noegle,
                             "kadence_s": p.kadence_s, "kilde": p.kilde}

    if p.kilde == "kv":
        alder = _alder_af_kv(p.noegle)
        ud["alder_s"] = alder
        if alder is None:
            # Kan vi ikke datere den, melder vi IKKE. Fravaer af tidsstempel er
            # ikke bevis for at uret staar — samme regel som i `in_flight_runs`.
            ud["tilstand"] = "ukendt"
        elif alder > p.kadence_s * p.for_langsom:
            ud["tilstand"] = "stille"
        else:
            ud["tilstand"] = "frisk"
        return ud

    siden = _nu() - timedelta(seconds=vindue)
    if p.kilde == "event":
        n = _antal("events", "created_at", siden, hvor=("kind", p.noegle))
    else:
        n = _antal(p.noegle, p.tidskolonne, siden)
    forventet = vindue / p.kadence_s
    ud.update({"antal": n, "forventet": round(forventet, 2), "vindue_s": vindue})
    if n is None:
        ud["tilstand"] = "ukendt"
    elif forventet >= 1.0 and n == 0:
        ud["tilstand"] = "stille"
    elif n > forventet * p.for_hurtig:
        # DEN RETNING DER BLEV OVERSET. Hjerteslaget stod her med 56 mod 2.
        ud["tilstand"] = "loebsk"
    else:
        ud["tilstand"] = "frisk"
    return ud


def maal_afstemning(a: Afstemning, *, vindue_s: float = 14400.0) -> dict[str, object]:
    """Sammenlign to bøger over det samme arbejde."""
    siden = _nu() - timedelta(seconds=vindue_s)
    haendelser = _antal("events", "created_at", siden, hvor=("kind", a.event_kind))
    bogfoert = _antal(a.tabel, a.tidskolonne, siden)
    ud: dict[str, object] = {"navn": a.navn, "haendelser": haendelser,
                             "bogfoert": bogfoert, "forventet": a.forventet,
                             "vindue_s": vindue_s}
    if haendelser is None or bogfoert is None:
        ud["tilstand"] = "ukendt"
        return ud
    if haendelser == 0 and bogfoert == 0:
        ud["tilstand"] = "frisk"          # intet arbejde er ikke en uenighed
        return ud
    if haendelser == 0:
        ud["tilstand"] = "uenig"
        ud["forhold"] = None
        return ud
    forhold = bogfoert / haendelser
    ud["forhold"] = round(forhold, 3)
    oevre = a.forventet * a.tolerance
    nedre = a.forventet / a.tolerance
    ud["tilstand"] = "frisk" if nedre <= forhold <= oevre else "uenig"
    return ud


def _kvitterede() -> set[str]:
    """Hvad har vi allerede meldt om?

    Fejler denne, ser vagten INGEN kvitteringer og melder alt forfra ved hvert
    tik. Det ville gøre den til larm, og larm bliver slukket. Derfor logges det
    — et modul om tavse fejl må ikke selv fejle tavst. (Gaten
    `verify_silent_except` fangede netop dette her i min egen kode.)
    """
    try:
        from core.runtime.db import get_runtime_state_value
        v = get_runtime_state_value(_KVITTERINGS_NOEGLE, default=None)
        return set(v) if isinstance(v, list) else set()
    except Exception:
        logger.warning(
            "indre_puls: kunne ikke laese kvitteringer — vagten vil melde "
            "kendte fejl igen", exc_info=True)
        return set()


def _gem_kvitterede(navne: set[str]) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_KVITTERINGS_NOEGLE, sorted(navne))
    except Exception:
        logger.warning("indre_puls: kunne ikke gemme kvitteringer", exc_info=True)


def tjek(*, meld: bool = True, foerste_koersel: bool = False) -> dict[str, object]:
    """Mål alt, og meld det der er nyt galt.

    ``foerste_koersel=True`` kvitterer alt der allerede er galt UDEN at melde.
    Uden det ville den første kørsel drukne feeden i kendte fejl, og den ægte
    melding ville forsvinde i støjen.

    En fejl meldes ÉN gang. Kommer pulsen tilbage og falder ud igen, meldes den
    på ny — det er et nyt udfald, ikke det samme.
    """
    maalinger = [maal_puls(p) for p in PULSE]
    maalinger += [maal_afstemning(a) for a in AFSTEMNINGER]
    daarlige = {str(m["navn"]) for m in maalinger
                if m.get("tilstand") in ("stille", "loebsk", "uenig")}
    kendte = _kvitterede()

    if foerste_koersel:
        _gem_kvitterede(daarlige)
        return {"maalinger": maalinger, "meldt": [], "kvitteret": sorted(daarlige)}

    nye = daarlige - kendte
    if meld:
        # ÉN melding per navn. Loekken gik foer over maalingerne, saa to pulse
        # der delte navn gav to beskeder om det samme.
        set_meldt: set[str] = set()
        for m in maalinger:
            navn = str(m["navn"])
            if navn in nye and navn not in set_meldt:
                set_meldt.add(navn)
                _meld(m)
    # Kun de AKTUELT daarlige huskes, saa en puls der kommer sig kan melde igen.
    _gem_kvitterede(daarlige)
    return {"maalinger": maalinger, "meldt": sorted(nye),
            "raske": sorted(kendte - daarlige)}


def _meld(m: dict[str, object]) -> None:
    """Send én melding gennem feeden.

    Kanalen var doed indtil 24/9-2026: `notifikations_emittere.system()` slog
    ejeren op i `users`-tabellen, som ikke har en ejer-raekke. NUL
    systemnotifikationer var nogensinde leveret. Derfor logges det ogsaa her —
    en vagt hvis meldinger forsvinder er vaerre end ingen vagt.
    """
    tilstand = str(m.get("tilstand"))
    navn = str(m.get("navn"))
    if tilstand == "stille":
        titel = f"{navn} står stille"
        tekst = (f"Forventet et slag hvert {float(m.get('kadence_s') or 0)/60:.0f}. minut. "
                 f"Sidste spor: {m.get('alder_s') or m.get('antal')}.")
    elif tilstand == "loebsk":
        titel = f"{navn} løber løbsk"
        tekst = (f"{m.get('antal')} slag i vinduet mod {m.get('forventet')} forventede. "
                 f"Et ur der tikker for tit ser friskt ud på enhver aldersmåling.")
    else:
        titel = f"{navn}: bøgerne stemmer ikke"
        tekst = (f"{m.get('haendelser')} hændelser mod {m.get('bogfoert')} bogførte "
                 f"(forhold {m.get('forhold')}). Arbejdet sker, men det bliver ikke skrevet.")
    logger.warning("indre_puls: %s — %s", titel, tekst)
    try:
        from core.services import notifikations_emittere
        notifikations_emittere.system("drift", titel, tekst)
    except Exception:
        logger.warning("indre_puls: kunne ikke sende meldingen", exc_info=True)


def build_indre_puls_surface() -> dict[str, object]:
    """Centralens flade. Læser kun — den melder ikke."""
    maalinger = [maal_puls(p) for p in PULSE]
    maalinger += [maal_afstemning(a) for a in AFSTEMNINGER]
    daarlige = [m for m in maalinger
                if m.get("tilstand") in ("stille", "loebsk", "uenig")]
    return {
        "active": True,
        "maalinger": maalinger,
        "antal": len(maalinger),
        "daarlige": len(daarlige),
        "summary": (f"{len(maalinger)} pulse, alle friske" if not daarlige
                    else f"{len(daarlige)} af {len(maalinger)} pulse er gale: "
                         + ", ".join(str(m["navn"]) for m in daarlige[:3])),
    }
