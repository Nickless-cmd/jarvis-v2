"""Rolle-aware git-eksekvering for code mode.

container/'repo'  → server-side subprocess (KUN owner; gate i route-laget).
workstation       → git via operator_bash på brugerens egen bro.

PR-oprettelse: GitHub-OAuth-connector (API) primært, gh CLI som fallback.
"""
from __future__ import annotations

import re
import subprocess


# ── Container (server-repo) ────────────────────────────────────────────────

def _git_container(repo: str, *a: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, timeout=timeout)


def commit_all_container(repo: str, message: str) -> dict:
    msg = (message or "").strip() or "WIP: ændringer fra code mode"
    add = _git_container(repo, "add", "-A")
    if add.returncode != 0:
        return {"status": "error", "detail": f"git add: {add.stderr[:200]}"}
    cm = _git_container(repo, "commit", "-m", msg)
    if cm.returncode != 0:
        out = (cm.stdout or "") + (cm.stderr or "")
        if "nothing to commit" in out or "working tree clean" in out:
            return {"status": "nochange", "message": msg}
        return {"status": "error", "detail": out[:200]}
    sha = _git_container(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    branch = _git_container(repo, "branch", "--show-current").stdout.strip()
    return {"status": "ok", "sha": sha, "branch": branch, "message": msg}


# ── Workstation (brugerens egen bro) ───────────────────────────────────────

def _operator_exec(name: str, args: dict) -> dict:
    from core.tools.simple_tools import execute_tool
    return execute_tool(name, args) or {}


def _ws_git(root: str, uid: str, gitargs: str, timeout: int = 60) -> tuple[int, str, str]:
    """Kør `git -C <root> <gitargs>` på brugerens bro. Returnér (rc, stdout, stderr)."""
    cmd = f"git -C {root!r} {gitargs}"
    res = _operator_exec("operator_bash", {"command": cmd, "_user_id": uid, "timeout_s": timeout})
    if res.get("status") != "ok":
        return (1, "", res.get("error") or "bridge_not_connected")
    r = res.get("result") or {}
    return (int(r.get("exit_code") or 0), str(r.get("stdout") or ""), str(r.get("stderr") or ""))


def commit_all_workstation(root: str, uid: str, message: str) -> dict:
    msg = (message or "").strip() or "WIP: ændringer fra code mode"
    rc, _, err = _ws_git(root, uid, "add -A")
    if rc != 0:
        return {"status": "error", "detail": f"git add: {err[:200]}"}
    rc, out, err = _ws_git(root, uid, f"commit -m {msg!r}")
    if rc != 0:
        blob = out + err
        if "nothing to commit" in blob or "working tree clean" in blob:
            return {"status": "nochange", "message": msg}
        return {"status": "error", "detail": blob[:200]}
    sha = _ws_git(root, uid, "rev-parse --short HEAD")[1].strip()
    branch = _ws_git(root, uid, "branch --show-current")[1].strip()
    return {"status": "ok", "sha": sha, "branch": branch, "message": msg}
