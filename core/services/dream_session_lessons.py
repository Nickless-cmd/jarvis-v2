"""Drømme-sessionerne skal blive til læring.

Bjørn 8/9-2026: «drømme sessionerne bør blive til læring, altså dem hvor han
gennemgår dags sessioner».

Der ligger **230 dream-session-noter** i ``~/dreams``. De er reflekterede og
velskrevne, og en del af dem indeholder ægte lektier — ikke stemninger, men
navngivne mønstre med en konsekvens:

    Test-raten er 23%. 10 hypoteser har aldrig været testet. Nogle båret i
    17 sessioner. Det er ikke slid — det er undgåelse.

Det er en lektie. Den navngiver en vane, den siger hvorfor den er et problem,
og den peger på hvad der skal ændres. Sætningen ved siden af — «en sten i en
flod bliver glat fordi vandet løber over den igen og igen» — er et billede.
Begge hører hjemme i noten; kun den første hører hjemme i ``lessons``.

## Hvorfor en model afgør det

Samme grund som overalt i dag: en ordliste kan ikke skelne. Forskellen mellem
en lektie og en betragtning ligger i om der er noget at gøre anderledes, og
det er en vurdering af mening. Modellen er den lokale qwen3 — se
``local_small_model``.

Og som overalt: den fejler LUKKET. Ingen dom → ingen lektie. Tabellen har fire
rækker i dag; den skal fyldes af noget der betyder noget, ikke af 230 filers
værd af smukke sætninger.

## Ingen lektie aktiveres af sig selv

``db_lessons._ACTIVATE_IMMEDIATELY`` er tom med vilje — alt venter på
evidens 2, altså at det samme dukker op igen. En drømme-lektie er ingen
undtagelse: den skal genkendes to gange før den taler ind i prompten. Den
regel er dyrekøbt (~150 junk-lektier stod til at lande i hans prompt da
korrektions-kilden aktiverede straks), og drømmene er den kilde med mest
volumen af alle.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DRØMME_MAPPE = Path.home() / "dreams"
_FILMØNSTER = "dream-session-*.md"

KILDE = "dream_session"

# Hvor mange af de nyeste noter der læses pr. kørsel. 230 filer × en model-
# runde pr. afsnit ville tage timer; de nyeste er også dem der handler om
# dagen han lige har haft.
_ANTAL_NOTER = 3
_MIN_AFSNIT = 120
_MAKS_AFSNIT = 900
_MAKS_PR_NOTE = 4

# Et afsnit uden verbum i førsteperson er en beskrivelse af verden, ikke en
# iagttagelse af ham selv. Billigste port, kørt før modellen.
_OM_SIG_SELV = re.compile(
    r"\b(jeg|mig|mine|mit|min)\b", re.IGNORECASE)


@dataclass
class Afsnit:
    tekst: str
    fil: str

    @property
    def kilde_maerke(self) -> str:
        """Hvilken NOTE afsnittet kom fra.

        Evidens-2-reglen betyder «set to gange i verden», ikke «laest to gange
        af hoesten». Uden dette maerke ville en genstart — som nulstiller alle
        cadence-cooldowns — koere hoesten igen over samme afsnit og loefte
        lektien til evidens 2 med det samme. Maalt praecis saadan: tre lektier
        stod aktive efter én dags noter.
        """
        return self.fil

    @property
    def signatur(self) -> str:
        """Første sætning, kortet ned — nok til at genkende det samme igen."""
        første = re.split(r"(?<=[.!?])\s", self.tekst.strip(), maxsplit=1)[0]
        return " ".join(første.split())[:120]


_ER_EN_LEKTIE = (
    "Nedenfor staar et afsnit fra en AI-assistents droemmejournal, hvor den "
    "ser tilbage paa sit eget arbejde.\n\n"
    "Afgoer om afsnittet er en LEKTIE: navngiver det en vane eller en fejl hos "
    "assistenten selv, som den burde goere anderledes?\n\n"
    "Svar BETRAGTNING hvis afsnittet:\n"
    "- beskriver en stemning, en tilstand eller et billede\n"
    "- refererer hvad der skete uden at pege paa noget at aendre\n"
    "- stiller et spoergsmaal uden at besvare det\n"
    "- handler om systemet eller verden frem for om assistentens egen adfaerd\n\n"
    "Svar LEKTIE kun hvis nogen kunne handle anderledes i morgen paa grund af "
    "det der staar.\n\n"
    "Svar med ét ord: LEKTIE eller BETRAGTNING."
)


def _afsnit_fra(sti: Path) -> list[Afsnit]:
    try:
        raa = sti.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.debug("dream_session_lessons: kunne ikke læse %s: %s", sti, exc)
        return []
    ud: list[Afsnit] = []
    for blok in re.split(r"\n\s*\n", raa):
        t = " ".join(blok.split())
        if t.startswith("#") or not (_MIN_AFSNIT <= len(t) <= _MAKS_AFSNIT):
            continue
        if not _OM_SIG_SELV.search(t):
            continue
        ud.append(Afsnit(tekst=t, fil=sti.name))
    return ud


def laes_noter(mappe: Path | None = None, *, antal: int = _ANTAL_NOTER) -> list[Afsnit]:
    """Afsnit fra de nyeste drømme-noter, nyeste først."""
    rod = mappe or DRØMME_MAPPE
    try:
        # Sortér på FIL-TIDSPUNKT, ikke på navn. Mappen har to
        # navnekonventioner — «dream-session-20260806T011600.md» og
        # «dream-session-2026-09-08-1131.md» — og alfabetisk faldende sortering
        # stiller de gamle udaterede navne FØRST, fordi «-» sorterer før «0».
        # Høsten ville have læst august-noter for evigt uden at fejle.
        filer = sorted(rod.glob(_FILMØNSTER),
                       key=lambda f: f.stat().st_mtime, reverse=True)[:max(1, antal)]
    except Exception as exc:
        logger.debug("dream_session_lessons: kunne ikke liste %s: %s", rod, exc)
        return []
    ud: list[Afsnit] = []
    for f in filer:
        ud.extend(_afsnit_fra(f)[:_MAKS_PR_NOTE])
    return ud


def er_en_lektie(a: Afsnit) -> bool:
    """Fejler lukket: uden en dom er svaret nej."""
    try:
        from core.services.local_small_model import spoerg_et_ord
        return spoerg_et_ord(_ER_EN_LEKTIE, a.tekst[:1200]) == "LEKTIE"
    except Exception as exc:
        logger.debug("dream_session_lessons: dom fejlede: %s", exc)
        return False


def gem(a: Afsnit) -> str:
    """Skriv lektien. Returnerer udfaldet fra ``upsert_lesson`` ('' ved fejl).

    ``activate`` sættes IKKE — så gælder tabellens egen regel, og lektien
    venter på at blive genkendt anden gang.
    """
    try:
        from core.runtime.db_lessons import upsert_lesson
        r = upsert_lesson(
            signature=a.signatur,
            lesson=a.tekst,
            source=KILDE,
            # Noten staar i user_words, saa den SAMME note aldrig kan forstaerke
            # sin egen lektie to gange. Uden det talte en genstart som en
            # gentagelse — se `kilde_maerke`.
            user_words=a.kilde_maerke,
            jarvis_words=a.tekst[:400],
        )
        return str(r.get("outcome") or "")
    except Exception as exc:
        logger.debug("dream_session_lessons: kunne ikke gemme lektie: %s", exc)
        return ""


def _allerede_hoestet(a: Afsnit) -> bool:
    """Er dette afsnit hoestet fra den SAMME note foer?

    Self-safe → True: kan vi ikke tjekke, hoester vi ikke igen. En manglende
    lektie koster ingenting; en lektie der loefter sig selv til evidens 2 ved
    at blive laest to gange underminerer hele reglen.
    """
    try:
        from core.runtime.db import connect
        from core.runtime.db_lessons import signature_key
        with connect() as c:
            row = c.execute(
                "SELECT 1 FROM lessons WHERE signature_key=? AND source=? "
                "AND user_words=? LIMIT 1",
                (signature_key(a.signatur), KILDE, a.kilde_maerke)).fetchone()
        return row is not None
    except Exception as exc:
        logger.debug("dream_session_lessons: hoest-opslag fejlede: %s", exc)
        return True


def koer_hoest(*, mappe: Path | None = None, antal: int = _ANTAL_NOTER) -> dict[str, object]:
    """Læs de nyeste drømme-noter og gem det der er lektier.

    Returnerer tællinger pr. udfald, så høsten kan efterprøves i Centralen
    frem for kun at kunne ses på hvad der dukkede op i tabellen.
    """
    tal: dict[str, int] = {}
    for a in laes_noter(mappe, antal=antal):
        if _allerede_hoestet(a):
            tal["allerede-hoestet"] = tal.get("allerede-hoestet", 0) + 1
            continue
        if not er_en_lektie(a):
            tal["betragtning"] = tal.get("betragtning", 0) + 1
            continue
        udfald = gem(a) or "fejl"
        tal[udfald] = tal.get(udfald, 0) + 1
    try:
        from core.services.central_core import central
        central().observe({"cluster": "memory", "nerve": "dream_session_lessons",
                           "kind": "høst", **tal})
    except Exception:
        pass
    return {"tal": tal}
