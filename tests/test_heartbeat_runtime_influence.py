"""Tests for heartbeat_runtime_influence.

Fokus (2026-07-14): event_trigger_shadow-meteret er FLYTTET ud af _build_influence_trace
(som kun bygges på den fulde aktivitets-drevne heartbeat-sti → tavs hele natten) og over i
den ubetingede daemon-sektion i heartbeat_runtime. Denne test låser flytningen fast: influence-
trace-byggeren må IKKE længere selv tikke shadow-meteret, ellers dobbelt-tikker vi (og gør data
aktivitets-skævt igen)."""
from __future__ import annotations

import inspect

from core.services import heartbeat_runtime_influence as influence


def test_build_influence_trace_exists_and_callable():
    assert callable(influence._build_influence_trace)


def test_influence_trace_no_longer_ticks_event_trigger_shadow():
    """Regression: event_trigger_shadow-tikket blev flyttet til den ubetingede daemon-sektion.
    _build_influence_trace må ikke kalde tick_event_trigger_shadow (ellers er tikket igen
    aktivitets-gated + potentielt dobbelt)."""
    src = inspect.getsource(influence._build_influence_trace)
    assert "tick_event_trigger_shadow" not in src, (
        "event_trigger_shadow-tikket hører hjemme i heartbeat_runtime's ubetingede "
        "daemon-sektion, ikke i den aktivitets-gatede _build_influence_trace"
    )
