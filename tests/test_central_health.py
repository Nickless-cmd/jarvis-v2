"""Tests for Central self-helbred (§1) — central_health + Central.self_diagnose.

Verificerer at self_diagnose prober decide+observe korrekt, at open_nerves rapporterer
trippede breakers, at degraded eskalerer (ntfy + incident), og at alt er self-safe.
"""
from __future__ import annotations


def test_self_diagnose_healthy():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    rep = c.self_diagnose()
    assert rep["decide_ok"] is True
    assert rep["observe_ok"] is True
    assert rep["degraded"] is False
    assert rep["open_breakers"] == []


def test_open_nerves_reports_tripped_breaker():
    from core.services.central_switches import CircuitBreaker
    b = CircuitBreaker(threshold=2)
    assert b.open_nerves() == []
    b.record("flaky", ok=False)
    b.record("flaky", ok=False)  # 2 ≥ threshold → åben
    assert "flaky" in b.open_nerves()
    b.record("flaky", ok=True)   # succes nulstiller
    assert b.open_nerves() == []


def test_check_returns_unresolved_severe(monkeypatch):
    from core.services import central_health as ch
    monkeypatch.setattr("core.runtime.db_central_incidents.count_unresolved", lambda **k: 7)
    rep = ch.check()
    assert rep["unresolved_severe"] == 7


def test_escalation_reasons():
    from core.services import central_health as ch
    assert ch._escalation_reasons({"degraded": False, "open_breakers": [], "unresolved_severe": 0}) == []
    r = ch._escalation_reasons({"degraded": True, "open_breakers": ["auth"], "unresolved_severe": 9})
    assert len(r) == 3


def test_observe_and_escalate_self_safe(monkeypatch):
    from core.services import central_health as ch
    # tving degraded → eskalering må ramme ntfy + incident UDEN at kaste
    monkeypatch.setattr(ch, "check", lambda: {"degraded": True, "open_breakers": ["x"],
                                              "unresolved_severe": 9, "decide_ok": False,
                                              "observe_ok": True})
    sent = {}
    monkeypatch.setattr("core.services.ntfy_gateway.send_notification",
                        lambda msg, **k: sent.update({"msg": msg}))
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: None)
    monkeypatch.setattr("core.runtime.db_central_incidents.has_open_incident",
                        lambda **k: False)
    rep = ch.observe_and_escalate()
    assert rep["degraded"] is True
    assert "self-helbred" in sent.get("msg", "")


def test_check_excludes_own_nerve_from_severe_count(monkeypatch):
    # self-helbreds-tælleren må IKKE tælle sine egne self_health-incidents → bryder loopet
    from core.services import central_health as ch
    seen = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.count_unresolved",
                        lambda **k: seen.update(k) or 0)
    ch.check()
    assert seen.get("exclude_nerve") == "central_health"


def test_escalate_dedups_when_alarm_already_open(monkeypatch):
    # alarm allerede åben → opret IKKE ny incident + ntfy (ingen stabling/spam)
    from core.services import central_health as ch
    monkeypatch.setattr(ch, "check", lambda: {"degraded": True, "open_breakers": ["x"],
                                              "unresolved_severe": 9, "decide_ok": False,
                                              "observe_ok": True})
    monkeypatch.setattr("core.runtime.db_central_incidents.has_open_incident",
                        lambda **k: True)
    calls = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: calls.append(k))
    monkeypatch.setattr("core.services.ntfy_gateway.send_notification",
                        lambda *a, **k: calls.append("ntfy"))
    ch.observe_and_escalate()
    assert calls == []  # dedup undertrykte både incident og ntfy


def test_escalate_auto_resolves_when_healthy(monkeypatch):
    # ingen reasons (rask) → luk hængende self_health-flag
    from core.services import central_health as ch
    monkeypatch.setattr(ch, "check", lambda: {"degraded": False, "open_breakers": [],
                                              "unresolved_severe": 0, "decide_ok": True,
                                              "observe_ok": True})
    resolved = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.resolve_central_incidents",
                        lambda **k: resolved.update(k) or 1)
    ch.observe_and_escalate()
    assert resolved.get("nerve") == "central_health"


def test_catalog_has_central_health():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("system")]
    assert "central_health" in names
