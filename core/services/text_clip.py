"""core/services/text_clip.py

ÉN ord-sikker tekst-klipper — mod "død ved tusinde snit".

Jarvis' tanker/hukommelse/udtryk blev klippet ved tilfældige BYTE-grænser overalt (`text[:N]+"…"`),
så de læste "…men har ." midt i et ord. Denne helper klipper i stedet ved SÆTNINGS- så ORD-grænse,
og tilføjer kun ellipsis hvis der FAKTISK blev klippet. Bevarer mening. Ren, ingen sideeffekter.

Standardisér på `clip_text` i stedet for spredte `[:N]`-slices + rstrip-ellipsis.
"""
from __future__ import annotations

_ELLIPSIS = "…"


def clip_text(value: object, *, limit: int, hard: bool = False) -> str:
    """Klip tekst til <= ~limit tegn UDEN at hugge midt i et ord.

    - Normaliserer whitespace.
    - Kortere end limit → returneres uændret (ingen ellipsis).
    - Ellers: klip ved sidste sætnings-slut (. ! ?) hvis den ligger rimeligt sent, ellers sidste
      ord-grænse (mellemrum). Kun ét kæmpe-ord uden mellemrum falder tilbage til hårdt snit.
    - `hard=True`: garantér len <= limit (medtag ellipsis i budgettet) — til steder med en streng
      byte-grænse (fx cache-nøgler). Default False = må overskride en anelse for at bevare et helt ord.
    Self-safe → aldrig kast; tom streng ved fejl.
    """
    try:
        text = " ".join(str(value or "").split()).strip()
        if len(text) <= int(limit):
            return text
        lim = max(int(limit), 1)
        budget = lim - len(_ELLIPSIS) if hard else lim
        budget = max(budget, 1)
        window = text[:budget]
        # (1) sætnings-grænse — kun hvis den udgør en meningsfuld del af vinduet
        best = -1
        for sep in (". ", "! ", "? ", "; ", "\n"):
            idx = window.rfind(sep)
            if idx > best:
                best = idx
        if best >= budget * 0.6:
            return window[: best + 1].rstrip()
        # (2) sidste ord-grænse
        sp = window.rfind(" ")
        if sp >= budget * 0.4:
            return window[:sp].rstrip() + " " + _ELLIPSIS
        # (3) ét langt ord uden grænse → hårdt snit (sjældent)
        return window.rstrip() + _ELLIPSIS
    except Exception:
        return ""


def clip_words(value: object, *, max_words: int) -> str:
    """Klip til et antal ORD (ikke tegn) — når ord er den meningsfulde enhed. Self-safe."""
    try:
        words = str(value or "").split()
        if len(words) <= int(max_words):
            return " ".join(words)
        return " ".join(words[: max(int(max_words), 1)]) + " " + _ELLIPSIS
    except Exception:
        return ""
