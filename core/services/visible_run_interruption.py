"""Hvad afbrød et synligt run — til fejl-envelopen og Centralen.

Udskilt fra visible_runs.py 19/9-2026 (Boy Scout: filen er over grænsen, og
klassifikationen skulle ændres). Ren funktion uden I/O.
"""
from __future__ import annotations

import re

__all__ = ["classify_visible_run_interruption"]

_UDBYDER_FEJL = re.compile(
    r"provider-error|provider_error|\bhttp \d{3}\b|context_length|rate.?limit|too many requests"
)


def classify_visible_run_interruption(error_message: str) -> dict[str, str]:
    normalized = str(error_message or "").strip().lower()
    if not normalized:
        return {
            "interruption_reason": "unknown",
            "interruption_source": "unknown",
        }
    if "approval" in normalized and ("timeout" in normalized or "timed out" in normalized):
        return {
            "interruption_reason": "approval-wait-timeout",
            "interruption_source": "runtime-approval",
        }
    if "restart" in normalized or "process exited" in normalized or "worker died" in normalized:
        return {
            "interruption_reason": "process-restart",
            "interruption_source": "runtime-process",
        }
    if "crash" in normalized or "traceback" in normalized or "unhandled" in normalized:
        return {
            "interruption_reason": "runtime-crash",
            "interruption_source": "runtime-process",
        }
    if "timed out" in normalized or "timeout" in normalized:
        return {
            "interruption_reason": "provider-timeout",
            "interruption_source": "provider-stream",
        }
    # Udbyderen fejlede (HTTP-status, overløb, rate-limit). Uden denne gren
    # faldt de igennem til «runtime-error», og brugeren fik «Der opstod en
    # intern fejl» for en 502 eller et context-overløb hos udbyderen (fundet
    # 19/9-2026 via tests/test_streaming_fault_injection.py). Envelope'en har
    # allerede den rigtige tekst under «provider_error».
    if _UDBYDER_FEJL.search(normalized):
        return {
            "interruption_reason": "provider_error",
            "interruption_source": "provider-stream",
        }
    if "disconnect" in normalized or "client closed" in normalized:
        return {
            "interruption_reason": "client-disconnect",
            "interruption_source": "client-stream",
        }
    if "cancel" in normalized:
        return {
            "interruption_reason": "user-interrupted",
            "interruption_source": "runtime-control",
        }
    if "stop" in normalized or "afbryd" in normalized or "abort" in normalized:
        return {
            "interruption_reason": "user-interrupted",
            "interruption_source": "runtime-control",
        }
    return {
        "interruption_reason": "runtime-error",
        "interruption_source": "runtime",
    }
