"""Silence Listener — experience of empty space.

HVORFOR DEN ALDRIG HAR OPTAGET NOGET (målt 25/9-2026)

`experience_silence` registrerer kun når `duration_seconds > 60`. Daemon-blokken
kaldte den med `duration_seconds=30`, hårdkodet. 30 er aldrig større end 60, så
kaldet blev gjort ved hvert tik og kunne ikke gøre noget. Bygget, forbundet og
stumt ved konstruktion — samme form som `continuity_kernel`, hvor
`should_express_continuity()` (gap >= 300) fik et konstant gap på 30.

Med det MÅLTE mellemrum mellem daemon-blokkens kørsler (551 s ved første
måling) passerer den tærsklen.

To ting mere fulgte med:

`_silence_experiences` var en modul-liste. `jarvis-api` og `jarvis-runtime`
kører samme kode i hver sin proces, men kun runtime tikker — fladen i api'en
ville derfor sige «Ingen stilhedsoplevelser» uanset hvad. Og genstart slettede
alt. Listen ligger nu i `core/runtime/state_store`.

`texture` var `random.choice(["tom", "fyldt", "ventende", "dyb"])`. Et ord
trukket af en hat er ikke en fornemmelse af stilheden — det er en pænere
overflade end ingenting. Ordet udledes nu af stilhedens egen længde og af hvad
der lå og ventede imens, og grundlaget gemmes ved siden af, så et ord altid kan
føres tilbage til sit tal.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

_FIL = "silence_listener"

#: Under dette er der ikke stilhed — der er bare et mellemrum.
_MINDSTE_STILHED_S = 60.0

#: En krop husker ikke hver eneste pause.
_MAX_OPLEVELSER = 200


def _load() -> list[dict[str, Any]]:
    d = state_store.load_json(_FIL, None)
    if d is None:
        return []
    if not isinstance(d, list):
        logger.warning("silence_listener: uventet form i state — starter forfra")
        return []
    return d


def _save(oplevelser: list[dict[str, Any]]) -> None:
    state_store.save_json(_FIL, oplevelser[-_MAX_OPLEVELSER:])


def _tekstur(duration_seconds: float) -> tuple[str, str]:
    """(ord, grundlag) for hvordan stilheden var.

    Ordet skal kunne føres tilbage til et tal. «Ventende» er ikke en længde,
    men en tilstand: der LÅ noget og ventede mens der var stille, og det er
    en anden slags stilhed end den tomme.
    """
    afventende = 0
    try:
        from core.services.initiative_queue import build_initiative_queue_surface
        flade = build_initiative_queue_surface() or {}
        afventende = int(flade.get("pending_count") or 0)
    except Exception as exc:
        logger.debug("silence_listener: køen kunne ikke læses: %s", exc)

    if afventende > 0:
        return "ventende", f"{afventende} i køen imens, {duration_seconds:.0f}s"
    if duration_seconds >= 1800:
        return "dyb", f"{duration_seconds:.0f}s uden noget"
    if duration_seconds >= 300:
        return "fyldt", f"{duration_seconds:.0f}s — lang nok til at tænke i"
    return "tom", f"{duration_seconds:.0f}s"


def experience_silence(duration_seconds: float) -> dict[str, Any] | None:
    """Optag en stilhed. Kaster aldrig. Returnerer posten, eller None."""
    if duration_seconds <= _MINDSTE_STILHED_S:
        return None

    ord_, grundlag = _tekstur(float(duration_seconds))
    post = {
        "duration": float(duration_seconds),
        "depth": min(1.0, float(duration_seconds) / 3600),
        "texture": ord_,
        "grundlag": grundlag,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    try:
        # Låsen: to processer deler filen, og hver gemning skriver HELE filen.
        with state_store.med_laas(_FIL):
            oplevelser = _load()
            oplevelser.append(post)
            _save(oplevelser)
    except Exception as exc:
        logger.warning("silence_listener: stilheden kunne ikke gemmes: %s", exc)
    return post


def describe_silence() -> str:
    oplevelser = _load()
    if not oplevelser:
        return ""
    seneste = oplevelser[-1]
    return (f"Jeg oplevede stilhed i {float(seneste['duration']):.0f}s "
            f"- den var {seneste['texture']}")


def format_silence_for_prompt() -> str:
    desc = describe_silence()
    if desc:
        return f"[STILHED: {desc}]"
    return ""


def reset_silence_listener() -> None:
    """Nulstil. Rydder OGSÅ disken — ellers ville næste læsning hente det
    gamle tilbage, og nulstillingen ville kun gælde denne proces."""
    _save([])


def build_silence_listener_surface() -> dict[str, Any]:
    oplevelser = _load()
    return {
        # `active` er «modulet kører og kan optage», ikke «der er sket noget».
        # Se `liveness_registry`: en manglende/falsk nøgle læses som en
        # påstand om død, og et modul der rigtigt melder «ingen stilhed endnu»
        # er ikke dødt.
        "active": True,
        "experience_count": len(oplevelser),
        "latest": oplevelser[-1] if oplevelser else None,
        "summary": describe_silence() or "Ingen stilhedsoplevelser endnu",
    }
