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


def clip_head_tail(value: object, *, limit: int, tail_frac: float = 0.35) -> str:
    """Bevar HOVED + HALE ved LINJE-grænser når tekst overskrider limit. Til tool-output (bash/read/
    web): slutningen (exit-kode, fejl, resultat) er ofte det VIGTIGSTE — ren head-afskæring smider den
    væk. Midten erstattes af en tydelig note. Self-safe.

    Før: `output[:16000] + "…"` klippede halen (og midt i ordet). Nu bevares både start og slut.
    """
    try:
        text = str(value or "")
        n = len(text)
        lim = max(int(limit), 200)
        if n <= lim:
            return text
        tail_budget = min(max(int(lim * tail_frac), 1), lim // 2)   # halen aldrig > halvdelen → hovedet bevares
        head_budget = lim - tail_budget
        head_raw = text[:head_budget]
        tail_raw = text[-tail_budget:]
        # snap til linje-grænser så vi ikke klipper midt i en linje …
        head = head_raw[: head_raw.rfind("\n")] if "\n" in head_raw else head_raw
        tail = tail_raw[tail_raw.find("\n") + 1:] if "\n" in tail_raw else tail_raw
        # … men hvis en KÆMPE linje (fx minificeret JSON) fik snap'et til at smide næsten alt væk,
        # fald tilbage til rå tegn-slice (bedre at bevare indhold end at kollapse til intet).
        if len(head) < head_budget * 0.4:
            head = head_raw
        if len(tail) < tail_budget * 0.4:
            tail = tail_raw
        omitted = n - len(head) - len(tail)
        return f"{head}\n\n… [{omitted} tegn udeladt i midten — hoved+hale bevaret] …\n\n{tail}"
    except Exception:
        try:
            return str(value or "")[: int(limit)]
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
