"""Påmindelsen om modne skygge-eksperimenter skal selv blive kaldt.

`shadow_experiment_registry` findes ordret fordi «BÅDE Bjørn og Claude glemmer
at komme tilbage og evaluere dem». Målt 18/9-2026 var modulet selv glemt:
`tick_shadow_review_reminder` havde NUL kaldere, så fire eksperimenter stod
modne i 65-71 dage uden at én påmindelse fyrede — 0 shadow_review-events i
basen.

Det er samme fejlklasse som resten af dagen: systemet knækker ikke, det tier.
"""
from __future__ import annotations

import inspect


def test_hjerteslaget_kalder_paamindelsen():
    from core.services import heartbeat_runtime

    kilde = inspect.getsource(heartbeat_runtime)
    assert "tick_shadow_review_reminder" in kilde, (
        "paamindelsen har ingen kalder — praecis den tilstand modulet findes "
        "for at forhindre")
    assert "register_known_shadows" in kilde


def test_registret_kan_pege_paa_de_modne(monkeypatch):
    from core.services import shadow_experiment_registry as reg

    data = {
        "gammelt": {"name": "gammelt", "started_ts": 0.0,
                    "review_after_hours": 24.0, "reviewed": False},
        "reviewet": {"name": "reviewet", "started_ts": 0.0,
                     "review_after_hours": 24.0, "reviewed": True},
        "ungt": {"name": "ungt", "started_ts": 10_000_000.0,
                 "review_after_hours": 99999.0, "reviewed": False},
    }
    monkeypatch.setattr(reg, "_load", lambda: {k: dict(v) for k, v in data.items()})
    modne = [x["name"] for x in reg.ready_for_review(now_ts=10_000_100.0)]
    assert modne == ["gammelt"], modne
