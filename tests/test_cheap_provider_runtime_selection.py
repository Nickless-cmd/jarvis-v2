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


def test_shadow_compare_off_is_noop(monkeypatch):
    """Task 9: default OFF → zero overhead, byte-identisk adfærd."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_central_route_shadow", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(sel, "_record_route_divergence",
                        lambda o, n: called.__setitem__("n", called["n"] + 1))
    sel._maybe_shadow_compare({"provider": "groq", "model": "y"})
    assert called["n"] == 0


def test_shadow_compare_on_records_divergence(monkeypatch):
    """Task 9: shadow ON → central_route FORESLÅR, divergens registreres."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_central_route_shadow", lambda: True)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "cerebras", "model": "gemma-4-31b"})
    seen = {}
    monkeypatch.setattr(sel, "_record_route_divergence",
                        lambda o, n: seen.update({"old": o, "new": n}))
    sel._maybe_shadow_compare({"provider": "groq", "model": "y"})
    assert seen["new"]["provider"] == "cerebras"
    assert seen["old"]["provider"] == "groq"


def test_cheap_selection_excludes_paid(monkeypatch):
    """15. jul: direkte cheap/daemon-selection er gratis-only — copilot-premium (paid)
    må aldrig vælges her (kun via central_route allow_paid)."""
    import core.services.cheap_provider_runtime_selection as sel
    fake = [
        {"provider": "copilot-premium", "model": "claude-sonnet-5", "credentials_ready": True,
         "priority": 5, "effective_priority": 5},
        {"provider": "cerebras", "model": "gemma-4-31b", "credentials_ready": True,
         "priority": 22, "effective_priority": 22},
    ]
    monkeypatch.setattr(sel, "_configured_cheap_candidates", lambda **kw: list(fake))
    monkeypatch.setattr(sel, "_candidate_quota_snapshot", lambda c: {"blocked": False})
    monkeypatch.setattr(sel, "_candidate_adaptive_snapshot",
                        lambda c: {"effective_priority": c.get("priority", 99), "adaptive_penalty": 0})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class",
                        lambda p: "paid" if p == "copilot-premium" else "free")
    t = sel.select_cheap_lane_target(task_kind="default")
    assert t.get("provider") != "copilot-premium"   # betalt ekskluderet
