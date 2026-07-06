"""Dark-products digest — dark-LLM-programmet: wire mørke daemon-PRODUKTER ind i Centralen.

Disse daemons har allerede fået deres LLM-egress observeret (daemon_llm.py →
central_llm_egress), MEN deres faktiske PRODUKT (mønster-skepsis, drøm-
konsolidering, dyb refleksion, semantisk hukommelse, regel-motor, stemme)
når aldrig Centralen — helt mørkt.

Bygget på soul-digest-arkitekturen (``central_soul_digest``): en runtime-
aggregator der kalder hver producents READ-ONLY ``build_*_surface`` i
try/except og reducerer til ``{liveness,count}``. Rå indhold (drøm-temaer,
refleksions-tekst, regel-navne, ...) forlader ALDRIG denne proces — KUN bool
liveness + int count pr. signal. Proxy'es som én samlet flade til
/central/dark-products (§24.4 PRIVATE_NO_EGRESS-ånd, reducér-ved-kilden).

Alle seks producenter er VERIFICERET read-only (ingen LLM/wait/sleep i
build_*_surface — kun state-/config-læsning).
"""
from __future__ import annotations

from typing import Callable

# (signal-navn, modul-sti, funktionsnavn). Hver producent er VERIFICERET at
# eksistere, være READ-ONLY, og returnere en dict. En manglende/kastende
# producent isoleres til {liveness:False, count:0} (self-safe pr. signal).
_DARK: list[tuple[str, str, str]] = [
    ("apophenia", "core.services.apophenia_guard", "build_apophenia_guard_surface"),
    ("dream_consolidation", "core.services.dream_consolidation_daemon", "build_dream_consolidation_surface"),
    ("deep_reflection", "core.services.deep_reflection_slot", "build_deep_reflection_surface"),
    ("semantic_memory", "core.services.semantic_memory", "build_semantic_memory_surface"),
    ("rule_engine", "core.services.rule_engine", "build_rule_engine_surface"),
    ("voice_daemon", "core.services.voice_daemon", "build_voice_daemon_surface"),
]


def _first_count(surface: dict) -> int:
    """Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den
    første liste-værdi, ellers den første ikke-negative int-værdi, ellers 0."""
    if not isinstance(surface, dict):
        return 0
    for v in surface.values():
        if isinstance(v, (list, tuple)):
            return len(v)
    for v in surface.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and v >= 0:
            return v
    return 0


def _reduce(surface) -> dict:
    """KUN liveness+count. Ingen tekst. Self-safe."""
    if not isinstance(surface, dict) or not surface:
        return {"liveness": False, "count": 0}
    active = surface.get("active")
    liveness = bool(active) if active is not None else True
    return {"liveness": liveness, "count": _first_count(surface)}


def build_dark_products_digest() -> dict:
    """Samlet reduceret dark-products-digest. Kaster ALDRIG.

    Kun liveness+count pr. signal (§24.4 reducér-ved-kilden). Rå indhold
    forlader ALDRIG runtime. Self-safe pr. signal (import/kald i try/except
    → ``{liveness:False,count:0}``).
    """
    import importlib
    signals: dict[str, dict] = {}
    for name, mod, fn in _DARK:
        try:
            m = importlib.import_module(mod)
            builder: Callable = getattr(m, fn)
            signals[name] = _reduce(builder())
        except Exception:
            signals[name] = {"liveness": False, "count": 0}
    live_count = sum(1 for s in signals.values() if s.get("liveness"))
    return {
        "signals": signals,
        "live_count": live_count,
        "total": len(signals),
    }
