"""F2: de modelvendte agent-vaerktoejer - udvalg, fast flade, ejer fra kontekst, routing."""
from __future__ import annotations

import pytest

NEW = ("dispatch_agent", "followup_agent", "wait_agents", "interrupt_agent", "close_agent", "integrate_agent_work")
ALL7 = ("dispatch_agent", "send_message_to_agent", "followup_agent", "list_agents",
        "wait_agents", "interrupt_agent", "close_agent", "integrate_agent_work")      # (spec'ens syv + integration)


@pytest.fixture
def tl(isolated_runtime, monkeypatch):
    import core.services.agent_contract_service as svc
    from core.identity import workspace_context as w
    from core.services import agent_runtime_spawn as M
    from core.services import in_flight_runs as ifr
    from core.tools import agent_contract_tools as t

    class H:
        t_, svc_ = t, svc
        started: list = []

        def on(self):
            svc.set_capability(True, role="owner")

        def as_user(self, uid="bjorn"):
            self._tok = w.set_context(workspace_name="bjorn", user_id=uid)

        def args(self, **kw):
            return {"_runtime_session_id": "sess-1", "_runtime_turn_id": "visible-p", **kw}

    h = H()
    h.started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: h.started.append(fn))

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            return {"text": "klart", "input_tokens": 1, "output_tokens": 1, "status": "completed"}

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_facade", lambda: _F())
    ifr._mutate(lambda r: r.clear())
    h.as_user()
    yield h
    ifr._mutate(lambda r: r.clear())
    w.reset_context(h._tok)


def _visible(role="owner", scope=""):
    from core.tools.simple_tools import get_tool_definitions
    return {d["function"]["name"] for d in get_tool_definitions(role=role, scope=scope)}


# --- definitioner og synlighed ------------------------------------------------------

def test_definitions_are_wellformed_and_required_fields_exist():
    from core.tools.agent_contract_tools import AGENT_CONTRACT_TOOL_DEFINITIONS as defs

    assert tuple(d["function"]["name"] for d in defs) == NEW
    for d in defs:
        p = d["function"]["parameters"]
        assert d["type"] == "function" and d["function"]["description"]
        assert set(p["required"]) <= set(p["properties"])
    by = {d["function"]["name"]: d["function"]["parameters"] for d in defs}
    assert by["dispatch_agent"]["required"] == ["goal"]
    assert by["wait_agents"]["properties"]["condition"]["enum"] == ["first_terminal", "all_terminal"]
    tgt = by["dispatch_agent"]["properties"]["target"]
    assert "enum" not in tgt and "client:<stable_client_id>" in tgt["description"] and "runtime-container" in tgt["description"]


def test_new_tools_are_hidden_while_the_engine_is_off_and_shown_when_on(tl):
    assert not set(NEW) & _visible()
    assert {"send_message_to_agent", "list_agents"} <= _visible()      # de gamle forsvinder aldrig
    tl.on()
    assert set(NEW) <= _visible()
    tl.svc_.set_capability(False)
    assert not set(NEW) & _visible()


def test_capability_read_failure_hides_the_tools(tl, monkeypatch):
    import core.runtime.db_core as core

    tl.on()
    monkeypatch.setattr(core, "get_runtime_state_bool",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db")))
    assert not set(NEW) & _visible()


@pytest.mark.parametrize("role", ["member", "guest"])
def test_non_owner_roles_never_get_the_new_tools_yet(tl, role):
    tl.on()
    assert not set(NEW) & _visible(role=role)


def test_handlers_are_registered_for_all_tools():
    from core.tools.simple_tools import _TOOL_HANDLERS

    assert all(n in _TOOL_HANDLERS for n in ALL7)


# --- fast flade -----------------------------------------------------------------------

def test_pinned_set_is_empty_when_off_and_all_seven_when_on(tl):
    from core.tools.copilot_tool_pruning import agent_contract_pinned

    assert agent_contract_pinned() == ()
    tl.on()
    assert agent_contract_pinned() == ALL7


def test_visible_pool_pins_all_seven_without_load_more_tools_and_is_message_independent(tl):
    from core.tools.copilot_tool_pruning import select_tools_for_visible
    from core.tools.simple_tools import get_tool_definitions

    defs = get_tool_definitions(role="owner", scope="")
    off = {d["function"]["name"] for d in select_tools_for_visible(defs, user_message="hej")}
    assert not set(NEW) & off
    tl.on()
    defs = get_tool_definitions(role="owner", scope="")
    a = [d["function"]["name"] for d in select_tools_for_visible(defs, user_message="hej")]
    b = [d["function"]["name"] for d in select_tools_for_visible(defs, user_message="refaktorer kode")]
    assert set(ALL7) <= set(a) and a == b          # byte-stabilt array -> prefiks-cachen holder
    assert len(a) <= 48


def test_session_pin_union_includes_the_seven_only_when_on(tl):
    from core.services.session_tool_pin import _med_garanterede

    assert not set(NEW) & set(_med_garanterede([]))
    tl.on()
    assert set(ALL7) <= set(_med_garanterede([]))


# --- adaptere --------------------------------------------------------------------------

def test_dispatch_tool_takes_the_owner_from_context_not_from_arguments(tl):
    tl.on()
    out = tl.t_._exec_dispatch_agent(tl.args(goal="find X", owner_user_id="anden",
                                             _runtime_user_id="anden"))
    assert out["status"] == "accepted"
    a = tl.svc_.c.get_assignment(assignment_id=out["assignment_id"], owner_user_id="bjorn")
    assert (a["owner_user_id"], a["origin_session_id"], a["parent_run_id"]) == (
        "bjorn", "sess-1", "visible-p")
    assert tl.svc_.c.get_assignment(assignment_id=out["assignment_id"], owner_user_id="anden") is None


def test_without_an_authenticated_owner_every_tool_is_refused(tl):
    from core.identity import workspace_context as w

    tl.on()
    w.set_context(workspace_name="bjorn", user_id="")
    for fn, extra in ((tl.t_._exec_dispatch_agent, {"goal": "x"}),
                      (tl.t_._exec_followup_agent, {"agent_id": "a", "goal": "x"}),
                      (tl.t_._exec_wait_agents, {"assignment_ids": ["a"]}),
                      (tl.t_._exec_interrupt_agent, {"agent_id": "a"}),
                      (tl.t_._exec_close_agent, {"agent_id": "a"})):
        out = fn(tl.args(**extra, _runtime_user_id="bjorn"))
        assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE"), fn.__name__
    assert tl.started == []


def test_full_tool_cycle_dispatch_wait_followup_close(tl):
    tl.on()
    d = tl.t_._exec_dispatch_agent(tl.args(goal="find X", idempotency_key="k"))
    again = tl.t_._exec_dispatch_agent(tl.args(goal="find X", idempotency_key="k"))
    assert again["replayed"] is True and again["assignment_id"] == d["assignment_id"]
    for f in list(tl.started):
        f()
    w = tl.t_._exec_wait_agents(tl.args(assignment_ids=[d["assignment_id"]]))
    assert w["satisfied"] is True
    f = tl.t_._exec_followup_agent(tl.args(agent_id=d["agent_id"], goal="nu y"))
    assert f["status"] == "accepted" and f["assignment_id"] != d["assignment_id"]
    for fn in list(tl.started[1:]):
        fn()
    c = tl.t_._exec_close_agent(tl.args(agent_id=d["agent_id"]))
    assert c["lifecycle_status"] == "closed"
    i = tl.t_._exec_interrupt_agent(tl.args(agent_id=d["agent_id"]))
    assert i["status"] == "noop"


def test_send_message_routes_bound_agents_to_the_contract_and_others_to_legacy(tl, monkeypatch):
    import core.tools.simple_tools_native as native

    seen = []
    monkeypatch.setattr(native, "_exec_send_message_to_agent", lambda a: seen.append(a) or {"legacy": 1})
    # slukket -> altid gammel
    assert tl.t_._exec_send_message_to_agent(tl.args(agent_id="x", content="hej")) == {"legacy": 1}
    tl.on()
    d = tl.t_._exec_dispatch_agent(tl.args(goal="find X"))
    out = tl.t_._exec_send_message_to_agent(tl.args(agent_id=d["agent_id"], content="husk edge"))
    assert out["status"] == "accepted" and out["message_id"] and len(seen) == 1
    # ukendt / ikke-bundet agent -> gammel
    assert tl.t_._exec_send_message_to_agent(tl.args(agent_id="agent-legacy", content="x")) == {"legacy": 1}
    assert len(seen) == 2


def test_list_agents_uses_the_contract_when_on_and_keeps_legacy_visible(tl, monkeypatch):
    import core.tools.simple_tools_native as native

    monkeypatch.setattr(native, "_exec_list_agents",
                        lambda a: {"status": "ok", "agents": [{"agent_id": "gammel"}], "count": 1})
    assert tl.t_._exec_list_agents(tl.args()) == {"status": "ok", "agents": [{"agent_id": "gammel"}], "count": 1}
    tl.on()
    d = tl.t_._exec_dispatch_agent(tl.args(goal="find X"))
    out = tl.t_._exec_list_agents(tl.args())
    assert [r["agent_id"] for r in out["agents"]] == [d["agent_id"]]
    assert out["legacy_agents"] == [{"agent_id": "gammel"}]


def test_an_error_while_deciding_the_capability_pins_nothing(tl, monkeypatch):
    monkeypatch.setattr(tl.svc_, "capability_enabled",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert tl.t_.contract_tool_names_advertised() == ()
    assert tl.t_.hidden_contract_tools() == tl.t_._NEW_ONLY
