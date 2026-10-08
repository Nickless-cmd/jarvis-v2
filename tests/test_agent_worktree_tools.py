"""C5b: agent-kun-vaerktoejerne wt_bash / wt_write_file - identitet fra serveren, aldrig fra modellen."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
needs_bwrap = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def tl(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_contract as c
    import core.services.agent_runtime_base as base
    import core.services.agent_worktrees as W
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.tools import agent_worktree_tools as T

    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    (repo / "a.txt").write_text("a\n")
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", "init", cwd=repo)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))

    class H:
        c_, W_, T_, base_ = c, W, T, base
        repo_ = str(repo)

        def agent(self, name, worktree=True):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id="bjorn", owner_session_id="s1")
            acc = c.accept_assignment(agent_id=name, owner_user_id="bjorn", origin_session_id="s1",
                                      goal="skriv", parent_agent_id="jarvis", parent_run_id="pr")
            return W.provision(owner_user_id="bjorn", assignment_id=acc["assignment_id"],
                               repo_path=str(repo)) if worktree else acc

    return H()


def test_the_tools_are_named_wt_and_do_not_collide_with_jarvis_own_worktree_tools(tl):
    from core.tools import worktree_tools as jarvis_wt

    mine = {d["function"]["name"] for d in tl.T_.WT_TOOL_DEFINITIONS}
    theirs = {d["function"]["name"] for d in jarvis_wt.WORKTREE_TOOL_DEFINITIONS}
    assert mine == {"wt_bash", "wt_write_file"} == set(tl.T_.WORKTREE_TOOL_NAMES) and not (mine & theirs)


def test_the_tools_are_hidden_from_jarvis_but_in_the_schema_of_a_worktree_write_agent(tl):
    from core.tools.simple_tools import get_tool_definitions

    visible = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    assert not ({"wt_bash", "wt_write_file"} & visible)
    allowed = tl.base_.tools_for_policy("worktree-write")
    assert {"wt_bash", "wt_write_file"} <= set(allowed)
    payload = {d["function"]["name"] for d in tl.base_._build_agent_tools_payload(allowed)}
    assert {"wt_bash", "wt_write_file"} <= payload
    ro = {d["function"]["name"] for d in tl.base_._build_agent_tools_payload(tl.base_.tools_for_policy("read-only-runtime"))}
    assert not ({"wt_bash", "wt_write_file"} & ro)


def test_a_writing_agent_gets_the_sandboxed_shell_and_not_the_container_one(tl):
    """8/10-2026: politikken arvede ``bash`` fra ``_READ_ONLY_TOOLS``, saa en
    skrivende agent fik BAADE ``bash`` (containeren) og ``wt_bash`` (sandkassen) —
    og valgte den usikre flade til at laese tre filer. Gaten parkerede kaldet, og
    Bjoern fik et godkendelses-kort for en ``sed -n``. ``wt_bash`` daekker alt
    agenten skal i sin egen kopi; ``bash`` hoerer ikke i dens saet."""
    allowed = set(tl.base_.tools_for_policy("worktree-write"))
    assert "bash" not in allowed
    assert {"wt_bash", "wt_write_file"} <= allowed
    # Laese-politikken er UROERT — den skal stadig have bash.
    assert "bash" in tl.base_.tools_for_policy("read-only-runtime")


def test_the_tools_are_registered_handlers_but_not_catalog_entries(tl):
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    assert "wt_bash" in _TOOL_HANDLERS and "wt_write_file" in _TOOL_HANDLERS
    assert not {"wt_bash", "wt_write_file"} & {d["function"]["name"] for d in TOOL_DEFINITIONS}


@pytest.mark.parametrize("args,code", [
    ({}, "NO_WORKTREE"),
    ({"_runtime_agent_id": "findes-ikke"}, "NO_WORKTREE"),
])
def test_without_a_server_side_identity_the_tools_refuse(tl, args, code):
    for fn, extra in ((tl.T_._exec_wt_bash, {"command": "echo x"}),
                      (tl.T_._exec_wt_write_file, {"path": "x", "content": "y"})):
        out = fn({**args, **extra})
        assert (out["status"], out["code"]) == ("error", code)


def test_an_agent_with_an_assignment_but_no_worktree_is_refused(tl):
    tl.agent("a1", worktree=False)
    out = tl.T_._exec_wt_bash({"_runtime_agent_id": "a1", "command": "echo x"})
    assert (out["status"], out["code"]) == ("error", "NO_WORKTREE")


@needs_bwrap
def test_the_tools_write_in_the_agents_own_worktree(tl):
    w = tl.agent("a1")
    out = tl.T_._exec_wt_bash({"_runtime_agent_id": "a1", "command": "echo hej > f.txt; cat f.txt"})
    assert out["status"] == "ok" and out["exit_code"] == 0 and out["stdout"] == "hej\n"
    assert json.loads(out["text"])["stdout"] == "hej\n"
    out = tl.T_._exec_wt_write_file({"_runtime_agent_id": "a1", "path": "d/g.txt", "content": "x"})
    assert out["status"] == "ok" and "skrev 1 bytes" in out["text"]
    assert open(os.path.join(w["path"], "d", "g.txt")).read() == "x"


@needs_bwrap
def test_a_forged_agent_id_in_the_models_arguments_is_overwritten_by_the_server(tl):
    """Modellen for agent A skriver `_runtime_agent_id: a2` i sit kald - skrivningen lander stadig hos A."""
    w1, w2 = tl.agent("a1"), tl.agent("a2")
    call = {"id": "c1", "function": {"name": "wt_write_file",
                                     "arguments": json.dumps({"path": "forfalsket.txt", "content": "PWN",
                                                              "_runtime_agent_id": "a2"})}}
    tl.base_._execute_agent_tool_call(call, agent_id="a1")
    assert os.path.exists(os.path.join(w1["path"], "forfalsket.txt"))
    assert not os.path.exists(os.path.join(w2["path"], "forfalsket.txt"))


@needs_bwrap
def test_tool_failures_become_error_results_never_exceptions(tl, monkeypatch):
    tl.agent("a1")
    out = tl.T_._exec_wt_write_file({"_runtime_agent_id": "a1", "path": "../ud.txt", "content": "x"})
    assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE")
    monkeypatch.setattr(sb.shutil, "which", lambda n: None)
    out = tl.T_._exec_wt_bash({"_runtime_agent_id": "a1", "command": "echo x"})
    assert out["status"] == "error" and out["code"] == "SandboxUnavailable"


@needs_bwrap
def test_a_retained_worktree_can_no_longer_be_written_to(tl):
    w = tl.agent("a1")
    tl.W_._set(w["worktree_id"], status="retained")
    out = tl.T_._exec_wt_bash({"_runtime_agent_id": "a1", "command": "echo x > sent.txt"})
    assert (out["status"], out["code"]) == ("error", "NO_WORKTREE") and not os.path.exists(os.path.join(w["path"], "sent.txt"))


def test_other_tools_never_see_an_agent_id_the_model_wrote(tl, monkeypatch):
    seen = []
    monkeypatch.setattr("core.tools.simple_tools.execute_tool", lambda name, arguments: seen.append((name, dict(arguments))) or {"status": "ok"})
    call = {"id": "c1", "function": {"name": "read_file", "arguments": json.dumps({"path": "a", "_runtime_agent_id": "a2"})}}
    tl.base_._execute_agent_tool_call(call, agent_id="a1")
    assert seen == [("read_file", {"path": "a"})]                        # ingen id, hverken forfalsket eller tilfoejet
