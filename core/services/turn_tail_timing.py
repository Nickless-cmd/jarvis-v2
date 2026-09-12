"""Hvor bliver sekunderne af EFTER svaret er skrevet færdigt?

Bjørn 12/9-2026: «det sker ofte at streamen hænger et par sekunder efter endt
svar … ved ikke om det er manglende svar fra serveren eller den henter noget
der kan forsinke afslutning af en stream».

Vi ved det heller ikke. Det er derfor dette er et MÅLEINSTRUMENT og ikke en
rettelse: mellem modellens sidste ord og `done` ligger persistering af svaret,
et turn-changelog, cost-bogføring, prompt-impact og et par oprydninger — og
`_git_changed_files` blev målt til 9 ms, så den kandidat er allerede udelukket.
At gætte videre ville være at rette noget tilfældigt og kalde det en løsning.

## Hvorfor den er tavs indtil den ikke er det

Der logges KUN når halen overstiger tærsklen. En linje pr. tur ville drukne i
journalen og blive filtreret væk; en linje når det faktisk er langsomt, bliver
læst. Samme regel som diff-badgen og prikken på Godkend.

## Hvorfor den ikke kan vælte en tur

Alt er i try/except hos kalderen, og modulet holder kun et dict. Et
måleinstrument der kan ødelægge det det måler, er værre end ingen måling.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# 500 ms. Under det mærker man det ikke; over det begynder en tur at "hænge".
TAERSKEL_S = 0.5

# run_id -> {"t0": float, "sidst": float, "skridt": [(navn, sekunder), ...]}
_haler: dict[str, dict[str, Any]] = {}

# Et loft, saa et run der aldrig naar sin slutning ikke lækker hukommelse.
_MAKS = 64


def start(run_id: str) -> None:
    rid = str(run_id or "")
    if not rid:
        return
    if len(_haler) >= _MAKS:
        # Smid den ÆLDSTE ud, ikke den nye. En hale der aldrig sluttede er
        # netop den slags der hober sig op.
        try:
            _haler.pop(next(iter(_haler)))
        except Exception:
            _haler.clear()
    nu = time.monotonic()
    _haler[rid] = {"t0": nu, "sidst": nu, "skridt": []}


def mark(run_id: str, navn: str) -> None:
    """Notér at ét led er færdigt. Gratis hvis `start` aldrig blev kaldt."""
    h = _haler.get(str(run_id or ""))
    if h is None:
        return
    nu = time.monotonic()
    h["skridt"].append((str(navn), nu - float(h["sidst"])))
    h["sidst"] = nu


def slut(run_id: str) -> float:
    """Afslut målingen. Returnerer halens længde i sekunder (0 hvis ukendt).

    Logger KUN når den overstiger tærsklen — og logger da HELE opdelingen, for
    et samlet tal siger at det var langsomt, ikke hvor.
    """
    rid = str(run_id or "")
    h = _haler.pop(rid, None)
    if h is None:
        return 0.0
    i_alt = time.monotonic() - float(h["t0"])
    if i_alt >= TAERSKEL_S:
        dele = " ".join(f"{n}={s * 1000:.0f}ms" for n, s in h["skridt"])
        logger.warning(
            "turn-tail: %.0f ms efter sidste ord foer stroemmen lukkede (run=%s) — %s",
            i_alt * 1000, rid, dele or "ingen delmaalinger",
        )
    return i_alt


def _nulstil_for_tests() -> None:
    _haler.clear()
