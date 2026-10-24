"""Observerende vagt: opdager en «mur» — flere pointer i én prosablok.

Baggrund (målt 24/10-2026, Bjørn + Codex): besked 219188 havde fire
selvstændige pointer liggende i ÉN blok på 1166 tegn uden linjeskift.
CommonMark gør et enkelt linjeskift til et mellemrum, og et afsnit helt uden
linjeskift bliver slet ikke delt — så fire tanker renderer som én ordstrøm.

Hvorfor dette er en OBSERVERENDE vagt og ikke en rettelse:
  Fire kriterier blev målt mod 300-400 faktiske assistentbeskeder samme dag.
  Kun ét gav et ægte hit:
    · >600 tegn + >=4 sætningsgrænser  → 7 hits, 6 falske positiver
    · >900 tegn                        → 12 hits, 10 var krypteret tekst
    · fed overskrift midt i blok       → 313 af 400 (fanger alt, beviser intet)
    · >900 tegn ELLER (>600 + >=8 sæt) → 2 hits, 1 falsk positiv
  Tærsklen er derfor ikke kalibreret godt nok til at måtte ændre teksten.
  En vagt der gætter forkert og «reparerer» ødelægger et svar der var i orden.
  Første fase måler derfor kun: den skriver en central-hændelse og lader
  teksten være urørt. Når fordelingen er kendt over nogle døgn, kan en
  format-only reparation overvejes — med de målte tal som grundlag.

Fail-open overalt: enhver fejl her må aldrig påvirke et svar.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

#: En blok skal være så lang før den overhovedet kan være en mur.
MIN_BLOK_TEGN = 900
#: ... eller være mellemlang MEN indeholde mange sætningsgrænser.
MIN_BLOK_TEGN_MANGE = 600
MANGE_SAETNINGER = 8

_FENCE = re.compile(r"```.*?```", re.S)
_LISTE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
_SAETNINGSSLUT = re.compile(r"[.!?](?:\s|$)")


def _prosablokke(text: str) -> list[str]:
    """Del teksten i blokke og kast kode, tabeller, lister og native-JSON væk.

    Kun almindelig prosa kan være en mur — en tabel eller en liste er allerede
    struktureret, og at tælle den som mur ville give falske positiver.
    """
    uden_kode = _FENCE.sub("\n\n", text)
    blokke: list[str] = []
    for raa in re.split(r"\n\s*\n", uden_kode):
        blok = raa.strip()
        if not blok:
            continue
        linjer = [l for l in blok.split("\n") if l.strip()]
        if sum(1 for l in linjer if _LISTE.match(l)) >= 2:
            continue
        if any(l.lstrip().startswith("|") for l in linjer):
            continue
        if blok.startswith(("#", ">", "{")):
            continue
        blokke.append(blok)
    return blokke


def find_walls(text: str) -> list[dict[str, object]]:
    """Returnér de prosablokke der ser ud som en mur. Tom liste = intet fundet."""
    if not text or len(text) < MIN_BLOK_TEGN_MANGE:
        return []
    fund: list[dict[str, object]] = []
    for blok in _prosablokke(text):
        laengde = len(blok)
        saetninger = len(_SAETNINGSSLUT.findall(blok))
        if laengde > MIN_BLOK_TEGN or (
            laengde > MIN_BLOK_TEGN_MANGE and saetninger >= MANGE_SAETNINGER
        ):
            fund.append(
                {
                    "tegn": laengde,
                    "saetninger": saetninger,
                    "start": blok[:80].replace("\n", " "),
                }
            )
    return fund


def observe(text: str, *, run_id: str = "") -> list[dict[str, object]]:
    """Mål uden at røre teksten. Skriver en central-hændelse ved fund.

    Returnerer fundene, så en kalder kan logge dem — men retter ALDRIG i
    ``text``. Fail-open: en fejl her må ikke påvirke svaret.
    """
    try:
        fund = find_walls(text)
    except Exception:
        logger.debug("wall_guard: målingen fejlede", exc_info=True)
        return []
    if not fund:
        return []
    try:
        from core.runtime.db_central_incidents import record_central_incident

        stoerste = max(fund, key=lambda f: int(f["tegn"]))
        record_central_incident(
            cluster="runtime",
            nerve="chat_wall_observed",
            kind="prose_wall",
            severity="info",
            message=(
                f"prosablok uden luft: {stoerste['tegn']} tegn / "
                f"{stoerste['saetninger']} sætninger (run={run_id or 'ukendt'})"
            ),
            dedup=True,
        )
    except Exception:
        logger.debug("wall_guard: kunne ikke registrere hændelse", exc_info=True)
    return fund
