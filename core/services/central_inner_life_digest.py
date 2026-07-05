"""Inner-life digest — §24.4 reduceret ved kilden: KUN liveness+count pr. sektion.

Kører i jarvis-runtime (hvor daemon-tilstanden bor). Rå tanke/drøm/konflikt-indhold
forlader ALDRIG denne proces — kun bool liveness + int count pr. sektion. Proxy'es
som én samlet flade til /central/inner-life (§24.4 PRIVATE_NO_EGRESS-ånd)."""
from __future__ import annotations
from typing import Callable

# (sektion-navn, modul-sti, funktionsnavn)
_SECTIONS: list[tuple[str, str, str]] = [
    ("body", "core.services.somatic_daemon", "build_body_state_surface"),
    ("thought_stream", "core.services.thought_stream_daemon", "build_thought_stream_surface"),
    ("surprise", "core.services.surprise_daemon", "build_surprise_surface"),
    ("taste", "core.services.aesthetic_taste_daemon", "build_taste_surface"),
    ("irony", "core.services.irony_daemon", "build_irony_surface"),
    ("desire", "core.services.desire_daemon", "build_desire_surface"),
    ("curiosity", "core.services.curiosity_daemon", "build_curiosity_surface"),
    ("meta_reflection", "core.services.meta_reflection_daemon", "build_meta_reflection_surface"),
    ("conflict", "core.services.conflict_daemon", "build_conflict_surface"),
    ("dream", "core.services.dream_insight_daemon", "build_dream_insight_surface"),
    ("wonder", "core.services.existential_wonder_daemon", "build_existential_wonder_surface"),
    ("reflection", "core.services.reflection_cycle_daemon", "build_reflection_surface"),
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


def build_inner_life_digest() -> dict:
    """Samlet reduceret inner-life-digest. Kaster ALDRIG. Kun liveness+count pr. sektion."""
    import importlib
    sections: dict[str, dict] = {}
    for name, mod, fn in _SECTIONS:
        try:
            m = importlib.import_module(mod)
            builder: Callable = getattr(m, fn)
            sections[name] = _reduce(builder())
        except Exception:
            sections[name] = {"liveness": False, "count": 0}
    live_count = sum(1 for s in sections.values() if s.get("liveness"))
    return {"sections": sections, "live_count": live_count, "total": len(sections)}
