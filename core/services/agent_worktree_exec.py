"""Skrivning i et agent-worktree - KUN gennem en sandbox (agent-contract-v1 C5b, spec 8.1 og 12.1).

Kommandoer og filskrivninger koeres i en bwrap-sandbox hvor ``/work`` er agentens worktree og det
ENESTE skrivbare mount. Alt andet er skrivebeskyttet eller en privat tmpfs; intet netvaerk, ingen
credentials, ingen andre ejeres filer. Git virker, men mod agentens EGEN private gitdir
(``agent_worktree_gitdir``): hovedrepoets refs, hooks, config og andre worktrees er ikke monteret, og
serveren importerer agentens commits bagefter med fsck (serveren laeser selv aendringerne med sit gemte
GIT_DIR). Et forsoeg paa at skrive via absolut sti, ``..``, symlink eller shell lander
i sandboxens tmpfs eller afvises - vaerten roeres ikke. Soeger ikke at haandhaeve noget i prompten:
graensen er mount-namespacet.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any

from core.services import agent_sandbox as sb
from core.services import agent_worktree_git as g
from core.services import agent_worktree_gitdir as agd
from core.services import agent_worktrees as wtm

logger = logging.getLogger(__name__)

MAX_TIMEOUT_S = 600
DEFAULT_TIMEOUT_S = 120
MAX_OUTPUT = 20_000
MAX_WRITE_BYTES = 1024 * 1024
_FILE_SIZE_LIMIT = 256 * 1024 * 1024
_ADDRESS_SPACE = 4 * 1024 ** 3

_WRITE_SCRIPT = (
    "import os, sys\n"
    "rel = sys.argv[1]\n"
    "root = os.path.realpath('/work')\n"
    "real = os.path.realpath(os.path.join('/work', rel))\n"
    "if real == root or not real.startswith(root + os.sep):\n"
    "    sys.stderr.write('STI-UDEN-FOR-WORKTREE'); sys.exit(3)\n"
    "os.makedirs(os.path.dirname(real), exist_ok=True)\n"
    "data = sys.stdin.buffer.read()\n"
    "with open(real, 'wb') as fh:\n"
    "    fh.write(data)\n"
    "print(len(data))\n"
)


class ExecError(RuntimeError):
    """Kommandoen blev afvist foer den koerte (stabil ``code``)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


def _active_worktree(worktree_id: str) -> dict[str, Any]:
    wt = wtm.get(worktree_id=worktree_id)
    if wt is None or wt["status"] != "active":
        raise ExecError("NO_WORKTREE", "worktree'et er ikke aktivt")
    if wt["over_quota"]:
        raise ExecError("CAPACITY", "worktree'et er over kvoten - nye skrivninger er stoppet")
    root = str(wtm.worktree_root())
    if not g.path_is_inside(wt["path"], root) or os.path.realpath(wt["path"]) != os.path.realpath(
            os.path.join(root, wt["agent_id"], wt["assignment_id"])):
        raise ExecError("INVALID_SCOPE", "worktree-stien passer ikke til posten")
    return wt


def _clip(data: bytes) -> tuple[str, bool]:
    text = data.decode("utf-8", "replace")
    return (text[:MAX_OUTPUT], len(text) > MAX_OUTPUT)


def _run(wt: dict[str, Any], command: list[str], *, timeout_s: float, stdin_bytes: bytes | None = None,
         with_git: bool = False) -> dict[str, Any]:
    timeout_s = max(1.0, min(float(timeout_s or DEFAULT_TIMEOUT_S), MAX_TIMEOUT_S))
    t0 = time.monotonic()
    mounts = agd.sandbox_mounts(wt["repo_path"], wt["path"]) if with_git else None
    proc = sb.spawn_in_sandbox(
        command, stdin=subprocess.PIPE if stdin_bytes is not None else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, worker_files={}, rw_binds={wt["path"]: "/work"},
        chdir="/work", address_space=_ADDRESS_SPACE, cpu_seconds=int(timeout_s) + 5,
        file_size=_FILE_SIZE_LIMIT, mounts=mounts, extra_env=agd.sandbox_env() if mounts else None)
    timed_out = False
    try:
        out, err = proc.communicate(input=stdin_bytes, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            logger.debug("sandbox-gruppen %s var allerede vaek", proc.pid)
        out, err = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                logger.debug("sandbox-gruppen %s var allerede vaek", proc.pid)
            proc.wait(timeout=10)
    so, sc = _clip(out)
    se, ec = _clip(err)
    growth = wtm.check_growth(worktree_id=wt["worktree_id"])
    return {"exit_code": proc.returncode, "stdout": so, "stderr": se, "truncated": sc or ec,
            "timed_out": timed_out, "duration_ms": int((time.monotonic() - t0) * 1000),
            "over_quota": growth["over_quota"]}


def run_in_worktree(*, worktree_id: str, command: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Koer en shell-kommando med worktree'et som /work. Kaster ``ExecError`` hvis den afvises."""
    if not str(command or "").strip():
        raise ExecError("INVALID_SCOPE", "kommandoen er tom")
    wt = _active_worktree(worktree_id)
    return _run(wt, ["/usr/bin/bash", "-c", command], timeout_s=timeout_s, with_git=True)


def write_file_in_worktree(*, worktree_id: str, path: str, content: str) -> dict[str, Any]:
    """Skriv en fil (relativ sti) i worktree'et. Stien loeses INDE i sandboxen og afvises hvis den
    forlader /work; selv uden det tjek kan sandboxen ikke skrive andre steder end /work."""
    data = str(content or "").encode("utf-8")
    if len(data) > MAX_WRITE_BYTES:
        raise ExecError("CAPACITY", f"filen er over {MAX_WRITE_BYTES} bytes")
    if not str(path or "").strip() or "\0" in str(path):
        raise ExecError("INVALID_SCOPE", "ugyldig sti")
    wt = _active_worktree(worktree_id)
    res = _run(wt, [sys.executable, "-c", _WRITE_SCRIPT, str(path)], timeout_s=30, stdin_bytes=data)
    if res["exit_code"] == 3:
        raise ExecError("INVALID_SCOPE", "stien forlader worktree'et")
    if res["exit_code"] != 0:
        raise ExecError("WRITE_FAILED", (res["stderr"] or res["stdout"])[:200])
    return {"path": path, "bytes": len(data), "over_quota": res["over_quota"]}
