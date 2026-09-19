"""Klassifikation af et afbrudt synligt run (core/services/visible_run_interruption)."""
import pytest

from core.services.visible_run_interruption import classify_visible_run_interruption as k
from core.services.visible_runs import _classify_visible_run_interruption as gammel_sti


@pytest.mark.parametrize("fejl", [
    "interrupted:followup-round-1-provider-error: HTTP 502",
    "provider-error: HTTP 400: context_length_exceeded: prompt too long",
    "HTTP 429 Too Many Requests",
    "rate limit exceeded",
])
def test_udbyder_fejl_er_provider_error_ikke_intern_fejl(fejl):
    # Før faldt de igennem til «runtime-error», og brugeren fik «Der opstod en
    # intern fejl» for en 502 eller et overløb hos udbyderen (19/9-2026).
    assert k(fejl) == {"interruption_reason": "provider_error", "interruption_source": "provider-stream"}


@pytest.mark.parametrize("fejl,forventet", [
    ("", "unknown"),
    ("approval timed out", "approval-wait-timeout"),
    ("worker died", "process-restart"),
    ("unhandled exception in loop", "runtime-crash"),
    ("provider request timed out", "provider-timeout"),   # timeout vinder over provider
    ("client closed the stream", "client-disconnect"),
    ("user cancel", "user-interrupted"),
    ("bruger afbryd", "user-interrupted"),
    ("noget helt andet", "runtime-error"),
])
def test_de_gamle_grene_er_uaendrede(fejl, forventet):
    assert k(fejl)["interruption_reason"] == forventet


def test_visible_runs_reeksporterer_den_samme_funktion():
    # Boy Scout-udskillelsen må ikke brække eksisterende importer.
    assert gammel_sti is k


def test_envelopen_kender_den_nye_grund():
    from core.services import central_error_envelope as cee
    env = cee.for_interruption(reason="provider_error", run_id="r", detail="HTTP 502")
    assert "udbyder" in env.to_client_event()["message"].lower()
