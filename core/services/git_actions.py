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
