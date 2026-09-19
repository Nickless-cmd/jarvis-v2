"""Én linje om hvad Jarvis TÆNKTE i en runde — til visningstilstanden «Tænkning».

Claude Desktop har tre visningstilstande: normal, thinking og verbose
(cc-desktop-chatview.md §1-2). I «thinking» står der «a one-line recap of
Claude's thinking above each tool group», og tilstanden sendes med til
hosten (`thinkingSummariesWanted`): den bestemmer hvad der PRODUCERES, ikke
kun hvordan det tegnes.

Samme kontrakt her. Resuméet koster et kald til den lille lokale model, så
det laves KUN når klienten har bedt om tænke-visningen — og det rider med i
runde-etikettens tråd og hændelse (`visible_run_trace.udsend_runde_etiket`),
fordi det er samme enhed: én værktøjsgruppe. Det gemmes på gruppens
`tool_use_summary`-blok som `thinking_summary`, så det overlever en
genindlæsning.

Kaster aldrig. Et resumé er en overskrift; en tur må aldrig vælte fordi
overskriften ikke kunne skrives.
"""
from __future__ import annotations

import logging
import re
from typing import Final

logger = logging.getLogger(__name__)

__all__ = ["MAKS_RESUME", "tanke_resume", "byg_prompt"]

#: Så meget af tænkningen modellen ser — HALEN, hvor konklusionen står.
MAKS_TANKE: Final[int] = 1500
#: Brugerens hensigt, som runde-etiketten (CC's 200 tegn).
MAKS_HENSIGT: Final[int] = 200
#: Linjen står over en værktøjsgruppe — lidt længere end etiketten, stadig én linje.
MAKS_RESUME: Final[int] = 70

_PROMPT = (
    "Du får et uddrag af en AI-assistents tænkning lige før den brugte værktøjer. "
    "Skriv ÉN kort linje på dansk, højst 60 tegn, der siger hvad den overvejede "
    "eller besluttede. Datid, ingen indledning, ingen anførselstegn, intet punktum.\n"
    "Eksempler: «Ville tjekke om værnet sidder i ruten» · «Mistænkte cachen for "
    "at være forældet» · «Besluttede at læse testen først»\n\n"
)


def _klip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s[-n:] if len(s) > n else s


def byg_prompt(tanke: str, hensigt: str = "") -> str:
    dele = [_PROMPT]
    if hensigt.strip():
        dele.append(f"Brugeren bad om: {_klip(hensigt, MAKS_HENSIGT)}\n")
    dele.append(f"Tænkning: {_klip(tanke, MAKS_TANKE)}\n\nLinje:")
    return "".join(dele)


_AFSLUT = re.compile(r"[\s.,;:!…]+$")


def _ryd(s: str) -> str:
    s = (s or "").split("\n")[0].strip()
    s = re.sub(r"^(?:linje|resumé|resume)\s*:\s*", "", s, flags=re.IGNORECASE)
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("“", "”")):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            s = s[1:-1].strip()
    s = _AFSLUT.sub("", s)
    if len(s) > MAKS_RESUME:
        klip = s[:MAKS_RESUME]
        mellemrum = klip.rfind(" ")
        s = _AFSLUT.sub("", (klip[:mellemrum] if mellemrum > 0 else klip))
    return s


def tanke_resume(tanke: str, hensigt: str = "") -> str:
    """Én linje om rundens tænkning, eller `""`."""
    if not (tanke or "").strip():
        return ""
    try:
        from core.services.tool_round_label import _kald_model
        ud = _ryd(_kald_model(byg_prompt(tanke, hensigt)))
    except Exception:
        logger.debug("tanke_resume: kald fejlede", exc_info=True)
        return ""
    # Et nøgent ord er ikke et resumé.
    return ud if len(ud.split()) >= 2 else ""
