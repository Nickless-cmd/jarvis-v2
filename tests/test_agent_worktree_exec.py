"""C5b: skrivning i et worktree KUN gennem sandboxen - og hvad der sker naar agenten proever at slippe ud."""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
pytestmark = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def ex(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_contract as c
    import core.services.agent_worktree_exec as E
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
        c_, E_, W_ = c, E, W
        repo_, tmp_ = str(repo), tmp_path

        def wt(self, name="a1"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id="bjorn", owner_session_id="s1")
            acc = c.accept_assignment(agent_id=name, owner_user_id="bjorn", origin_session_id="s1",
                                      goal="skriv kode", parent_agent_id="jarvis", parent_run_id="pr")
            return W.provision(owner_user_id="bjorn", assignment_id=acc["assignment_id"], repo_path=str(repo))

        def run(self, w, cmd, **kw):
            return E.run_in_worktree(worktree_id=w["worktree_id"], command=cmd, **kw)

        def host_snapshot(self):
            """Alt paa vaerten der IKKE maa aendre sig: hovedrepoets filer og HEAD."""
            return (sh("git", "rev-parse", "HEAD", cwd=repo).strip(), sh("git", "status", "--porcelain", cwd=repo),
                    (repo / "a.txt").read_text())

    return H()


def test_a_command_runs_in_the_worktree_and_its_files_appear_there(ex):
    w = ex.wt()
    out = ex.run(w, "echo hej > fil.txt && cat fil.txt && pwd && ls")
    assert out["exit_code"] == 0 and out["stdout"].split() == ["hej", "/work", "a.txt", "fil.txt"]
    assert open(os.path.join(w["path"], "fil.txt")).read() == "hej\n"
    assert out["timed_out"] is False and out["truncated"] is False


def test_write_file_writes_unicode_and_creates_directories(ex):
    w = ex.wt()
    res = ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="src/pkg/ny.py", content="print('æøå')\n")
    assert res["bytes"] == len("print('æøå')\n".encode())
    assert open(os.path.join(w["path"], "src", "pkg", "ny.py"), encoding="utf-8").read() == "print('æøå')\n"


def test_the_agent_can_run_python_tests_inside(ex):
    w = ex.wt()
    ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="t.py", content="assert 1 + 1 == 2\nprint('GROEN')\n")
    out = ex.run(w, f"{__import__('sys').executable} t.py")
    assert out["exit_code"] == 0 and "GROEN" in out["stdout"]


# --- forsoeg paa at slippe ud: vaerten maa aldrig aendre sig ------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "echo PWN > /etc/pwn-test",
    "echo PWN > ../escape.txt",
    "echo PWN > ../../escape2.txt",
    "echo PWN > /escape3.txt",
    "mkdir -p /media/projects/x && echo PWN > /media/projects/x/y",
    "echo PWN >> /work/../../../escape4.txt",
])
def test_writes_outside_the_worktree_never_reach_the_host(ex, cmd, tmp_path):
    w = ex.wt()
    before = ex.host_snapshot()
    ex.run(w, cmd)
    root = ex.W_.worktree_root()
    assert not os.path.exists("/etc/pwn-test") and not os.path.exists("/escape3.txt")
    assert not os.path.exists(os.path.join(os.path.dirname(w["path"]), "escape.txt"))     # worktree'ets foraeldre
    assert not os.path.exists(str(root / "escape.txt")) and not os.path.exists(str(root / "escape2.txt"))
    assert not os.path.exists("/media/projects/x")
    assert ex.host_snapshot() == before


def test_an_absolute_host_path_does_not_exist_inside_the_sandbox(ex, tmp_path):
    w = ex.wt()
    target = tmp_path / "bjorns" / "vigtig.txt"
    target.parent.mkdir()
    target.write_text("ORIGINAL")
    out = ex.run(w, f"echo PWN > {target}; cat {target}")
    assert out["exit_code"] != 0 and target.read_text() == "ORIGINAL"


def test_a_symlink_to_a_host_file_cannot_be_written_through(ex, tmp_path):
    w = ex.wt()
    target = tmp_path / "bjorns-fil.txt"
    target.write_text("ORIGINAL")
    os.symlink(target, os.path.join(w["path"], "link"))            # lagt dér udefra, som om agenten gjorde det
    ex.run(w, "echo PWN > link")
    ex.run(w, f"ln -sf {target} link2; echo PWN > link2")          # og oprettet af agenten selv
    assert target.read_text() == "ORIGINAL"


def test_a_symlink_to_the_hosts_etc_is_dangling_inside(ex):
    w = ex.wt()
    out = ex.run(w, "ln -s /etc/shadow s; cat s; ls /etc /home /media 2>&1 | head -20")
    assert "root:" not in out["stdout"]


@pytest.mark.parametrize("path", ["../x.txt", "/abs/x.txt", "a/../../x.txt", "/etc/pwn-test", "..", "."])
def test_write_file_refuses_paths_that_leave_the_worktree(ex, path):
    w = ex.wt()
    before = ex.host_snapshot()
    with pytest.raises(ex.E_.ExecError) as e:
        ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path=path, content="PWN")
    assert e.value.code in ("INVALID_SCOPE", "WRITE_FAILED")
    assert not os.path.exists("/abs/x.txt") and not os.path.exists("/etc/pwn-test")
    assert ex.host_snapshot() == before


def test_write_file_follows_a_symlink_only_when_it_stays_inside(ex, tmp_path):
    w = ex.wt()
    outside = tmp_path / "udenfor.txt"
    outside.write_text("ORIGINAL")
    os.symlink(outside, os.path.join(w["path"], "ud"))
    os.symlink("a.txt", os.path.join(w["path"], "ind"))
    with pytest.raises(ex.E_.ExecError):
        ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="ud", content="PWN")
    ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="ind", content="NY-A\n")
    assert outside.read_text() == "ORIGINAL" and open(os.path.join(w["path"], "a.txt")).read() == "NY-A\n"


def test_the_main_repository_is_unreachable_from_inside(ex):
    w = ex.wt()
    before = ex.host_snapshot()
    out = ex.run(w, f"git -C /work status; ls {ex.repo_} 2>&1; cat {ex.repo_}/a.txt 2>&1")
    assert "proj" not in out["stdout"].replace("/work", "") or "No such file" in out["stdout"] + out["stderr"]
    assert ex.host_snapshot() == before


def test_there_is_no_network_and_no_host_environment_inside(ex, monkeypatch):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    monkeypatch.setenv("JARVIS_TEST_SECRET", "laekket")
    w = ex.wt()
    port = srv.getsockname()[1]
    try:
        out = ex.run(w, f"{__import__('sys').executable} -c \"import socket; s=socket.socket(); s.settimeout(2); "
                        f"exec('try:\\n s.connect((chr(49)+chr(50)+chr(55)+\\'.0.0.1\\', {port})); print(1)\\nexcept OSError: print(0)')\"; "
                        "env | grep -c JARVIS_TEST_SECRET")
        assert out["stdout"].split() == ["0", "0"]
    finally:
        srv.close()


def test_the_other_agents_worktree_is_invisible(ex):
    w1, w2 = ex.wt("a1"), ex.wt("a2")
    ex.run(w1, "echo hemmelig > kun-a1.txt")
    out = ex.run(w2, f"ls /work; ls {ex.W_.worktree_root()} 2>&1; cat {w1['path']}/kun-a1.txt 2>&1")
    lines = out["stdout"].splitlines()
    assert lines[0] == "a.txt" and "kun-a1.txt" not in lines          # kun egen /work (fejlbeskeden naevner filnavnet)
    assert "hemmelig" not in out["stdout"] and "No such file" in out["stdout"]


# --- graenser ------------------------------------------------------------------------------------------------------

def test_a_command_is_killed_at_the_timeout_with_its_children(ex):
    w = ex.wt()
    t0 = time.monotonic()
    out = ex.run(w, "sleep 100 & sleep 100 & wait", timeout_s=2)
    assert out["timed_out"] is True and time.monotonic() - t0 < 20
    time.sleep(0.5)
    left = subprocess.run(["pgrep", "-f", "sleep 100"], capture_output=True, text=True).stdout.split()
    assert left == []


def test_output_is_truncated_and_flagged(ex):
    w = ex.wt()
    out = ex.run(w, "yes x | head -c 100000")
    assert len(out["stdout"]) == ex.E_.MAX_OUTPUT and out["truncated"] is True


def test_the_timeout_is_clamped_to_the_maximum(ex, monkeypatch):
    w = ex.wt()
    seen = {}
    real = ex.E_._run

    def spy(wt, command, *, timeout_s, stdin_bytes=None):
        seen["t"] = timeout_s
        return real(wt, ["/usr/bin/true"], timeout_s=1)

    monkeypatch.setattr(ex.E_, "_run", spy)
    ex.run(w, "true", timeout_s=99999)
    assert seen["t"] == 99999                                           # _run klemmer selv; se naeste test


def test__run_clamps_timeout_and_never_below_one_second(ex):
    w = ex.wt()
    t0 = time.monotonic()
    ex.E_._run(w, ["/usr/bin/true"], timeout_s=0)
    assert time.monotonic() - t0 < 15


def test_growth_over_the_quota_is_reported_and_blocks_the_next_command(ex, monkeypatch):
    w = ex.wt()
    monkeypatch.setattr(ex.W_, "PER_ASSIGNMENT_BYTES", 1000)
    out = ex.run(w, "head -c 5000 /dev/zero > stor.bin")
    assert out["over_quota"] is True and os.path.exists(os.path.join(w["path"], "stor.bin"))
    with pytest.raises(ex.E_.ExecError) as e:
        ex.run(w, "echo mere")
    assert e.value.code == "CAPACITY" and os.path.exists(os.path.join(w["path"], "stor.bin"))   # intet slettet


def test_oversized_writes_and_empty_input_are_refused(ex):
    w = ex.wt()
    with pytest.raises(ex.E_.ExecError) as e:
        ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="x", content="y" * (ex.E_.MAX_WRITE_BYTES + 1))
    assert e.value.code == "CAPACITY"
    for bad in ("", "  ", "a\0b"):
        with pytest.raises(ex.E_.ExecError):
            ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path=bad, content="x")
    with pytest.raises(ex.E_.ExecError):
        ex.run(w, "   ")


def test_only_an_active_worktree_with_a_matching_path_can_be_used(ex):
    w = ex.wt()
    ex.W_._set(w["worktree_id"], status="retained")
    with pytest.raises(ex.E_.ExecError) as e:
        ex.run(w, "echo x")
    assert e.value.code == "NO_WORKTREE"
    ex.W_._set(w["worktree_id"], status="active", path=str(ex.tmp_ / "andet"))
    with pytest.raises(ex.E_.ExecError) as e:
        ex.run(w, "echo x")
    assert e.value.code == "INVALID_SCOPE"
    with pytest.raises(ex.E_.ExecError):
        ex.E_.run_in_worktree(worktree_id="wt-findes-ikke", command="echo x")


def test_without_a_sandbox_nothing_is_written_outside_one(ex, monkeypatch):
    w = ex.wt()
    monkeypatch.setattr(sb.shutil, "which", lambda name: None)
    with pytest.raises(sb.SandboxUnavailable):
        ex.run(w, "echo x > ikke-skrevet.txt")
    assert not os.path.exists(os.path.join(w["path"], "ikke-skrevet.txt"))


def test_two_agents_write_concurrently_into_their_own_worktrees_only(ex):
    w1, w2 = ex.wt("a1"), ex.wt("a2")
    res = {}

    def go(name, w):
        res[name] = ex.run(w, f"echo {name} > eget.txt; sleep 0.5; cat eget.txt")

    ts = [threading.Thread(target=go, args=(n, w)) for n, w in (("a1", w1), ("a2", w2))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert res["a1"]["stdout"].strip() == "a1" and res["a2"]["stdout"].strip() == "a2"
    assert open(os.path.join(w1["path"], "eget.txt")).read() == "a1\n"
    assert open(os.path.join(w2["path"], "eget.txt")).read() == "a2\n"


def test_changes_made_in_the_sandbox_are_what_the_server_reads_as_the_diff(ex):
    from core.services import agent_worktree_git as g

    w = ex.wt()
    ex.E_.write_file_in_worktree(worktree_id=w["worktree_id"], path="ny.py", content="print(1)\n")
    ex.run(w, "echo ekstra >> a.txt; rm -f nothing")
    files = {f["path"]: f["status"] for f in g.changed_files(w["gitdir"], w["path"], w["base_commit"])}
    assert files == {"ny.py": "A", "a.txt": "M"}
