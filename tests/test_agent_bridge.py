"""E: agenter paa et klient-target. Rigtig sqlite; broen er en kontrolleret soem (``dispatch=``)."""
from __future__ import annotations

import json

import pytest

OWNER, SESSION, CLIENT = "u1", "s1", "desk-1"


@pytest.fixture
def br(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_bridge as store
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import agent_bridge as B
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())

    class Wire:
        """Scriptede svar pr. kald; husker hvad der blev sendt."""
        def __init__(self): self.script, self.calls = [], []
        async def __call__(self, **kw):
            self.calls.append(kw)
            nxt = self.script.pop(0) if self.script else {"status": "ok", "result": "ok", "sent": True}
            return nxt

    class H:
        B_, store_, c_ = B, store, c
        wire = Wire()
        sleeps: list = []

        def agent(self, name="a1", target=f"client:{CLIENT}", owner=OWNER, session=SESSION, policy="client-operator"):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g", tool_policy=policy)
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                                      parent_agent_id="jarvis", parent_run_id="pr", target=target)
            conn = c._conn()                   # EN forbindelse: execute og commit paa hver sin taber skrivningen
            conn.execute("UPDATE agent_assignments SET status='active' WHERE assignment_id=?", (acc["assignment_id"],))
            conn.commit()
            return {"agent_id": name}, acc

        def tc(self, name="operator_read_file", args=None, call_id="call-1"):
            return {"id": call_id, "function": {"name": name, "arguments": json.dumps(args or {"path": "/x"})}}

        def run(self, agent, acc, tc=None, **kw):
            return B.invoke_tool_call(agent=agent, run_id=acc["run_id"], tc=tc or self.tc(),
                                      dispatch=self.wire, sleep=self.sleeps.append, **kw)

        def inv(self, iid=None):
            rows = c._conn().execute("SELECT * FROM agent_bridge_invocations ORDER BY created_at").fetchall()
            return [dict(r) for r in rows] if iid is None else dict(
                c._conn().execute("SELECT * FROM agent_bridge_invocations WHERE invocation_id=?", (iid,)).fetchone())

        def status(self, acc):
            r = c._conn().execute("SELECT status FROM agent_runs WHERE run_id=?", (acc["run_id"],)).fetchone()
            a = c._conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                                  (acc["assignment_id"],)).fetchone()
            return r["status"], a["status"]
    h = H()
    h.wire.script, h.wire.calls, h.sleeps[:] = [], [], []
    yield h
    ifr._mutate(lambda r: r.clear())


# --- target ------------------------------------------------------------------------------------

@pytest.mark.parametrize("target,expected", [
    ("runtime-container", ("container", "")), ("", ("container", "")), ("client:desk-1", ("client", "desk-1")),
    ("client:a.b_c-1", ("client", "a.b_c-1")),
])
def test_valid_targets(br, target, expected):
    assert br.B_.parse_target(target) == expected


@pytest.mark.parametrize("target", ["client:", "client:../x", "client:a b", "client:" + "x" * 200, "other", "client:-x"])
def test_invalid_targets_are_refused(br, target):
    with pytest.raises(ValueError):
        br.B_.parse_target(target)


def test_check_client_target_refuses_offline_wrong_capabilities_and_all_writes(br, monkeypatch):
    info = {}
    monkeypatch.setattr("core.services.agent_bridge_dispatch.client_info", lambda u, c: info.get(c))
    chk = lambda target=f"client:{CLIENT}", writes=False: br.B_.check_client_target(  # noqa: E731
        owner_user_id=OWNER, target=target, writes=writes)
    assert chk(target="runtime-container") is None
    assert chk()["code"] == "CLIENT_OFFLINE"
    assert chk(target="client:../x")["code"] == "INVALID_SCOPE"
    info[CLIENT] = {"capabilities": ["phone_location"]}
    assert chk()["code"] == "INVALID_SCOPE"
    info[CLIENT] = {"capabilities": ["operator_read_file"]}
    assert chk() is None
    assert chk(writes=True)["code"] == "INVALID_SCOPE" and "annoncerer ikke" in chk(writes=True)["detail"]
    info[CLIENT] = {"capabilities": ["operator_read_file", "agent_worktree"]}
    assert "ikke bygget" in chk(writes=True)["detail"]            # selv med kapabilitet: intet falsk worktree


def test_allowed_tools_are_only_what_the_client_announces_and_default_to_reads(br, monkeypatch):
    monkeypatch.setattr("core.services.agent_bridge_dispatch.client_info", lambda u, c: {
        "capabilities": ["operator_read_file", "operator_write_file", "operator_bash", "phone_location"]})
    a = br.B_.allowed_tools_for_client
    assert a(OWNER, f"client:{CLIENT}", None) == ["operator_read_file"]
    assert a(OWNER, f"client:{CLIENT}", ["operator_write_file", "operator_bash", "operator_ikke_annonceret",
                                         "bash", "phone_location"]) == ["operator_bash", "operator_write_file"]


# --- ikke-klient-agenter roeres ikke ------------------------------------------------------------

def test_a_container_agent_and_a_legacy_agent_are_not_routed_over_the_bridge(br):
    ag, acc = br.agent(target="runtime-container")
    assert br.run(ag, acc) is None
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    create_agent_registry_entry(agent_id="legacy", role="researcher", goal="g")
    assert br.B_.invoke_tool_call(agent={"agent_id": "legacy"}, run_id="r", tc=br.tc(), dispatch=br.wire) is None
    assert br.wire.calls == [] and br.inv() == []


def test_a_bound_agent_with_a_blank_session_is_refused_not_defaulted(br):
    ag, acc = br.agent()
    conn = br.c_._conn()
    conn.execute("UPDATE agent_assignments SET origin_session_id='_default' WHERE assignment_id=?",
                 (acc["assignment_id"],))
    conn.commit()
    out = json.loads(br.run(ag, acc))
    assert (out["status"], out["code"], out["phase"]) == ("error", "INVALID_SCOPE", "bridge")
    assert br.wire.calls == []


# --- det normale kald ---------------------------------------------------------------------------

def test_a_read_goes_to_the_bound_client_with_owner_and_target_from_the_assignment(br):
    ag, acc = br.agent()
    out = json.loads(br.run(ag, acc, br.tc(args={"path": "/etc/hosts", "_runtime_user_id": "angriber",
                                                  "_operator_workspace_root": "/"})))
    assert out["status"] == "ok" and out["result"] == "ok"
    call = br.wire.calls[0]
    assert (call["user_id"], call["client_id"], call["tool"]) == (OWNER, CLIENT, "operator_read_file")
    assert call["args"] == {"path": "/etc/hosts"}                 # underscore-felter fra modellen er fjernet
    assert call["extra"]["invocation_id"] == out["invocation_id"] and call["extra"]["idempotency_class"] == "read"
    row = br.inv(out["invocation_id"])
    assert (row["state"], row["owner_user_id"], row["origin_session_id"], row["client_id"]) == (
        "succeeded", OWNER, SESSION, CLIENT)


def test_a_non_operator_tool_is_denied_and_never_runs_in_the_container(br):
    ag, acc = br.agent()
    for name in ("bash", "read_file", "wt_bash", "", "operator"):
        out = json.loads(br.run(ag, acc, br.tc(name=name)))
        assert (out["code"], out["phase"]) == ("POLICY_DENIED", "bridge"), name
    assert br.wire.calls == [] and br.inv() == []


def test_a_client_handler_error_is_a_known_failed_outcome_not_unknown(br):
    ag, acc = br.agent()
    br.wire.script = [{"status": "error", "error": "ENOENT: /x", "sent": True}]
    out = json.loads(br.run(ag, acc))
    assert (out["code"], out["error"]) == ("TOOL_FAILED", "ENOENT: /x")
    assert br.inv()[0]["state"] == "failed" and br.status(acc) == ("queued", "active")


def test_the_same_tool_call_after_success_returns_the_stored_result_without_a_second_send(br):
    ag, acc = br.agent()
    br.wire.script = [{"status": "ok", "result": {"n": 1}, "sent": True}]
    first = json.loads(br.run(ag, acc, br.tc(name="operator_write_file", call_id="same")))
    again = json.loads(br.run(ag, acc, br.tc(name="operator_write_file", call_id="same")))
    assert first["result"] == {"n": 1} and again == {"status": "ok", "result": {"n": 1}, "replayed": True}
    assert len(br.wire.calls) == 1


# --- klienten er vaek foer afsendelse ------------------------------------------------------------

def test_an_offline_client_is_retried_briefly_then_refused_and_nothing_runs_elsewhere(br):
    ag, acc = br.agent()
    br.wire.script = [{"status": "error", "error": "client_not_connected", "sent": False}] * 10
    out = json.loads(br.run(ag, acc))
    assert (out["code"], out["phase"]) == ("CLIENT_OFFLINE", "bridge")
    assert len(br.wire.calls) == br.B_.UNSENT_RETRIES + 1 and len(br.sleeps) == br.B_.UNSENT_RETRIES
    assert {c["client_id"] for c in br.wire.calls} == {CLIENT}
    assert br.inv()[0]["state"] == "failed" and br.status(acc) == ("queued", "active")


def test_the_client_returning_during_the_wait_lets_the_call_through(br):
    ag, acc = br.agent()
    br.wire.script = [{"status": "error", "error": "client_not_connected", "sent": False},
                      {"status": "ok", "result": "tilbage", "sent": True}]
    assert json.loads(br.run(ag, acc))["result"] == "tilbage"


# --- uafgjort udfald ------------------------------------------------------------------------------

TIMEOUT = {"status": "error", "error": "bridge_timeout", "sent": True}


def test_a_read_that_times_out_is_retried_with_the_same_id_and_then_succeeds(br):
    ag, acc = br.agent()
    br.wire.script = [TIMEOUT, {"status": "ok", "result": "andet forsoeg", "sent": True}]
    out = json.loads(br.run(ag, acc))
    assert out["result"] == "andet forsoeg"
    assert len({c["extra"]["invocation_id"] for c in br.wire.calls}) == 1 and len(br.wire.calls) == 2


def test_a_read_that_keeps_timing_out_ends_unknown_after_its_retries(br):
    ag, acc = br.agent()
    br.wire.script = [TIMEOUT] * 5
    with pytest.raises(br.B_.BridgeHalt):
        br.run(ag, acc)
    assert len(br.wire.calls) == 1 + br.B_.READ_RETRIES and br.inv()[0]["state"] == "outcome_unknown"


@pytest.mark.parametrize("err,sent", [("bridge_timeout", True), ("bridge_disconnected", True),
                                      ("bridge_forward_failed", None), ("bridge_call_cancelled", True)])
def test_a_write_without_receipt_is_never_retried_and_stops_the_run(br, err, sent):
    ag, acc = br.agent()
    br.wire.script = [{"status": "error", "error": err, "sent": sent}] * 3
    with pytest.raises(br.B_.BridgeHalt) as e:
        br.run(ag, acc, br.tc(name="operator_write_file", args={"path": "/x", "content": "y"}))
    assert len(br.wire.calls) == 1                                   # INGEN blind retry af en skrivning
    row = br.inv()[0]
    assert (row["state"], row["idem_class"], e.value.args[0]) == (
        "outcome_unknown", "write", f"OUTCOME_UNKNOWN:{row['invocation_id']}")
    assert br.status(acc) == ("outcome_unknown", "waiting")
    reg = br.c_._conn().execute("SELECT status, last_error FROM agent_registry WHERE agent_id='a1'").fetchone()
    assert reg["status"] == "outcome_unknown" and "OUTCOME_UNKNOWN" in reg["last_error"]
    assert br.B_.run_is_halted(acc["run_id"]) is True


def test_after_a_halt_every_further_client_call_for_the_assignment_is_refused(br):
    ag, acc = br.agent()
    br.wire.script = [TIMEOUT]
    with pytest.raises(br.B_.BridgeHalt):
        br.run(ag, acc, br.tc(name="operator_bash", args={"command": "rm -rf build"}, call_id="c1"))
    n = len(br.wire.calls)
    for name in ("operator_bash", "operator_read_file"):          # ogsaa en ren laesning: intet nyt ud til klienten
        with pytest.raises(br.B_.BridgeHalt):
            br.run(ag, acc, br.tc(name=name, args={"command": "rm -rf build"}, call_id="c-" + name))
    assert len(br.wire.calls) == n and len(br.inv()) == 1


def test_replaying_the_halted_call_after_a_restart_halts_again_without_sending(br):
    ag, acc = br.agent()
    br.wire.script = [TIMEOUT]
    tc = br.tc(name="operator_write_file", args={"path": "/x", "content": "y"}, call_id="c1")
    with pytest.raises(br.B_.BridgeHalt):
        br.run(ag, acc, tc)
    conn = br.c_._conn()
    conn.execute("UPDATE agent_runs SET status='running' WHERE run_id=?", (acc["run_id"],))
    conn.commit()
    with pytest.raises(br.B_.BridgeHalt):
        br.B_.invoke_tool_call(agent=ag, run_id=acc["run_id"], tc=tc, dispatch=br.wire)
    assert len(br.wire.calls) == 1


# --- afgoerelse -----------------------------------------------------------------------------------

def _halt(br, name="a1"):
    ag, acc = br.agent(name=name)
    br.wire.script = [TIMEOUT]
    with pytest.raises(br.B_.BridgeHalt):
        br.run(ag, acc, br.tc(name="operator_write_file", args={"path": "/x", "content": "y"}))
    return ag, acc, br.inv()[-1]["invocation_id"]


@pytest.mark.parametrize("status,words", [("completed", "var udfoert"), ("not_started", "blev IKKE udfoert")])
def test_the_clients_status_at_reconnect_settles_the_waiting_assignment(br, status, words):
    ag, acc, iid = _halt(br)
    out = br.B_.apply_client_report(owner_user_id=OWNER, client_id=CLIENT, reports=[
        {"invocation_id": iid, "status": status, "result": "ok"}])
    assert out[iid].startswith("verified_")
    a = br.c_._conn().execute("SELECT status, outcome_json FROM agent_assignments WHERE assignment_id=?",
                              (acc["assignment_id"],)).fetchone()
    assert a["status"] == "failed" and words in a["outcome_json"] and "Intet er genudfoert" in a["outcome_json"]
    assert br.c_._conn().execute("SELECT COUNT(*) FROM agent_result_outbox WHERE message_kind='terminal' AND assignment_id=?",
                                 (acc["assignment_id"],)).fetchone()[0] == 1   # praecis EN terminalbesked
    assert len(br.wire.calls) == 1                                   # intet blev sendt igen


def test_a_running_or_unknown_report_leaves_the_assignment_waiting(br):
    ag, acc, iid = _halt(br)
    for status in ("running", "unknown"):
        br.B_.apply_client_report(owner_user_id=OWNER, client_id=CLIENT, reports=[{"invocation_id": iid, "status": status}])
    assert br.status(acc) == ("outcome_unknown", "waiting")


def test_a_human_decision_settles_it_and_only_the_owner_may_make_it(br):
    ag, acc, iid = _halt(br)
    with pytest.raises(br.c_.ContractError):
        br.B_.human_resolve(invocation_id=iid, owner_user_id="u2", executed=True, actor_user_id="u2")
    assert br.status(acc)[1] == "waiting"
    row = br.B_.human_resolve(invocation_id=iid, owner_user_id=OWNER, executed=False, actor_user_id=OWNER)
    assert row["state"] == "human_resolved"
    a = br.c_._conn().execute("SELECT status, outcome_json FROM agent_assignments WHERE assignment_id=?",
                              (acc["assignment_id"],)).fetchone()
    assert a["status"] == "failed" and "afgjort som ikke udfoert" in a["outcome_json"]


def test_status_query_lists_only_this_owners_and_clients_unresolved_calls(br):
    ag, acc, iid = _halt(br)
    assert br.B_.status_query_for(OWNER, CLIENT) == [iid]
    assert br.B_.status_query_for(OWNER, "telefon-1") == [] and br.B_.status_query_for("u2", CLIENT) == []


# --- dispatch_agent --------------------------------------------------------------------------------

@pytest.fixture
def dsp(br, monkeypatch):
    import core.services.agent_contract_service as svc
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    svc.set_capability(True, role="owner")
    caps = {}
    monkeypatch.setattr("core.services.agent_bridge_dispatch.client_info", lambda u, c: caps.get((u, c)))

    class D:
        def d(self, **kw):
            base = dict(owner_user_id=OWNER, origin_session_id=SESSION, goal="laes en fil", parent_run_id="pr",
                        target=f"client:{CLIENT}")
            base.update(kw)
            return svc.dispatch_agent(**base)

        def n(self, t):
            return br.c_._conn().execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    d = D()
    d.caps, d.br = caps, br
    return d


def test_dispatch_to_an_offline_client_is_refused_and_creates_nothing(dsp):
    before = dsp.n("agent_registry")
    out = dsp.d()
    assert (out["status"], out["code"], out["phase"]) == ("error", "CLIENT_OFFLINE", "admission")
    assert dsp.n("agent_registry") == before and dsp.n("agent_assignments") == 0


def test_dispatch_to_a_connected_client_binds_target_and_restricts_the_tools(dsp):
    dsp.caps[(OWNER, CLIENT)] = {"capabilities": ["operator_read_file", "operator_bash", "phone_location"]}
    out = dsp.d()
    assert out["status"] == "accepted"
    a = dsp.br.c_._conn().execute("SELECT target FROM agent_assignments WHERE assignment_id=?",
                                  (out["assignment_id"],)).fetchone()
    assert a["target"] == f"client:{CLIENT}"
    reg = dsp.br.c_._conn().execute("SELECT allowed_tools_json, tool_policy FROM agent_registry WHERE agent_id=?",
                                    (out["agent_id"],)).fetchone()
    assert json.loads(reg["allowed_tools_json"]) == ["operator_read_file"] and reg["tool_policy"] == "read-only-client"


def test_dispatch_refuses_a_code_agent_on_a_client_and_other_peoples_clients(dsp):
    dsp.caps[(OWNER, CLIENT)] = {"capabilities": ["operator_read_file", "agent_worktree"]}
    out = dsp.d(writes=True, workspace="/repo")
    assert (out["code"], out["phase"]) == ("INVALID_SCOPE", "admission") and dsp.n("agent_registry") == 0
    other = dsp.d(owner_user_id="u2")                                # u2 har ingen klient med det id
    assert other["code"] == "CLIENT_OFFLINE"
    assert dsp.d(target="client:../x")["code"] == "INVALID_SCOPE"
    assert dsp.d(target="anden")["code"] == "INVALID_SCOPE"


# --- gennem den rigtige agent-motor -------------------------------------------------------------------

@pytest.fixture
def eng(dsp, monkeypatch):
    """Rigtig dispatch + rigtig execute_agent_task; kun modellen og broens ledning er falske."""
    from core.services import agent_runtime_spawn as M
    import core.services.agent_bridge_dispatch as D

    class F:
        def __init__(self): self.rounds = []
        def execute_with_role_or_fallback(self, **kw):
            self.rounds.append(kw)
            if len(self.rounds) == 1:
                return {"text": "", "input_tokens": 3, "output_tokens": 1, "status": "completed",
                        "tool_calls": [{"id": "t1", "function": {"name": "operator_read_file",
                                                                 "arguments": json.dumps({"path": "/etc/hosts"})}}]}
            return {"text": "faerdig: indholdet er laest", "input_tokens": 3, "output_tokens": 2,
                    "status": "completed", "tool_calls": []}

    f = F()
    monkeypatch.setattr(M, "_facade", lambda: f)
    monkeypatch.setattr("core.services.agent_runtime_base._facade", lambda: f)
    monkeypatch.setattr(M, "agent_tools_enabled", lambda: True)
    wire = dsp.br.wire
    wire.calls.clear()

    async def fake(**kw):
        return await wire(**kw)
    monkeypatch.setattr(D, "dispatch_pinned", fake)
    monkeypatch.setattr(dsp.br.B_.time, "sleep", lambda s: None)
    dsp.caps[(OWNER, CLIENT)] = {"capabilities": ["operator_read_file", "operator_bash"]}
    dsp.model = f
    dsp.M = M
    import core.services.agent_runtime_base as base
    dsp.container_tool_calls = []
    monkeypatch.setattr(base, "_execute_agent_tool_call",
                        lambda tc, agent_id: dsp.container_tool_calls.append(tc) or json.dumps({"status": "ok"}))
    return dsp


def test_a_full_client_run_reads_over_the_bridge_and_completes_with_one_terminal_message(eng, monkeypatch):
    started = []
    import core.services.agent_contract_service as svc
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    out = eng.d()
    assert out["status"] == "accepted"
    eng.br.wire.script = [{"status": "ok", "result": "127.0.0.1 localhost", "sent": True}]
    for fn in started:
        fn()
    assert eng.br.wire.calls and eng.br.wire.calls[0]["client_id"] == CLIENT
    assert len(eng.br.wire.calls) == 1                              # kaldet er sendt EN gang
    tool_msgs = [m for m in eng.model.rounds[1]["messages"] if m.get("role") == "tool"]
    assert len(tool_msgs) == 1 and "127.0.0.1 localhost" in tool_msgs[0]["content"]   # modellen faar KLIENTENS svar
    assert eng.container_tool_calls == []                           # intet blev koert i containeren
    a = eng.br.c_._conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                                  (out["assignment_id"],)).fetchone()
    assert a["status"] == "completed"
    assert eng.br.c_._conn().execute("SELECT COUNT(*) FROM agent_result_outbox WHERE message_kind='terminal' AND assignment_id=?",
                                     (out["assignment_id"],)).fetchone()[0] == 1


def test_an_unknown_bridge_call_halts_the_real_run_without_a_terminal_result(eng, monkeypatch):
    started = []
    import core.services.agent_contract_service as svc
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    out = eng.d()
    eng.br.wire.script = [TIMEOUT] * 5
    for fn in started:
        fn()
    conn = eng.br.c_._conn()
    run = conn.execute("SELECT status, error_phase, error_code FROM agent_runs WHERE assignment_id=?",
                       (out["assignment_id"],)).fetchone()
    a = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id=?", (out["assignment_id"],)).fetchone()
    assert (run["status"], run["error_phase"], run["error_code"]) == ("outcome_unknown", "bridge", "OUTCOME_UNKNOWN")
    assert a["status"] == "waiting"
    assert conn.execute("SELECT COUNT(*) FROM agent_result_outbox WHERE message_kind='terminal' AND assignment_id=?",
                        (out["assignment_id"],)).fetchone()[0] == 0           # intet falsk resultat, intet "fejlet"
    assert len(eng.model.rounds) == 1                                         # modellen blev ikke spurgt igen
    reg = conn.execute("SELECT status FROM agent_registry WHERE agent_id=?", (out["agent_id"],)).fetchone()
    assert reg["status"] == "outcome_unknown"


def _loop_that(eng, monkeypatch, *, raises):
    """Erstat tool-loekken: den saetter runnet i outcome_unknown (som broen goer) og enten kaster eller
    returnerer en almindelig fejl-udfald - begge former skal ende uden at runnet afsluttes."""
    import core.services.agent_worker_runner as worker

    def fake(*, agent, prompt, requires_tools, run_id="", resume=None, **kwargs):
        br = eng.br
        row = br.c_._conn().execute("SELECT assignment_id FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
        ident = {"run_id": run_id, "assignment_id": row["assignment_id"]}
        br.store_.begin(invocation_id="inv-x", owner_user_id=OWNER, origin_session_id=SESSION, agent_id=agent["agent_id"],
                        assignment_id=ident["assignment_id"], run_id=run_id, client_id=CLIENT,
                        tool="operator_write_file", idem_class="write", args={"p": 1})
        br.store_.mark_unknown("inv-x", "timeout")
        halt = br.B_._halt(ident, br.store_.get("inv-x"))
        if raises:
            raise halt
        from core.services.agent_runtime_base import _loop_result    # en ægte fejl-udfald, ikke en afkortet dict
        return _loop_result({"final_text": "", "error_str": "OUTCOME_UNKNOWN", "total_tool_calls": 0, "total_input": 0,
                             "total_output": 0, "total_cost": 0.0, "duration_ms": 1, "rounds": 1},
                            scout=False, provider="p", model="m")

    monkeypatch.setattr(worker, "run_agent_in_worker", fake)


@pytest.mark.parametrize("raises", [True, False])
def test_the_run_is_never_finalised_whether_the_loop_raises_or_returns_a_failure(eng, monkeypatch, raises):
    import core.services.agent_contract_service as svc
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    _loop_that(eng, monkeypatch, raises=raises)
    out = eng.d()
    for fn in started:
        fn()
    conn = eng.br.c_._conn()
    run = conn.execute("SELECT status FROM agent_runs WHERE assignment_id=?", (out["assignment_id"],)).fetchone()
    a = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id=?", (out["assignment_id"],)).fetchone()
    assert (run["status"], a["status"]) == ("outcome_unknown", "waiting")
    assert conn.execute("SELECT COUNT(*) FROM agent_result_outbox WHERE message_kind='terminal' AND assignment_id=?",
                        (out["assignment_id"],)).fetchone()[0] == 0


def test_a_late_report_cannot_settle_an_assignment_that_is_no_longer_waiting(br):
    ag, acc = br.agent()                                           # assignmentet er 'active', ikke 'waiting'
    br.store_.begin(invocation_id="inv-z", owner_user_id=OWNER, origin_session_id=SESSION, agent_id="a1",
                    assignment_id=acc["assignment_id"], run_id=acc["run_id"], client_id=CLIENT,
                    tool="operator_write_file", idem_class="write", args={"p": 1})
    br.store_.mark_unknown("inv-z", "timeout")
    br.B_.apply_client_report(owner_user_id=OWNER, client_id=CLIENT, reports=[{"invocation_id": "inv-z", "status": "completed"}])
    assert br.store_.get("inv-z")["state"] == "verified_executed"
    assert br.status(acc)[1] == "active"                           # afgoerelsen roerer ikke et assignment der koerer
    assert br.c_._conn().execute("SELECT status FROM agent_registry WHERE agent_id='a1'").fetchone()[0] != "failed"


def test_a_halt_sends_gds_separate_state_message_once_and_never_a_terminal_one(eng, monkeypatch):
    import core.services.agent_contract_service as svc
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    out = eng.d()
    eng.br.wire.script = [TIMEOUT] * 5
    for fn in started:
        fn()
    rows = eng.br.c_._conn().execute("SELECT message_kind, state_code FROM agent_result_outbox WHERE assignment_id=?",
                                     (out["assignment_id"],)).fetchall()
    assert [(r[0], r[1]) for r in rows] == [("state", "outcome_unknown")]
