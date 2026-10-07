"""Leverance C, hul 2: en REEL pids-graense pr. sandbox (cgroup TasksMax) - argv, fail-closed og en rigtig, bounded fork-bombe."""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
needs_sandbox = pytest.mark.skipif(not USABLE, reason=f"sandbox (bwrap + cgroup-scope) kan ikke bruges her: {WHY}")


@pytest.fixture(autouse=True)
def fresh_probe(monkeypatch):
    monkeypatch.setattr(sb, "_probe_cache", None)
    monkeypatch.delenv(sb.PIDS_OFF_ENV, raising=False)


def test_the_scope_prefix_sets_tasksmax_and_comes_between_prlimit_and_bwrap(monkeypatch):
    monkeypatch.setattr(sb, "cgroup_pids_available", lambda **_: (True, ""))
    seen = {}

    def fake_popen(argv, **kw):
        seen["argv"], seen["env"] = argv, kw.get("env")
        raise RuntimeError("stop")

    monkeypatch.setattr(sb.subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError):
        sb.spawn_in_sandbox([sys.executable, "-c", "pass"], worker_files={}, pids_limit=77)
    argv = seen["argv"]
    i_pr, i_sd, i_bw = (next(i for i, a in enumerate(argv) if a.endswith(n)) for n in ("prlimit", "systemd-run", "bwrap"))
    assert i_pr < i_sd < i_bw
    assert argv[i_sd + 1:i_sd + 7] == ["--user", "--scope", "--quiet", "--collect", "-p", "TasksMax=77"]
    assert seen["env"]["XDG_RUNTIME_DIR"]                    # en systemd-service har den ofte ikke selv


def test_without_an_enforceable_cgroup_limit_the_agent_does_not_run(monkeypatch):
    monkeypatch.setattr(sb, "cgroup_pids_available", lambda **_: (False, "ingen brugermanager"))
    with pytest.raises(sb.SandboxUnavailable) as e:
        sb.spawn_in_sandbox([sys.executable, "-c", "pass"], worker_files={})
    assert "pids-graense" in str(e.value) and "ingen brugermanager" in str(e.value)
    assert sb.sandbox_usable() == (False, "pids-graense kan ikke haandhaeves (cgroup): ingen brugermanager")


def test_only_an_explicit_opt_out_runs_without_the_scope(monkeypatch):
    monkeypatch.setattr(sb, "cgroup_pids_available", lambda **_: (False, "x"))
    monkeypatch.setenv(sb.PIDS_OFF_ENV, "off")
    assert sb.pids_prefix(512) == []
    monkeypatch.setenv(sb.PIDS_OFF_ENV, "0")                       # alt andet end "off" er IKKE et fravalg
    with pytest.raises(sb.SandboxUnavailable):
        sb.pids_prefix(512)
    monkeypatch.delenv(sb.PIDS_OFF_ENV)
    assert sb.pids_prefix(None) == []                              # kaldet bad eksplicit om ingen graense


def test_a_missing_systemd_run_is_unavailable_not_skipped(monkeypatch):
    real = sb.shutil.which
    monkeypatch.setattr(sb.shutil, "which", lambda n: None if n == "systemd-run" else real(n))
    ok, why = sb.cgroup_pids_available(force=True)
    assert ok is False and "systemd-run" in why


def test_the_probe_result_is_cached_for_a_short_while(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(sb.subprocess, "run", fake_run)
    assert sb.cgroup_pids_available(force=True) == (True, "")
    assert sb.cgroup_pids_available() == (True, "") and len(calls) == 1
    assert sb.cgroup_pids_available(force=True) == (True, "") and len(calls) == 2


# --- rigtig fork-bombe ------------------------------------------------------------------------------------------

#: Et FINITET fork-trae (2**10 blade, hver sover 6 s): en rigtig bombe i form, men afgraenset - uden en
#: graense ville ~1000 processer leve; med TasksMax=N kan der hoejst vaere N. Taelling med bash-builtins
#: (ingen fork) saa den ogsaa virker naar fork er afvist.
BOMB = (
    "bomb() { local d=$1; if [ $d -le 0 ]; then sleep 6; return; fi; bomb $((d-1)) & bomb $((d-1)) & wait; }\n"
    "bomb 10 &\n"
    "sleep 2\n"
    "n=0; for d in /proc/[0-9]*; do n=$((n+1)); done\n"
    "echo PROCS=$n\n"
)


@needs_sandbox
def test_a_fork_bomb_is_held_at_the_limit_and_the_host_stays_responsive(monkeypatch):
    t0 = time.monotonic()
    proc = sb.spawn_in_sandbox(["/usr/bin/bash", "-c", BOMB], worker_files={}, pids_limit=48,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    n = int(out.decode().split("PROCS=")[1].split()[0])
    assert proc.returncode == 0
    assert 20 <= n <= 48                                       # bomben naaede graensen, men ikke over
    assert b"retry" in err or b"fork" in err.lower() or b"Resource" in err      # forks blev afvist af kernen
    assert time.monotonic() - t0 < 15
    assert subprocess.run(["true"]).returncode == 0            # vaerten kan stadig forke


@needs_sandbox
def test_the_worktree_command_path_carries_the_pids_limit(monkeypatch, tmp_path):
    seen = {}
    real = sb.spawn_in_sandbox

    def spy(*a, **kw):
        seen.update(kw)
        return real(*a, **kw)

    import core.services.agent_worktree_exec as E
    monkeypatch.setattr(E.sb, "spawn_in_sandbox", spy)
    wt = {"worktree_id": "w", "path": str(tmp_path), "repo_path": str(tmp_path), "agent_id": "a", "assignment_id": "x"}
    monkeypatch.setattr(E.wtm, "check_growth", lambda **_: {"over_quota": False})
    out = E._run(wt, ["/usr/bin/true"], timeout_s=5)
    assert out["exit_code"] == 0 and seen["pids_limit"] == sb.PIDS_COMMAND == 512
