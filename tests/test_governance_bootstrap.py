"""Kontakten skal virke på begge døre.

decision_review blev slået fra som daemon 11/6-2026 pga. selv-bias. Men den
SAMME funktion kørte videre som dagligt job herfra, uden om daemon-gaten:
registret sagde DEAKTIVERET mens den skrev 30.867 domme over tre måneder.
Testen holder fast i at jobbet nu spørger daemon_manager først.
"""

from __future__ import annotations

import pytest

from core.services import governance_bootstrap as GB


def _hent_handler(monkeypatch, job_type: str):
    """Kør registreringen med en opsamlende register_handler og find én handler."""
    from core.services import jobs_engine

    opsamlet: dict = {}
    monkeypatch.setattr(
        jobs_engine, "register_handler",
        lambda kind, fn: opsamlet.__setitem__(kind, fn),
    )
    GB.ensure_default_job_handlers()
    assert job_type in opsamlet, "%s blev ikke registreret" % job_type
    return opsamlet[job_type]


def test_jobbet_respekterer_daemon_kontakten(monkeypatch):
    from core.services import daemon_manager as dm

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(dm, "is_enabled", lambda navn: False)
    monkeypatch.setattr(
        "core.services.decision_review_prompter.review_pending_decisions",
        lambda **kw: pytest.fail("review må ikke køre når daemonen er slået fra"),
    )

    ud = handler({})
    assert ud["status"] == "ok"
    assert ud["result"]["status"] == "disabled"


def test_jobbet_koerer_naar_daemonen_er_taendt(monkeypatch):
    from core.services import daemon_manager as dm
    from core.services import decision_review_prompter as P

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(dm, "is_enabled", lambda navn: True)
    monkeypatch.setattr(P, "review_pending_decisions", lambda **kw: {"status": "ok", "reviewed": 2})

    ud = handler({})
    assert ud["result"]["reviewed"] == 2


def test_ulaeselig_gate_stopper_ikke_jobbet(monkeypatch):
    """Fail-open som resten af runtimen: kan gaten ikke læses, kører vi videre."""
    from core.services import daemon_manager as dm
    from core.services import decision_review_prompter as P

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(
        dm, "is_enabled",
        lambda navn: (_ for _ in ()).throw(RuntimeError("registret utilgængeligt")),
    )
    monkeypatch.setattr(P, "review_pending_decisions", lambda **kw: {"status": "ok", "reviewed": 1})

    ud = handler({})
    assert ud["result"]["reviewed"] == 1
