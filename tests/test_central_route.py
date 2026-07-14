"""Tests for core/services/central_route.py — Central-ejet unified router."""
from __future__ import annotations
import core.services.central_route as cr


def test_route_returns_target_for_healthy_lane(monkeypatch):
    monkeypatch.setattr(cr, "_rank_candidates",
                        lambda lane, task, exclude: [("groq", "llama-3.3-70b-versatile")])
    t = cr.route(lane="cheap")
    assert t["provider"] == "groq"
    assert t["is_floor"] is False


def test_route_never_raises_falls_to_floor(monkeypatch):
    monkeypatch.setattr(cr, "_rank_candidates", lambda lane, task, exclude: [])
    monkeypatch.setattr("core.services.cheap_lane_floor.floor_targets",
                        lambda: [("deepseek", "deepseek-chat")])
    t = cr.route(lane="cheap")               # tom kandidat-liste
    assert t["is_floor"] is True             # aldrig raise
    assert t["provider"] in ("deepseek", "floor")


def test_provider_history_computes_error_rate(monkeypatch):
    """Task 10: fejlrate + oppetid fra invocation-rækker."""
    import core.services.central_route as cr
    # 10 kald, 2 fejl → error_rate 0.2, uptime 80%
    fake = [("ok", 100)] * 8 + [("rate-limited", 0), ("http-error:503", 0)]
    monkeypatch.setattr(cr, "_fetch_invocations", lambda provider, since: fake)
    h = cr.provider_history("groq", hours=24)
    assert h["calls"] == 10
    assert h["error_rate"] == 0.2
    assert h["uptime_pct"] == 80.0


def test_provider_history_empty_is_safe(monkeypatch):
    import core.services.central_route as cr
    monkeypatch.setattr(cr, "_fetch_invocations", lambda provider, since: [])
    h = cr.provider_history("unknown")
    assert h["calls"] == 0 and h["error_rate"] == 0.0
