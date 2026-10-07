"""F4d: integration af en kodeagents arbejde - approval bundet til diffen, fletning uden at roere nogens working tree."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from core.services import agent_worktree_git as g

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}
O, S = "bjorn", "s1"


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def ig(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    import core.services.agent_integration as I
    import core.services.agent_worktrees as W
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    (repo / "a.txt").write_text("linje 1\nlinje 2\nlinje 3\n")
    (repo / "b.txt").write_text("b\n")
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", "init", cwd=repo)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))
    svc.set_capability(True, role="owner")

    class H:
        appr_, c_, svc_, I_, W_ = appr, c, svc, I, W
        repo_ = str(repo)

        def finished(self, name="a1", edit=True):
            """Et afsluttet kodeassignment med et bevaret worktree og agentens aendringer."""
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=O, owner_session_id=S)
            acc = c.accept_assignment(agent_id=name, owner_user_id=O, origin_session_id=S, goal="skriv",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            wt = W.provision(owner_user_id=O, assignment_id=acc["assignment_id"], repo_path=str(repo))
            if edit:
                open(os.path.join(wt["path"], "a.txt"), "w").write("linje 1\nAGENTENS linje 2\nlinje 3\n")
                open(os.path.join(wt["path"], "ny.py"), "w").write("print('ny')\n")
            c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
            W.snapshot_for_assignment(assignment_id=acc["assignment_id"])
            return acc, W.get(worktree_id=wt["worktree_id"])

        def ask(self, acc):
            return I.request_integration(owner_user_id=O, origin_session_id=S, assignment_id=acc["assignment_id"])

        def human(self, r, decision="approve"):
            return svc.decide_approval(approval_id=r["approval_id"], decision=decision, actor_user_id=O,
                                       actor_kind="human", digest=r["args_digest"])

        def host(self):
            return {"head": sh("git", "rev-parse", "HEAD", cwd=repo).strip(),
                    "status": sh("git", "status", "--porcelain", cwd=repo),
                    "a": (repo / "a.txt").read_text(), "index": sh("git", "ls-files", "-s", cwd=repo),
                    "branches": sh("git", "branch", "--format=%(refname:short)", cwd=repo)}

        def messages(self):
            return [json.loads(m["payload_json"]) | {"type": m["result_type"]}
                    for m in c._conn().execute("SELECT * FROM agent_result_outbox WHERE result_type LIKE 'integration:%'")]

    return H()


def test_a_request_binds_the_exact_diff_and_only_jarvis_asked(ig):
    acc, wt = ig.finished()
    r = ig.ask(acc)
    args = json.loads(r["arguments_json"])
    assert (r["kind"], r["tool_name"], r["requested_by"], r["risk_class"], r["status"]) == (
        "integration", "integrate_worktree", "jarvis", "integration", "pending")
    assert (args["worktree_id"], args["branch"], args["base_commit"], args["files"]) == (
        wt["worktree_id"], wt["branch"], wt["base_commit"], 2)
    assert len(args["diff_sha256"]) == 64 and sorted(args["files_preview"]) == ["A ny.py", "M a.txt"]
    assert ig.ask(acc)["approval_id"] == r["approval_id"]                      # idempotent for samme diff


def test_changing_the_work_changes_the_digest_so_an_old_approval_cannot_cover_it(ig):
    acc, wt = ig.finished()
    first = ig.ask(acc)
    open(os.path.join(wt["path"], "ny.py"), "w").write("print('aendret efter anmodningen')\n")
    second = ig.ask(acc)
    assert second["approval_id"] != first["approval_id"] and second["args_digest"] != first["args_digest"]


@pytest.mark.parametrize("case", ["anden-ejer", "ikke-retained", "ingen-aendringer", "intet-worktree"])
def test_a_request_is_refused_for_the_wrong_state_or_owner(ig, case):
    acc, wt = ig.finished(edit=case != "ingen-aendringer")
    owner = "bjorn"
    if case == "anden-ejer":
        owner = "anden"
    elif case == "ikke-retained":
        ig.W_._set(wt["worktree_id"], status="active")
    elif case == "intet-worktree":
        acc = {"assignment_id": "asg-findes-ikke"}
    with pytest.raises(ig.c_.ContractError):
        ig.I_.request_integration(owner_user_id=owner, origin_session_id=S, assignment_id=acc["assignment_id"])
    assert ig.appr_.list_for_owner(owner_user_id=O) == []


def test_approval_merges_onto_a_new_branch_without_touching_anyones_working_tree(ig):
    acc, wt = ig.finished()
    # Bjoerns checkout er beskidt: en aendret fil + en staget fil. Intet af det maa roeres.
    (os.path.join(ig.repo_, "b.txt"))
    open(os.path.join(ig.repo_, "b.txt"), "w").write("b - Bjoerns uafsluttede aendring\n")
    open(os.path.join(ig.repo_, "staget.txt"), "w").write("staget\n")
    sh("git", "add", "staget.txt", cwd=ig.repo_)
    before = ig.host()
    r = ig.ask(acc)
    out = ig.human(r)
    assert out["status"] == "ok" and out["integration"]["status"] == "integrated"
    branch = out["integration"]["integrate_branch"]
    assert branch == f"integrate/{acc['assignment_id']}"
    after = ig.host()
    assert (after["head"], after["status"], after["a"], after["index"]) == (
        before["head"], before["status"], before["a"], before["index"])            # ALT paa vaerten er uroert
    assert after["branches"].split() == sorted(set(before["branches"].split()) | {branch})   # agent/<id> fandtes allerede
    assert sh("git", "show", f"{branch}:a.txt", cwd=ig.repo_) == "linje 1\nAGENTENS linje 2\nlinje 3\n"
    assert sh("git", "show", f"{branch}:ny.py", cwd=ig.repo_) == "print('ny')\n"
    parents = sh("git", "log", "-1", "--format=%P", branch, cwd=ig.repo_).split()
    assert parents[0] == before["head"] and len(parents) == 2
    assert sh("git", "rev-parse", wt["branch"], cwd=ig.repo_).strip() == parents[1]
    assert sh("git", "log", "-1", "--format=%P", wt["branch"], cwd=ig.repo_).strip() == wt["base_commit"]


def test_the_merge_keeps_changes_made_on_main_after_the_agent_started(ig):
    acc, wt = ig.finished()
    open(os.path.join(ig.repo_, "b.txt"), "w").write("b - aendret paa main bagefter\n")
    sh("git", "commit", "-qam", "main gik videre", cwd=ig.repo_)
    new_head = sh("git", "rev-parse", "HEAD", cwd=ig.repo_).strip()
    out = ig.human(ig.ask(acc))
    branch = out["integration"]["integrate_branch"]
    assert sh("git", "show", f"{branch}:b.txt", cwd=ig.repo_) == "b - aendret paa main bagefter\n"
    assert sh("git", "show", f"{branch}:a.txt", cwd=ig.repo_).count("AGENTENS") == 1
    assert sh("git", "log", "-1", "--format=%P", branch, cwd=ig.repo_).split()[0] == new_head


def test_the_approval_is_used_exactly_once_and_the_worktree_is_marked_integrated(ig):
    acc, wt = ig.finished()
    r = ig.ask(acc)
    ig.human(r)
    assert ig.appr_.get(approval_id=r["approval_id"])["status"] == "consumed"
    assert ig.I_.execute_approved(ig.appr_.get(approval_id=r["approval_id"])) == {"status": "not_consumed"}
    w = ig.W_.get(worktree_id=wt["worktree_id"])
    assert (w["status"], w["decision"]) == ("decided", "integrated")
    assert len(ig.messages()) == 1


def test_jarvis_is_told_the_outcome_through_the_normal_inbox(ig):
    from core.services.agent_result_inbox import claim_for_model_step

    acc, _ = ig.finished()
    ig.c_.claim_pending_results(owner_user_id=O, origin_session_id=S)                    # det terminale resultat er set
    ig.human(ig.ask(acc))
    text = claim_for_model_step(owner_user_id=O, session_id=S)
    assert "status=integrated" in text and "integrate/" in text and "git merge --ff-only" in text


def test_if_the_work_changed_after_the_approval_nothing_is_integrated(ig):
    acc, wt = ig.finished()
    r = ig.ask(acc)
    open(os.path.join(wt["path"], "ny.py"), "w").write("print('SMUGLET IND EFTER GODKENDELSEN')\n")
    before = ig.host()
    out = ig.human(r)
    assert out["integration"]["status"] == "failed" and out["integration"]["error_code"] == "DIFF_CHANGED"
    assert ig.host() == before and ig.appr_.get(approval_id=r["approval_id"])["status"] == "consumed"
    assert [m["error_code"] for m in ig.messages()] == ["DIFF_CHANGED"]
    assert ig.W_.get(worktree_id=wt["worktree_id"])["status"] == "retained"             # intet afgjort
    again = ig.ask(acc)                                                                  # en ny anmodning er mulig
    assert again["approval_id"] != r["approval_id"]


def test_a_conflict_creates_no_branch_and_reports_the_files(ig):
    acc, wt = ig.finished()
    open(os.path.join(ig.repo_, "a.txt"), "w").write("linje 1\nMAINS linje 2\nlinje 3\n")
    sh("git", "commit", "-qam", "main aendrede samme linje", cwd=ig.repo_)
    before = ig.host()
    out = ig.human(ig.ask(acc))
    assert out["integration"]["status"] == "conflict" and out["integration"]["error_code"] == "MERGE_CONFLICT"
    assert out["integration"]["conflicts"] == ["a.txt"]
    assert ig.host() == before and f"integrate/{acc['assignment_id']}" not in ig.host()["branches"]
    assert ig.W_.get(worktree_id=wt["worktree_id"])["status"] == "retained"


def test_an_existing_branch_is_never_overwritten(ig):
    acc, _ = ig.finished()
    sh("git", "branch", f"integrate/{acc['assignment_id']}", cwd=ig.repo_)
    old = sh("git", "rev-parse", f"integrate/{acc['assignment_id']}", cwd=ig.repo_).strip()
    out = ig.human(ig.ask(acc))
    assert out["integration"]["error_code"] == "BRANCH_EXISTS"
    assert sh("git", "rev-parse", f"integrate/{acc['assignment_id']}", cwd=ig.repo_).strip() == old


def test_a_denied_integration_changes_nothing(ig):
    acc, wt = ig.finished()
    before = ig.host()
    out = ig.human(ig.ask(acc), "deny")
    assert out["approval"]["status"] == "denied" and "integration" not in out
    assert ig.host() == before and ig.messages() == []
    assert ig.W_.get(worktree_id=wt["worktree_id"])["status"] == "retained"
    with pytest.raises(ig.c_.ContractError) as e:                                        # samme diff kan ikke anmodes igen
        ig.ask(acc)
    assert e.value.code == "POLICY_DENIED"


@pytest.mark.parametrize("kind", ["agent", "model", "jarvis"])
def test_jarvis_cannot_approve_his_own_integration_request(ig, kind):
    acc, _ = ig.finished()
    r = ig.ask(acc)
    before = ig.host()
    out = ig.svc_.decide_approval(approval_id=r["approval_id"], decision="approve", actor_user_id=O,
                                  actor_kind=kind, digest=r["args_digest"])
    assert (out["status"], out["code"]) == ("error", "POLICY_DENIED")
    assert ig.host() == before and ig.appr_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_the_supervisor_finishes_an_integration_approved_just_before_a_restart(ig):
    acc, _ = ig.finished()
    r = ig.ask(acc)
    ig.appr_.decide(approval_id=r["approval_id"], decision="approve", actor_user_id=O, actor_kind="human",
                    digest=r["args_digest"])                         # besluttet, men execute_approved blev ikke kaldt
    assert f"integrate/{acc['assignment_id']}" not in ig.host()["branches"]
    ig.svc_.supervise()
    assert f"integrate/{acc['assignment_id']}" in ig.host()["branches"]
    ig.svc_.supervise()                                              # ikke to gange
    assert len(ig.messages()) == 1


def test_an_agent_that_rewrites_its_dot_git_file_cannot_steer_the_servers_commit(ig, tmp_path):
    acc, wt = ig.finished()
    other = tmp_path / "andet"
    other.mkdir()
    sh("git", "init", "-q", cwd=other)
    (other / "hemmelig.txt").write_text("HEMMELIGT")
    sh("git", "add", "-A", cwd=other)
    sh("git", "commit", "-q", "-m", "x", cwd=other)
    open(os.path.join(wt["path"], ".git"), "w").write(f"gitdir: {other}/.git\n")
    out = ig.human(ig.ask(acc))
    assert out["integration"]["status"] == "integrated"
    tree = sh("git", "ls-tree", "-r", "--name-only", out["integration"]["integrate_branch"], cwd=ig.repo_).split()
    assert "hemmelig.txt" not in tree and ".git" not in tree and "ny.py" in tree


def test_the_service_entry_needs_the_engine_and_returns_an_approval_request_view(ig):
    acc, _ = ig.finished()
    out = ig.svc_.request_integration(owner_user_id=O, origin_session_id=S, assignment_id=acc["assignment_id"])
    assert out["status"] == "approval_requested" and "kan ikke godkende" in out["note"]
    assert "arguments_json" not in out["approval"] and out["approval"]["tool_name"] == "integrate_worktree"
    ig.svc_.set_capability(False)
    off = ig.svc_.request_integration(owner_user_id=O, origin_session_id=S, assignment_id=acc["assignment_id"])
    assert (off["status"], off["code"]) == ("error", "POLICY_DENIED")


def test_the_tool_is_pinned_hidden_when_off_and_uses_the_authenticated_owner(ig):
    from core.identity import workspace_context as w
    from core.tools import agent_contract_tools as T

    acc, _ = ig.finished()
    tok = w.set_context(workspace_name="bjorn", user_id=O)
    try:
        out = T._exec_integrate_agent_work({"_runtime_session_id": S, "assignment_id": acc["assignment_id"],
                                            "owner_user_id": "anden", "_runtime_user_id": "anden"})
        assert out["status"] == "approval_requested"
        w.set_context(workspace_name="bjorn", user_id="")
        bad = T._exec_integrate_agent_work({"_runtime_session_id": S, "assignment_id": acc["assignment_id"]})
        assert (bad["status"], bad["code"]) == ("error", "INVALID_SCOPE")
    finally:
        w.reset_context(tok)
    assert "integrate_agent_work" in T.CONTRACT_TOOL_NAMES and "integrate_agent_work" in T._NEW_ONLY
