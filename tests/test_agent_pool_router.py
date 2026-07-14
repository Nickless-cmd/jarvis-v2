"""Tests for core/services/agent_pool_router.py — agent-pool routing + kvalitets-læring."""
from __future__ import annotations
import core.services.agent_pool_router as apr


def test_route_agent_task_delegates_to_central_route(monkeypatch):
    """Task 11: route_agent_task router gennem central_route (lane=agent)."""
    seen = {}

    def fake_route(*, lane, task, exclude):
        seen.update({"lane": lane, "task": task})
        return {"provider": "cerebras", "model": "gemma-4-31b", "lane": lane,
                "is_floor": False}

    monkeypatch.setattr("core.services.central_route.route", fake_route)
    r = apr.route_agent_task(kind="coding")
    assert r["provider"] == "cerebras"
    assert seen["lane"] == "agent"
    assert seen["task"]["kind"] == "coding"


def test_update_task_score_ema(monkeypatch):
    """Task 12: EMA-opdatering af task_score fra outcome."""
    store = {}
    monkeypatch.setattr(apr, "_load_task_scores", lambda p, m: {"coding": 0.5})
    monkeypatch.setattr(apr, "_save_task_scores",
                        lambda p, m, s: store.update(s))
    apr.update_task_score(provider="cerebras", model="gemma-4-31b",
                          kind="coding", outcome_quality=1.0, lr=0.1)
    assert abs(store["coding"] - 0.55) < 1e-6      # (1-0.1)*0.5 + 0.1*1.0


def test_update_task_score_seeds_at_half(monkeypatch):
    store = {}
    monkeypatch.setattr(apr, "_load_task_scores", lambda p, m: {})   # ukendt
    monkeypatch.setattr(apr, "_save_task_scores", lambda p, m, s: store.update(s))
    apr.update_task_score(provider="x", model="y", kind="reasoning",
                          outcome_quality=1.0, lr=0.1)
    assert abs(store["reasoning"] - 0.55) < 1e-6   # seed 0.5 -> 0.55


def test_resolve_target_routes_through_pool_when_flag_on(monkeypatch):
    """Bjørn: agent:explore skal kalde fra agent-poolen. /v1/agent/step's
    _resolve_target router gennem route_agent_task når flag'et er ON."""
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "agent_pool_router_enabled")
    monkeypatch.setattr("core.services.agent_pool_router.route_agent_task",
                        lambda **kw: {"provider": "cerebras", "model": "gemma-4-31b"})
    assert al._resolve_target() == ("cerebras", "gemma-4-31b")


def test_resolve_target_uses_visible_when_flag_off(monkeypatch):
    """Flag OFF → uændret visible-adfærd (route_agent_task kaldes ikke)."""
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_flag", lambda name, default=False: False)
    called = {"n": 0}
    monkeypatch.setattr("core.services.agent_pool_router.route_agent_task",
                        lambda **kw: called.__setitem__("n", called["n"] + 1) or {})
    monkeypatch.setattr("core.services.central_router_adapt.resolve_visible_model",
                        lambda **kw: ("deepseek", "deepseek-v4-flash"))
    assert al._resolve_target() == ("deepseek", "deepseek-v4-flash")
    assert called["n"] == 0
