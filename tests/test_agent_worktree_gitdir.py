"""Leverance C, hul 1: git INDE I sandboxen - en legitim commit lykkes, en ondsindet agent naar intet uden for sin gitdir.

Alt koerer mod rigtig bwrap, rigtig git og rigtig sqlite. Beviset for "naar intet" er et byte-for-byte
fingeraftryk af hovedrepoets ``.git`` og et fremmed worktree foer og efter agentens angreb.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
pytestmark = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


def fingerprint(root) -> dict[str, str]:
    """Sti -> indholds-hash for ALLE filer og symlinks under root (mapper uden filer taeller ikke)."""
    out: dict[str, str] = {}
    for dp, dn, fn in os.walk(root, followlinks=False):
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.islink(p):
                out[p] = "link:" + os.readlink(p)
            else:
                out[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


@pytest.fixture
def env(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_contract as c
    import core.services.agent_worktree_exec as E
    import core.services.agent_worktree_gitdir as AGD
    import core.services.agent_worktrees as W
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    (repo / "a.txt").write_text("a\n")
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\ntouch %s/HOOK-RAN\n" % tmp_path)
    hook.chmod(0o755)
    sh("git", "add", "-A", cwd=repo)
    subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "init"], cwd=repo, env=ENV, check=True)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))

    class H:
        c_, E_, W_, AGD_ = c, E, W, AGD
        repo_, tmp_ = str(repo), tmp_path

        def task(self, name):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id="bjorn", owner_session_id="s1")
            return c.accept_assignment(agent_id=name, owner_user_id="bjorn", origin_session_id="s1",
                                       goal="skriv kode", parent_agent_id="jarvis", parent_run_id="pr")

        def wt(self, name="a1"):
            acc = self.task(name)
            w = W.provision(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=str(repo))
            return w, acc

        def run(self, w, cmd, **kw):
            return E.run_in_worktree(worktree_id=w["worktree_id"], command=cmd, **kw)

        def main_refs(self):
            return sh("git", "for-each-ref", "--format=%(refname) %(objectname)", cwd=repo).strip().splitlines()

        def settle(self, acc):
            c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
            return W.snapshot_for_assignment(assignment_id=acc["assignment_id"])

    return H()


LEGIT = ("echo ny > ny.txt && git add -A && git commit -q -m 'agentens commit' && git log --oneline | wc -l "
         "&& git rev-parse HEAD")


def test_a_legitimate_commit_succeeds_and_shows_up_in_the_snapshot(env):
    w, acc = env.wt()
    before_refs = env.main_refs()
    out = env.run(w, LEGIT)
    assert out["exit_code"] == 0 and out["stderr"] == "" and out["timed_out"] is False
    n, tip = out["stdout"].split()
    assert n == "2"                                           # init + agentens commit
    summary = env.settle(acc)
    assert summary["errors"] == [] and summary["commits"] == 1 and summary["files"] == 1
    assert set(summary["artifacts"]) == {"diff.patch", "changes.json"}
    from core.runtime import db_agent_artifacts as art
    run_id = env.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    changes = json.loads(art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/changes.json")["content"])
    assert changes["commits"] == [tip] and changes["files"] == [{"status": "A", "path": "ny.txt"}]
    diff = art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/diff.patch")["content"]
    assert "+ny" in diff
    # commit'en er importeret under agent-work; agentens gren i hovedrepoet er uroert (integrationen bruger den)
    after = env.main_refs()
    assert sorted(after) == sorted(before_refs + [f"refs/agent-work/{acc['assignment_id']} {tip}"])
    assert sh("git", "cat-file", "-t", tip, cwd=env.repo_).strip() == "commit"
    assert sh("git", "log", "-1", "--format=%an <%ae>|%s", tip, cwd=env.repo_).strip() == \
        "Jarvis agent <agent@jarvis.local>|agentens commit"


def test_uncommitted_work_alone_has_no_commits_and_the_import_ref_stays_at_the_base(env):
    w, acc = env.wt()
    env.run(w, "echo x > u.txt")
    summary = env.settle(acc)
    assert summary["commits"] == 0 and summary["files"] == 1 and summary["errors"] == []
    assert f"refs/agent-work/{acc['assignment_id']} {w['base_commit']}" in env.main_refs()


def test_git_status_inside_sees_a_clean_tree_at_the_base(env):
    w, _ = env.wt()
    out = env.run(w, "git status --porcelain; git rev-parse --abbrev-ref HEAD; git diff --stat")
    assert out["exit_code"] == 0 and out["stdout"].split() == [f"agent/{w['assignment_id']}"]


def _attack(env, w, other):
    """Alt hvad en ondsindet agent kan finde paa mod git-opsaetningen. Fejl i enkelttrin er forventede."""
    objs = env.AGD_._objects_chain(env.repo_)
    main = env.repo_
    script = "\n".join([
        "git config core.hooksPath /work/hooks",
        "git config filter.pwn.clean 'touch %s/FILTER-RAN'" % env.tmp_,
        "git config --local alias.x '!touch %s/ALIAS-RAN'" % env.tmp_,
        "echo '[core]\nhooksPath=/work/hooks' >> /gitdir/config",
        "echo 'ref: refs/heads/main' > /gitdir/HEAD",
        "git checkout -q -b other",
        "git symbolic-ref HEAD refs/heads/other",
        "git pack-refs --all --prune",
        "echo '* filter=pwn' > .gitattributes",
        "mkdir -p hooks; printf '#!/bin/sh\\ntouch %s/AGENT-HOOK-RAN\\n' > hooks/pre-commit; chmod +x hooks/pre-commit"
        % env.tmp_,
        *[f"echo pwn > {o}/pwn; echo pwn > {o}/info/alternates; rm -rf {o}/pack" for o in objs],
        f"ls {main}/.git/hooks {main}/.git/config {main}/.git/refs {main}/.git/worktrees 2>&1",
        f"echo pwn > {main}/.git/refs/heads/pwn; echo pwn > {main}/a.txt; echo pwn > {main}/.git/config",
        f"git -C {main} update-ref refs/heads/pwn HEAD; git push {main} HEAD:refs/heads/pwn",
        f"echo pwn > {other}/pwn.txt; echo pwn > {other}.gitdir/config; echo pwn > {other}.gitdir/HEAD",
        "echo 'gitdir: /nowhere' > .git",
        "git update-ref refs/heads/main HEAD; git tag v1; git branch evil",
        "git add -A && git commit -q -m 'ondsindet' && echo COMMITTED",
        "echo '/work' > /gitdir/commondir",                       # plantes paa sandboxens tmpfs, aldrig paa vaerten
        "mkdir -p /gitdir/info; echo '* filter=pwn' > /gitdir/info/attributes",
        "true",
    ])
    return env.run(w, script)


def test_a_malicious_agent_cannot_touch_the_main_repo_other_worktrees_or_its_own_gitdir_config(env):
    w, acc = env.wt("a1")
    w2, _ = env.wt("a2")
    gd = env.AGD_.gitdir_path(w["path"])
    host_before = {
        "main_git": fingerprint(os.path.join(env.repo_, ".git")),
        "main_files": fingerprint(env.repo_),
        "other_wt": fingerprint(w2["path"]),
        "other_gd": fingerprint(env.AGD_.gitdir_path(w2["path"])),
        "own_ro": {n: open(os.path.join(gd, n), "rb").read() for n in ("config", "HEAD", "packed-refs")},
    }
    top_before = sorted(os.listdir(gd))
    refs_before = env.main_refs()

    out = _attack(env, w, w2["path"])

    assert out["timed_out"] is False and "COMMITTED" in out["stdout"]
    assert not any((env.tmp_ / n).exists() for n in ("FILTER-RAN", "ALIAS-RAN", "HOOK-RAN", "AGENT-HOOK-RAN"))
    assert fingerprint(os.path.join(env.repo_, ".git")) == host_before["main_git"]
    assert fingerprint(env.repo_) == host_before["main_files"]
    assert fingerprint(w2["path"]) == host_before["other_wt"]
    assert fingerprint(env.AGD_.gitdir_path(w2["path"])) == host_before["other_gd"]
    assert {n: open(os.path.join(gd, n), "rb").read() for n in ("config", "HEAD", "packed-refs")} == \
        host_before["own_ro"]
    assert sorted(os.listdir(gd)) == top_before == ["HEAD", "config", "idx", "objects", "packed-refs", "refs"]
    assert env.main_refs() == refs_before
    # selve angrebsscriptet naaede ikke at committe via en hook eller et filter; "ondsindet" commit'en er
    # agentens egen (den maa gerne commite i sin egen gren) men importen kopierer KUN den ene gren
    summary = env.settle(acc)
    assert summary["errors"] == []
    names = [r.split()[0] for r in env.main_refs()]
    assert sorted(set(names) - {r.split()[0] for r in refs_before}) == [f"refs/agent-work/{acc['assignment_id']}"]
    assert not any((env.tmp_ / n).exists() for n in ("FILTER-RAN", "ALIAS-RAN", "HOOK-RAN", "AGENT-HOOK-RAN"))


def test_core_hookspath_and_friends_cannot_be_changed_from_inside(env):
    w, _ = env.wt()
    out = env.run(w, "git config core.hooksPath /work/h; echo rc=$?; git config --get core.hooksPath; "
                     "git config alias.x '!id'; echo rc=$?")
    assert out["stdout"].split() == ["rc=255", "/dev/null", "rc=255"] or out["stdout"].split() == \
        ["rc=1", "/dev/null", "rc=1"] or "rc=0" not in out["stdout"]
    assert "/dev/null" in out["stdout"]


def test_the_main_repository_objects_are_readable_but_read_only_inside(env):
    w, _ = env.wt()
    objs = env.AGD_._objects_chain(env.repo_)
    out = env.run(w, f"git cat-file -t HEAD && touch {objs[0]}/x 2>&1; echo rc=$?")
    assert out["stdout"].split()[0] == "commit" and "Read-only" in out["stdout"] and "rc=1" in out["stdout"]
    assert not os.path.exists(os.path.join(objs[0], "x"))


def test_a_symlinked_branch_ref_cannot_make_the_import_read_or_write_outside(env):
    w, acc = env.wt()
    secret = env.tmp_ / "secret-ref"
    secret.write_text("0123456789012345678901234567890123456789\n")
    gd = env.AGD_.gitdir_path(w["path"])
    ref = os.path.join(gd, "refs", "heads", "agent", acc["assignment_id"])
    os.remove(ref)
    os.symlink(str(secret), ref)                       # det en agent ville goere via sin skrivbare refs/
    summary = env.settle(acc)
    assert summary["errors"] != [] and "commits" not in summary
    assert env.W_.get(worktree_id=w["worktree_id"])["status"] == "retained"
    assert secret.read_text() == "0123456789012345678901234567890123456789\n"
    assert not any("agent-work" in r and w["base_commit"] not in r for r in env.main_refs())


def test_a_deleted_branch_ref_means_no_commits_not_a_stuck_worktree(env):
    w, acc = env.wt()
    env.run(w, "git update-ref -d refs/heads/agent/%s" % acc["assignment_id"])
    summary = env.settle(acc)
    assert summary["errors"] == [] and summary["commits"] == 0
    assert env.W_.get(worktree_id=w["worktree_id"])["status"] == "retained"


def test_without_a_private_gitdir_an_older_worktree_still_runs_shell_but_has_no_git(env):
    import shutil
    w, _ = env.wt()
    shutil.rmtree(env.AGD_.gitdir_path(w["path"]))
    out = env.run(w, "echo ok > f.txt; git status 2>&1 | head -1; cat f.txt")
    assert out["exit_code"] == 0 and "ok" in out["stdout"] and "not a git repository" in out["stdout"]


def test_the_archive_bundle_contains_the_agents_commits_and_removal_cleans_everything(env):
    w, acc = env.wt()
    env.run(w, LEGIT)
    env.settle(acc)
    t0 = datetime.now(UTC)
    out = env.W_.sweep(now=t0 + timedelta(days=31))
    assert out["archived"] == [w["worktree_id"]] and out["blocked"] == []
    from core.runtime import db_agent_artifacts as art
    run_id = env.c_._conn().execute("SELECT run_id FROM agent_runs").fetchone()["run_id"]
    bundle = art.read_artifact(owner_user_id="bjorn", ref=f"{run_id}/worktree.bundle")
    assert bundle["status"] == "ok"
    assert not os.path.exists(w["path"]) and not os.path.exists(env.AGD_.gitdir_path(w["path"]))
    assert not any("agent-work" in r for r in env.main_refs())


def test_a_tampered_dot_git_file_does_not_stop_removal(env):
    w, acc = env.wt()
    env.run(w, "echo 'gitdir: /nowhere' > .git; echo x > f")
    env.settle(acc)
    d = env.W_.decide(owner_user_id="bjorn", worktree_id=w["worktree_id"], decision="discarded")
    t0 = datetime.fromisoformat(d["decided_at"].replace("Z", "+00:00"))
    out = env.W_.sweep(now=t0 + timedelta(days=8))
    assert out["removed"] == [w["worktree_id"]] and not os.path.exists(w["path"])


def test_pack_refs_cannot_prune_the_agents_branch_out_of_the_persistent_refs(env):
    w, acc = env.wt()
    out = env.run(w, "echo n > n.txt && git add -A && git commit -q -m c && git pack-refs --all --prune; "
                     "echo rc=$?; git rev-parse HEAD")
    assert "rc=0" not in out["stdout"]                              # packed-refs er skrivebeskyttet
    summary = env.settle(acc)
    assert summary["errors"] == [] and summary["commits"] == 1
