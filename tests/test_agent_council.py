"""F5: raad og review-kaede paa agentmotoren. Rigtig dispatch + rigtig sqlite; kun modellen er falsk."""
from __future__ import annotations

import json

import pytest

O, S, R = "u1", "s1", "run-parent"


@pytest.fixture
def cn(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_council as store
    import core.services.agent_contract_service as svc
    from core.services import agent_council as A
    from core.services import agent_runtime_spawn as M
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    started: list = []
    prompts: list[str] = []

    class F:
        def execute_with_role_or_fallback(self, **kw):
            text = kw.get("message") or ""
            prompts.append(text)
            if "FEJLOPGAVE" in text:
                raise RuntimeError("modellen faldt")
            return {"text": "min vurdering: " + text[-30:].replace("\n", " "), "input_tokens": 3,
                    "output_tokens": 2, "status": "completed"}

    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_snapshot_tools", lambda agent: [])
    monkeypatch.setattr(M, "_facade", lambda: F())
    monkeypatch.setattr("core.services.agent_runtime_base._facade", lambda: F())
    svc.set_capability(True, role="owner")

    class H:
        A_, c_, store_, svc_ = A, c, store, svc
        prompts_ = prompts

        def run_all(self):
            fns, started[:] = list(started), []
            for f in fns:
                f()

        def members(self, n=3, tasks=None):
            tasks = tasks or [f"vurdering {i}" for i in range(n)]
            return [{"role": r, "task": t} for r, t in zip(["critic", "planner", "researcher", "executor",
                                                           "devils_advocate", "watcher"], tasks)]

        def convene(self, **kw):
            base = dict(owner_user_id=O, origin_session_id=S, topic="skal vi?", facts="FAKTA: x er sandt",
                        members=self.members(), parent_run_id=R)
            base.update(kw)
            return A.convene(**base)

        def n(self, table, where="1=1"):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

        def status(self, aid):
            return c._conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=?", (aid,)).fetchone()[0]
    yield H()
    ifr._mutate(lambda r: r.clear())


# --- indkaldelse ---------------------------------------------------------------------------------

@pytest.mark.parametrize("members,why", [
    ([], "2-6"), ([{"role": "critic", "task": "a"}], "2-6"),
    ([{"role": "critic", "task": f"t{i}"} for i in range(7)], "2-6"),
    ([{"role": "critic", "task": ""}, {"role": "planner", "task": "b"}], "role og task"),
    ([{"role": "", "task": "a"}, {"role": "planner", "task": "b"}], "role og task"),
    ([{"role": "critic", "task": "samme"}, {"role": "planner", "task": "samme"}], "forskellige"),
    ("ikke en liste", "2-6"),
])
def test_invalid_councils_are_refused_before_anything_is_created(cn, members, why):
    out = cn.convene(members=members)
    assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE") and why in out["error"]
    assert cn.n("agent_registry") == 0 and cn.n("agent_councils") == 0


def test_a_missing_topic_a_closed_engine_and_a_missing_session_are_refused(cn):
    assert cn.convene(topic="  ")["code"] == "INVALID_SCOPE"
    assert cn.convene(origin_session_id="")["code"] == "INVALID_SCOPE"
    cn.svc_.set_capability(False, role="owner")
    assert cn.convene()["code"] == "POLICY_DENIED" and cn.n("agent_councils") == 0


def test_a_council_is_one_assignment_per_member_with_the_same_facts_and_their_own_task(cn):
    out = cn.convene(members=cn.members(3))
    assert out["status"] == "accepted" and out["council_status"] == "gathering" and out["replayed"] is False
    assert len(out["members"]) == 3 and len({m["agent_id"] for m in out["members"]}) == 3
    assert cn.n("agent_assignments") == 3
    cn.run_all()
    mine = [p for p in cn.prompts_ if "Du er raadsmedlem" in p]
    assert len(mine) == 3
    assert all("FAKTA: x er sandt" in p and "EMNE: skal vi?" in p for p in mine)
    for i in range(3):
        assert sum(f"vurdering {i}" in p for p in mine) == 1                 # hvert medlem har SIN opgave
    assert [cn.status(m["assignment_id"]) for m in out["members"]] == ["completed"] * 3


def test_convening_twice_with_the_same_key_returns_the_same_council_and_a_changed_one_conflicts(cn):
    a = cn.convene(idempotency_key="k")
    b = cn.convene(idempotency_key="k")
    assert b["council_id"] == a["council_id"] and b["replayed"] is True and cn.n("agent_assignments") == 3
    assert cn.convene(idempotency_key="k", topic="noget andet")["code"] == "IDEMPOTENCY_CONFLICT"
    assert cn.convene(idempotency_key="k", members=cn.members(2))["code"] == "IDEMPOTENCY_CONFLICT"


def test_without_room_for_every_member_nothing_is_started(cn, monkeypatch):
    monkeypatch.setattr(cn.svc_, "MAX_ACTIVE_PER_PARENT", 2)
    out = cn.convene(members=cn.members(3))
    assert (out["code"], out["status"]) == ("CAPACITY", "error") and "3 pladser" in out["error"]
    assert cn.n("agent_registry") == 0 and cn.n("agent_councils") == 0
    assert cn.convene(members=cn.members(2))["status"] == "accepted"          # to passer


def test_six_council_members_fit_the_worker_cap_and_a_seventh_task_queues(cn):
    assert cn.convene(members=cn.members(6))["status"] == "accepted"
    assert cn.n("agent_councils", "status='gathering'") == 1
    other = cn.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="en syvende", parent_run_id=R)
    assert other["status"] == "accepted" and other["assignment_status"] == "queued"


def test_a_failing_dispatch_midway_stops_the_started_members_and_cancels_the_council(cn, monkeypatch):
    real = cn.svc_.dispatch_agent
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 3:
            return {"status": "error", "code": "MODEL_UNAVAILABLE", "error": "ingen model", "phase": "admission"}
        return real(**kw)

    monkeypatch.setattr(cn.svc_, "dispatch_agent", flaky)
    out = cn.convene(members=cn.members(4))
    assert (out["status"], out["code"], out["failed_member"], out["council_status"]) == (
        "error", "MODEL_UNAVAILABLE", 3, "cancelled")
    c = cn.store_.get(out["council_id"], O)
    assert c["status"] == "cancelled" and len(c["members"]) == 2
    reg = cn.c_._conn().execute("SELECT status FROM agent_registry WHERE agent_id IN (?,?)",
                                (c["members"][0]["agent_id"], c["members"][1]["agent_id"])).fetchall()
    assert [r[0] for r in reg] == ["cancelled", "cancelled"]
    assert cn.A_.advance() == []                                              # et annulleret raad faar ingen syntese


# --- syntesen --------------------------------------------------------------------------------------

def test_nothing_happens_until_every_member_is_terminal(cn):
    out = cn.convene()
    assert cn.A_.advance() == []
    cn.run_all()
    assert cn.store_.get(out["council_id"], O)["status"] == "gathering"       # advance er ikke koert endnu
    assert [d["action"] for d in cn.A_.advance()] == ["synthesis_started"]


def test_the_synthesis_is_created_once_when_all_are_terminal_and_names_the_failed_member(cn):
    members = cn.members(3, tasks=["vurdering a", "FEJLOPGAVE b", "vurdering c"])
    out = cn.convene(members=members)
    cn.run_all()
    done = cn.A_.advance()
    assert len(done) == 1 and done[0]["action"] == "synthesis_started"
    c = cn.store_.get(out["council_id"], O)
    assert c["status"] == "synthesizing" and c["synthesis_assignment_id"] == done[0]["assignment_id"]
    row = cn.c_._conn().execute("SELECT goal, status FROM agent_assignments WHERE assignment_id=?",
                                (c["synthesis_assignment_id"],)).fetchone()
    assert "Medlem 2 (planner) FEJLEDE" in row["goal"] and "INTET svar" in row["goal"]
    assert "Medlem 1 (critic) SVAREDE" in row["goal"] and "Medlem 3 (researcher) SVAREDE" in row["goal"]
    assert "NAVNGIV udtrykkeligt de 1 medlem" in row["goal"]
    assert cn.A_.advance() == [] and cn.n("agent_assignments") == 4          # idempotent: ingen anden syntese


def test_an_all_success_council_does_not_ask_the_synthesis_to_name_failures(cn):
    out = cn.convene()
    cn.run_all()
    cn.A_.advance()
    goal = cn.c_._conn().execute("SELECT goal FROM agent_assignments WHERE assignment_id=?",
                                 (cn.store_.get(out["council_id"], O)["synthesis_assignment_id"],)).fetchone()[0]
    assert "FEJLEDE" not in goal and "NAVNGIV" not in goal


def test_the_parent_is_woken_by_the_synthesis_not_by_each_member(cn):
    out = cn.convene()
    cn.run_all()
    cn.A_.advance()
    syn = cn.store_.get(out["council_id"], O)["synthesis_assignment_id"]
    waits = cn.c_._conn().execute("SELECT condition, assignment_ids_json, parent_run_id FROM agent_wait_contracts").fetchall()
    assert [(w["condition"], json.loads(w["assignment_ids_json"]), w["parent_run_id"]) for w in waits] == [
        ("first_terminal", [syn], R)]


def test_the_council_is_done_when_the_synthesis_is_terminal(cn):
    out = cn.convene()
    cn.run_all()
    cn.A_.advance()
    assert cn.store_.get(out["council_id"], O)["status"] == "synthesizing"
    cn.run_all()                                                              # syntesen koerer
    assert [d["action"] for d in cn.A_.advance()] == ["done"]
    c = cn.store_.get(out["council_id"], O)
    assert c["status"] == "done" and cn.status(c["synthesis_assignment_id"]) == "completed"
    assert cn.A_.advance() == []


def test_a_synthesis_that_cannot_be_accepted_yet_is_retried_next_tick(cn, monkeypatch):
    out = cn.convene()
    cn.run_all()
    real = cn.svc_.dispatch_agent
    monkeypatch.setattr(cn.svc_, "dispatch_agent", lambda **kw: {"status": "error", "code": "CAPACITY", "error": "fuldt"})
    assert cn.A_.advance() == [] and cn.store_.get(out["council_id"], O)["status"] == "gathering"
    monkeypatch.setattr(cn.svc_, "dispatch_agent", real)
    assert [d["action"] for d in cn.A_.advance()] == ["synthesis_started"]


def test_supervise_advances_councils(cn, monkeypatch):
    out = cn.convene()
    cn.run_all()
    cn.svc_.supervise()
    assert cn.store_.get(out["council_id"], O)["status"] == "synthesizing"


def test_another_owners_council_is_invisible_and_cannot_be_advanced_into_their_session(cn):
    out = cn.convene()
    assert cn.store_.get(out["council_id"], "u2") is None
    cn.run_all()
    cn.A_.advance()
    syn_owner = cn.c_._conn().execute("SELECT owner_user_id, origin_session_id, parent_run_id FROM agent_assignments "
                                      "WHERE goal LIKE '%Du er syntese%'").fetchone()
    assert (syn_owner[0], syn_owner[1], syn_owner[2]) == (O, S, R)


# --- review-kaeden ------------------------------------------------------------------------------------

@pytest.fixture
def rv(cn):
    from core.runtime import db_agent_artifacts as art

    class V:
        def builder(self, session=S, owner=O, diff="diff --git a/x b/x\n+ny linje", changes='{"files":["x"]}'):
            out = cn.svc_.dispatch_agent(owner_user_id=owner, origin_session_id=session, goal="byg x", parent_run_id=R)
            cn.run_all()
            run = cn.c_._conn().execute("SELECT run_id FROM agent_runs WHERE assignment_id=?", (out["assignment_id"],)).fetchone()[0]
            common = dict(agent_id=out["agent_id"], run_id=run, assignment_id=out["assignment_id"], owner_user_id=owner)
            if diff:
                art.write_artifact(name="diff.patch", data=diff, **common)
            if changes:
                art.write_artifact(name="changes.json", data=changes, **common)
            return out

        def review(self, builder_id, **kw):
            base = dict(owner_user_id=O, origin_session_id=S, builder_assignment_id=builder_id,
                        requirements="x skal vaere implementeret", parent_run_id=R)
            base.update(kw)
            return cn.A_.dispatch_review(**base)
    v = V()
    v.cn = cn
    return v


def test_the_reviewer_gets_the_actual_diff_and_the_builders_claim_is_labelled_a_claim(rv):
    b = rv.builder()
    out = rv.review(b["assignment_id"])
    assert out["status"] == "accepted" and out["reviews_assignment_id"] == b["assignment_id"]
    assert out["evidence"] == {"diff_chars": len("diff --git a/x b/x\n+ny linje"), "has_changes": True,
                               "builder_claim_included": True}
    row = rv.cn.c_._conn().execute("SELECT goal, target FROM agent_assignments WHERE assignment_id=?",
                                   (out["assignment_id"],)).fetchone()
    reg = rv.cn.c_._conn().execute("SELECT role, tool_policy FROM agent_registry WHERE agent_id=?", (out["agent_id"],)).fetchone()
    assert (reg["role"], reg["tool_policy"]) == ("reviewer", "read-only-runtime")
    rv.cn.run_all()
    prompt = [p for p in rv.cn.prompts_ if "FAKTISKE AENDRINGER" in p][0]
    assert "+ny linje" in prompt and "x skal vaere implementeret" in prompt and '{"files":["x"]}' in prompt
    assert "PAASTAND du skal efterproeve" in prompt and "min vurdering" in prompt     # builderens svar, mærket


def test_a_builder_without_a_diff_artifact_is_reported_as_unverifiable(rv):
    b = rv.builder(diff="", changes="")
    out = rv.review(b["assignment_id"])
    assert out["evidence"]["diff_chars"] == 0 and out["evidence"]["has_changes"] is False
    rv.cn.run_all()
    assert any("ingen diff-artefakt - arbejdet kan ikke efterproeves" in p for p in rv.cn.prompts_)


@pytest.mark.parametrize("mut,code", [
    (lambda rv, b: dict(builder_assignment_id="asg-findes-ikke"), "INVALID_SCOPE"),
    (lambda rv, b: dict(owner_user_id="u2"), "INVALID_SCOPE"),
    (lambda rv, b: dict(origin_session_id="anden-session"), "INVALID_SCOPE"),
    (lambda rv, b: dict(requirements="  "), "INVALID_SCOPE"),
])
def test_a_review_of_an_unknown_or_foreign_builder_or_without_requirements_is_refused(rv, mut, code):
    b = rv.builder()
    before = rv.cn.n("agent_registry")
    out = rv.review(b["assignment_id"], **mut(rv, b))
    assert (out["status"], out["code"]) == ("error", code) and rv.cn.n("agent_registry") == before


def test_an_unfinished_builder_cannot_be_reviewed_yet(rv):
    out = rv.cn.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="byg y", parent_run_id=R)
    res = rv.review(out["assignment_id"])
    assert res["code"] == "INVALID_TRANSITION" and "ikke faerdig" in res["error"]


def test_reviewing_the_same_builder_twice_is_idempotent(rv):
    b = rv.builder()
    a1, a2 = rv.review(b["assignment_id"]), rv.review(b["assignment_id"])
    assert a2["assignment_id"] == a1["assignment_id"] and a2["replayed"] is True


# --- tools ---------------------------------------------------------------------------------------------

def test_the_model_tools_go_through_the_same_service_with_owner_and_run_from_the_runtime(cn, monkeypatch):
    from core.tools import agent_contract_tools as T
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: O)
    out = T._exec_convene_agent_council({"_runtime_session_id": S, "_runtime_turn_id": R, "topic": "t", "facts": "f",
                                         "members": cn.members(2), "user_id": "angriber"})
    assert out["status"] == "accepted" and len(out["members"]) == 2
    c = cn.store_.get(out["council_id"], O)
    assert (c["owner_user_id"], c["parent_run_id"]) == (O, R)
    bad = T._exec_review_agent_work({"_runtime_session_id": S, "builder_assignment_id": "x", "requirements": "y"})
    assert bad["code"] == "INVALID_SCOPE"
    assert {"convene_agent_council", "review_agent_work"} <= set(T.CONTRACT_TOOL_NAMES) & T._NEW_ONLY


def test_the_reviewer_stays_read_only_even_if_the_role_default_is_widened(rv, monkeypatch):
    from core.services import agent_runtime_base as base
    monkeypatch.setitem(base.AGENT_ROLE_TEMPLATES["reviewer"], "default_tool_policy", "can-spawn")
    out = rv.review(rv.builder()["assignment_id"])
    reg = rv.cn.c_._conn().execute("SELECT tool_policy FROM agent_registry WHERE agent_id=?", (out["agent_id"],)).fetchone()
    assert reg["tool_policy"] == "read-only-runtime"
