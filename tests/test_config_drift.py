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


def test_declared_port_reads_disk_not_memory(monkeypatch, tmp_path):
    # Bjørns bug: in-memory har gammel port, men disk-filen er rettet → nerven SKAL se disken
    import json as _json
    f = tmp_path / "runtime.json"
    f.write_text(_json.dumps({"port": 8011}), encoding="utf-8")
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", f)
    assert cd._declared_port() == 8011


def test_observe_auto_resolves_when_no_drift(monkeypatch):
    # filen er korrekt (ingen drift) → hængende config_drift-flag skal auto-resolves
    monkeypatch.setattr(cd, "_declared_port", lambda: 8080)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    resolved = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.resolve_central_incidents",
                        lambda **k: resolved.update(k) or 1)
    rep = cd.observe_config_drift()
    assert rep["drift"] is False
    assert resolved.get("nerve") == "config_drift"


def test_observe_dedups_repeated_drift(monkeypatch):
    # samme drift-besked allerede uløst → opret IKKE en ny (rate-limit)
    monkeypatch.setattr(cd, "_declared_port", lambda: 8010)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    monkeypatch.setattr("core.runtime.db_central_incidents.has_unresolved_message",
                        lambda **k: True)
    calls = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: calls.append(k))
    rep = cd.observe_config_drift()
    assert rep["drift"] is True
    assert calls == []  # dublet undertrykt


def test_catalog_has_config_drift():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("system")]
    assert "config_drift" in names


def test_transient_stall_is_not_drift(monkeypatch):
    """Regression for incident 15372 (27/10-2026): proben fik ikke svar fra den deklarerede
    port inden 2 s, men porten svarede igen få sekunder senere — runtime.json sagde hele
    tiden 8011. En transient stall (last, DB-lås, GIL) er IKKE en config-fejl.

    Uden genforsøget blev der flagget drift, og med daglig cooldown holdt det falske flag
    systemet rødt i op til 24 timer."""
    # 9999 er med vilje IKKE i _ALT_PORTS: så rammes den kun af den hurtige vej og af
    # genforsøget — ikke af kandidat-løkken. Ellers kan testen bestå på et tilfælde.
    monkeypatch.setattr(cd, "_declared_port", lambda: 9999)
    monkeypatch.setattr(cd, "_RETRY_PAUSE_S", 0)

    # Kald 1 (hurtig vej) og kald 2 (kandidat-løkken) fejler; kald 3 (genforsøget) svarer.
    kø = [False, False, True]

    def _api(p):
        if int(p) == 9999:
            return kø.pop(0) if kø else True
        return int(p) == 8080  # API'et svarer på 8080 hele tiden

    monkeypatch.setattr(cd, "_api_responds", _api)
    rep = cd.check_port_drift()
    assert rep["drift"] is False, f"en stall må ikke læses som drift: {rep}"
    assert rep["declared_port"] == 9999
    assert rep["actual_port"] == 9999


def test_real_drift_survives_the_retry(monkeypatch):
    """Genforsøget må ikke gøre nerven blind: en ÆGTE mismatch skal stadig flagges efter
    både første probe og genforsøg."""
    monkeypatch.setattr(cd, "_declared_port", lambda: 8010)
    monkeypatch.setattr(cd, "_RETRY_PAUSE_S", 0)
    monkeypatch.setattr(cd, "_api_responds", lambda p: p == 8080)
    rep = cd.check_port_drift()
    assert rep["drift"] is True
    assert rep["declared_port"] == 8010
    assert rep["actual_port"] == 8080


def test_healthy_state_costs_one_probe(monkeypatch):
    """Sund tilstand: den deklarerede port svarer → alternativerne probes slet ikke.
    (Før: fem prober hver gang, op til 10 s i værste fald.)"""
    monkeypatch.setattr(cd, "_declared_port", lambda: 8011)
    probede = []

    def _api(p):
        probede.append(p)
        return p == 8011

    monkeypatch.setattr(cd, "_api_responds", _api)
    rep = cd.check_port_drift()
    assert rep["drift"] is False
    assert probede == [8011], f"kun den deklarerede port skal probes, fik {probede}"
