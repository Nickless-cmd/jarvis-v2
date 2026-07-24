"""Tests for core/services/central_route.py — Central-ejet unified router."""
from __future__ import annotations
import core.services.central_route as cr


def test_route_returns_target_for_healthy_lane(monkeypatch):
    monkeypatch.setattr(cr, "_scored_candidates",
                        lambda lane, task, exclude: [(0.0, 1.0, "groq", "llama-3.3-70b-versatile")])
    t = cr.route(lane="cheap")
    assert t["provider"] == "groq"
    assert t["is_floor"] is False


def test_route_never_raises_falls_to_floor(monkeypatch):
    monkeypatch.setattr(cr, "_scored_candidates", lambda lane, task, exclude: [])
    monkeypatch.setattr("core.services.cheap_lane_floor.floor_targets",
                        lambda: [("deepseek", "deepseek-chat")])
    t = cr.route(lane="cheap")               # tom kandidat-liste
    assert t["is_floor"] is True             # aldrig raise
    assert t["provider"] in ("deepseek", "floor")


def test_route_spread_off_is_winner_take_all(monkeypatch):
    # flag OFF (default): winner-take-all, scored[0] wins deterministically.
    monkeypatch.setattr(cr, "_scored_candidates", lambda lane, task, exclude: [
        (0.0, 1.0, "cerebras", "m1"), (0.0, 2.0, "gemini", "m2")])
    monkeypatch.setattr(cr, "_flag_cheap_provider_spread", lambda: False)
    for _ in range(5):
        t = cr.route(lane="cheap")
        assert t["provider"] == "cerebras"
        assert t["reason"] == "central-route:ranked"


def test_route_spread_on_uses_quota_weighted_pick(monkeypatch):
    # flag ON + cheap lane: route delegates to the quota-weighted pick and marks it.
    monkeypatch.setattr(cr, "_scored_candidates", lambda lane, task, exclude: [
        (0.0, 1.0, "cerebras", "m1"), (0.0, 2.0, "gemini", "m2")])
    monkeypatch.setattr(cr, "_flag_cheap_provider_spread", lambda: True)
    monkeypatch.setattr(cr, "_weighted_provider_pick", lambda scored, rng=None: ("gemini", "m2"))
    t = cr.route(lane="cheap")
    assert t["provider"] == "gemini"
    assert t["reason"] == "central-route:quota-spread"


def test_weighted_pick_is_quota_proportional():
    # direct: more headroom (lower rank) -> higher weight -> chosen at low r.
    scored = [(0.0, 1.0, "cerebras", "m1"), (0.0, 2.0, "gemini", "m2"), (0.0, 4.0, "mistral", "m3")]

    class RNG:
        def __init__(self, v): self.v = v
        def random(self): return self.v

    assert cr._weighted_provider_pick(scored, RNG(0.0)) == ("cerebras", "m1")
    assert cr._weighted_provider_pick(scored, RNG(0.99)) == ("mistral", "m3")
    # best model per provider wins the dedup
    scored2 = [(0.0, 1.0, "cerebras", "m1"), (0.0, 3.0, "cerebras", "m9"), (0.0, 2.0, "gemini", "m2")]
    assert cr._weighted_provider_pick(scored2, RNG(0.0)) == ("cerebras", "m1")


def test_route_spread_on_agent_lane_unchanged(monkeypatch):
    # spread is cheap-only: agent lane stays winner-take-all even with flag on.
    monkeypatch.setattr(cr, "_scored_candidates", lambda lane, task, exclude: [
        (-0.9, 1.0, "deepseek", "deepseek-chat"), (0.0, 1.0, "cerebras", "m1")])
    monkeypatch.setattr(cr, "_flag_cheap_provider_spread", lambda: True)
    t = cr.route(lane="agent")
    assert t["provider"] == "deepseek"
    assert t["reason"] == "central-route:ranked"


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


def test_rank_honors_task_kind(monkeypatch):
    """central_route SKAL matche select's task_kind-semantik: background=proxies først,
    important=drop proxies. Ellers router den background til betalt deepseek."""
    import core.services.central_route as cr
    fake_cands = [
        {"provider": "deepseek", "model": "deepseek-chat", "priority": 5, "credentials_ready": True},
        {"provider": "opencode", "model": "big-pickle", "priority": 80, "credentials_ready": True},
    ]
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._configured_cheap_candidates",
                        lambda include_public_proxy=True: [c for c in fake_cands
                                                           if include_public_proxy or c["provider"] != "opencode"])
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._is_public_proxy",
                        lambda p: p in ("opencode", "arko", "ollamafreeapi"))
    monkeypatch.setattr("core.services.central_route_headroom.headroom_ok", lambda p: True)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_weight", lambda p: 1.0)
    # background → opencode (gratis proxy) FØRST, ikke betalt deepseek
    bg = cr._rank_candidates("cheap", {"kind": "background"}, frozenset())
    assert bg[0][0] == "opencode"
    # important → deepseek (proxies droppet)
    imp = cr._rank_candidates("cheap", {"kind": "important"}, frozenset())
    assert all(p != "opencode" for p, _ in imp)
    # default → priority-orden (deepseek priority 5 vinder)
    df = cr._rank_candidates("cheap", {"kind": "default"}, frozenset())
    assert df[0][0] == "deepseek"


def test_agent_lane_excludes_non_openai_chat(monkeypatch):
    """Agent-lanen må kun route til openai-chat (agent-step-kompatible). gemini/codex
    m.fl. ekskluderes så de ikke trigger deepseek-fallback. Daemon-lanen beholder dem."""
    import core.services.central_route as cr
    fake = [
        {"provider": "nvidia-nim", "model": "m1", "priority": 10, "credentials_ready": True},
        {"provider": "arko", "model": "jarvis-cheap-lane", "priority": 90, "credentials_ready": True},  # arko-protokol
    ]
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._configured_cheap_candidates",
                        lambda include_public_proxy=True: fake)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_ok", lambda p: True)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_weight", lambda p: 1.0)
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._is_public_proxy",
                        lambda p: p == "arko")
    agent = cr._rank_candidates("agent", {"kind": "coding"}, frozenset())
    assert [p for p, _ in agent] == ["nvidia-nim"]          # arko (non-openai-chat) ekskluderet
    cheap = cr._rank_candidates("cheap", {"kind": "coding"}, frozenset())
    assert "arko" in [p for p, _ in cheap]                  # men beholdt på cheap-lane


def test_cost_gate_free_default_paid_requires_allow_paid(monkeypatch):
    """Bjørn 15. jul: gratis = frit valg (default), betalt = rigtige opgaver (allow_paid).
    central_route ekskluderer cost_class=paid medmindre task.allow_paid=True."""
    import core.services.central_route as cr
    fake = [
        {"provider": "cerebras", "model": "gemma-4-31b", "priority": 22, "credentials_ready": True},
        {"provider": "copilot-premium", "model": "claude-opus-4.8", "priority": 5, "credentials_ready": True},
    ]
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._configured_cheap_candidates",
                        lambda include_public_proxy=True: fake)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_ok", lambda p: True)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_weight", lambda p: 1.0)
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._is_public_proxy", lambda p: False)
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class",
                        lambda p: "paid" if p == "copilot-premium" else "free")
    # default: betalt ekskluderet → kun cerebras
    free_only = [p for p, _ in cr._rank_candidates("agent", {"kind": "coding"}, frozenset())]
    assert free_only == ["cerebras"]
    # allow_paid: copilot-premium inkluderet OG #1 (prio 5 < cerebras 22)
    with_paid = cr._rank_candidates("agent", {"kind": "coding", "allow_paid": True}, frozenset())
    assert with_paid[0][0] == "copilot-premium"
