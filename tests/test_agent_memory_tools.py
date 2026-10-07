"""Leverance C, hul 3: agent_note - agentens EGNE noter gennem et policykontrolleret vaerktoej (spec 7.2)."""
from __future__ import annotations

import hashlib
import json

import pytest

O, S, R = "bjorn", "sess-1", "visible-p"


@pytest.fixture
def mt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_memory as m
    import core.services.agent_contract_service as svc
    import core.services.agent_runtime_base as base
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import in_flight_runs as ifr
    from core.tools import agent_memory_tools as T

    ifr._mutate(lambda r: r.clear())
    svc.set_capability(True, role="owner")
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: None)

    class H:
        c_, m_, T_, svc_, base_ = c, m, T, svc, base

        def agent(self, name="a1", owner=O, session="s1", assignment=True):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g")
            if owner:
                c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            if assignment and owner:
                return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                           goal="g", parent_agent_id="jarvis", parent_run_id="pr")

        def call(self, as_agent, /, **args):
            """Som runtimen: gennem den vaerktoejskaldsvej agenten faktisk bruger (overskriver identiteten)."""
            tc = {"function": {"name": "agent_note", "arguments": json.dumps(args)}}
            return json.loads(base._execute_agent_tool_call(tc, agent_id=as_agent))

        def notes(self, agent_id=None):
            q, a = "SELECT * FROM agent_memory_notes", ()
            if agent_id:
                q, a = q + " WHERE agent_id=?", (agent_id,)
            return [dict(r) for r in c._conn().execute(q + " ORDER BY agent_id, version", a)]

        def count(self, table):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    yield H()
    ifr._mutate(lambda r: r.clear())


def test_an_agent_writes_reads_and_corrects_its_own_note_with_a_full_change_trail(mt):
    acc = mt.agent()
    w1 = mt.call("a1", action="write", content="foerste udkast")
    assert (w1["status"], w1["version"], w1["author"], w1["source_assignment_id"], w1["supersedes_note_id"],
            w1["chars"]) == ("ok", 1, "agent:a1", acc["assignment_id"], "", len("foerste udkast"))
    assert w1["text"] == "note v1 gemt (14 tegn)"
    w2 = mt.call("a1", action="write", content="rettet udkast")
    assert (w2["version"], w2["supersedes_note_id"]) == (2, w1["note_id"])
    rd = mt.call("a1", action="read")
    assert rd["status"] == "ok" and rd["note"]["content"] == "rettet udkast" and rd["note"]["version"] == 2
    assert rd["text"] == "[note v2 · agent:a1]\nrettet udkast"
    hist = mt.call("a1", action="history")
    assert [(v["version"], v["author"], v["chars"]) for v in hist["versions"]] == [(2, "agent:a1", 13),
                                                                                  (1, "agent:a1", 14)]
    assert [n["content"] for n in mt.notes("a1")] == ["foerste udkast", "rettet udkast"]   # den gamle bevares


def test_the_note_comes_back_in_the_agents_recall_with_low_trust_framing(mt):
    mt.agent()
    mt.call("a1", action="write", content="husk: koer testene foer commit")
    out = mt.m_.recall(owner_user_id=O, agent_id="a1", session_id="s1")
    assert "husk: koer testene foer commit" in out["text"] and "LAVERE tillid" in out["text"] and out["error"] == ""


def test_a_forged_identity_or_target_never_reaches_another_agents_memory(mt):
    mt.agent("a1")
    mt.agent("victim", owner="anden", session="s9")
    mt.m_.write_note(owner_user_id="anden", agent_id="victim", content="offerets note", author="agent:victim")
    before = mt.notes("victim")
    out = mt.call("a1", action="write", content="overskriv", _runtime_agent_id="victim", agent_id="victim",
                  owner_user_id="anden", target="victim")
    assert out["status"] == "ok" and out["author"] == "agent:a1"
    assert mt.notes("victim") == before                                   # offeret er uroert
    assert [n["agent_id"] for n in mt.notes() if n["content"] == "overskriv"] == ["a1"]
    leak = mt.call("a1", action="read", _runtime_agent_id="victim", agent_id="victim")
    assert leak["note"]["content"] == "overskriv" and "offerets" not in json.dumps(leak)
    assert "offerets" not in json.dumps(mt.call("a1", action="history", agent_id="victim"))


def test_a_note_written_by_one_owners_agent_is_invisible_to_a_same_named_role_of_another_owner(mt):
    mt.agent("a1")
    mt.agent("a2", owner="anden", session="s2")
    mt.call("a1", action="write", content="hemmelig for bjorn")
    assert mt.call("a2", action="read") == {"status": "ok", "text": "ingen note endnu", "note": None}
    assert mt.m_.recall(owner_user_id="anden", agent_id="a1", session_id="s1")["text"] == ""


@pytest.mark.parametrize("fn_args,code", [
    ({}, "POLICY_DENIED"),                                      # Jarvis/ingen identitet
    ({"_agent": "findes-ikke"}, "POLICY_DENIED"),
])
def test_without_a_server_side_agent_identity_the_tool_refuses(mt, fn_args, code):
    for args in ({"action": "write", "content": "x"}, {"action": "read"}, {"action": "history"}):
        out = mt.T_._exec_agent_note({**args, **({"_runtime_agent_id": fn_args["_agent"]} if fn_args else {})})
        assert (out["status"], out["code"]) == ("error", code)
    assert mt.notes() == []


def test_a_legacy_unscoped_agent_has_no_memory_tool_access(mt):
    mt.agent("old", owner=None)
    for args in ({"action": "write", "content": "x"}, {"action": "read"}):
        out = mt.call("old", **args)
        assert (out["status"], out["code"]) == ("error", "POLICY_DENIED")
    assert mt.notes() == []


def test_notes_are_only_written_during_an_open_assignment(mt):
    acc = mt.agent()
    mt.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    out = mt.call("a1", action="write", content="for sent")
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED") and mt.notes("a1") == []
    # laesning af egne noter er stadig tilladt efter afslutning (det er hukommelse, ikke et run)
    assert mt.call("a1", action="read")["note"] is None


@pytest.mark.parametrize("content,code", [("", "INVALID_SCOPE"), ("   \n ", "INVALID_SCOPE"),
                                          ("x" * 4001, "CAPACITY")])
def test_empty_and_oversized_notes_are_refused_and_nothing_is_written(mt, content, code):
    mt.agent()
    out = mt.call("a1", action="write", content=content)
    assert (out["status"], out["code"]) == ("error", code) and mt.notes("a1") == []


def test_a_note_at_the_size_limit_is_accepted(mt):
    mt.agent()
    out = mt.call("a1", action="write", content="x" * 4000)
    assert out["status"] == "ok" and out["chars"] == 4000


def test_one_assignment_can_only_write_ten_note_versions(mt):
    mt.agent()
    for i in range(10):
        assert mt.call("a1", action="write", content=f"v{i}")["status"] == "ok"
    out = mt.call("a1", action="write", content="den ellevte")
    assert (out["status"], out["code"]) == ("error", "CAPACITY") and len(mt.notes("a1")) == 10


@pytest.mark.parametrize("args", [{}, {"action": "slet"}, {"action": "write_summary", "content": "x"}])
def test_unknown_actions_are_refused(mt, args):
    mt.agent()
    out = mt.call("a1", **args)
    assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE") and mt.notes("a1") == []


def test_the_tool_cannot_touch_summaries_errors_relations_or_the_collective_layers(mt):
    acc = mt.agent()
    mt.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed", summary="gjort")
    mt.agent("a1b")
    before = {t: mt.count(t) for t in ("agent_memory_summaries", "agent_memory_errors", "agent_session_relations",
                                       "agent_assignments", "agent_registry")}
    summary_before = [dict(r) for r in mt.c_._conn().execute("SELECT * FROM agent_memory_summaries")]
    mt.call("a1b", action="write", content="min note", table="agent_memory_summaries", session_id="s9")
    after = {t: mt.count(t) for t in before}
    assert after == before
    assert [dict(r) for r in mt.c_._conn().execute("SELECT * FROM agent_memory_summaries")] == summary_before
    # de kollektive lag: intet nyt overhovedet i observationer/cross-agent-hukommelse
    tables = {r[0] for r in mt.c_._conn().execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("agent_observations", "cross_agent_memory"):
        if t in tables:
            assert mt.count(t) == 0


# --- registrering og cache-stabilitet -----------------------------------------------------------------------------

def test_the_tool_is_a_handler_but_not_in_jarvis_catalog_or_pinned_surface(mt):
    from core.tools.agent_contract_tools import CONTRACT_TOOL_NAMES
    from core.tools.simple_tools import _TOOL_HANDLERS, get_tool_definitions
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    assert "agent_note" in _TOOL_HANDLERS and mt.T_.MEMORY_TOOL_NAMES == ("agent_note",)
    assert "agent_note" not in {d["function"]["name"] for d in TOOL_DEFINITIONS}
    assert "agent_note" not in {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    assert "agent_note" not in CONTRACT_TOOL_NAMES
    assert [d["function"]["name"] for d in mt.T_.MEMORY_TOOL_DEFINITIONS] == ["agent_note"]


def _payload_hash(base, allowed):
    return hashlib.sha256(json.dumps(base._build_agent_tools_payload(allowed), sort_keys=True).encode()).hexdigest()


def test_a_contract_dispatched_tool_agent_gets_the_tool_and_its_array_is_the_same_for_every_task(mt):
    a = mt.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="foerste opgave", parent_run_id=R,
                               tool_policy="read-only-runtime")
    b = mt.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="HELT anden opgave med andre ord",
                               parent_run_id=R, tool_policy="read-only-runtime", description="kontekst")
    assert a["status"] == b["status"] == "accepted", (a, b)
    reg = {r["agent_id"]: json.loads(r["allowed_tools_json"]) for r in
           mt.c_._conn().execute("SELECT agent_id, allowed_tools_json FROM agent_registry")}
    ta, tb = reg[a["agent_id"]], reg[b["agent_id"]]
    assert ta == tb == [*mt.base_.tools_for_policy("read-only-runtime"), "agent_note"]
    ha, hb = (_payload_hash(mt.base_, t) for t in (ta, tb))
    assert ha == hb                                                       # byte-ens: funktion af politikken, ikke beskeden
    names = [d["function"]["name"] for d in mt.base_._build_agent_tools_payload(ta)]
    assert names.count("agent_note") == 1


def test_a_text_only_policy_and_a_non_contract_spawn_get_no_memory_tool(mt):
    from core.services.agent_runtime_spawn import spawn_agent_task

    out = mt.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="planlaeg", parent_run_id=R,
                                 role="planner")                           # default-politik "none"
    assert out["status"] == "accepted"
    legacy = spawn_agent_task(role="researcher", goal="gammel vej", tool_policy="read-only-runtime",
                              auto_execute=False)
    reg = {r["agent_id"]: json.loads(r["allowed_tools_json"]) for r in
           mt.c_._conn().execute("SELECT agent_id, allowed_tools_json FROM agent_registry")}
    assert reg[out["agent_id"]] == [] and "agent_note" not in reg[legacy["agent_id"]]


def test_a_code_agent_keeps_both_its_worktree_tools_and_the_note_tool(mt, tmp_path, monkeypatch):
    import subprocess
    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_GLOBAL": "/dev/null", "PATH": "/usr/bin:/bin"}
    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(cmd, cwd=repo, env=env, check=True, capture_output=True)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))
    out = mt.svc_.dispatch_agent(owner_user_id=O, origin_session_id=S, goal="skriv kode", parent_run_id=R,
                                 writes=True, workspace=str(repo))
    assert out["status"] == "accepted", out
    row = mt.c_._conn().execute("SELECT allowed_tools_json FROM agent_registry WHERE agent_id=?",
                                (out["agent_id"],)).fetchone()
    assert json.loads(row["allowed_tools_json"]) == [*mt.base_.tools_for_policy("worktree-write"), "agent_note"]


def test_an_agent_demoted_to_legacy_unscoped_with_an_open_assignment_still_cannot_write(mt):
    mt.agent("old2")
    conn = mt.c_._conn()
    conn.execute("UPDATE agent_registry SET owner_user_id='legacy_unscoped' WHERE agent_id='old2'")
    conn.execute("UPDATE agent_assignments SET owner_user_id='legacy_unscoped' WHERE agent_id='old2'")
    conn.commit()
    out = mt.call("old2", action="write", content="x")
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED") and mt.notes("old2") == []
