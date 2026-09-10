"""Tests for maintenance/health cadence-producers.

Fokus: hygiene-produceren der lukker kognitive governance-hændelser (10. sep 2026).
Den blev til fordi 931 uløste `gate_enforce`-incidents hobede sig op og fyldte både
panelet og `root_causes()` med governance-støj. Husets klassiske fejl er netop den:
koden skrives, og ingen kalder den — derfor tjekker disse tests både registreringen
OG at produceren faktisk kalder sweepet.
"""
from __future__ import annotations

import inspect

import core.services.internal_cadence_maintenance as M


def _registered() -> dict:
    """Kør registreringen med en indsamler i stedet for den rigtige registry."""
    seen: dict = {}
    M.register_maintenance_producers(lambda spec: seen.__setitem__(spec.name, spec))
    return seen


def test_incident_retention_er_registreret_som_producer():
    """Uden en kadence-producer vokser governance-hændelserne ubegrænset."""
    assert "central_incident_retention" in _registered()


def test_incident_retention_koerer_hver_time():
    assert _registered()["central_incident_retention"].cooldown_minutes == 60


def test_incident_retention_kalder_udloebs_funktionen():
    """Produceren skal kalde `expire_gate_enforce_incidents` — ellers er den bygget
    og aldrig kørt. Vinduet er 2 timer: kadencen kører hver time, og en hændelse skal
    kunne ses i panelet i mere end én cyklus før den lukkes."""
    src = inspect.getsource(_registered()["central_incident_retention"].run_fn)
    assert "expire_gate_enforce_incidents" in src
    assert "older_than_hours=2.0" in src


def test_incident_retention_lukker_gamle_governance_incidents(isolated_runtime):
    """Ende-til-ende: en gammel kognitiv governance-hændelse lukkes af produceren."""
    from datetime import UTC, datetime, timedelta

    from core.runtime.db_central_incidents import (
        list_central_incidents, record_central_incident,
    )
    from core.runtime.db_core import connect

    rid = record_central_incident(cluster="proactivity", nerve="verification",
                                  kind="gate_enforce", severity="info", message="gammel")
    old_ts = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE central_incidents SET ts = ? WHERE id = ?", (old_ts, rid))

    out = _registered()["central_incident_retention"].run_fn(trigger="test")
    assert out["status"] == "ok" and out["expired"] == 1
    assert all(r["id"] != rid for r in list_central_incidents(unresolved_only=True))
