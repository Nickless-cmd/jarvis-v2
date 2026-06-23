"""Degenerations-guard — fang model-repetitions-løkker i streaming-laget.

Bjørn 23. jun: en model spiralede ind i at generere "probe_ollama864.py ...
probe_ollama991.py" ~7000 gange = 147.812 tegn rent skrald, streamet OG persisteret
som "gyldigt svar", indtil han manuelt cancellede. Det forgiftede så sessionens kontekst
(84% af alt) → hver efterfølgende tur degenererede lettere. Runtimen havde INGEN guard
mod runaway-repetition.

Denne detektor er provider-AGNOSTISK (lever i den delte stream-konsumption) og dræber
løkken ved kilden — ~token 50 i stedet for ~7000. Kerne-trick: DIGIT-NORMALISÉR tokens
(``probe_ollama864`` og ``probe_ollama865`` → ``probe_ollama#``) så en optællende sekvens
kollapser til ÉT token og afslører sig som repetition. Konservative tærskler → en ægte
lang, varieret besked (rigtig directory-listing, kodefil) udløser den ALDRIG.

Ren CPU, self-safe, ingen side-effekter.
"""
from __future__ import annotations

import re
from collections import Counter

_DIGIT = re.compile(r"\d+")
_MIN_CHARS = 1500        # under dette = for kort til at være en runaway
_MIN_TOKENS = 150
_REP_COUNT = 80          # samme digit-normaliserede token gentaget så mange gange
_MAX_DIVERSITY = 0.18    # distinkte/total under dette = degeneration (lav variation)


def check_degeneration(text: str) -> tuple[bool, str]:
    """→ (er_degenereret, menneskelæsbar_grund). Self-safe → (False, '') ved enhver fejl."""
    try:
        if not text or len(text) < _MIN_CHARS:
            return False, ""
        toks = text.split()
        if len(toks) < _MIN_TOKENS:
            return False, ""
        norm = [_DIGIT.sub("#", t) for t in toks]
        counts = Counter(norm)
        top_tok, top_n = counts.most_common(1)[0]
        diversity = len(counts) / len(norm)
        if top_n >= _REP_COUNT and diversity < _MAX_DIVERSITY:
            return True, (f"runaway-repetition: '{top_tok[:24]}'×{top_n} "
                          f"(diversitet {diversity:.0%}, {len(toks)} tokens)")
        return False, ""
    except Exception:
        return False, ""
