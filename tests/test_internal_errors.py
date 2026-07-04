"""Tests for the canonical error reporter — /api/internal/errors/report (Fase 0).

Thin, loopback-only, FAIL-OPEN adapter over existing Central machinery. Pins:
valid → 202 + correlation_id; missing field → 422; unknown kind → coerced (202);
non-local → 403; proxy-forwarded → 403; internal failure → still 202; severity
escalation → incident with correct mapping.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


def _app() -> FastAPI:
    from apps.api.jarvis_api.routes.internal_errors import router
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def local_client() -> TestClient:
    return TestClient(_app(), client=("127.0.0.1", 5000))


@pytest.fixture
def remote_client() -> TestClient:
    return TestClient(_app())  # default host "testclient" = non-local


def _valid_payload(**over) -> dict:
    payload = {
        "kind": "model.rate_limited", "severity": "warning", "recoverable": "retry",
        "message": "provider 429 mid-turn",
        "origin": {"file": "core/foo.py", "function": "do_thing"},
        "scope": "run", "session_id": "sess-1", "run_id": "run-abc",
        "context": {"attempt": 3}, "source": "runtime",
    }
    payload.update(over)
    return payload


def test_valid_report_returns_202_with_correlation_id(local_client):
    r = local_client.post("/api/internal/errors/report", json=_valid_payload())
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "accepted"
    assert body["correlation_id"] == "run-abc"


def test_missing_required_field_is_rejected(local_client):
    payload = _valid_payload()
    del payload["message"]
    r = local_client.post("/api/internal/errors/report", json=payload)
    assert r.status_code in (400, 422)


def test_unknown_kind_is_coerced_not_rejected(local_client, monkeypatch):
    captured = {}
    monkeypatch.setattr("core.services.central_anomaly.record_anomaly",
                        lambda **kw: captured.update(kw))
    r = local_client.post("/api/internal/errors/report", json=_valid_payload(kind=""))
    assert r.status_code == 202
    assert captured.get("exc_type") == "ui.unknown"


def test_non_localhost_is_rejected(remote_client):
    r = remote_client.post("/api/internal/errors/report", json=_valid_payload())
    assert r.status_code == 403


def test_proxy_forwarded_is_rejected(local_client):
    r = local_client.post("/api/internal/errors/report", json=_valid_payload(),
                          headers={"x-forwarded-for": "1.2.3.4"})
    assert r.status_code == 403


def test_internal_failure_is_fail_open(local_client, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("central down")
    monkeypatch.setattr("core.services.central_anomaly.record_anomaly", _boom)
    monkeypatch.setattr("core.services.central_error_envelope.envelope_from_kind", _boom)
    r = local_client.post("/api/internal/errors/report", json=_valid_payload())
    assert r.status_code == 202 and r.json()["status"] == "accepted"


def test_error_severity_escalates_to_incident(local_client, monkeypatch):
    recorded = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **kw: recorded.update(kw) or 1)
    monkeypatch.setattr("core.services.central_anomaly.record_anomaly", lambda **kw: None)
    # kind server.error → KIND_MAP severity 'error' → eskalerer
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="server.error", severity="error"))
    assert r.status_code == 202
    assert recorded["nerve"] == "canonical_error" and recorded["severity"] == "error"


def test_critical_maps_to_severe_incident(local_client, monkeypatch):
    recorded = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **kw: recorded.update(kw) or 1)
    monkeypatch.setattr("core.services.central_anomaly.record_anomaly", lambda **kw: None)
    # kind infra.host_down → KIND_MAP severity 'critical' → incident 'severe'
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="infra.host_down", severity="critical"))
    assert r.status_code == 202 and recorded["severity"] == "severe"


# ── Fase 1: healer-invokation (kun auto-recoverable kinds, fail-open) ────────

def test_auto_recoverable_kind_triggers_heal(local_client, monkeypatch):
    import core.services.error_healers as eh
    calls = []
    monkeypatch.setattr(eh, "healers_enabled", lambda: True)
    monkeypatch.setattr(eh, "heal_error", lambda kind, **kw: calls.append(kind))
    # central.daemon_dead → KIND_MAP recoverable == "auto"
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="central.daemon_dead", severity="error"))
    assert r.status_code == 202
    assert calls == ["central.daemon_dead"]


def test_non_auto_kind_does_not_trigger_heal(local_client, monkeypatch):
    import core.services.error_healers as eh
    calls = []
    monkeypatch.setattr(eh, "healers_enabled", lambda: True)
    monkeypatch.setattr(eh, "heal_error", lambda kind, **kw: calls.append(kind))
    # network.timeout → recoverable == "retry" (ikke auto) → healer røres ikke
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="network.timeout", severity="warning"))
    assert r.status_code == 202 and calls == []


def test_heal_raising_still_returns_202(local_client, monkeypatch):
    import core.services.error_healers as eh
    def _boom(*a, **k):
        raise RuntimeError("healer blew up")
    monkeypatch.setattr(eh, "healers_enabled", lambda: True)
    monkeypatch.setattr(eh, "heal_error", _boom)
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="central.daemon_dead", severity="error"))
    assert r.status_code == 202  # fail-open: healing-fejl brækker aldrig ingest


def test_healers_disabled_skips_heal(local_client, monkeypatch):
    import core.services.error_healers as eh
    calls = []
    monkeypatch.setattr(eh, "healers_enabled", lambda: False)
    monkeypatch.setattr(eh, "heal_error", lambda kind, **kw: calls.append(kind))
    r = local_client.post("/api/internal/errors/report",
                          json=_valid_payload(kind="central.daemon_dead", severity="error"))
    assert r.status_code == 202 and calls == []
