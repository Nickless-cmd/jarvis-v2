from __future__ import annotations

from datetime import UTC, datetime


def test_diagnostics_detects_starvation_and_stale_quota(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 0,
        "saved_at": "2026-09-18T11:59:00+00:00",
        "slots": [{
            "slot_id": "groq::llama::default", "provider": "groq",
            "auth_profile": "default", "egress": "home", "weight": 0,
            "status": "cooldown", "breaker_level": 0,
            "consecutive_failures": 1,
        }],
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {
        "windows": [{
            "provider": "groq", "auth_profile": "default", "period": "month",
            "unit": "tokens", "limit": 1000, "remaining": 500, "used": 500,
            "observed_usage": 500, "freshness": "stale", "source": "configured",
        }],
    })
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {
        "udbydere": [{"provider": "groq", "credentials_ready": True}],
    })
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    findings = diagnostics.diagnose_cheap_lane(
        now=datetime(2026, 9, 18, 12, tzinfo=UTC)
    )["findings"]
    codes = {finding["code"] for finding in findings}

    assert {"no-eligible-slot", "provider-starvation", "quota-stale"} <= codes
    assert all("severity" in finding and "evidence" in finding for finding in findings)


def test_diagnostics_detects_concentration_credentials_and_exhaustion(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 2,
        "saved_at": "2026-09-18T12:00:00+00:00",
        "slots": [
            {"slot_id": "a", "provider": "groq", "auth_profile": "default",
             "egress": "home", "weight": 1, "status": "healthy",
             "breaker_level": 0, "consecutive_failures": 0},
            {"slot_id": "b", "provider": "groq", "auth_profile": "default",
             "egress": "home", "weight": 1, "status": "healthy",
             "breaker_level": 0, "consecutive_failures": 0},
        ],
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {
        "windows": [{
            "provider": "groq", "auth_profile": "default", "period": "day",
            "unit": "requests", "limit": 100, "remaining": 4, "used": 96,
            "observed_usage": 96, "freshness": "fresh", "source": "provider",
        }],
    })
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {
        "udbydere": [{"provider": "mistral", "credentials_ready": False}],
    })
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    codes = {
        item["code"] for item in diagnostics.diagnose_cheap_lane(
            now=datetime(2026, 9, 18, 12, tzinfo=UTC)
        )["findings"]
    }
    assert {"capacity-concentrated", "quota-near-exhaustion", "credentials-missing"} <= codes
