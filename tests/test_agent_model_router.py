"""D: modelkald for en agent - genvalidering ved kaldet og failover. Rigtig sqlite, falsk facade."""
from __future__ import annotations

import pytest

ANDEN, BJORN = "anden-bruger", "bjorn-id"
CHAIN = [
    {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m1"},
    {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m2"},
    {"route_source": "cheap_lane_fallback", "provider": "kilo", "model": "m3"},
]


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_route as R
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import agent_model_router as M
    from core.services.agent_model_policy import ModelUnavailable

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: BJORN)

    class F:
        """Falsk facade: scriptede svar pr. (provider/model); logger hvert kald."""
        def __init__(self): self.calls, self.fail = [], set()
        def execute_with_role_or_fallback(self, **kw):
            self.calls.append(kw)
            key = f"{kw['provider']}/{kw['model']}"
            if key in self.fail:
                raise M.ModelCallFailed("nede", provider=kw["provider"], model=kw["model"])
            return {"text": "ok", "provider": kw["provider"], "model": kw["model"], "status": "completed"}

    class H:
        c_, R_, M_, E_ = c, R, M, ModelUnavailable
        f = F()

        def agent(self, owner=ANDEN, chain=CHAIN, name="a1", policy="read-only-runtime", current=0):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g", tool_policy=policy,
                                        provider=chain[current]["provider"], model=chain[current]["model"])
            if owner:
                c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id="s1")
                acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id="s1",
                                          goal="g", parent_agent_id="jarvis", parent_run_id="pr")
                R.record_decision(assignment_id=acc["assignment_id"], agent_id=name, owner_user_id=owner,
                                  decision={"route_source": chain[current]["route_source"],
                                            "provider": chain[current]["provider"],
                                            "model": chain[current]["model"], "candidates": chain,
                                            "rejected": []}, attempt=1)
            return {"agent_id": name, "tool_policy": policy, "provider": chain[current]["provider"],
                    "model": chain[current]["model"]}

        def call(self, agent, **kw):
            return M.call_agent_model(agent=agent, facade=self.f, requires_tools=True, lane="agent",
                                      provider=agent["provider"], model=agent["model"], **kw)

        def reg(self, name="a1"):
            r = c._conn().execute("SELECT provider, model FROM agent_registry WHERE agent_id=?",
                                  (name,)).fetchone()
            return (r["provider"], r["model"])

    return H()


def used(rt):
    return [(k["provider"], k["model"]) for k in rt.f.calls]


def test_a_healthy_first_candidate_is_called_with_the_authenticated_owner_and_nothing_is_switched(rt):
    ag = rt.agent()
    res = rt.call(ag)
    assert res["model"] == "m1" and used(rt) == [("copilot-premium", "m1")]
    assert rt.f.calls[0]["owner_user_id"] == ANDEN
    assert [r["attempt"] for r in rt.R_.attempts_for_assignment(
        rt.R_.latest_for_agent("a1")["assignment_id"])] == [1]


def test_a_failing_model_moves_to_the_next_pool_candidate_before_the_owners_fallback(rt):
    ag = rt.agent()
    rt.f.fail = {"copilot-premium/m1"}
    res = rt.call(ag)
    assert res["model"] == "m2" and used(rt) == [("copilot-premium", "m1"), ("copilot-premium", "m2")]
    latest = rt.R_.latest_for_agent("a1")
    assert (latest["attempt"], latest["provider"], latest["model"], latest["route_source"]) == (
        2, "copilot-premium", "m2", "agent_pool")
    assert "nede" in latest["decision"]["failover_reason"] or latest["decision"]["failover_reason"]
    assert rt.reg() == ("copilot-premium", "m2")       # skiftet er varigt - naeste kald starter paa m2


def test_the_switch_survives_into_the_next_call_even_with_a_stale_agent_dict(rt):
    ag = rt.agent()
    rt.f.fail = {"copilot-premium/m1"}
    rt.call(ag)
    rt.f.calls.clear()
    rt.call(ag)                                          # ag er stadig m1 - gemt rute er sandheden
    assert used(rt) == [("copilot-premium", "m2")]


def test_the_cheap_lane_is_reached_only_after_every_pool_model_failed(rt):
    ag = rt.agent()
    rt.f.fail = {"copilot-premium/m1", "copilot-premium/m2"}
    assert rt.call(ag)["model"] == "m3"
    assert rt.R_.latest_for_agent("a1")["route_source"] == "cheap_lane_fallback"


def test_a_fully_failed_chain_is_model_unavailable_with_every_attempt(rt):
    ag = rt.agent()
    rt.f.fail = {"copilot-premium/m1", "copilot-premium/m2", "kilo/m3"}
    with pytest.raises(rt.E_) as e:
        rt.call(ag)
    assert e.value.code == "MODEL_UNAVAILABLE" and [a["model"] for a in e.value.reasons] == ["m1", "m2", "m3"]


def test_a_possibly_executed_write_is_never_hidden_behind_a_model_switch(rt):
    ag = rt.agent(policy="worktree-write", name="w1")
    rt.f.fail = {"copilot-premium/m1"}
    with pytest.raises(rt.M_.ModelCallFailed):
        rt.call(ag, tools_executed=True)
    assert used(rt) == [("copilot-premium", "m1")] and rt.reg("w1") == ("copilot-premium", "m1")
    rt.f.calls.clear()
    assert rt.call(ag, tools_executed=False)["model"] == "m2"        # foer noget er udfoert: failover er ok


def test_a_read_only_agent_may_switch_model_after_tools_have_run(rt):
    ag = rt.agent(policy="read-only-runtime")
    rt.f.fail = {"copilot-premium/m1"}
    assert rt.call(ag, tools_executed=True)["model"] == "m2"


# --- ejergraensen ved kaldet --------------------------------------------------------------------

DEEPSEEK_CHAIN = [{"route_source": "agent_pool", "provider": "deepseek", "model": "deepseek-v4-pro"},
                  {"route_source": "cheap_lane_fallback", "provider": "kilo", "model": "m3"}]


def test_deepseek_in_anothers_chain_is_denied_before_any_call_and_skipped(rt):
    ag = rt.agent(owner=ANDEN, chain=DEEPSEEK_CHAIN)          # en forfalsket/forkert gemt rute
    res = rt.call(ag)
    assert res["model"] == "m3"
    assert all(p != "deepseek" for p, _ in used(rt))          # deepseek-API'et blev ALDRIG kaldt


def test_deepseek_is_allowed_for_the_platform_owner(rt):
    ag = rt.agent(owner=BJORN, chain=DEEPSEEK_CHAIN)
    assert rt.call(ag)["model"] == "deepseek-v4-pro"


def test_a_chain_with_only_denied_candidates_is_unavailable_not_a_call(rt):
    ag = rt.agent(owner=ANDEN, chain=DEEPSEEK_CHAIN[:1], name="d1")
    with pytest.raises(rt.E_) as e:
        rt.call(ag)
    assert rt.f.calls == [] and e.value.reasons[0]["reason"].startswith("policy:")


def test_a_legacy_agent_goes_the_old_way_without_an_owner_argument(rt):
    ag = rt.agent(owner="", name="legacy")
    rt.call(ag)
    assert "owner_user_id" not in rt.f.calls[0] and used(rt) == [("copilot-premium", "m1")]


def test_a_model_outside_the_route_is_called_as_is_never_swapped_for_another(rt):
    ag = rt.agent()
    ag["provider"], ag["model"] = "copilot-premium", "uden-for-ruten"
    rt.call(ag)
    assert used(rt) == [("copilot-premium", "uden-for-ruten")]


# --- selve providerkaldet: ingen tavs failover for en agent med ejer ------------------------------

@pytest.fixture
def prov(monkeypatch, isolated_runtime):
    import core.services.cheap_provider_runtime as cpr
    calls = []

    def chat(**kw):
        calls.append(kw)
        raise RuntimeError("provider nede")

    monkeypatch.setattr(cpr, "_execute_provider_chat", chat)
    pool = []
    import core.services.non_visible_lane_execution as nv
    monkeypatch.setattr(nv, "execute_cheap_lane_via_pool",
                        lambda **kw: pool.append(kw) or {"status": "completed", "text": "fra puljen"})
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: BJORN)
    return nv, calls, pool


def test_with_an_owner_a_provider_failure_raises_instead_of_silently_switching_model(prov):
    nv, calls, pool = prov
    from core.services.agent_model_router import ModelCallFailed
    with pytest.raises(ModelCallFailed):
        nv.execute_with_role_or_fallback(message="x", provider="copilot-premium", model="m1",
                                         owner_user_id=ANDEN)
    assert len(calls) == 1 and pool == []


def test_without_an_owner_the_old_silent_failover_is_unchanged(prov):
    nv, calls, pool = prov
    res = nv.execute_with_role_or_fallback(message="x", provider="copilot-premium", model="m1")
    assert res["text"] == "fra puljen" and len(pool) == 1


def test_the_provider_call_itself_refuses_deepseek_for_a_non_owner_before_the_network(prov):
    nv, calls, pool = prov
    from core.services.agent_model_policy import ProviderDenied
    with pytest.raises(ProviderDenied):
        nv.execute_with_role_or_fallback(message="x", provider="deepseek", model="deepseek-v4-pro",
                                         owner_user_id=ANDEN)
    assert calls == [] and pool == []


def test_an_open_circuit_breaker_is_a_visible_failure_for_an_owner_agent(prov, monkeypatch):
    nv, calls, pool = prov
    monkeypatch.setattr("core.services.provider_circuit_breaker.should_skip", lambda p, m: True)
    from core.services.agent_model_router import ModelCallFailed
    with pytest.raises(ModelCallFailed, match="circuit breaker"):
        nv.execute_with_role_or_fallback(message="x", provider="copilot-premium", model="m1",
                                         owner_user_id=ANDEN)
    assert calls == [] and pool == []
    res = nv.execute_with_role_or_fallback(message="x", provider="copilot-premium", model="m1")
    assert res["text"] == "fra puljen" and calls == []        # uden ejer: den gamle sti


def test_route_sources_are_a_closed_set(rt):
    ag = rt.agent()
    lat = rt.R_.latest_for_agent("a1")
    with pytest.raises(ValueError):
        rt.R_.record_decision(assignment_id=lat["assignment_id"], agent_id="a1", owner_user_id=ANDEN,
                              decision={"route_source": "stjaalet", "provider": "p", "model": "m"}, attempt=9)
