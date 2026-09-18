from __future__ import annotations


def test_dashboard_keeps_healthy_sections_when_central_fails(monkeypatch):
    import core.services.cheap_lane_dashboard as dashboard

    monkeypatch.setattr(dashboard, "capacity_snapshot", lambda: {
        "windows": [{"remaining": 80, "limit": 100}], "totals": {},
    })
    monkeypatch.setattr(dashboard, "fuld_registrering", lambda: {
        "udbydere": [{"provider": "groq"}], "modeller": [], "opsummering": {},
    })
    monkeypatch.setattr(dashboard, "balancer_snapshot", lambda: {
        "eligible_now": 1, "blocked_now": 0, "slots": [],
    })
    monkeypatch.setattr(dashboard, "invocation_trends", lambda **_kw: {
        "requests": 4, "tokens": 120, "errors": 0, "cost_usd": 0,
    })
    monkeypatch.setattr(dashboard, "diagnose_cheap_lane", lambda: {
        "findings": [], "status": "healthy",
    })
    monkeypatch.setattr(
        dashboard, "central_evidence", lambda **_kw: (_ for _ in ()).throw(
            RuntimeError("down")
        )
    )

    snapshot = dashboard.build_cheap_lane_dashboard(window_hours=24)

    assert snapshot["status"] == "partial"
    assert snapshot["sections"]["capacity"]["data"]["windows"]
    assert snapshot["sections"]["central"]["error"]["code"] == "source-unavailable"
    assert snapshot["kpis"]["requests"] == 4


def test_dashboard_has_versioned_complete_section_envelopes(monkeypatch):
    import core.services.cheap_lane_dashboard as dashboard

    monkeypatch.setattr(dashboard, "capacity_snapshot", lambda: {"windows": [], "totals": {}})
    monkeypatch.setattr(dashboard, "fuld_registrering", lambda: {"udbydere": []})
    monkeypatch.setattr(dashboard, "balancer_snapshot", lambda: {
        "eligible_now": 0, "blocked_now": 0, "slots": [],
    })
    monkeypatch.setattr(dashboard, "invocation_trends", lambda **_kw: {
        "requests": 0, "tokens": 0, "errors": 0, "cost_usd": 0,
    })
    monkeypatch.setattr(dashboard, "diagnose_cheap_lane", lambda: {
        "findings": [], "status": "healthy",
    })
    monkeypatch.setattr(dashboard, "central_evidence", lambda **_kw: [])

    snapshot = dashboard.build_cheap_lane_dashboard(window_hours=6)

    assert snapshot["schema_version"] == 1
    assert snapshot["status"] == "complete"
    assert snapshot["window_hours"] == 6
    assert set(snapshot["sections"]) == {
        "capacity", "providers", "balancer", "trends", "diagnostics", "central",
    }
    assert all("source" in section and "freshness" in section
               for section in snapshot["sections"].values())
