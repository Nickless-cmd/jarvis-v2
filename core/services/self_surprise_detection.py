"""Self-Surprise Detection — "Huh, det havde jeg ikke forventet af mig selv."

Forventning vs. faktisk udfald → modsigelse = overraskelse.

**To rettelser, to halvdele af samme bug.**

1. *17. aug:* kaldsstedet sendte en hardkodet ``0.6`` ind i gaten ``> 0.6``, så negativ
   overraskelse var matematisk umulig. 19.698 af 19.698 var positive.
2. *18. aug (denne):* rettelsen efterlod en to-værdi-konstant uden død zone. ``weak → 0.5``
   betød reelt *"jeg forventer at fejle"*, og da 98% af alle runs lykkes, blev hver succes
   til en "overraskelse" — 54 nye på ét døgn, stadig nul negative. Forventningen bæres nu
   af modellens *empiriske* succesrate, og der er en død zone hvor intet kan overraske.

Se `self_surprise_expectation` for forventnings-modellen og begrundelsen for zonen.
"""
from __future__ import annotations

from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_cognitive_self_surprise, list_cognitive_self_surprises
from core.services.self_surprise_expectation import (
    classify_outcome,
    expectation_verdict,
    expected_success_rate,
    is_legacy_degenerate,
)

_NARRATIVE = {
    "positive": "Overraskende succes i {d} — forventede at fejle men klarede det.",
    "negative": "Uventet fejl i {d} — var sikker men tog fejl.",
}


def detect_self_surprise(
    *,
    actual_outcome: str,
    expected_confidence: float | None = None,
    model: str = "",
    domain: str = "",
    run_id: str = "",
) -> dict[str, object] | None:
    """Registrér en overraskelse — eller ``None``, hvilket er det normale.

    ``expected_confidence`` er valgfri: udelades den, udleder detektoren selv en
    kalibreret forventning fra ``model``'s egen historik. Kaldere skal foretrække
    at sende ``model`` og lade forventningen være ægte; den eksplicitte parameter
    findes for tests og for kaldere der allerede *har* en målt forventning.
    """
    outcome_kind = classify_outcome(actual_outcome)
    expected = (
        float(expected_confidence)
        if expected_confidence is not None
        else expected_success_rate(model)
    )

    surprise_type = expectation_verdict(expected, outcome_kind)
    if surprise_type is None:
        return None  # Ingen sikker forventning blev modsagt → ingen overraskelse.

    surprise_id = f"surp-{uuid4().hex[:8]}"
    result = insert_cognitive_self_surprise(
        surprise_id=surprise_id,
        surprise_type=surprise_type,
        narrative=_NARRATIVE[surprise_type].format(d=domain or "ukendt domæne"),
        expected_confidence=expected,
        actual_outcome=actual_outcome,
        domain=domain,
        run_id=run_id,
    )
    event_bus.publish(
        "cognitive_state.self_surprise", {"type": surprise_type, "domain": domain}
    )
    return result


def build_self_surprise_surface() -> dict[str, object]:
    """Overfladen Jarvis faktisk kan se.

    Rækker fra den defekte detektor filtreres bort på læsesiden — de er ikke slettet,
    men de må ikke fremstå som hans nuværende selv-overraskelses-tilstand. Uden det
    filter ville de 10 nyeste altid være gammel støj, fordi ægte overraskelser nu er
    sjældne (som de skal være).
    """
    raw = list_cognitive_self_surprises(limit=40)
    items = [
        i for i in raw if not is_legacy_degenerate(i.get("expected_confidence", 0.0))
    ][:10]
    suppressed = len(raw) - len([i for i in raw if not is_legacy_degenerate(i.get("expected_confidence", 0.0))])

    positive = sum(1 for i in items if i.get("surprise_type") == "positive")
    negative = len(items) - positive
    summary = (
        f"{len(items)} overraskelser ({positive}+, {negative}-)"
        if items
        else "Ingen overraskelser endnu"
    )
    return {
        "active": bool(items),
        "items": items,
        "positive_count": positive,
        "negative_count": negative,
        "legacy_suppressed": suppressed,
        "summary": summary,
    }
