"""D: premium-agentpulje -> ejerafhaengig fallback. Rigtig katalog, rigtig sqlite; kun kandidatlisten styres."""
from __future__ import annotations

import pytest

BJORN, ANDEN = "bjorn-id", "anden-bruger"


@pytest.fixture
def pol(isolated_runtime, monkeypatch):
    from core.services import agent_model_policy as P

    class H:
        P_ = P
        configured: list[dict] = []

        def cands(self, *models):
            """models: (provider, model) - alle med klare credentials."""
            self.configured = [{"provider": p, "model": m, "credentials_ready": True, "priority": 10 + i}
                               for i, (p, m) in enumerate(models)]

        def route(self, owner=ANDEN, **kw):
            return P.decide_route(owner_user_id=owner, **kw)

        def budget(self, cap=10.0, spent=0.0):
            monkeypatch.setattr("core.services.cost_optimization_daemon._load_budgets",
                                lambda: {"cost_daily_budget_usd": cap})
            monkeypatch.setattr("core.costing.ledger.today_cost", lambda: spent)

    h = H()
    # den nederste soem: katalogets kandidater. central_route._scored_candidates koerer rigtigt ovenpaa
    monkeypatch.setattr("core.services.cheap_provider_runtime_selection._configured_cheap_candidates",
                        lambda **kw: list(h.configured))
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: BJORN)
    monkeypatch.setattr("core.services.central_route_headroom.headroom_ok", lambda p: True)
    h.budget()
    return h


PREMIUM = ("copilot-premium", "claude-sonnet-5")
PREMIUM2 = ("copilot-premium", "gpt-5.2")
FREE = ("kilo", "tencent/fri-model-120b:free")


# --- puljen: samme for Bjoern og en anden bruger ------------------------------------------------

@pytest.mark.parametrize("owner", [BJORN, ANDEN])
def test_the_premium_pool_serves_both_owners_with_provenance(pol, owner):
    pol.cands(PREMIUM, FREE)
    d = pol.route(owner)
    assert (d["route_source"], d["provider"], d["model"], d["owner_user_id"]) == (
        "agent_pool", "copilot-premium", "claude-sonnet-5", owner)
    assert d["candidates"][0] == {"route_source": "agent_pool", "provider": "copilot-premium",
                                  "model": "claude-sonnet-5"}
    assert d["contract"] == "agent-route-v1" and d["decided_at"] and d["hard"] is False


def test_one_failing_top_model_is_not_exhaustion_the_next_pool_model_is_tried_first(pol, monkeypatch):
    pol.cands(PREMIUM, PREMIUM2, FREE)
    monkeypatch.setattr("core.services.agent_model_fitness.er_blokeret",
                        lambda p, m, rolle="": m == "claude-sonnet-5")
    d = pol.route(ANDEN)
    assert (d["route_source"], d["model"]) == ("agent_pool", "gpt-5.2")
    assert {"stage": "agent_pool", "provider": "copilot-premium", "model": "claude-sonnet-5",
            "reason": "fitness:maalt_uegnet"} in d["rejected"]


def test_the_chain_puts_every_pool_model_before_the_owners_fallback(pol):
    pol.cands(PREMIUM, PREMIUM2, FREE)
    assert [(c["route_source"], c["model"]) for c in pol.route(ANDEN)["candidates"]] == [
        ("agent_pool", "claude-sonnet-5"), ("agent_pool", "gpt-5.2"),
        ("cheap_lane_fallback", "tencent/fri-model-120b:free")]
    assert [(c["route_source"], c["provider"]) for c in pol.route(BJORN)["candidates"]] == [
        ("agent_pool", "copilot-premium"), ("agent_pool", "copilot-premium"),
        ("owner_deepseek_fallback", "deepseek")]


# --- udtoemt pulje: ejerafhaengig fallback -------------------------------------------------------

def test_exhausted_pool_gives_bjorn_deepseek_and_everyone_else_the_cheap_lane(pol):
    pol.cands(FREE)                                   # ingen premium-kandidater
    b, a = pol.route(BJORN), pol.route(ANDEN)
    assert (b["route_source"], b["provider"]) == ("owner_deepseek_fallback", "deepseek")
    assert (a["route_source"], a["provider"], a["model"]) == ("cheap_lane_fallback", "kilo", FREE[1])
    assert all(c["provider"] != "deepseek" for c in a["candidates"])


def test_deepseek_is_priced_before_start_and_premium_is_reported_as_unpriced(pol):
    pol.cands(FREE)
    b = pol.route(BJORN, budget_tokens=100_000)
    assert b["cost_basis"] == "deepseek_prisliste" and b["estimated_cost_usd"] > 0 and b["tokens"] == 100_000
    pol.cands(PREMIUM)
    p = pol.route(ANDEN)
    assert (p["estimated_cost_usd"], p["cost_basis"]) == (None, "premium_request_uden_dollarpris")
    pol.cands(FREE, ("copilot-premium", "claude-sonnet-5"))
    pol.configured = [c for c in pol.configured if c["provider"] != "copilot-premium"]
    assert pol.route(ANDEN)["estimated_cost_usd"] == 0.0


@pytest.mark.parametrize("owner,setup,expected", [
    (BJORN, lambda h: (h.cands(FREE), h.budget(cap=1.0, spent=1.0)), "budget:dagsloftet_naaet"),
    (BJORN, lambda h: (h.cands(FREE), h.budget(cap=0.0)), "budget:ukendt_dagsloft"),
    (ANDEN, lambda h: h.cands(), "ingen_egnet_kandidat"),
])
def test_when_the_relevant_fallback_is_unusable_the_answer_is_model_unavailable_with_reasons(
        pol, owner, setup, expected):
    setup(pol)
    with pytest.raises(pol.P_.ModelUnavailable) as e:
        pol.route(owner)
    assert e.value.code == "MODEL_UNAVAILABLE"
    assert any(expected in r["reason"] for r in e.value.reasons), e.value.reasons


# --- eksplicit model ------------------------------------------------------------------------------

def test_an_explicit_pool_model_is_honoured_and_a_hard_unknown_model_fails_clearly(pol):
    pol.cands(PREMIUM, PREMIUM2, FREE)
    d = pol.route(ANDEN, requested_model="copilot-premium/gpt-5.2", hard=True)
    assert (d["route_source"], d["model"], len(d["candidates"])) == ("explicit", "gpt-5.2", 1)
    with pytest.raises(pol.P_.ModelUnavailable) as e:
        pol.route(ANDEN, requested_model="copilot-premium/findes-ikke", hard=True)
    assert e.value.reasons[0]["reason"] == "ikke_i_ejerens_tilladte_ruter"
    soft = pol.route(ANDEN, requested_model="copilot-premium/findes-ikke")
    assert soft["route_source"] == "agent_pool" and soft["rejected"][0]["stage"] == "explicit"


@pytest.mark.parametrize("owner", [BJORN, ANDEN])
def test_explicit_deepseek_neither_skips_the_pool_nor_unlocks_anything(pol, owner):
    pol.cands(PREMIUM, FREE)
    with pytest.raises(pol.P_.ModelUnavailable) as e:
        pol.route(owner, requested_model="deepseek/deepseek-v4-pro", hard=True)
    assert e.value.reasons[0]["reason"] in ("agentpuljen_har_en_egnet_kandidat",
                                            "deepseek_er_kun_for_platformens_ejer")
    soft = pol.route(owner, requested_model="deepseek-v4-pro")
    assert soft["route_source"] == "agent_pool" and soft["provider"] == "copilot-premium"
    assert not (soft["candidates"][0]["provider"] == "deepseek")


def test_bjorn_gets_the_requested_deepseek_model_only_when_the_pool_is_empty(pol):
    pol.cands(FREE)
    d = pol.route(BJORN, requested_model="deepseek/deepseek-v4-pro", hard=True)
    assert (d["route_source"], d["provider"], d["model"]) == (
        "owner_deepseek_fallback", "deepseek", "deepseek-v4-pro")
    with pytest.raises(pol.P_.ModelUnavailable):
        pol.route(ANDEN, requested_model="deepseek/deepseek-v4-pro", hard=True)


@pytest.mark.parametrize("forged", ["", "   "])
def test_a_missing_owner_gets_no_route_at_all(pol, forged):
    pol.cands(FREE)
    with pytest.raises(pol.P_.ModelUnavailable) as e:
        pol.route(forged)
    assert e.value.reasons[0]["reason"] == "owner_ukendt"


@pytest.mark.parametrize("forged", ["bjorn", "admin", BJORN.upper(), " " + BJORN[:-1]])
def test_a_forged_owner_id_never_reaches_deepseek(pol, forged):
    pol.cands(FREE)
    d = pol.route(forged)
    assert d["route_source"] == "cheap_lane_fallback"
    assert all(c["provider"] != "deepseek" for c in d["candidates"])
    assert pol.P_.is_platform_owner(forged) is False


# --- kontrollen ved providerkaldet ----------------------------------------------------------------

@pytest.mark.parametrize("owner,ok", [(BJORN, True), (ANDEN, False), ("", False)])
def test_guard_call_is_the_check_at_the_provider_call(pol, owner, ok):
    P = pol.P_
    if ok:
        P.guard_call(owner_user_id=owner, provider="deepseek", model="deepseek-v4-flash")
    else:
        with pytest.raises(P.ProviderDenied):
            P.guard_call(owner_user_id=owner, provider="deepseek", model="deepseek-v4-flash")
    P.guard_call(owner_user_id=owner or "x", provider="copilot-premium", model="m") if owner else None


# --- dispatch: ruten fastlaegges foer agenten oprettes ----------------------------------------------

@pytest.fixture
def dsp(pol, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.services import in_flight_runs as ifr

    started: list = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    svc.set_capability(True, role="owner")
    ifr._mutate(lambda r: r.clear())

    class H:
        c_, svc_ = c, svc

        def d(self, owner=ANDEN, **kw):
            base = dict(owner_user_id=owner, origin_session_id="s1", goal="find X", parent_run_id="pr")
            base.update(kw)
            return svc.dispatch_agent(**base)

        def n(self, table):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    yield pol, H()
    ifr._mutate(lambda r: r.clear())


def test_a_refused_route_creates_no_half_child(dsp):
    pol, h = dsp
    pol.cands()                                       # hverken pulje eller cheap lane
    before = (h.n("agent_registry"), h.n("agent_assignments"), h.n("agent_route_decisions"))
    out = h.d()
    assert (out["status"], out["code"], out["phase"]) == ("error", "MODEL_UNAVAILABLE", "admission")
    assert out["reasons"] and (h.n("agent_registry"), h.n("agent_assignments"),
                               h.n("agent_route_decisions")) == before


def test_an_accepted_dispatch_stores_the_decision_and_the_agent_runs_on_that_model(dsp):
    pol, h = dsp
    pol.cands(PREMIUM, FREE)
    out = h.d()
    assert out["status"] == "accepted" and out["route"] == {
        "route_source": "agent_pool", "provider": "copilot-premium", "model": "claude-sonnet-5"}
    from core.runtime import db_agent_route as r
    rows = r.attempts_for_assignment(out["assignment_id"])
    assert [(x["attempt"], x["route_source"], x["owner_user_id"]) for x in rows] == [(1, "agent_pool", ANDEN)]
    assert rows[0]["decision"]["candidates"] and rows[0]["decision"]["rejected"] == []
    reg = h.c_._conn().execute("SELECT provider, model FROM agent_registry WHERE agent_id=?",
                               (out["agent_id"],)).fetchone()
    assert (reg["provider"], reg["model"]) == ("copilot-premium", "claude-sonnet-5")


def test_a_forged_deepseek_request_through_dispatch_is_refused_before_anything_exists(dsp):
    pol, h = dsp
    pol.cands(FREE)
    before = h.n("agent_registry")
    out = h.d(ANDEN, model="deepseek/deepseek-v4-pro", model_required=True)
    assert out["code"] == "MODEL_UNAVAILABLE" and h.n("agent_registry") == before
    ok = h.d(ANDEN, model="deepseek/deepseek-v4-pro")             # praeference: ignoreres, ikke indroemmet
    assert ok["status"] == "accepted" and ok["route"]["provider"] == "kilo"
    assert h.d(BJORN, model="deepseek/deepseek-v4-pro", model_required=True)["route"]["provider"] == "deepseek"


def test_model_required_is_part_of_the_idempotency_digest(dsp):
    pol, h = dsp
    pol.cands(PREMIUM, FREE)
    a = h.d(idempotency_key="k1", model="copilot-premium/claude-sonnet-5")
    b = h.d(idempotency_key="k1", model="copilot-premium/claude-sonnet-5", model_required=True)
    assert a["status"] == "accepted" and b["code"] == "IDEMPOTENCY_CONFLICT"


def test_the_agent_is_created_on_exactly_the_decided_provider_and_model_not_spawns_own_pick(dsp):
    pol, h = dsp
    pol.cands(PREMIUM, PREMIUM2, FREE)                # spawn ville selv vaelge PREMIUM (hoejeste kapabilitet)
    out = h.d(model="copilot-premium/gpt-5.2", model_required=True)
    reg = h.c_._conn().execute("SELECT provider, model FROM agent_registry WHERE agent_id=?",
                               (out["agent_id"],)).fetchone()
    assert out["route"]["model"] == "gpt-5.2" and (reg["provider"], reg["model"]) == (
        "copilot-premium", "gpt-5.2")


def test_the_owners_own_requirement_is_the_first_reason_and_a_long_rejection_list_is_capped(pol, monkeypatch):
    many = [("copilot-premium", f"modeller-{i}") for i in range(60)]
    pol.cands(*many, FREE)
    monkeypatch.setattr("core.services.agent_model_fitness.er_blokeret", lambda p, m, rolle="": m != "x")
    with pytest.raises(pol.P_.ModelUnavailable) as e:
        pol.route(ANDEN, requested_model="deepseek/deepseek-v4-pro", hard=True)
    assert e.value.reasons[0]["reason"] == "deepseek_er_kun_for_platformens_ejer"
    assert len(e.value.reasons) == pol.P_.MAX_REJECTED + 1
    assert e.value.reasons[-1]["reason"].endswith("_flere_afvisninger_udeladt")
    pol.cands(*many, PREMIUM, FREE)
    monkeypatch.setattr("core.services.agent_model_fitness.er_blokeret", lambda p, m, rolle="": m.startswith("modeller-"))
    d = pol.route(ANDEN)
    assert d["rejected_total"] == 60 and len(d["rejected"]) == pol.P_.MAX_REJECTED + 1
