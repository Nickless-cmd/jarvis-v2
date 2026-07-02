"""core/services/central_prompt_composer.py

Tråd 2 (Intelligent Central-spec §4): Centralen som modellens KONTEKST-KOMPONIST.

Bjørns idé: modellen er en stateless genial gæst. I dag propper vi ALT i en mega-system-prompt hver
tur (awareness, 78 surfaces, somatik, mood) uanset relevans. Men Centralen HOLDER alt alligevel — så
lad den bygge præcis den kontekst DENNE tur kræver. Prompt-evolution bliver dermed "Centralen lærer
RELEVANS-FUNKTIONEN": hvilken kontekst der betyder noget for hvilket input.

TO-DELT PROMPT (cache-bevidst — ellers koster det tokens i stedet for at spare):
  * FAST KERNE (forrest, cachet): SOUL/identitet/system — FROSSEN, rører vi ALDRIG.
  * DYNAMISK HALE (bagest, EFTER cache-grænsen): kun awareness/state denne tur kræver. Her spares.

Dette modul er substratet: tur-type-klassifikator + relevans-vægte (governed) + should_include-switch.
SIKKERHED: shadow-first — should_include returnerer ALTID True medmindre `prompt_relevance_live_enabled`
+ en resolveret relevans-hypotese har bevist en sektion er død vægt for en tur-type. Konservativ ved
tvivl (inkludér). Identitet + sikkerhed = frossen kerne, gates ALDRIG. Alt self-safe, kaster ALDRIG.

STATUS: substrat + switch bygget. Wiring ind i prompt_contract (kald should_include på hale-sektioner,
UDEN FOR build_visible_stable_prefix/cache-grænsen) + relevans-hypotese-generering = næste omhyggelige skridt.
"""
from __future__ import annotations

from typing import Any

_LIVE_FLAG = "prompt_relevance_live_enabled"     # Bjørns switch (default OFF → inkludér alt)
_WEIGHTS_KEY = "prompt_relevance_weights"        # {"turn_type|section": weight} (runtime_state_kv)
_INCLUDE_THRESHOLD = 0.3                          # under denne vægt (og live) → udelad sektion
_DOMAIN = "prompt_relevance"                      # §8.1 isoleret mutations-domæne

# FROSNE sektioner der ALDRIG gates (identitet + sikkerhed = frossen kerne).
FROZEN_SECTIONS: frozenset[str] = frozenset({
    "soul", "identity", "user", "security", "safety", "system", "core",
})

# Tur-type-klassifikation (grov, deterministisk, model-fri). Rækkefølge = prioritet.
_TURN_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("kode", ("kode", "bug", "traceback", "funktion", "python", "import ", "def ", "class ",
              "fejl i", "stacktrace", "kompil", "deploy", "commit", "refactor")),
    ("hukommelse", ("husk", "tidligere", "sidste gang", "hvad sagde", "genkald", "kan du huske")),
    ("opgave", ("lav ", "byg ", "implementer", "tilføj", "ret ", "opdater", "skriv ", "opret")),
    ("spørgsmål", ("hvad ", "hvorfor", "hvordan", "hvem ", "hvornår", "kan du forklare", "?")),
)


def classify_turn_type(user_message: str) -> str:
    """Grov tur-type fra brugerbeskeden (kode/hukommelse/opgave/spørgsmål/samtale). Model-fri, self-safe."""
    m = str(user_message or "").lower()
    if not m.strip():
        return "samtale"
    for ttype, kws in _TURN_PATTERNS:
        if any(kw in m for kw in kws):
            return ttype
    return "samtale"


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def is_live_enabled() -> bool:
    return bool(_kv_get(_LIVE_FLAG, False))


def get_weight(turn_type: str, section: str) -> float:
    """Relevans-vægt for (tur-type, sektion). Default 1.0 = altid inkludér. Self-safe."""
    try:
        w = _kv_get(_WEIGHTS_KEY, {}) or {}
        if isinstance(w, dict):
            return float(w.get(f"{turn_type}|{section}", 1.0))
    except Exception:
        pass
    return 1.0


def should_include(turn_type: str, section: str, *, threshold: float = _INCLUDE_THRESHOLD) -> bool:
    """DEN RENE SWITCH (som get_gut_bias): skal denne sektion med i halen for denne tur-type?
    Shadow (default): ALTID True — intet skæres. Frosne sektioner: ALTID True. Live + lav vægt: udelad.
    Konservativ ved tvivl. Self-safe → True (inkludér)."""
    try:
        if str(section or "").lower() in FROZEN_SECTIONS:
            return True
        if not is_live_enabled():
            return True                         # shadow: intet skæres endnu
        return get_weight(turn_type, section) >= float(threshold)
    except Exception:
        return True                             # fail-open på inklusion (aldrig skjul ved fejl)


def observe_composition(turn_type: str, *, sections_total: int, sections_included: int,
                        outcome: str = "") -> None:
    """Egress-frit substrat: hvad blev komponeret denne tur (til fremtidig relevans-hypotese-generering).
    Kun skalarer/tur-type-navn — aldrig prompt-INDHOLD. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", f"prompt_compose:{turn_type}",
                       value=float(sections_included),
                       meta={"total": int(sections_total), "included": int(sections_included),
                             "outcome": str(outcome)[:24]})
    except Exception:
        pass


def build_central_prompt_composer_surface() -> dict[str, object]:
    """Mission Control surface — read-only: live-status + relevans-vægte (hvad Centralen VILLE skære)."""
    w = _kv_get(_WEIGHTS_KEY, {}) or {}
    low = {k: v for k, v in (w.items() if isinstance(w, dict) else [])
           if isinstance(v, (int, float)) and float(v) < _INCLUDE_THRESHOLD}
    return {"active": True, "live_enabled": is_live_enabled(),
            "threshold": _INCLUDE_THRESHOLD, "weight_count": len(w) if isinstance(w, dict) else 0,
            "would_drop": low, "frozen_sections": sorted(FROZEN_SECTIONS)}
