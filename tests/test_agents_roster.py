"""A1: agents_summary() gains a full `roster` — every pool (provider, model) as a
fixed row (active/idle/inactive), merged with recent agent activity."""
from __future__ import annotations


class _Slot:
    def __init__(self, p, m):
        self.provider = p
        self.model = m
        self.auth_profile = "default"
        self.egress = "home"


def _clear_trace():
    from core.services import central_trace
    central_trace.sink()._buf.clear()


def test_agents_summary_has_full_roster(monkeypatch):
    from core.services import agents
    _clear_trace()
    # stub build_slot_pool to a known small model set
    monkeypatch.setattr(
        "core.services.cheap_lane_balancer.build_slot_pool",
        lambda: [_Slot("groq", "llama-x"), _Slot("groq", "llama-x"),  # dup -> one row
                 _Slot("cohere", "command-r")],
    )
    out = agents.agents_summary()
    roster = out.get("roster")
    assert isinstance(roster, list)
    keys = {r["model_key"] for r in roster}
    assert keys == {"groq/llama-x", "cohere/command-r"}   # deduped
    # a model with no activity is inactive
    assert all(r["status"] in ("active", "idle", "inactive") for r in roster)
    assert any(r["status"] == "inactive" for r in roster)
    # existing keys preserved (backward-compat)
    for k in ("agent_spawns", "agent_errors", "council_sessions", "council_deadlocks"):
        assert k in out
    # row shape
    row = roster[0]
    for k in ("model_key", "provider", "model", "status", "last_run_at",
              "tokens_in", "tokens_out", "cost_usd", "current_activity",
              "tool_calls", "role"):
        assert k in row


def test_roster_self_safe_if_pool_fails(monkeypatch):
    from core.services import agents
    _clear_trace()
    monkeypatch.setattr(
        "core.services.cheap_lane_balancer.build_slot_pool",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    out = agents.agents_summary()
    assert out.get("roster") == []   # never breaks


def test_roster_row_flips_active_with_summed_tokens(monkeypatch):
    """Inject a fresh agent result for a pool model → its roster row becomes
    active with tokens summed across the two dispatches."""
    from core.services import agents
    _clear_trace()
    monkeypatch.setattr(
        "core.services.cheap_lane_balancer.build_slot_pool",
        lambda: [_Slot("groq", "llama-x"), _Slot("cohere", "command-r")],
    )
    # Two dispatches on the same model → tokens must aggregate.
    agents.note_agent_result("a1", "completed", tokens_in=100, tokens_out=50,
                             cost_usd=0.01, tool_calls=2, role="researcher",
                             provider="groq", model="llama-x")
    agents.note_agent_result("a2", "running", tokens_in=10, tokens_out=5,
                             cost_usd=0.002, tool_calls=1, role="researcher",
                             provider="groq", model="llama-x")
    out = agents.agents_summary()
    rows = {r["model_key"]: r for r in out["roster"]}
    active = rows["groq/llama-x"]
    assert active["status"] == "active"          # fresh activity
    assert active["tokens_in"] == 110
    assert active["tokens_out"] == 55
    assert round(active["cost_usd"], 4) == 0.012
    assert active["tool_calls"] == 3
    assert active["role"] == "researcher"
    assert active["last_run_at"] != ""
    # untouched model stays inactive
    assert rows["cohere/command-r"]["status"] == "inactive"
