"""Keep real mid-flight user steers distinct from runtime turn notices."""
from __future__ import annotations

from typing import Any

from core.services.visible_followup_events import ToolExchange


_STOP_WORDS = frozenset({"stop", "stop.", "cancel", "afbryd", "abort", "stop nu"})


def append_real_user_steers(
    exchanges: list[ToolExchange], steers: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    """Læg ægte klient-styringer i HISTORIKKEN — ikke i halen.

    Bjørn 7/10-2026: «den skal bar ikk sende den samme i alle runder.. kun til
    næste runde». Halen genopbygges hver runde, så en styring dér blev gensendt
    som en frisk brugerbesked i hver eneste runde — modellen svarede den 12
    gange for én besked.

    Historikken vokser append-only. Her staar styringen ÉN gang, i sin naturlige
    position mellem runderne, og bliver en del af det cachelagrede praefiks fra
    naeste runde. DeepSeek-praefiks-cachen roeres derfor ikke — i modsaetning til
    halen, som genopbygges hver runde og altid er et cache-miss.

    Stopper ved en afbrydelses-styring: resten maa ikke naa frem.
    """
    accepted: list[dict[str, Any]] = []
    for steer in steers:
        content = str(steer.get("content") or "").strip()
        if not content:
            continue
        exchanges.append(
            ToolExchange(text="", tool_calls=[], results=[], user_message=content)
        )
        accepted.append({**steer, "content": content})
        if content.lower() in _STOP_WORDS:
            return accepted, True
    return accepted, False
