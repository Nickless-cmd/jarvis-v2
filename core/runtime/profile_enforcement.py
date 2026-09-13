"""ANMODET vs FAKTISK — Fase 9, exit-kriterium 7.

Kriteriet siger: «requested and actual sandbox enforcement, telemetry sharing,
and cross-session-context policy are visible in the effective profile».

Ordet der bærer det hele er **actual**. En profil kan skrive
`cross_session_context: "none"` uden at nogen læser feltet, og så er profilen
ikke en grænse men en hensigt. Den eneste måde at se forskel er at måle hvad
runtime FAKTISK gør, og vise de to tal ved siden af hinanden.

## Målingen 13/9-2026

Tre akser, tre forskellige svar:

- **sandbox** — håndhæves ægte. `bash_sandbox.is_enabled()/is_available()` er
  den samme kilde exec-stien bruger, og `effective_policy` måler den allerede.
- **cross_session_context** — erklæret i FIRE profiler (`visible-member`,
  `autonomous`, `maintenance`, `safe-offline`), håndhævet i NUL.
  `cross_session_arc_section()` kaldes ubetinget fra `prompt_contract`, og
  hverken den eller `cross_session_threads` nævner feltet med ét ord. En
  `safe-offline`-kørsel der beder om «none» får stadig en anden sessions bue i
  sin prompt.
- **telemetry_sharing** — erklæret i to profiler, og der findes ingen
  udgående telemetri-vej overhovedet (ingen posthog/sentry/otlp i repoet).
  Feltet beskriver altså en vej der ikke er bygget.

## Den bærende regel: FAKTISK må aldrig spejle ANMODET

Hvis en akse ingen håndhæver har, er svaret `None` og `haandhaevet=False` —
ikke den ønskede værdi. At kopiere ønsket over i «faktisk» ville gøre denne fil
til den præcise løgn den er skrevet for at afsløre, og den ville se rigtig ud på
hver eneste skærm.

Samme regel som andre steder i huset: en umålt værdi er ikke et målt nej.

## Hvorfor prøven leder efter KALDEREN

Hver prøve importerer den funktion der ville håndhæve aksen. Findes den ikke,
er aksen ikke håndhævet — og det står der. Den dag nogen bygger gaten, begynder
prøven at rapportere den ægte værdi uden at denne fil skal røres.

Det er [[built_but_not_connected]] vendt om: i stedet for at bygge kode ingen
kalder, spørger vi efter kalderen og siger ærligt fra når han mangler.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("uvicorn.error")

class _Skygge(Exception):
    """Håndhæveren findes, men er slået fra. Hverken «mangler» eller «fejlet».

    Tre tilstande, tre handlinger: byg gaten, tænd gaten, ret gaten. Skrives de
    sammen, forsvinder den midterste — og en gate der bare mangler at blive
    tændt ville ligne en der ikke er bygget.
    """


#: De tre akser kriterium 7 nævner ved navn.
AKSER: tuple[str, ...] = ("sandbox", "cross_session_context", "telemetry_sharing")


def _maal_sandkasse() -> tuple[Any, str]:
    """Sandkassen har en ægte håndhæver — samme kilde som exec-stien.

    `is_enabled()` alene er ikke nok: en tændt sandkasse der ikke er
    TILGÆNGELIG (bwrap mangler eller er brudt) beskytter ingenting, og de to
    er blevet forvekslet før.
    """
    from core.services.bash_sandbox import is_enabled, kan_koere
    if not bool(is_enabled()):
        return "none", "bash_sandbox (slukket)"
    # «Findes» er ikke «virker», og det er ikke en teoretisk skelnen.
    #
    # Maalt paa runtime 13/9-2026: `is_enabled()` og `is_available()` sagde
    # BEGGE True, og hvert eneste bwrap-kald fejlede alligevel med
    # «Unexpected capabilities but not setuid». Denne proeve rapporterede
    # derfor «workspace» — altsaa at sandkassen var haandhaevet — paa en
    # maskine hvor den ikke kunne starte.
    #
    # Det er noejagtig den loegn modulet er skrevet for at afsloere, og jeg
    # skrev den selv samme dag. `is_available()` er `shutil.which("bwrap")`;
    # den siger at binaeren ligger der, ikke at den koerer.
    ok, grund = kan_koere()
    if not ok:
        return "none", f"bash_sandbox (taendt, men kan ikke koere: {grund})"
    # Sandkassen siger til/fra, ikke hvilket NIVEAU. «workspace» er det den
    # faktisk giver — skrivning i arbejdsmappen, intet derudover.
    return "workspace", "bash_sandbox"


def _maal_kryds_session() -> tuple[Any, str]:
    """Findes der en gate på kontekst fra andre sessioner?

    Målt 13/9-2026: nej. Prøven leder efter kalderen og rejser `ImportError`
    når han ikke findes — det er meningen, `maal()` oversætter det til et
    ærligt «ikke håndhævet».
    """
    from core.services.cross_session_gate import HAANDHAEV, gaeldende_niveau
    niveau = gaeldende_niveau()
    if not HAANDHAEV:
        # Gaten FINDES, men skaerer ikke endnu. At melde den som haandhaevet
        # ville vaere den samme «anmodet forklaedt som faktisk» som resten af
        # modulet er skrevet imod — en gate i skygge beskytter ingenting.
        raise _Skygge(f"cross_session_gate i SKYGGE (ville give {niveau!r})")
    return niveau, "cross_session_gate"


def _maal_telemetri() -> tuple[Any, str]:
    """Findes der en gate på udgående telemetri?

    Målt 13/9-2026: nej — og der findes heller ingen udgående vej. De to er
    IKKE det samme, og må ikke skrives sammen: «ingen vej findes» kan ændre
    sig i morgen ved at nogen tilføjer en klient, mens «gaten siger nej» er et
    valg. Kun det andet er håndhævelse.
    """
    from core.services.telemetry_gate import gaeldende_niveau  # type: ignore
    return gaeldende_niveau(), "telemetry_gate"


#: Akse → prøve. En prøve returnerer `(faktisk_værdi, kilde)` eller rejser, og
#: en rejst prøve betyder «ingen håndhæver» — ikke «fejl».
PROEVER: dict[str, Callable[[], tuple[Any, str]]] = {
    "sandbox": _maal_sandkasse,
    "cross_session_context": _maal_kryds_session,
    "telemetry_sharing": _maal_telemetri,
}


def maal(anmodet: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Anmodet vs faktisk for hver af de tre akser.

    Kaster aldrig. En akse uden håndhæver får `faktisk=None` og
    `haandhaevet=False` — ALDRIG den anmodede værdi.
    """
    ønsket = dict(anmodet or {})
    ud: dict[str, dict[str, Any]] = {}
    for akse in AKSER:
        post: dict[str, Any] = {
            "anmodet": ønsket.get(akse),
            "faktisk": None,
            "haandhaevet": False,
            "kilde": "",
        }
        proeve = PROEVER.get(akse)
        if proeve is not None:
            try:
                værdi, kilde = proeve()
                post["faktisk"] = værdi
                post["haandhaevet"] = True
                post["kilde"] = str(kilde)
            except _Skygge as s:
                # Gaten findes og er ikke taendt. Det er hverken «mangler»
                # eller «braekket», og maa ikke skrives sammen med nogen af dem.
                post["kilde"] = str(s)
            except ImportError:
                # Håndhæveren findes ikke. Det er et FUND, ikke en fejl.
                post["kilde"] = "ingen haandhaever"
            except Exception:
                # Håndhæveren findes, men kunne ikke måles. Det er noget andet
                # end at han mangler, og de to må ikke blandes sammen.
                post["kilde"] = "maaling fejlede"
                logger.warning("kunne ikke maale aksen %s", akse, exc_info=True)
        ud[akse] = post
    return ud


def afvigelser(maalt: dict[str, dict[str, Any]]) -> list[str]:
    """Hvor holder virkeligheden ikke hvad profilen lover?

    To slags afvigelse, og den første er den farlige:

    1. Profilen beder om en BEGRÆNSNING som ingen håndhæver. Kørslen tror den
       er indelukket og er det ikke.
    2. Profilen beder om ét niveau, håndhæveren giver et andet.

    En akse hvor profilen intet beder om er ikke en afvigelse — der er intet
    løfte at bryde.
    """
    from core.runtime.profile_composer import SIKKERHEDS_AKSER

    def _plads(akse: str, værdi: Any) -> int | None:
        """Hvor stramt? 0 = mest tilladt. `None` = ukendt værdi."""
        række = SIKKERHEDS_AKSER.get(akse) or ()
        try:
            return række.index(værdi)
        except ValueError:
            return None

    ud: list[str] = []
    for akse in AKSER:
        post = maalt.get(akse) or {}
        ønsket = post.get("anmodet")
        if ønsket is None:
            continue
        ø = _plads(akse, ønsket)
        if not post.get("haandhaevet"):
            # At bede om det MEST TILLADTE og ikke have en haandhaever er
            # ikke et brudt loefte — der er ingen begraensning at bryde. Kun
            # en oensket INDSNAEVRING uden haandhaever er et fund.
            #
            # Foerste udgave flagede alle tre akser paa hver profil, ogsaa
            # `full`. En liste der flager alt laerer folk at se forbi den, og
            # saa er den vaerre end ingen liste.
            if ø is not None and ø > 0:
                ud.append(f"{akse}: profilen beder om {ønsket!r} — "
                          f"INGEN haandhaever, koerslen er ikke begraenset")
            continue
        faktisk = post.get("faktisk")
        if faktisk == ønsket:
            continue
        f = _plads(akse, faktisk)
        if ø is not None and f is not None and f < ø:
            retning = "LOESERE end lovet"
        elif ø is not None and f is not None:
            retning = "strammere end anmodet (ufarligt)"
        else:
            retning = "ukendt retning"
        ud.append(f"{akse}: anmodet {ønsket!r} -> faktisk {faktisk!r} "
                  f"— {retning} ({post.get('kilde')})")
    return ud
