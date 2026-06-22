"""Tests for config-drift-nerven (§7) — port declared↔runtime mismatch (8010/8011-buggen).

Verificerer at drift detekteres når API'en svarer på en ANDEN port end den deklarerede, at
ingen drift når den deklarerede svarer, og at observe+incident er self-safe.
"""
from __future__ import annotations

from core.services import config_drift as cd


def test_no_drift_when_declared_responds(monkeypatch):
    monkeypatch.setattr(cd, "_declared_port", lambda: 8080)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    rep = cd.check_port_drift()
    assert rep["drift"] is False
    assert rep["actual_port"] == 8080


def test_drift_when_api_on_other_port(monkeypatch):
    # settings siger 8010, men API svarer kun på 8080 → DRIFT (præcis Bjørns bug)
    monkeypatch.setattr(cd, "_declared_port", lambda: 8010)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    rep = cd.check_port_drift()
    assert rep["drift"] is True
    assert rep["declared_port"] == 8010
    assert rep["actual_port"] == 8080


def test_no_drift_when_nothing_reachable(monkeypatch):
    # API helt nede → ingen drift-konklusion (kan ikke afgøre; ikke en config-fejl)
    monkeypatch.setattr(cd, "_declared_port", lambda: 8010)
    monkeypatch.setattr(cd, "_api_responds", lambda p: False)
    rep = cd.check_port_drift()
    assert rep["drift"] is False
    assert rep["actual_port"] is None


def test_observe_config_drift_flags_incident(monkeypatch):
    monkeypatch.setattr(cd, "_declared_port", lambda: 8010)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    flagged = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: flagged.update(k))
    monkeypatch.setattr("core.services.ntfy_gateway.send_notification", lambda *a, **k: None)
    rep = cd.observe_config_drift()
    assert rep["drift"] is True
    assert flagged.get("nerve") == "config_drift"
    assert flagged.get("severity") == "severe"


def test_observe_self_safe_no_drift(monkeypatch):
    monkeypatch.setattr(cd, "_declared_port", lambda: 8080)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    rep = cd.observe_config_drift()  # må ikke kaste, ingen incident
    assert rep["drift"] is False


def test_catalog_has_config_drift():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("system")]
    assert "config_drift" in names
