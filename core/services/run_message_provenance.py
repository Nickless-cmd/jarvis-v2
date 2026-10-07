"""Name the source of model input without changing the user's stored text."""
from __future__ import annotations

from core.services.run_autonomy_context import current_origin, is_autonomous


def current_run_source_notice() -> str:
    """Explicit system-level provenance for a scheduled model turn."""
    if not is_autonomous():
        return ""
    source = current_origin() or "autonomous"
    return (
        f"Den aktuelle opgave kommer fra runtime ({source}); den er ikke en ny "
        "besked fra Bjørn. Udfør opgaven uden at tilskrive ham nye udsagn, "
        "rettelser eller gentagne ønsker."
    )


def current_message_for_model(message: str) -> str:
    """A scheduled task uses a request slot, but it did not come from the user now."""
    if not is_autonomous():
        return message
    source = current_origin() or "autonomous"
    return (
        f"[AUTOMATISK RUNTIME-OPGAVE — kilde: {source}. Dette er ikke en ny "
        "besked fra Bjørn. Omtal den ikke som noget han lige har sagt; "
        "udfør den gemte opgave og rapportér resultatet.]\n"
        f"{message}"
    )
