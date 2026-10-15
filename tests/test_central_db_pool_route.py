"""Tests for /central/db-pool — owner-gated, proces-lokal pool-attribution.

Sporet fra 15/10-2026: de ~92 åbne forbindelser til jarvis.db kunne ikke henføres
til en tråd (/proc's fd-tabel er delt mellem tråde). Routen gør tællingen læsbar i
drift. Det der testes — gennem den ægte handler, som FastAPI selv kalder den:

  * owner-gaten propagerer (403 slipper ikke igennem)
  * routen læser DENNE proces' pool og lægger modparten ved siden af — kun fra api,
    for fra runtime ville modparten være os selv
  * en kastende tælling → {} frem for en fejl (self-safe)
  * `db_pool` er registreret som runtime-flade, så api kan nå runtime'ens tal over 8011
  * routen er faktisk registreret i app'en (ellers er alt ovenstående ligegyldigt)
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_db_pool as cdp


def test_owner_gate_propagates(monkeypatch):
    def deny() -> None:
        raise HTTPException(status_code=403, detail="Centralen er kun for owner")

    monkeypatch.setattr(cdp, "_require_owner", deny)
    with pytest.raises(HTTPException) as ei:
        cdp.get_db_pool()
    assert ei.value.status_code == 403


def test_api_laeser_begge_processer(monkeypatch):
    """Fra api skal svaret bære BÅDE api'ens egen pool og runtime'ens."""
    monkeypatch.setattr(cdp, "_require_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.central_xproc.process_role", lambda: "api"
    )
    monkeypatch.setattr(cdp, "_own_pool", lambda: {"pooled": 34, "orphaned": {}})
    monkeypatch.setattr(cdp, "_runtime_pool", lambda: {"pooled": 52, "orphaned": {}})

    ud = cdp.get_db_pool()
    assert ud["api"] == {"pooled": 34, "orphaned": {}}
    assert ud["runtime"] == {"pooled": 52, "orphaned": {}}
    assert "ts" in ud


def test_runtime_rolle_udelader_modparten(monkeypatch):
    """Kører routen i runtime-processen, er `proxy_or_local` lokal — så modparten
    må IKKE med, ellers udgiver vi ét tal for to."""
    monkeypatch.setattr(cdp, "_require_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.central_xproc.process_role", lambda: "runtime"
    )
    monkeypatch.setattr(cdp, "_own_pool", lambda: {"pooled": 52, "orphaned": {}})

    def _aldrig_kaldt():
        raise AssertionError("modparten blev spurgt fra runtime-processen")

    monkeypatch.setattr(cdp, "_runtime_pool", _aldrig_kaldt)

    ud = cdp.get_db_pool()
    assert ud["runtime"] == {"pooled": 52, "orphaned": {}}
    assert "api" not in ud


def test_self_safe_when_stats_raise(monkeypatch):
    """En kastende tælling må ikke vælte routen — {} for den nøgle."""
    import core.runtime.db_core as db_core

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(db_core, "pool_connection_stats", boom)
    assert cdp._own_pool() == {}


def test_db_pool_er_registreret_som_runtime_flade():
    """Uden denne kan api ikke nå runtime'ens tal over 8011."""
    from apps.api.jarvis_api.routes import internal_runtime_surface as irs

    assert "db_pool" in irs._BUILDERS
    assert callable(irs._BUILDERS["db_pool"])


def test_routen_er_registreret_i_appen():
    from apps.api.jarvis_api.app import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/central/db-pool" in paths
