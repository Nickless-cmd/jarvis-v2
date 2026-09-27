from __future__ import annotations

from datetime import UTC, datetime


def test_recent_invocations_reads_every_page_in_window(monkeypatch):
    import core.runtime.db_cheap_lane_control as db
    from core.services.cheap_lane_diagnostics import recent_invocations

    pages = {
        "": {"items": [{"invocation_id": "new"}], "next_cursor": "older"},
        "older": {"items": [{"invocation_id": "old"}], "next_cursor": None},
    }
    monkeypatch.setattr(db, "list_cheap_lane_invocations", lambda **kw: pages[kw.get("cursor", "")])

    rows = recent_invocations(since=datetime(2026, 9, 26, tzinfo=UTC))
    assert [row["invocation_id"] for row in rows] == ["new", "old"]


def test_invocation_health_is_split_by_account_and_provider():
    from core.services.cheap_lane_diagnostics import invocation_health

    rows = [
        {"provider": "groq", "auth_profile": "default", "status": "completed", "latency_ms": 100},
        {"provider": "groq", "auth_profile": "account2", "status": "failed", "latency_ms": 900},
        {"provider": "groq", "auth_profile": "account2", "status": "completed", "latency_ms": 300},
    ]
    health = invocation_health(rows)

    assert health["requests"] == 3
    assert health["failures"] == 1
    assert health["p95_latency_ms"] == 900
    assert health["by_profile"]["account2"]["failures"] == 1
    assert health["by_provider_profile"]["groq::default"]["p95_latency_ms"] == 100


def test_route_integrity_waits_for_inflight_invocation(isolated_runtime):
    from datetime import timedelta
    from core.runtime.db_core import connect
    from core.runtime.db_cheap_lane_control import _ensure_control_schema
    from core.services.cheap_lane_diagnostics import route_integrity

    now = datetime.now(UTC)
    old = (now - timedelta(minutes=10)).isoformat()
    fresh = now.isoformat()
    with connect() as conn:
        _ensure_control_schema(conn)
        for route_id, created_at in (("old", old), ("fresh", fresh)):
            conn.execute(
                "INSERT INTO cheap_lane_route_decisions "
                "(route_decision_id,correlation_id,created_at) VALUES (?,?,?)",
                (route_id, route_id, created_at),
            )

    mismatches = route_integrity(since=now - timedelta(hours=1))
    assert [row["route_decision_id"] for row in mismatches] == ["old"]


def test_local_ollama_fallback_is_not_a_pool_route_bypass():
    from core.services.cheap_lane_diagnostics import unrouted_pool_invocations

    rows = [
        {"provider": "ollama", "status": "failed", "route_decision_id": ""},
        {"provider": "groq", "status": "failed", "route_decision_id": ""},
        {"provider": "groq", "status": "completed", "route_decision_id": "route-1"},
    ]
    assert unrouted_pool_invocations(rows) == [rows[1]]


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


def test_account_cooldown_is_one_parked_finding_not_four_breakers(monkeypatch):
    import core.services.cheap_lane_diagnostics as diagnostics

    slots = [
        {"slot_id": f"chatanywhere::m{i}::default", "provider": "chatanywhere",
         "auth_profile": "default", "egress": "home", "weight": 0,
         "status": "cooldown", "breaker_level": 3,
         "consecutive_failures": 10, "cooldown_reason": "provider-blocked",
         "account_block_reason": "provider-blocked",
         "account_block_until": "2026-09-18T18:00:00+00:00"}
        for i in range(4)
    ]
    slots.append({
        "slot_id": "groq::bad-model::default", "provider": "groq",
        "auth_profile": "default", "egress": "home", "weight": 0.1,
        "status": "recovering", "breaker_level": 3,
        "consecutive_failures": 10, "cooldown_reason": "model-not-found",
        "account_block_reason": None,
    })
    monkeypatch.setattr(diagnostics, "balancer_snapshot", lambda: {
        "eligible_now": 1, "saved_at": "2026-09-18T12:00:00+00:00", "slots": slots,
    })
    monkeypatch.setattr(diagnostics, "capacity_snapshot", lambda **_kw: {"windows": []})
    monkeypatch.setattr(diagnostics, "fuld_registrering", lambda: {"udbydere": []})
    monkeypatch.setattr(diagnostics, "recent_invocations", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "route_integrity", lambda **_kw: [])
    monkeypatch.setattr(diagnostics, "central_evidence", lambda **_kw: [])

    findings = diagnostics.diagnose_cheap_lane(
        now=datetime(2026, 9, 18, 12, tzinfo=UTC)
    )["findings"]
    parked = [item for item in findings if item["code"] == "account-parked"]
    breakers = [item for item in findings if item["code"] == "breaker-repeated"]
    starvation = [item for item in findings if item["code"] == "provider-starvation"]
    assert len(parked) == 1
    assert parked[0]["severity"] == "medium"
    assert parked[0]["evidence"]["affected_slots"] == 4
    assert parked[0]["evidence"]["reason"] == "provider-blocked"
    assert [item["slot_id"] for item in breakers] == ["groq::bad-model::default"]
    assert len(starvation) == 1 and starvation[0]["severity"] == "medium"
