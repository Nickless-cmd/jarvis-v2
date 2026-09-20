"""Overstort værktøjs-output gemmes i en fil i stedet for at blive klippet væk.

## Hvorfor (20/9-2026)

Vi klipper i dag et værktøjsresultat ved 8.000 tegn og sætter «[tool result
truncated for follow-up context; N chars omitted]». Halen er dermed VÆK —
ikke gemt et andet sted, ikke hentbar. Kalder han et værktøj igen for at se
resten, får han det samme klip.

DeepSeek-harness' `dsh-spill-local` gør det modsatte: den oversize tekst
skrives til en privat, session-scoped fil, og modellen får STIEN plus besked
om at læse eller grep'e den. Intet tabes, og konteksten bliver alligevel lille.

Deres tre krav, som er grunden til at det ikke bare er «skriv en fil»:

* Filen er privat for brugeren (0700 på mappen).
* Navnet er uforudsigeligt, så et delt rod ikke kan læses på gæt.
* Hver session grupperes under en stabil mappe, så en plantet symlink ikke
  kan omdirigere skrivningen.

En forskel fra deres: vores eneste nuværende kalder er en MODUL-GLOBAL
adapter uden adgang til hvilken session den arbejder for, så uden et
session-id grupperes filerne pr. DATO. De tre krav ovenfor holder stadig —
gruppering er til oprydning, ikke til adgangskontrol. Får kalderen en dag en
session med, falder den automatisk tilbage til deres form.

Bjørns stående krav er det samme sted fra den anden side: «intet skæres uden
vi har snakket om det først». Spild skærer ikke — det flytter.
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

#: Hvor længe en spildfil ligger. Den er et arbejdsdokument for ÉN tur, ikke
#: et arkiv; ryddes ved opstart så disken ikke løber fuld af halerne.
OPBEVARING_DAGE = 7
_SIKKERT_NAVN = re.compile(r"[^A-Za-z0-9_.-]")


def _rod() -> Path:
    """Under `state_store`s mappe — ikke `Path.home()` direkte.

    Det er ikke kosmetik: tests har et autouse-værn der peger `_STATE_DIR`
    mod en tmp-mappe, netop fordi testdata én gang endte i den ægte
    `in_flight_runs.json` og blev kørt som rigtige ture. Låner vi deres rod,
    arver vi værnet gratis.
    """
    from core.runtime import state_store
    return Path(state_store._STATE_DIR) / "spild"


def _mappe(session_id: str) -> Path:
    """Sessionens egen mappe, oprettet med 0700. Navnet renses.

    Rensningen er ikke kosmetik: et session-id der kunne indeholde `..` eller
    en skråstreg ville lade kalderen vælge hvor på disken vi skriver.
    """
    raa = str(session_id or "").strip() or time.strftime("dag-%Y-%m-%d")
    navn = _SIKKERT_NAVN.sub("_", raa)[:80] or "ukendt"
    sti = _rod() / navn
    sti.mkdir(parents=True, exist_ok=True, mode=0o700)
    return sti


def gem(tekst: str, *, session_id: str = "", vaerktoej: str = "") -> str:
    """Skriv teksten til en privat fil og giv stien. "" hvis det ikke lykkes.

    Returnerer "" i stedet for at kaste: kan vi ikke spilde, skal kalderen
    falde tilbage på sin gamle klipning — et værktøjsresultat må aldrig gå
    tabt fordi disken sagde nej.
    """
    try:
        mappe = _mappe(session_id)
        rent = _SIKKERT_NAVN.sub("_", str(vaerktoej or "ud"))[:40] or "ud"
        sti = mappe / f"{rent}-{uuid4().hex}.txt"
        sti.write_text(str(tekst or ""), encoding="utf-8")
        os.chmod(sti, 0o600)
        return str(sti)
    except Exception as exc:  # disk/rettigheder: kalderen klipper som før
        logger.warning("spild: kunne ikke gemme %s: %s", vaerktoej, exc)
        return ""


def henvisning(sti: str, *, vist: int, i_alt: int) -> str:
    """Den tekst der erstatter halen. Siger hvad der mangler OG hvor det er."""
    mangler = max(0, int(i_alt) - int(vist))
    return (
        f"\n\n[De første {vist} tegn står ovenfor. De resterende {mangler} er "
        f"IKKE væk — hele resultatet ({i_alt} tegn) ligger i {sti}. "
        f"Læs eller grep i den fil hvis du mangler noget derfra.]"
    )


def ryd(*, dage: int = OPBEVARING_DAGE) -> int:
    """Slet spildfiler ældre end `dage`. Giver antallet der blev slettet."""
    rod = _rod()
    if not rod.is_dir():
        return 0
    graense = time.time() - max(0, int(dage)) * 86400.0
    slettet = 0
    for sti in rod.rglob("*.txt"):
        try:
            if sti.stat().st_mtime < graense:
                sti.unlink()
                slettet += 1
        except OSError as exc:  # en fil vi ikke må røre skal ikke stoppe resten
            logger.debug("spild: kunne ikke slette %s: %s", sti, exc)
    for mappe in rod.iterdir():
        try:
            if mappe.is_dir() and not any(mappe.iterdir()):
                mappe.rmdir()
        except OSError as exc:  # tom-tjek kan race med en ny skrivning
            logger.debug("spild: kunne ikke rydde mappe %s: %s", mappe, exc)
    return slettet
