"""C3: tre versionsmaerkede promptlag + snapshot foer foerste modelkald."""
from __future__ import annotations

import json

import pytest

KEY = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3"          # ser ud som en GitHub-token (testvaerdi)
CTX = {"user_id": "bjorn", "parent_session_id": "s1", "parent_run_id": "pr", "projekt": "jarvis"}


@pytest.fixture
def pl(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.services.agent_prompt_layers as L
    from core.services import agent_runtime_spawn as M
    from core.services.agent_runtime_spawn import spawn_agent_task

    sent = {}

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            row = c._conn().execute("SELECT run_id FROM agent_run_prompts").fetchone()
            sent["snapshot_existed_before_call"] = row is not None
            sent["message"] = kw.get("message")
            return {"text": "klar", "input_tokens": 1, "output_tokens": 1, "status": "completed"}

    monkeypatch.setattr(M, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(M, "_snapshot_tools", lambda agent: [])
    monkeypatch.setattr(M, "_facade", lambda: _F())
    from core.services import agent_runtime_base as base
    monkeypatch.setattr(base, "_facade", lambda: M._facade())

    class H:
        c_, L_, M_, sent_ = c, L, M, sent

        def spawn(self, **kw):
            kw.setdefault("role", "researcher")
            kw.setdefault("goal", "find X i y.py")
            kw.setdefault("context", dict(CTX))
            return spawn_agent_task(auto_execute=False, **kw)

    return H()


def _agent(h, agent_id):
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    return get_agent_registry_entry(agent_id)


def test_layers_are_labelled_versioned_and_carry_the_assignment(pl):
    a = pl.spawn()
    layers = pl.L_.build_layered_prompt(agent=_agent(pl, a["agent_id"]), messages_text="(beskeder)",
                                        execution_mode="solo-task", extra_instruction="Svar kort.")
    t = layers["text"]
    assert f"[DELEGATION · agent-delegation-v1]" in t and "[ROLLE · researcher ·" in t
    assert f"[OPGAVE · {layers['assignment_id']}]" in t
    assert f"Du arbejder for Jarvis på assignment `{layers['assignment_id']}`." in t
    assert "opfind ikke udført arbejde" in t and "Afslut med evidens" in t
    for needle in ("Mål: find X i y.py", "Target: runtime-container", "Resultatformat (efter relevans):",
                   "findings", "uncertainty", "next_action", "Samtalen hidtil:\n(beskeder)", "Svar kort."):
        assert needle in t, needle
    assert t.index("[DELEGATION") < t.index("[ROLLE") < t.index("[OPGAVE")
    assert (layers["delegation_version"], layers["role_version"], layers["owner_user_id"]) == (
        "agent-delegation-v1", "v1", "bjorn")
    assert set(layers["digests"]) == {"delegation", "role", "assignment"}


def test_identity_fields_stay_out_of_the_childs_context_package(pl):
    a = pl.spawn()
    t = pl.L_.build_layered_prompt(agent=_agent(pl, a["agent_id"]), messages_text="",
                                   execution_mode="solo-task")["text"]
    assert "projekt" in t and "bjorn" not in t.split("Kontekst:")[1].split("\n")[0]
    assert "parent_session_id" not in t


def test_secrets_are_redacted_from_the_effective_prompt(pl):
    a = pl.spawn(goal=f"brug token {KEY} til at hente")
    layers = pl.L_.build_layered_prompt(agent=_agent(pl, a["agent_id"]), messages_text="",
                                        execution_mode="solo-task")
    assert KEY not in layers["text"] and "[hemmelighed fjernet]" in layers["text"]


def test_a_legacy_agent_without_an_assignment_gets_no_layers(pl):
    a = pl.spawn(context={})
    assert pl.L_.build_layered_prompt(agent=_agent(pl, a["agent_id"]), messages_text="",
                                      execution_mode="solo-task") is None


def test_snapshot_exists_before_the_first_model_call_and_matches_what_is_sent(pl):
    a = pl.spawn()
    pl.M_.execute_agent_task(agent_id=a["agent_id"])
    assert pl.sent_["snapshot_existed_before_call"] is True
    run = pl.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    snap = pl.L_.get_prompt_snapshot(owner_user_id="bjorn", run_id=run)
    assert snap["effective_text"] == pl.sent_["message"]
    assert (snap["delegation_version"], snap["role_version"], snap["owner_user_id"]) == (
        "agent-delegation-v1", "v1", "bjorn")
    assert snap["provider"] == _agent(pl, a["agent_id"])["provider"]
    assert set(json.loads(snap["layer_digests_json"])) == {"delegation", "role", "assignment"}


def test_snapshot_reads_are_owner_checked(pl):
    a = pl.spawn()
    pl.M_.execute_agent_task(agent_id=a["agent_id"])
    run = pl.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    assert pl.L_.get_prompt_snapshot(owner_user_id="anden", run_id=run) is None
    assert pl.L_.get_prompt_snapshot(owner_user_id="bjorn", run_id="findes-ikke") is None


def test_tool_schema_and_names_are_part_of_the_snapshot(pl, monkeypatch):
    a = pl.spawn()
    layers = pl.L_.build_layered_prompt(agent=_agent(pl, a["agent_id"]), messages_text="",
                                        execution_mode="solo-task")
    tools = [{"type": "function", "function": {"name": "read_file", "parameters": {}}}]
    assert pl.L_.snapshot_prompt(run_id="r1", agent=_agent(pl, a["agent_id"]), layers=layers,
                                 tools_payload=tools) is True
    assert pl.L_.snapshot_prompt(run_id="r2", agent=_agent(pl, a["agent_id"]), layers=layers,
                                 tools_payload=[]) is True
    one, two = (pl.L_.get_prompt_snapshot(owner_user_id="bjorn", run_id=r) for r in ("r1", "r2"))
    assert json.loads(one["tool_names_json"]) == ["read_file"]
    assert one["tool_schema_sha256"] != two["tool_schema_sha256"]


def test_a_snapshot_failure_never_aborts_the_run(pl, monkeypatch):
    monkeypatch.setattr(pl.c_, "_conn", pl.c_._conn)          # uaendret - fejlen kommer i INSERT
    real = pl.L_.snapshot_prompt

    def boom(**kw):
        import core.runtime.db_agent_contract as cc
        orig = cc._conn
        cc._conn = lambda: (_ for _ in ()).throw(RuntimeError("db"))
        try:
            return real(**kw)
        finally:
            cc._conn = orig

    monkeypatch.setattr(pl.L_, "snapshot_prompt", boom)
    a = pl.spawn()
    pl.M_.execute_agent_task(agent_id=a["agent_id"])
    (st,) = [r["status"] for r in pl.c_._conn().execute("SELECT status FROM agent_assignments")]
    assert st == "completed"


def test_legacy_agents_keep_the_old_flat_prompt(pl):
    a = pl.spawn(context={})
    pl.M_.execute_agent_task(agent_id=a["agent_id"])
    assert pl.sent_["message"].startswith("System prompt:")
    assert pl.sent_["snapshot_existed_before_call"] is False
