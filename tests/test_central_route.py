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
