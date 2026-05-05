"""User-facing error messages for visible runs (Jarvis voice).

When the visible-model provider raises an exception, we previously sent
`str(exc)` straight to the chat surface. That leaked Python internals
(e.g. `<urlopen error [Errno 111] Connection refused>`) directly to the
user.

This module classifies common provider exceptions and returns a short
Danish message in Jarvis' voice — honest about what's broken without
exposing repr-text.
"""
from __future__ import annotations


def friendly_provider_error_message(exc: Exception) -> str:
    """Return a Jarvis-voice Danish message for a visible-model exception.

    Falls back to a generic but still in-voice message for unknown
    exception types. Never raises.
    """
    try:
        text = str(exc).lower()
    except Exception:
        text = ""

    if "connection refused" in text or "errno 111" in text:
        return (
            "Min LLM-backend svarer ikke lige nu — sandsynligvis er Ollama-laget "
            "nede. Prøv igen om et øjeblik."
        )

    # HTTP status codes must come before generic SSL/timeout branches because
    # "504 Gateway Timeout" contains both "504" and "timeout".
    if "502" in text or "bad gateway" in text:
        return (
            "Min LLM-backend returnerede 502 — typisk når modellen er ved at "
            "starte op igen eller er overbelastet. Prøv igen om et øjeblik."
        )

    if "503" in text or "service unavailable" in text:
        return (
            "Min LLM-backend er midlertidigt ude af drift (503). Prøv igen "
            "om et øjeblik."
        )

    if "504" in text or "gateway timeout" in text:
        return (
            "Min LLM-backend svarede ikke i tide (504 gateway timeout). "
            "Prøv igen om et øjeblik."
        )

    if "429" in text or "too many requests" in text or "rate limit" in text:
        return (
            "Jeg har ramt en rate-limit på backend'en. Vent et øjeblik og "
            "prøv igen."
        )

    # SSL must come before generic timeout — SSL handshake timeouts contain
    # "timed out" but are primarily SSL issues.
    if "ssl" in text and ("handshake" in text or "certificate" in text):
        return (
            "SSL-handshake til backend fejlede. Prøv igen om et øjeblik."
        )

    if isinstance(exc, TimeoutError) or "timed out" in text or "timeout" in text:
        return (
            "Backend hang for længe — jeg kunne ikke nå at svare i tide. "
            "Prøv igen om et øjeblik."
        )

    if "name or service not known" in text or "nodename nor servname" in text:
        return (
            "Kan ikke finde min backend-host — DNS eller netværk er nede. "
            "Prøv igen når forbindelsen er tilbage."
        )

    if "no such host" in text or "host unreachable" in text:
        return (
            "Min backend-host er ikke nåelig lige nu. Prøv igen om et øjeblik."
        )

    return (
        "Noget gik galt i min visible-lane. Tjek logs hvis det fortsætter — "
        "jeg er stadig her, bare uden mund lige nu."
    )
