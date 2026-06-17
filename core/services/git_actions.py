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


# ── Dispatch + remote-parsing ──────────────────────────────────────────────

def commit_all(target: dict, container_repo: str, uid: str, message: str) -> dict:
    kind = (target or {}).get("kind")
    if kind == "container":
        return commit_all_container(container_repo, message)
    if kind == "workstation":
        root = str((target or {}).get("root") or "")
        if not root:
            return {"status": "no_repo"}
        return commit_all_workstation(root, uid, message)
    return {"status": "error", "detail": "ukendt target"}


def parse_owner_repo(remote_url: str) -> str:
    u = (remote_url or "").strip()
    if not u:
        return ""
    u = re.sub(r"\.git$", "", u)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+)$", u)
    return m.group(1) if m else ""


# ── PR-orkestrering (commit → branch → push → PR: API primær, gh fallback) ──

def _ws_git_raw(root: str, uid: str, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Kør vilkårlig kommando i `root` på brugerens bro (til gh)."""
    full = f"cd {root!r} && {cmd}"
    res = _operator_exec("operator_bash", {"command": full, "_user_id": uid, "timeout_s": timeout})
    if res.get("status") != "ok":
        return (1, "", res.get("error") or "bridge_not_connected")
    r = res.get("result") or {}
    return (int(r.get("exit_code") or 0), str(r.get("stdout") or ""), str(r.get("stderr") or ""))


def create_pr(target: dict, container_repo: str, uid: str, title: str, body: str) -> dict:
    """Commit → branch hvis på default → push → PR (API, ellers gh-fallback)."""
    kind = (target or {}).get("kind")
    ws = kind == "workstation"
    root = str((target or {}).get("root") or "") if ws else container_repo
    if not root:
        return {"status": "no_repo"}

    def g(args: str):
        if ws:
            return _ws_git(root, uid, args)
        cp = _git_container(root, *_split_gh(args))
        return (cp.returncode, cp.stdout, cp.stderr)

    rc, out, _ = g("symbolic-ref --quiet refs/remotes/origin/HEAD")
    base = out.strip().rsplit("/", 1)[-1] if rc == 0 and out.strip() else "main"
    branch = g("branch --show-current")[1].strip()
    if not branch or branch == base:
        short = g("rev-parse --short HEAD")[1].strip() or "work"
        branch = f"jarvis/work-{short}"
        if g(f"switch -c {branch}")[0] != 0:
            return {"status": "error", "detail": "kunne ikke oprette branch"}
    g("add -A")
    g(f"commit -m {(title or 'Ændringer fra code mode')!r}")
    if g(f"push -u origin {branch}")[0] != 0:
        return {"status": "error", "detail": "git push fejlede (creds?)"}

    from core.services import github_connector
    repo = parse_owner_repo(g("remote get-url origin")[1].strip())
    if repo:
        api = github_connector.create_pr(uid, repo, head=branch, base=base, title=title, body=body)
        if api.get("status") == "ok":
            return {"status": "ok", "url": api.get("url"), "branch": branch, "via": "api"}
    return _create_pr_gh(ws, root, uid, base, branch, title, body)


def _create_pr_gh(ws: bool, root: str, uid: str, base: str, branch: str, title: str, body: str) -> dict:
    args = f"pr create --base {base} --head {branch}"
    args += f" --title {title!r} --body {(body or title)!r}" if (title or "").strip() else " --fill"
    if ws:
        rc, out, err = _ws_git_raw(root, uid, f"gh {args}")
    else:
        cp = subprocess.run(["gh", *_split_gh(args)], cwd=root, capture_output=True, text=True, timeout=120)
        rc, out, err = cp.returncode, cp.stdout, cp.stderr
    if rc != 0:
        return {"status": "error", "detail": (err or out)[:250] or "gh utilgængelig"}
    url = next((w for w in (out or "").split() if w.startswith("http")), "")
    return {"status": "ok", "url": url, "branch": branch, "via": "gh"}


def _split_gh(args: str) -> list[str]:
    import shlex
    return shlex.split(args)
