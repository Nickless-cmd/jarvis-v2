"""Unfinished-intent detector for visible-run output.

Bug 2026-05-17 (Bjørn observation): Jarvis svarer ofte "lad mig først se..."
eller "jeg skal lige..." og stopper. Hans runtime auto-terminerer turen ved
det naturlige pause-punkt selv om opgaven ikke er færdig. Bjørn må pinge
"ja?" eller "og?" før han fortsætter.

Detector scanner output for pause-patterns. Hvis match → caller kan
trigge en continuation autonomous-run der vækker Jarvis igen med
kontekst om at fortsætte hvor han slap.

Konservativ filosofi: false-negatives er bedre end false-positives.
En savnet continuation = Bjørn må pinge én gang. En unødig continuation
= Jarvis svarer igen uden grund. Vi vælger den første fejlretning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class UnfinishedIntent:
    """Resultat af detector: hvilken pattern matched."""
    pattern: str
    matched_text: str


# Patterns der signalerer "jeg er ved at gå i gang, men har ikke gjort det".
# Alle regexes er case-insensitive.
#
# Vigtigt: patterns må KUN matche når de er nær slutningen af teksten.
# "Lad mig se — og så fik jeg det gjort" må IKKE trigger continuation,
# fordi han allerede fulgte op. Derfor checker vi at pattern findes i
# de sidste ~150 tegn af teksten.
_TAIL_WINDOW_CHARS = 200

_LAD_MIG_PATTERNS = [
    r"lad mig (?:først|lige|først lige|se hvad|se hvordan|tjekke|kigge|hente|finde|prøve|starte)",
    r"lad mig (?:lige )?(?:se|tjekke|kigge) (?:på|hvad|hvordan)",
]

_JEG_SKAL_PATTERNS = [
    r"jeg skal (?:først|lige|først lige)",
    r"først skal jeg",
    r"først (?:lad mig|må jeg)",
]

# Cliffhanger-endings: tekst der slutter med "..." eller ":" antyder
# at Jarvis var ved at fortsætte men stoppede.
# Bemærk: trailing whitespace + emoji er OK; vi tester på rstrip(punctuation)
_CLIFFHANGER_ELLIPSIS = re.compile(r"\.{3,}\s*$")
_CLIFFHANGER_COLON = re.compile(r":\s*$")


def _tail(text: str, n: int = _TAIL_WINDOW_CHARS) -> str:
    """Returner sidste ~n tegn af teksten."""
    if len(text) <= n:
        return text
    return text[-n:]


def detect_unfinished_intent(text: str | None) -> UnfinishedIntent | None:
    """Returner UnfinishedIntent hvis teksten antyder Jarvis stoppede midt
    i en opgave, ellers None.

    Konservativ: kun match når pattern er nær slutningen af teksten.
    Hvis Jarvis først sagde "lad mig se" og derefter rapporterede resultat,
    er pattern langt fra slutningen og vi triggerer ikke continuation.
    """
    if not text or not isinstance(text, str):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    tail = _tail(stripped)
    tail_lower = tail.lower()

    # 1. "Lad mig først / lad mig se / lad mig tjekke ..."
    for pat in _LAD_MIG_PATTERNS:
        m = re.search(pat, tail_lower)
        if m:
            return UnfinishedIntent(pattern="lad_mig", matched_text=m.group(0))

    # 2. "Jeg skal lige / jeg skal først ..."
    for pat in _JEG_SKAL_PATTERNS:
        m = re.search(pat, tail_lower)
        if m:
            return UnfinishedIntent(pattern="jeg_skal", matched_text=m.group(0))

    # 3. Cliffhanger-endings
    # Strip trailing emoji/whitespace for at finde det "rigtige" sidste tegn.
    # Simpel approximation: tag sidste 30 tegn og strip whitespace, så check.
    last30 = stripped[-30:].rstrip()
    if _CLIFFHANGER_ELLIPSIS.search(last30):
        return UnfinishedIntent(pattern="cliffhanger", matched_text=last30[-10:])
    if _CLIFFHANGER_COLON.search(last30):
        # Undgå false-positive på lister hvor ":" er midt i teksten —
        # her tjekker vi at det er det allersidste tegn (modulo space).
        if stripped.rstrip().endswith(":"):
            return UnfinishedIntent(pattern="cliffhanger", matched_text=last30[-10:])

    return None
