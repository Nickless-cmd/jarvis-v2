"""C5a: worktree-manageren - rigtig git, rigtig sqlite, kvoter, aflevering og retention."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from datetime import UTC, datetime, timedelta

import pytest

from core.services import agent_worktree_git as g

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def wt(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_contract as c
    import core.services.agent_worktrees as W
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    (repo / "a.txt").write_text("a\n")
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", "init", cwd=repo)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))

    class H:
        c_, W_, repo_ = c, W, str(repo)

        def task(self, name="a1", owner="bjorn"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id="s1")
            return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id="s1",
                                       goal="skriv kode", parent_agent_id="jarvis", parent_run_id="pr")

        def prov(self, acc=None, **kw):
            acc = acc or self.task()
            return W.provision(owner_user_id="bjorn", assignment_id=acc["assignment_id"],
                               repo_path=kw.pop("repo", str(repo)), **kw), acc

        def rows(self):
            return [dict(r) for r in c._conn().execute("SELECT * FROM agent_worktrees")]

        def head(self):
            return sh("git", "rev-parse", "HEAD", cwd=repo).strip()

    return H()


# --- oprettelse ------------------------------------------------------------------------------------------

def test_provision_creates_an_isolated_worktree_bound_to_owner_agent_and_assignment(wt):
    w, acc = wt.prov()
    assert (w["status"], w["owner_user_id"], w["agent_id"], w["assignment_id"], w["target"]) == (
        "active", "bjorn", "a1", acc["assignment_id"], "runtime-container")
    assert w["branch"] == f"agent/{acc['assignment_id']}" and w["base_commit"] == wt.head()
    assert w["path"].startswith(str(wt.W_.worktree_root())) and (os.path.isdir(w["path"]))
    assert open(os.path.join(w["path"], "a.txt")).read() == "a\n"
    assert w["gitdir"].startswith(os.path.join(wt.repo_, ".git", "worktrees"))
    assert w["reserved_bytes"] >= wt.W_.WORKING_ALLOWANCE_BYTES


def test_two_assignments_never_share_a_writable_worktree(wt):
    w1, _ = wt.prov(wt.task("a1"))
    w2, _ = wt.prov(wt.task("a2"))
    assert w1["path"] != w2["path"] and w1["branch"] != w2["branch"]
    open(os.path.join(w1["path"], "kun-a1.txt"), "w").write("x")
    assert not os.path.exists(os.path.join(w2["path"], "kun-a1.txt"))


@pytest.mark.parametrize("case", ["anden-ejer", "afsluttet", "dublet", "udenfor-rod", "ugyldig-ref", "ukendt"])
def test_reserve_refuses_without_leaving_anything_behind(wt, case, tmp_path):
    acc = wt.task()
    owner, aid, repo, ref = "bjorn", acc["assignment_id"], wt.repo_, "HEAD"
    if case == "anden-ejer":
        owner = "anden"
    elif case == "afsluttet":
        wt.c_.commit_terminal_outcome(assignment_id=aid, status="completed")
    elif case == "dublet":
        wt.prov(acc)
    elif case == "udenfor-rod":
        other = tmp_path / "udenfor"; other.mkdir(); sh("git", "init", "-q", cwd=other)
        repo = str(other)
    elif case == "ugyldig-ref":
        ref = "--upload-pack=x"
    elif case == "ukendt":
        aid = "asg-findes-ikke"
    before = len(wt.rows())
    with pytest.raises(wt.c_.ContractError) as e:
        wt.W_.reserve(owner_user_id=owner, assignment_id=aid, repo_path=repo, base_ref=ref)
    assert e.value.code == "INVALID_SCOPE" and len(wt.rows()) == before


def test_a_failed_creation_leaves_no_half_worktree_and_frees_the_reservation(wt, monkeypatch):
    def boom(*a, **k):
        os.makedirs(a[1], exist_ok=True)
        open(os.path.join(a[1], "halvt"), "w").write("x")
        raise g.GitError("diskfuld")

    monkeypatch.setattr(g, "add_worktree", boom)
    acc = wt.task()
    with pytest.raises(wt.c_.ContractError):
        wt.W_.provision(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    (row,) = wt.rows()
    assert row["status"] == "failed" and "diskfuld" in row["last_error"] and not os.path.exists(row["path"])
    q = wt.W_.quota_status()
    assert (q["writing"], q["retained"], q["bytes"]) == (0, 0, 0)


# --- kvoter ------------------------------------------------------------------------------------------------

def test_concurrent_writing_limit_blocks_the_next_without_creating_it(wt, monkeypatch):
    monkeypatch.setattr(wt.W_, "MAX_CONCURRENT_WRITING", 2)
    wt.prov(wt.task("a1")); wt.prov(wt.task("a2"))
    acc = wt.task("a3")
    with pytest.raises(wt.c_.ContractError) as e:
        wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    assert e.value.code == "CAPACITY" and "samtidige" in e.value.detail and len(wt.rows()) == 2


def test_the_retained_limit_counts_retained_worktrees_too(wt, monkeypatch):
    monkeypatch.setattr(wt.W_, "MAX_RETAINED", 2)
    w1, a1 = wt.prov(wt.task("a1")); wt.prov(wt.task("a2"))
    wt.c_.commit_terminal_outcome(assignment_id=a1["assignment_id"], status="completed")
    wt.W_.snapshot_for_assignment(assignment_id=a1["assignment_id"])         # a1 er nu retained, ikke fri
    acc = wt.task("a3")
    with pytest.raises(wt.c_.ContractError) as e:
        wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    assert e.value.code == "CAPACITY" and "bevarede" in e.value.detail


@pytest.mark.parametrize("attr,value,needle", [
    ("PER_ASSIGNMENT_BYTES", 10, "pr. assignment"),
    ("TARGET_TOTAL_BYTES", 10, "samlede"),
])
def test_byte_quotas_refuse_before_anything_is_created(wt, monkeypatch, attr, value, needle):
    monkeypatch.setattr(wt.W_, attr, value)
    acc = wt.task()
    with pytest.raises(wt.c_.ContractError) as e:
        wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    assert e.value.code == "CAPACITY" and needle in e.value.detail and wt.rows() == []


def test_the_free_space_floor_wins_over_the_quota(wt, monkeypatch):
    monkeypatch.setattr(wt.W_, "_free_floor", lambda path: (10 * 1024 ** 3, 10 * 1024 ** 3))
    acc = wt.task()
    with pytest.raises(wt.c_.ContractError) as e:
        wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    assert e.value.code == "CAPACITY" and "ledig plads" in e.value.detail


def test_simultaneous_reservations_cannot_overshoot_the_limit(wt, monkeypatch):
    monkeypatch.setattr(wt.W_, "MAX_CONCURRENT_WRITING", 1)
    accs = [wt.task(f"a{i}") for i in range(4)]
    results = []

    def go(acc):
        try:
            wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
            results.append("ok")
        except wt.c_.ContractError as exc:
            results.append(exc.code)

    ts = [threading.Thread(target=go, args=(a,)) for a in accs]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["CAPACITY"] * 3 + ["ok"] and len(wt.rows()) == 1


def test_growth_over_the_quota_stops_new_writes_and_deletes_nothing(wt, monkeypatch):
    w, _ = wt.prov()
    assert wt.W_.writes_allowed(worktree_id=w["worktree_id"]) is True
    open(os.path.join(w["path"], "stor.bin"), "wb").write(b"x" * 5000)
    monkeypatch.setattr(wt.W_, "PER_ASSIGNMENT_BYTES", 1000)
    out = wt.W_.check_growth(worktree_id=w["worktree_id"])
    assert out["over_quota"] is True and out["size_bytes"] >= 5000
    assert wt.W_.writes_allowed(worktree_id=w["worktree_id"]) is False
    assert os.path.exists(os.path.join(w["path"], "stor.bin"))              # tilstanden bevares


# --- aflevering ---------------------------------------------------------------------------------------------

def _work(w):
    open(os.path.join(w["path"], "a.txt"), "w").write("a\nagentens linje\n")
    open(os.path.join(w["path"], "ny.py"), "w").write("print('ny')\n")


def test_terminal_settlement_delivers_diff_files_and_keeps_the_worktree_unmerged(wt):
    from core.runtime import db_agent_artifacts as art
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    w, acc = wt.prov()
    head_before = wt.head()
    _work(w)
    update_agent_registry_entry("a1", status="completed")
    (m,) = wt.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")
    payload = json.loads(m["payload_json"])
    result = json.loads(art.read_artifact(owner_user_id="bjorn", ref=payload["artifact_ref"])["content"])
    ws = result["worktree"]
    assert (ws["files"], ws["commits"], ws["errors"]) == (2, 0, []) and ws["branch"] == w["branch"]
    run_id = payload["last_run_id"]
    diff = art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/diff.patch")["content"]
    changes = json.loads(art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/changes.json")["content"])
    assert "+agentens linje" in diff and "ny.py" in diff
    assert {f["path"] for f in changes["files"]} == {"a.txt", "ny.py"}
    row = wt.rows()[0]
    assert row["status"] == "retained" and row["size_bytes"] > 0 and os.path.isdir(w["path"])
    assert wt.head() == head_before and "main" in sh("git", "branch", "--show-current", cwd=wt.repo_)
    assert open(os.path.join(wt.repo_, "a.txt")).read() == "a\n"              # hovedgrenen er roert ikke


def test_the_artifacts_are_only_readable_by_the_owner(wt):
    from core.runtime import db_agent_artifacts as art
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    w, acc = wt.prov()
    _work(w)
    update_agent_registry_entry("a1", status="completed")
    run_id = wt.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    assert art.read_artifact(owner_user_id="anden", ref=f"{run_id}/diff.patch")["status"] == "NOT_FOUND"


def test_a_diff_over_the_artifact_limit_keeps_the_worktree_and_says_so(wt, monkeypatch):
    from core.runtime import db_agent_artifacts as art

    w, acc = wt.prov()
    _work(w)
    monkeypatch.setattr(art, "MAX_RUN_BYTES", 60)
    wt.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    summary = wt.W_.snapshot_for_assignment(assignment_id=acc["assignment_id"])
    assert any("diff.patch" in e for e in summary["errors"])
    row = wt.rows()[0]
    assert row["status"] == "retained" and "ArtifactTooLarge" in row["last_error"] and os.path.isdir(w["path"])


def test_an_assignment_without_a_worktree_is_untouched_by_settlement(wt):
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    wt.task()
    update_agent_registry_entry("a1", status="completed")
    (m,) = wt.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")
    assert m and wt.rows() == []


# --- beslutning og retention ----------------------------------------------------------------------------------

def _retained(wt, name="a1"):
    w, acc = wt.prov(wt.task(name))
    _work(w)
    wt.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    wt.W_.snapshot_for_assignment(assignment_id=acc["assignment_id"])
    return wt.W_.get(worktree_id=w["worktree_id"])


def test_decide_is_owner_checked_and_only_from_retained(wt):
    w = _retained(wt)
    with pytest.raises(wt.c_.ContractError):
        wt.W_.decide(owner_user_id="anden", worktree_id=w["worktree_id"], decision="discarded")
    with pytest.raises(wt.c_.ContractError):
        wt.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="merged")
    d = wt.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="discarded")
    assert (d["status"], d["decision"]) == ("decided", "discarded")
    with pytest.raises(wt.c_.ContractError):
        wt.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="discarded")


def test_a_decided_worktree_is_removed_after_seven_days_and_only_then(wt):
    w = _retained(wt)
    d = wt.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="integrated")
    t0 = datetime.fromisoformat(d["decided_at"].replace("Z", "+00:00"))
    assert wt.W_.sweep(now=t0 + timedelta(days=6, hours=23))["removed"] == []
    assert os.path.isdir(w["path"])
    out = wt.W_.sweep(now=t0 + timedelta(days=7, minutes=1))
    assert out["removed"] == [w["worktree_id"]] and not os.path.exists(w["path"])
    assert wt.rows()[0]["status"] == "removed"
    assert wt.W_.quota_status()["retained"] == 0                         # kvoten frigives foerst nu


def test_an_undecided_worktree_needs_attention_at_14_days_and_is_archived_at_30(wt):
    from core.runtime import db_agent_artifacts as art

    w = _retained(wt)
    t0 = datetime.fromisoformat(w["retained_at"].replace("Z", "+00:00"))
    assert wt.W_.sweep(now=t0 + timedelta(days=13))["attention"] == []
    assert wt.W_.sweep(now=t0 + timedelta(days=15))["attention"] == [w["worktree_id"]]
    assert os.path.isdir(w["path"])
    out = wt.W_.sweep(now=t0 + timedelta(days=31))
    assert out["archived"] == [w["worktree_id"]] and not os.path.exists(w["path"])
    run_id = wt.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    assert "+agentens linje" in art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/diff.patch")["content"]
    assert wt.rows()[0]["status"] == "archived"


def test_archiving_failure_keeps_the_worktree(wt, monkeypatch):
    w = _retained(wt)
    monkeypatch.setattr(wt.W_, "_archive", lambda wt_: False)
    t0 = datetime.fromisoformat(w["retained_at"].replace("Z", "+00:00"))
    out = wt.W_.sweep(now=t0 + timedelta(days=31))
    assert out["archived"] == [] and out["blocked"] == [w["worktree_id"]] and os.path.isdir(w["path"])


def test_unknown_and_stale_creating_states_block_all_cleanup(wt):
    w, _ = wt.prov()
    wt.W_._set(w["worktree_id"], status="unknown")
    out = wt.W_.sweep(now=NOW + timedelta(days=400))
    assert out["blocked"] == [w["worktree_id"]] and os.path.isdir(w["path"])
    w2, _ = wt.prov(wt.task("a2"))
    wt.W_._set(w2["worktree_id"], status="creating")
    out = wt.W_.sweep(now=datetime.now(UTC) + timedelta(hours=2))
    assert out["stale"] == [w2["worktree_id"]] and wt.W_.get(worktree_id=w2["worktree_id"])["status"] == "unknown"


def test_cleanup_refuses_a_tampered_path_and_a_mismatched_owner_never_touching_other_agents(wt, tmp_path):
    w1 = _retained(wt, "a1")
    w2 = _retained(wt, "a2")
    for w in (w1, w2):
        wt.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="discarded")
    later = datetime.now(UTC) + timedelta(days=10)
    precious = tmp_path / "bjorns-egne-filer"; precious.mkdir(); (precious / "vigtig.txt").write_text("!")
    wt.W_._set(w1["worktree_id"], path=str(precious))                     # databasen pege paa noget andet
    c = wt.c_._conn()
    c.execute("UPDATE agent_assignments SET owner_user_id='anden' WHERE assignment_id=?", (w2["assignment_id"],))
    c.commit()
    out = wt.W_.sweep(now=later)
    assert out["removed"] == []
    assert (precious / "vigtig.txt").exists() and os.path.isdir(w2["path"])


def test_reconcile_marks_a_vanished_worktree_unknown_never_removed(wt):
    import shutil

    w, _ = wt.prov()
    shutil.rmtree(w["path"])
    assert wt.W_.reconcile() == [w["worktree_id"]]
    assert wt.rows()[0]["status"] == "unknown"


def test_quota_status_reports_the_numbers_and_ignores_other_targets(wt):
    wt.prov(wt.task("a1"))
    q = wt.W_.quota_status()
    assert (q["writing"], q["retained"], q["max_writing"], q["max_retained"]) == (1, 1, 12, 24)
    assert q["bytes"] >= wt.W_.WORKING_ALLOWANCE_BYTES
    assert wt.W_.quota_status(target="client:laptop")["writing"] == 0


def test_a_crash_during_creation_leaves_a_creating_trace(wt, monkeypatch):
    def crash(*a, **k):
        raise SystemExit("proces doede midt i git")

    monkeypatch.setattr(g, "add_worktree", crash)
    acc = wt.task()
    w = wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
    with pytest.raises(SystemExit):
        wt.W_.materialize(worktree_id=w["worktree_id"])
    assert wt.rows()[0]["status"] == "creating"                          # sporet findes til genoprettelsen


def test_the_reservation_check_and_insert_are_one_atomic_step(wt, monkeypatch):
    """Tving et vindue mellem taelling og INSERT: uden en skrivelaas ville alle fire komme igennem."""
    import time

    monkeypatch.setattr(wt.W_, "MAX_CONCURRENT_WRITING", 1)
    real = wt.W_._quota

    def slow(conn, target):
        out = real(conn, target)
        time.sleep(0.25)
        return out

    monkeypatch.setattr(wt.W_, "_quota", slow)
    accs = [wt.task(f"a{i}") for i in range(4)]
    results = []

    def go(acc):
        try:
            wt.W_.reserve(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=wt.repo_)
            results.append("ok")
        except wt.c_.ContractError as exc:
            results.append(exc.code)
        except Exception as exc:
            results.append(type(exc).__name__)

    ts = [threading.Thread(target=go, args=(a,)) for a in accs]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["CAPACITY"] * 3 + ["ok"] and len(wt.rows()) == 1


def test_a_record_pointing_at_ANOTHER_agents_valid_worktree_never_removes_it(wt):
    """Den farlige variant: stien er et ægte worktree - bare ikke dette assignments."""
    w1 = _retained(wt, "a1")
    w2 = _retained(wt, "a2")
    wt.W_.decide(owner_user_id="bjorn", worktree_id=w1["worktree_id"], decision="discarded")
    wt.W_._set(w1["worktree_id"], path=w2["path"], branch=w2["branch"])
    out = wt.W_.sweep(now=datetime.now(UTC) + timedelta(days=10))
    assert out["removed"] == [] and os.path.isdir(w2["path"])
    assert os.path.exists(os.path.join(w2["path"], "ny.py"))
