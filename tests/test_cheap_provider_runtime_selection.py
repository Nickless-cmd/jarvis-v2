"""Tests for core/services/cheap_provider_runtime_selection.py — pool + floor."""
from __future__ import annotations


def test_pool_falls_to_floor_instead_of_raising(monkeypatch):
    """Spec Fund 4: execute_cheap_lane_via_pool må ALDRIG rejse 'no-healthy-provider'
    — den falder til bunden (cheap_lane_floor)."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "select_cheap_lane_target",
                        lambda **kw: {"active": False, "provider": ""})
    called = {}

    def fake_floor(*, message, lane, reason):
        called["reason"] = reason
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "is_floor": True}

    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = sel.execute_cheap_lane_via_pool(message="hej")
    assert res["provider"] == "floor"          # ingen exception
    assert called["reason"] == "no-healthy-provider"
