"""Delt lager for de følte overflader — så de overlever en procesgrænse.

Målt 2026-09-05: **alle 14** følte overflader i `visible_inner_life._FELT_SURFACES`
var tomme i prompten, samtidig med at eventbussen havde 183
`thought_stream.fragment_generated` på syv dage. Fragmenterne blev skabt; de nåede
bare aldrig frem.

Årsagen er en procesgrænse. Daemonerne holder deres tilstand i modul-globaler:

    _cached_fragment: str = ""
    _fragment_buffer: list[str] = []

    def build_thought_stream_surface() -> dict:
        return {"latest_fragment": _cached_fragment, ...}

Daemonen kører i **jarvis-runtime**. Prompten bygges i **jarvis-api**. To
processer, hver sit sæt globaler — så overfladen i den proces der bygger prompten
er tom, uanset hvor flittigt daemonen arbejder. Det er mekanismen bag «skriveside
enorm, læseside nålestik»: hullet er ikke i logikken, det er mellem processerne.

Reglen her er bevidst enkel: **har den lokale proces indhold, er den friskest.**
Er den tom, læses den delte tilstand. Producent-processen bruger altså altid sine
egne globaler (ingen ekstra DB-læsning i den varme sti), og api-processen — som
aldrig har noget — får det daemonen sidst skrev.

Ingen tidsstempler at holde styr på, ingen synkronisering. Kun: tom → spørg de
andre.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_KEY_PREFIX = "felt_surface."


def _state_key(name: str) -> str:
    return _KEY_PREFIX + str(name or "").strip()


def is_empty_payload(payload: Any) -> bool:
    """Er overfladen reelt tom?

    Tom = ingen af værdierne bærer noget. Præcis den form vi målte:
    ``{'latest_fragment': '', 'fragment_buffer': [], 'fragment_count': 0}``.
    Tal-felter som ``fragment_count: 0`` tæller IKKE som indhold — de er
    afledte af de tomme lister.
    """
    if not isinstance(payload, dict) or not payload:
        return True
    for vaerdi in payload.values():
        if isinstance(vaerdi, (str, bytes)):
            if vaerdi.strip():
                return False
        elif isinstance(vaerdi, (list, tuple, set, dict)):
            if len(vaerdi) > 0:
                return False
        elif isinstance(vaerdi, bool):
            if vaerdi:
                return False
        elif isinstance(vaerdi, (int, float)):
            continue  # afledte tællere beviser ikke indhold
        elif vaerdi is not None:
            return False
    return True


def save_surface(name: str, payload: dict[str, Any]) -> None:
    """Gem en overflade så andre processer kan læse den. Aldrig kastende.

    Kaldes fra daemonens skrive-sti. En fejl her må ikke kunne vælte et tick.
    """
    if not isinstance(payload, dict):
        return
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_state_key(name), dict(payload))
    except Exception as exc:
        logger.debug("felt_surface_store: kunne ikke gemme '%s': %s", name, exc)


def load_surface(name: str) -> dict[str, Any]:
    """Læs en gemt overflade. {} hvis der intet er, eller ved enhver fejl."""
    try:
        from core.runtime.db import get_runtime_state_value
        data = get_runtime_state_value(_state_key(name))
        return dict(data) if isinstance(data, dict) else {}
    except Exception as exc:
        logger.debug("felt_surface_store: kunne ikke læse '%s': %s", name, exc)
        return {}


def shared_surface(name: str, local_builder: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Overfladen som den skal se ud, uanset hvilken proces der spørger.

    Har den lokale proces indhold, vinder den. Ellers hentes det delte. Er begge
    tomme, returneres den lokale form — så kaldere stadig får de forventede
    nøgler i stedet for en tom dict.
    """
    try:
        lokal = local_builder() or {}
    except Exception as exc:
        logger.debug("felt_surface_store: lokal builder for '%s' fejlede: %s", name, exc)
        lokal = {}

    if not is_empty_payload(lokal):
        return lokal

    delt = load_surface(name)
    if not is_empty_payload(delt):
        return delt
    return lokal

# De 14 følte overflader. Kanonisk liste — `visible_inner_life._FELT_SURFACES`
# er visnings-rækkefølgen, denne er hvad der persisteres. En test vogter at de
# to holder sig identiske, så en ny kilde ikke stilfærdigt falder ud af lageret.
FELT_SURFACE_NAMES: tuple[str, ...] = (
    "thought_stream", "meta_reflection", "curiosity", "existential_wonder",
    "aesthetic_taste", "code_aesthetic", "irony", "creative_drift",
    "development_narrative", "dream_insight", "desire", "absence", "conflict",
    "surprise",
)


def persist_local_surfaces() -> dict[str, object]:
    """Gem de følte overflader som DENNE proces kan se dem.

    Kaldes fra runtime-processen, hvor daemonerne bor og deres globaler er
    varme. Kun ikke-tomme overflader gemmes — ellers ville en tom producent
    overskrive noget der faktisk stod der.

    Det er dette kald der lukker procesgrænsen: daemonen skriver til sine
    globaler som altid, og her løftes de over i delt tilstand så prompt-
    processen kan se dem.
    """
    from core.services.signal_surface_router import _get_router

    gemt: list[str] = []
    tomme: list[str] = []
    try:
        router = _get_router()
    except Exception as exc:
        logger.debug("felt_surface_store: kunne ikke hente router: %s", exc)
        return {"saved": [], "empty": [], "error": str(exc)}

    for navn in FELT_SURFACE_NAMES:
        fn = router.get(navn)
        if fn is None:
            continue
        try:
            payload = fn() or {}
        except Exception:
            continue
        if is_empty_payload(payload):
            tomme.append(navn)
            continue
        save_surface(navn, payload)
        gemt.append(navn)
    return {"saved": gemt, "empty": tomme}
