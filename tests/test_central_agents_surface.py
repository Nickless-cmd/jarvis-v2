"""Roster-wiring for build_agents_surface (/central/agents live route).

build_agents_surface() (served by routes/central.py::central_agents — registered
before the shadowed central_absorb_routes.get_agents) must now expose the full
model roster from core.services.agents so the CLI can consume it, WITHOUT dropping
any pre-existing key. Roster sourcing is self-safe: a failure → roster == [].
"""
from __future__ import annotations

import core.services.agents as agents_mod
from core.services.central_agents_surface import build_agents_surface

_ROSTER = [
    {"model_key": "prov/mA", "provider": "prov", "model": "mA", "status": "active",
     "last_run_at": "2026-07-16T00:00:00+00:00", "tokens_in": 10, "tokens_out": 5,
     "cost_usd": 0.0, "current_activity": "agent: ok", "tool_calls": 1, "role": "agent"},
    {"model_key": "prov/mB", "provider": "prov", "model": "mB", "status": "inactive",
     "last_run_at": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
     "current_activity": "", "tool_calls": 0, "role": ""},
]

# Keys build_agents_surface exposed BEFORE roster was added — all must survive.
_PREEXISTING_KEYS = {
    "windows", "lane_breakdown", "breakdown_window", "dispatches", "recent",
    "note", "generated_at",
}


def test_roster_present_and_backward_compatible(monkeypatch):
    monkeypatch.setattr(
        agents_mod, "agents_summary",
        lambda *a, **k: {"roster": _ROSTER}, raising=True,
    )
    body = build_agents_surface(window="today")

    # New key: the roster is exposed verbatim.
    assert isinstance(body.get("roster"), list)
    assert body["roster"] == _ROSTER

    # Backward compatible: every pre-existing key still present.
    for key in _PREEXISTING_KEYS:
        assert key in body, f"pre-existing key {key!r} was dropped"


def test_roster_self_safe_on_error(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("roster source down")
    monkeypatch.setattr(agents_mod, "agents_summary", _boom, raising=True)

    body = build_agents_surface(window="today")
    # A roster failure must never break the surface — roster falls back to [].
    assert body.get("roster") == []
    for key in _PREEXISTING_KEYS:
        assert key in body
