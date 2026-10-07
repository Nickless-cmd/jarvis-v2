"""Tænke-sprog — killswitch for hvilket sprog ræsonnementet føres i.

## Hvorfor

Målt 30/9-2026 (A/B mod DeepSeek v4-flash, n=3 pr. arm, samme danske opgave,
samme danske slutsvar):

    dansk tænkning:   3.100 tænke-tokens, 19,3 s
    engelsk tænkning: 1.660 tænke-tokens, 10,6 s
    forhold:          1,87x tokens, 1,82x tid

Effekten kræver en **hård** instruktion. En mild formulering («tænk grundigt på
dansk») ændrede målt ingenting: modellen tænkte engelsk alligevel og skrev blot
«We need answer in Danish» i sin første linje. Derfor er direktivet herunder
formuleret som et krav, ikke et ønske — og det siger eksplicit at det ikke er
nok at *nævne* at svaret skal være dansk.

## Hvordan den slår igennem uden genstart

Flaget ligger i runtime-state (`core/runtime/db_core.py`), som læses ved kaldet
med en 2-sekunders read-cache og write-through på skriv. Et skift er derfor
synligt på **næste tur** i samme proces, og inden for 2 s på tværs af processer.
Ingen genstart.

## Hvor instruktionen lægges

I promptens **dynamiske hale** (efter `DYNAMIC_TAIL_SENTINEL`), ikke i det
cachede præfiks. Halen flyttes ud på den sidste brugerbesked, så det stabile
systemhoved + historikken forbliver én cachebar prefix — kun den nye tur er et
miss. Direktivet koster altså intet på cache-hit.

Bemærk at hele pointen er at *indholdet* af tænkningen skifter sprog, ikke
svaret: Bjørn får stadig dansk.
"""
from __future__ import annotations

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value

KV_KEY = "think_language"
DEFAULT = "da"
VALID = ("da", "en")

# Den HÅRDE instruktion. Formuleringen er ikke pynt: den milde variant blev
# målt virkningsløs 30/9 (modellen tænkte engelsk trods «tænk på dansk»).
_EN_DIRECTIVE = (
    "🧠 THINKING LANGUAGE: reason and think EXCLUSIVELY in English — every "
    "internal step, plan, and tool decision. Do NOT think in Danish, and do not "
    "merely note that the answer must be Danish: the reasoning ITSELF is English. "
    "Your visible reply to Bjørn stays DANISH, unchanged."
)


def current() -> str:
    """Aktivt tænke-sprog. Ukendt værdi eller fejl → 'da' (fail-soft)."""
    try:
        raw = get_runtime_state_value(KV_KEY, DEFAULT)
    except Exception:  # DB utilgaengelig → dansk er den sikre standard. Denne laesning ligger i prompt-assembly, saa den maa aldrig kaste og tage en tur med sig.
        return DEFAULT
    val = str(raw or "").strip().lower()
    return val if val in VALID else DEFAULT


def is_english() -> bool:
    """True når tænkningen skal føres på engelsk."""
    return current() == "en"


def set_language(lang: str) -> str:
    """Sæt tænke-sprog. Ukendt værdi afvises — returnerer det aktive sprog."""
    val = str(lang or "").strip().lower()
    if val not in VALID:
        return current()
    set_runtime_state_value(KV_KEY, val)
    return val


def directive() -> str:
    """Instruktionen til prompt-halen — tom streng når dansk er aktivt.

    Tom når dansk kører, så prompten er byte-identisk med før killswitchen
    blev bygget. Det er med vilje: ingen adfærdsændring før Bjørn beder om den.
    """
    return _EN_DIRECTIVE if is_english() else ""
