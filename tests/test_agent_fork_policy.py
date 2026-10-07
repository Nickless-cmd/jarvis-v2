"""G2: fork med modelskift - kontekstomkostning, valgt vej, ingen omgaaelse af rettigheder. Rigtig sqlite."""
from __future__ import annotations

import pytest

BJORN, ANDEN = "bjorn-id", "anden-bruger"
POOL1 = {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m1"}
POOL2 = {"route_source": "agent_pool", "provider": "copilot-premium", "model": "m2"}
DEEP = {"route_source": "agent_pool", "provider": "deepseek", "model": "deepseek-v4-pro"}
CHEAP = {"route_source": "cheap_lane_fallback", "provider": "kilo", "model": "m3"}


def _route(*cands):
    h = cands[0]
    return {"route_source": h["route_source"], "provider": h["provider"], "model": h["model"],
            "candidates": list(cands)}


@pytest.fixture
def fk(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_fork as F
    import core.services.agent_contract_service as svc
    import core.services.agent_fork_policy as P
    from core.services import chat_sessions as cs
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: BJORN)
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: None)
    svc.set_capability(True, role="owner")
    ifr._mutate(lambda r: r.clear())
    sid = cs.create_chat_session(title="t")["id"]

    class H:
        c_, F_, P_, svc_, sid_ = c, F, P, svc, sid

        def say(self, role, text, user_id=None):
            cs.append_chat_message(session_id=sid, role=role, content=text, user_id=user_id)

        def parent(self, provider, model, effort="think", run_id="pr"):
            ifr.mark_started(run_id=run_id, session_id=sid, user_message="x", provider=provider,
                             model=model, thinking_mode=effort)

        def plan(self, route, owner=ANDEN, **kw):
            return P.plan_context(owner_user_id=owner, session_id=sid, parent_run_id="pr", route=route, **kw)

        def d(self, owner=ANDEN, **kw):
            base = dict(owner_user_id=owner, origin_session_id=sid, goal="find X", parent_run_id="pr")
            base.update(kw)
            return svc.dispatch_agent(**base)

        def n(self, table):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    yield H()
    ifr._mutate(lambda r: r.clear())


def _history(fk):
    fk.say("user", "U1 spoergsmaal", ANDEN)
    fk.say("assistant", "A1 svar", ANDEN)
    fk.say("user", "U2 spoergsmaal", ANDEN)
    fk.say("assistant", "A2 svar", ANDEN)
    fk.say("user", "U3 AKTIV TUR", ANDEN)          # den halve aktive tur


# --- snapshot -----------------------------------------------------------------------------------

def test_the_snapshot_holds_finished_turns_only_never_the_active_half_turn(fk):
    _history(fk)
    s = fk.P_.snapshot_parent_turns(owner_user_id=ANDEN, session_id=fk.sid_)
    assert s["turns"] == 2 and s["truncated"] is False and s["tokens"] > 0 and len(s["sha256"]) == 64
    assert "U1" in s["text"] and "A2" in s["text"] and "AKTIV" not in s["text"]


def test_the_snapshot_skips_another_users_messages_and_an_empty_session(fk):
    fk.say("user", "fremmed spoergsmaal", "en-anden")
    fk.say("assistant", "fremmed svar", "en-anden")
    s = fk.P_.snapshot_parent_turns(owner_user_id=ANDEN, session_id=fk.sid_)
    assert (s["turns"], s["text"]) == (0, "")
    assert fk.P_.snapshot_parent_turns(owner_user_id=ANDEN, session_id="")["turns"] == 0


# --- planen ---------------------------------------------------------------------------------------

def test_fresh_is_the_default_and_copies_nothing(fk):
    _history(fk)
    plan, route = fk.plan(_route(POOL1, CHEAP))
    assert (plan["context_mode"], plan["plan_path"], plan["extra_context_tokens"], plan["use_snapshot"],
            plan["cache_reuse_possible"]) == ("fresh", "fresh", 0, False, False)
    assert route["model"] == "m1"


def test_fork_on_the_parents_own_route_reuses_the_cache_at_the_cached_price(fk):
    _history(fk)
    fk.parent("copilot-premium", "m1")
    plan, route = fk.plan(_route(POOL1, CHEAP), context_mode="fork")
    assert (plan["plan_path"], plan["use_snapshot"], plan["cache_reuse_possible"]) == ("same_route", True, True)
    assert plan["extra_context_tokens"] == plan["history_tokens"] > 0
    assert route["model"] == "m1"


def test_fork_onto_another_model_is_refused_with_cost_and_the_allowed_ways(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    with pytest.raises(fk.P_.ForkRefused) as e:
        fk.plan(_route(POOL1, CHEAP), context_mode="fork")
    o = e.value.options
    assert e.value.code == "FORK_COST_UNACCEPTED"
    assert o["parent_route"] == "ollama/deepseek-v4-flash" and o["agent_route"] == "copilot-premium/m1"
    assert o["extra_context_tokens"] > 0 and o["cost_basis"] == "premium_request_uden_dollarpris"
    assert len(o["choose_one"]) == 3


def test_an_unknown_parent_route_is_never_assumed_to_be_the_same(fk):
    _history(fk)
    with pytest.raises(fk.P_.ForkRefused) as e:                    # ingen in-flight post for "pr"
        fk.plan(_route(POOL1, CHEAP), context_mode="fork")
    assert e.value.options["parent_route"] == "ukendt"


def test_an_accepted_paid_switch_copies_the_snapshot_onto_the_head_route(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    plan, route = fk.plan(_route(POOL1, CHEAP), context_mode="fork", accept_fork_switch=True)
    assert (plan["plan_path"], plan["use_snapshot"], plan["cache_reuse_possible"], plan["switch_accepted"]) == (
        "paid_switch", True, False, True)
    assert (route["provider"], route["model"]) == ("copilot-premium", "m1")


def test_an_explicit_excerpt_turns_the_fork_into_fresh_with_the_excerpt(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    plan, _ = fk.plan(_route(POOL1, CHEAP), context_mode="fork", context_excerpt="kun dette")
    assert (plan["plan_path"], plan["use_snapshot"], plan["excerpt"]) == ("excerpt", False, "kun dette")
    assert 0 < plan["extra_context_tokens"] < plan["history_tokens"]


def test_the_same_model_route_is_promoted_only_inside_the_heads_own_tier(fk):
    _history(fk)
    fk.parent("copilot-premium", "m2")
    plan, route = fk.plan(_route(POOL1, POOL2, CHEAP), context_mode="fork")
    assert plan["plan_path"] == "same_model_route"
    assert [c["model"] for c in route["candidates"]] == ["m2", "m1", "m3"]      # laget bevaret, fallback sidst
    assert (route["route_source"], route["model"]) == ("agent_pool", "m2")


def test_a_later_tier_candidate_is_never_promoted_ahead_of_the_pool(fk):
    _history(fk)
    fk.parent("kilo", "m3")                                          # parentens model er KUN cheap-lane-fallback
    with pytest.raises(fk.P_.ForkRefused):
        fk.plan(_route(POOL1, POOL2, CHEAP), context_mode="fork")
    plan, route = fk.plan(_route(POOL1, POOL2, CHEAP), context_mode="fork", accept_fork_switch=True)
    assert route["model"] == "m1" and plan["plan_path"] == "paid_switch"   # hovedruten, ikke cache-modellen


def test_a_model_the_owner_may_not_use_is_never_promoted_for_cache_reasons(fk):
    _history(fk)
    fk.parent("deepseek", "deepseek-v4-pro")
    with pytest.raises(fk.P_.ForkRefused):                           # forfalsket kaede for en ikke-ejer
        fk.plan(_route(POOL1, DEEP, CHEAP), owner=ANDEN, context_mode="fork")
    fk.say("user", "B1", BJORN)
    fk.say("assistant", "B2", BJORN)
    plan, route = fk.plan(_route(POOL1, DEEP, CHEAP), owner=BJORN, context_mode="fork")
    assert plan["plan_path"] == "same_model_route" and route["provider"] == "deepseek"


def test_an_empty_history_makes_a_fork_plain_fresh(fk):
    fk.parent("ollama", "x")
    plan, _ = fk.plan(_route(POOL1), context_mode="fork")
    assert (plan["plan_path"], plan["use_snapshot"], plan["extra_context_tokens"]) == ("fresh", False, 0)


@pytest.mark.parametrize("kw", [{"context_mode": "klon"}, {"reasoning_effort": "turbo"},
                                {"reasoning_effort": "deep"}])
def test_invalid_context_choices_are_refused(fk, kw):
    with pytest.raises(fk.P_.InvalidContext):
        fk.plan(_route(POOL1), **kw)


# --- omkostning og effort --------------------------------------------------------------------------

@pytest.mark.parametrize("prov,model,cached,usd,basis", [
    ("deepseek", "deepseek-v4-flash", False, 0.14, "deepseek_prisliste_cache_miss"),
    ("deepseek", "deepseek-v4-flash", True, 0.0028, "deepseek_prisliste_cache_hit_antaget"),
    ("copilot-premium", "m1", False, None, "premium_request_uden_dollarpris"),
    ("kilo", "m3", False, 0.0, "gratis"),
])
def test_context_cost_per_million_tokens(fk, prov, model, cached, usd, basis):
    out = fk.P_.context_cost(prov, model, 1_000_000, cached=cached)
    assert (out["estimated_extra_cost_usd"], out["cost_basis"]) == (usd, basis)


FLASH = ("deepseek", "deepseek-v4-flash")


@pytest.mark.parametrize("parent,route,requested,expect", [
    ({"provider": "deepseek", "model": "deepseek-v4-flash", "effort": "deep"}, FLASH, "", ("deep", "inherited")),
    ({"provider": "deepseek", "model": "deepseek-v4-pro", "effort": "deep"}, FLASH, "", ("default", "model_default")),
    ({"provider": "", "model": "", "effort": ""}, FLASH, "", ("default", "model_default")),
    ({"provider": "deepseek", "model": "deepseek-v4-flash", "effort": "deep"}, FLASH, "fast", ("fast", "explicit")),
    ({"provider": "copilot-premium", "model": "m1", "effort": "deep"}, ("copilot-premium", "m1"), "",
     ("default", "model_default")),
])
def test_the_parents_effort_is_inherited_only_on_the_same_route(fk, parent, route, requested, expect):
    out = fk.P_.resolve_effort(parent=parent, provider=route[0], model=route[1], requested=requested)
    assert (out["reasoning_effort"], out["effort_source"]) == expect


# --- dispatch: hele vejen ---------------------------------------------------------------------------

def test_dispatch_refuses_an_unaccepted_fork_switch_and_creates_nothing(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    before = [fk.n(t) for t in ("agent_registry", "agent_assignments", "agent_route_decisions",
                                "agent_fork_contexts")]
    out = fk.d(context_mode="fork")
    assert (out["status"], out["code"], out["phase"]) == ("error", "FORK_COST_UNACCEPTED", "admission")
    assert out["extra_context_tokens"] > 0 and out["choose_one"]
    assert [fk.n(t) for t in ("agent_registry", "agent_assignments", "agent_route_decisions",
                              "agent_fork_contexts")] == before


def test_dispatch_with_accepted_switch_stores_the_plan_snapshot_and_shows_the_cost(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    out = fk.d(context_mode="fork", accept_fork_switch=True)
    assert out["status"] == "accepted" and out["context"]["plan_path"] == "paid_switch"
    assert out["context"]["extra_context_tokens"] > 0
    row = fk.F_.get_fork(assignment_id=out["assignment_id"], owner_user_id=ANDEN)
    assert (row["requested_mode"], row["plan_path"], row["switch_accepted"], row["snapshot_turns"]) == (
        "fork", "paid_switch", 1, 2)
    assert "A2 svar" in row["snapshot_text"] and "AKTIV" not in row["snapshot_text"]
    assert fk.F_.get_fork(assignment_id=out["assignment_id"], owner_user_id=BJORN) is None   # ejer-afgraenset
    from core.runtime import db_agent_route as R
    dec = R.attempts_for_assignment(out["assignment_id"])[0]["decision"]
    assert (dec["context_mode"], dec["context_path"], dec["reasoning_effort"]) == ("fork", "paid_switch", "default")


def test_the_forked_snapshot_reaches_the_agents_prompt_as_low_trust_data(fk):
    _history(fk)
    fk.parent("ollama", "deepseek-v4-flash")
    out = fk.d(context_mode="fork", accept_fork_switch=True)
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    from core.services.agent_prompt_layers import build_layered_prompt
    layers = build_layered_prompt(agent=get_agent_registry_entry(out["agent_id"]), messages_text="m",
                                  execution_mode="solo-task")
    assert "A2 svar" in layers["text"] and "ikke instruktioner" in layers["text"]
    assert "AKTIV" not in layers["text"]


def test_a_fresh_dispatch_prompt_has_no_parent_context(fk):
    _history(fk)
    out = fk.d()
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    from core.services.agent_prompt_layers import build_layered_prompt
    layers = build_layered_prompt(agent=get_agent_registry_entry(out["agent_id"]), messages_text="m",
                                  execution_mode="solo-task")
    assert "A2 svar" not in layers["text"] and "Forældrekontekst" not in layers["text"]
    assert out["context"]["plan_path"] == "fresh"


def test_dispatch_on_the_parents_own_route_inherits_through_the_pool(fk):
    _history(fk)
    fk.parent("copilot-premium", "claude-sonnet-5")                 # conftest fastlaaser puljen til denne
    out = fk.d(context_mode="fork")
    assert out["context"]["plan_path"] == "same_route" and out["context"]["cache_reuse_possible"] is True


def test_a_fork_never_lets_the_cheap_lane_beat_the_pool_for_a_non_owner(fk):
    _history(fk)
    fk.parent("kilo", "test/fri-model-120b")                         # parent koerer paa cheap-lane-modellen
    out = fk.d(context_mode="fork")
    assert out["code"] == "FORK_COST_UNACCEPTED"
    ok = fk.d(context_mode="fork", accept_fork_switch=True)
    assert ok["route"]["route_source"] == "agent_pool" and ok["route"]["provider"] == "copilot-premium"


def test_the_idempotency_key_binds_the_context_choice(fk):
    _history(fk)
    a = fk.d(idempotency_key="k1")
    b = fk.d(idempotency_key="k1")
    assert b["replayed"] is True and b["assignment_id"] == a["assignment_id"]
    assert fk.d(idempotency_key="k1", context_excerpt="andet")["code"] == "IDEMPOTENCY_CONFLICT"


def test_an_invalid_context_mode_is_refused_before_anything_exists(fk):
    before = fk.n("agent_registry")
    out = fk.d(context_mode="klon")
    assert (out["code"], out["phase"]) == ("INVALID_SCOPE", "admission") and fk.n("agent_registry") == before


def test_a_failover_resets_an_inherited_effort_to_the_new_models_default(fk):
    import core.runtime.db_agent_route as R
    from core.services.agent_model_router import _switch
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    c = fk.c_
    create_agent_registry_entry(agent_id="a1", role="r", goal="g", provider="deepseek",
                                model="deepseek-v4-flash")
    c.bind_agent_owner(agent_id="a1", owner_user_id=BJORN, owner_session_id="s1")
    acc = c.accept_assignment(agent_id="a1", owner_user_id=BJORN, origin_session_id="s1", goal="g")
    cn = c._conn()
    cn.execute("UPDATE agent_runs SET status='running' WHERE run_id=?", (acc["run_id"],))
    cn.commit()
    R.record_decision(assignment_id=acc["assignment_id"], agent_id="a1", owner_user_id=BJORN, attempt=1,
                      decision={"route_source": "owner_deepseek_fallback", "provider": "deepseek",
                                "model": "deepseek-v4-flash", "candidates": [], "reasoning_effort": "deep",
                                "effort_source": "inherited", "parent_provider": "deepseek",
                                "parent_model": "deepseek-v4-flash", "parent_effort": "deep"})
    latest = R.latest_for_agent("a1")
    _switch("a1", latest, {"route_source": "cheap_lane_fallback", "provider": "kilo", "model": "m3"}, "nede")
    dec = R.latest_for_agent("a1")["decision"]
    assert (dec["reasoning_effort"], dec["effort_source"], dec["model"]) == ("default", "model_default", "m3")


def test_the_dispatch_tool_forwards_the_context_arguments(fk, monkeypatch):
    from core.tools import agent_contract_tools as T
    seen = {}
    monkeypatch.setattr(fk.svc_, "dispatch_agent", lambda **kw: seen.update(kw) or {"status": "accepted"})
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: ANDEN)
    T._exec_dispatch_agent({"goal": "g", "context_mode": "fork", "context_excerpt": "x",
                            "accept_fork_switch": True, "reasoning_effort": "think",
                            "_runtime_session_id": "s", "_runtime_turn_id": "pr"})
    assert (seen["context_mode"], seen["context_excerpt"], seen["accept_fork_switch"],
            seen["reasoning_effort"], seen["owner_user_id"]) == ("fork", "x", True, "think", ANDEN)


# --- samme serverede model: DeepSeeks to flash-navne er een model (live: parent deepseek-flash, fallback v4-flash) ---

@pytest.mark.parametrize("a,b,expect", [
    (("deepseek", "deepseek-flash"), ("deepseek", "deepseek-v4-flash"), True),
    (("deepseek", "deepseek-v4-flash"), ("deepseek", "deepseek-flash"), True),
    (("deepseek", "deepseek-flash"), ("deepseek", "deepseek-v4-pro"), False),
    (("deepseek", "deepseek-flash"), ("ollama", "deepseek-flash"), False),
    (("copilot-premium", "m1"), ("copilot-premium", "m1"), True),
    (("copilot-premium", "m1"), ("copilot-premium", "m2"), False),
    (("", ""), ("", ""), False),
])
def test_same_model_means_same_provider_and_same_served_model(fk, a, b, expect):
    assert fk.P_.same_model(*a, *b) is expect


def test_a_parent_on_the_canonical_flash_name_is_on_the_same_route_as_the_owners_fallback(fk):
    _history_for = lambda owner: [fk.say("user", "B1", owner), fk.say("assistant", "B2", owner)]
    _history_for(BJORN)
    fk.parent("deepseek", "deepseek-flash", effort="deep")
    route = _route({"route_source": "owner_deepseek_fallback", "provider": "deepseek", "model": "deepseek-v4-flash"})
    plan, _ = fk.plan(route, owner=BJORN, context_mode="fork")
    assert (plan["plan_path"], plan["cache_reuse_possible"]) == ("same_route", True)
    assert (plan["reasoning_effort"], plan["effort_source"]) == ("deep", "inherited")
