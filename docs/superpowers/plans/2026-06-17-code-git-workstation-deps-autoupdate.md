---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Code-mode Git + Workstation + Dependency-Doctor + Auto-Update — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rolle-aware git-actions (server + workstation) med PR via GitHub-API/gh, en cross-OS dependency-doctor, og in-app auto-update i jarvis-desk.

**Architecture:** Backend git-action-service (`core/services/git_actions.py`) ruter mellem server-subprocess og `operator_bash` på brugerens bro; PR via `github_connector.create_pr` (OAuth-API) med gh-fallback. Desk-siden: Electron-main `depDoctor`/`depInstall` + `autoUpdate` med IPC til renderer-kort.

**Tech Stack:** Python 3.11 (FastAPI, httpx, subprocess), conda-env `ai`; jarvis-desk (Electron 33, React, TypeScript, vitest, electron-updater, electron-builder).

**Test-kommandoer:** backend `/opt/conda/envs/ai/bin/python -m pytest tests/<fil> -v`; desk (i `apps/jarvis-desk/`) `npx vitest run <fil>` + `npx tsc -b`.

**Deploy efter hver fase:** backend → `git push origin main && git push target main && ssh bs@10.0.0.39 "sudo systemctl restart jarvis-api"`; desk → bump `apps/jarvis-desk/package.json`-version → `npm run package:linux` → `sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb`.

---

## File Structure

**Backend (ny/ændret):**
- Create: `core/services/git_actions.py` — rolle-aware git-eksekvering (container-subprocess + workstation via operator_bash) + remote/branch-parsing.
- Modify: `core/services/github_connector.py` — `_post` + `create_pr`.
- Modify: `apps/api/jarvis_api/routes/chat.py` — route `/chat/git/commit-all` + `/chat/git/create-pr` gennem `git_actions`; behold owner-gate for container.
- Test: `tests/test_git_actions.py`, `tests/test_github_connector_pr.py`.

**Desk (ny/ændret):**
- Modify: `apps/jarvis-desk/src/lib/api.ts` — `commitAllChanges`/`createPullRequest` tager nu `target`.
- Modify: `apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx` — send `target` + vis workstation-knapper.
- Create: `apps/jarvis-desk/electron/depDoctor.ts` + `depInstall.ts` (+ tests).
- Modify: `apps/jarvis-desk/electron/main.ts` + `preload.ts` — IPC for dep + update.
- Modify: `apps/jarvis-desk/electron/autoUpdate.ts` — eksplicitte events.
- Create: `apps/jarvis-desk/src/components/shell/DependencyCard.tsx`, `UpdateCard.tsx` (+ tests).

---

## Fase 1 — Git-eksekverings-lag (rolle-aware)

### Task 1.1: git_actions — container commit_all (flyt fra chat.py)

**Files:**
- Create: `core/services/git_actions.py`
- Test: `tests/test_git_actions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_git_actions.py
from unittest.mock import patch, MagicMock
from core.services import git_actions


def _cp(rc=0, out="", err=""):
    m = MagicMock(); m.returncode = rc; m.stdout = out; m.stderr = err; return m


def test_commit_all_container_ok():
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        if args[2:4] == ["commit", "-m"]:
            return _cp(0, "")
        if args[2] == "rev-parse":
            return _cp(0, "abc1234\n")
        if args[2] == "branch":
            return _cp(0, "main\n")
        return _cp(0, "")
    with patch("subprocess.run", side_effect=fake_run):
        res = git_actions.commit_all_container("/repo", "min besked")
    assert res["status"] == "ok"
    assert res["sha"] == "abc1234"
    assert res["branch"] == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_commit_all_container_ok -v`
Expected: FAIL (module/function findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/git_actions.py
"""Rolle-aware git-eksekvering for code mode.

container/'repo'  → server-side subprocess (KUN owner; gate i route-laget).
workstation       → git via operator_bash på brugerens egen bro.
"""
from __future__ import annotations
import subprocess


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_commit_all_container_ok -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/git_actions.py tests/test_git_actions.py
git commit -m "feat(git_actions): container commit_all"
```

### Task 1.2: git_actions — workstation commit_all via operator_bash

**Files:**
- Modify: `core/services/git_actions.py`
- Test: `tests/test_git_actions.py`

- [ ] **Step 1: Write the failing test**

```python
def test_commit_all_workstation_routes_uid():
    seen = {}
    def fake_exec(name, args):
        seen["name"] = name; seen["args"] = args
        # operator_bash-svarform: {status, result:{stdout,stderr,exit_code}}
        if "commit" in args["command"]:
            return {"status": "ok", "result": {"stdout": "", "stderr": "", "exit_code": 0}}
        if "rev-parse" in args["command"]:
            return {"status": "ok", "result": {"stdout": "def5678\n", "exit_code": 0}}
        if "branch --show-current" in args["command"]:
            return {"status": "ok", "result": {"stdout": "feat/x\n", "exit_code": 0}}
        return {"status": "ok", "result": {"stdout": "", "exit_code": 0}}
    with patch.object(git_actions, "_operator_exec", side_effect=fake_exec):
        res = git_actions.commit_all_workstation("/home/u/proj", "u123", "msg")
    assert res["status"] == "ok"
    assert res["sha"] == "def5678"
    assert seen["args"]["_user_id"] == "u123"   # rolle-routing til egen bro
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_commit_all_workstation_routes_uid -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/git_actions.py — tilføj:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py -v`
Expected: PASS (begge tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/git_actions.py tests/test_git_actions.py
git commit -m "feat(git_actions): workstation commit_all via operator_bash"
```

### Task 1.3: Route /chat/git/commit-all gennem git_actions (rolle-gate)

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py` (erstat `_commit_all_sync`-kald)
- Test: `tests/test_git_actions.py` (route-gate-test via TestClient er valgfri; gate-logik unit-testes her)

- [ ] **Step 1: Write the failing test**

```python
def test_route_target_dispatch():
    from core.services import git_actions
    with patch.object(git_actions, "commit_all_container", return_value={"status": "ok"}) as c, \
         patch.object(git_actions, "commit_all_workstation", return_value={"status": "ok"}) as w:
        git_actions.commit_all({"kind": "container", "root": "repo"}, "/repo", "u", "m")
        git_actions.commit_all({"kind": "workstation", "root": "/p"}, "/repo", "u", "m")
    c.assert_called_once(); w.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_route_target_dispatch -v`
Expected: FAIL (`commit_all` findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/git_actions.py — tilføj dispatcher:
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
```

```python
# apps/api/jarvis_api/routes/chat.py — erstat _CommitAllBody + endpoint:
class _CommitAllBody(BaseModel):
    target: dict = {"kind": "container", "root": "repo"}
    message: str = ""


@router.post("/git/commit-all")
async def chat_commit_all(body: _CommitAllBody) -> dict:
    import asyncio
    from core.identity.workspace_context import current_user_id
    from core.services import git_actions
    uid = current_user_id() or ""
    kind = (body.target or {}).get("kind")
    if kind == "container":
        base = _owner_repo_base("repo")  # owner-gate + repo-sti
        return await asyncio.to_thread(git_actions.commit_all, body.target, str(base), uid, body.message)
    # workstation: ejeren af broen (uid'en) — ingen owner-gate, men egen bro
    return await asyncio.to_thread(git_actions.commit_all, body.target, "", uid, body.message)
```

Bevar `_owner_repo_base` (findes). Fjern `_commit_all_sync` (flyttet til git_actions).

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py -v && /opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/routes/chat.py`
Expected: PASS + compile OK.

- [ ] **Step 5: Commit**

```bash
git add core/services/git_actions.py apps/api/jarvis_api/routes/chat.py tests/test_git_actions.py
git commit -m "feat(git_actions): rolle-aware commit-all route dispatch"
```

---

## Fase 2 — PR (OAuth-API + gh-fallback)

### Task 2.1: github_connector.create_pr (API)

**Files:**
- Modify: `core/services/github_connector.py`
- Test: `tests/test_github_connector_pr.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_github_connector_pr.py
from unittest.mock import patch, MagicMock
from core.services import github_connector as gc


def test_create_pr_posts_and_returns_url():
    token = {"access_token": "t"}
    resp = MagicMock(); resp.status_code = 201
    resp.json = lambda: {"html_url": "https://github.com/o/r/pull/5", "number": 5}
    with patch.object(gc, "get_fresh_token", return_value=token), \
         patch("httpx.post", return_value=resp) as post:
        res = gc.create_pr("u", "o/r", head="feat/x", base="main", title="T", body="B")
    assert res["status"] == "ok"
    assert res["url"] == "https://github.com/o/r/pull/5"
    assert post.call_args.kwargs["json"]["head"] == "feat/x"


def test_create_pr_no_token():
    with patch.object(gc, "get_fresh_token", return_value=None):
        res = gc.create_pr("u", "o/r", head="h", base="main", title="T", body="")
    assert res["status"] == "error" and res["error"] == "github_not_connected"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_github_connector_pr.py -v`
Expected: FAIL (`create_pr` findes ikke).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/github_connector.py — tilføj:
def _post(user_id: str, path: str, payload: dict) -> dict:
    token = get_fresh_token(user_id, "github")
    if not token or not token.get("access_token"):
        return {"status": "error", "error": "github_not_connected"}
    try:
        import httpx
        r = httpx.post(_API + path, headers=_headers(token), json=payload, timeout=30)
        if r.status_code in (401, 403):
            return {"status": "error", "error": "github_not_connected"}
        if r.status_code not in (200, 201):
            return {"status": "error", "error": f"github_http_{r.status_code}", "detail": r.text[:200]}
        return {"status": "ok", "data": r.json()}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"github_request_failed: {e}"}


def create_pr(user_id: str, repo: str, *, head: str, base: str, title: str, body: str = "") -> dict:
    """Opret PR i `repo` (owner/name). head/base = branch-navne."""
    if not (repo or "").strip():
        return {"status": "error", "error": "repo_required"}
    res = _post(user_id, f"/repos/{repo}/pulls",
                {"title": title or head, "head": head, "base": base, "body": body or title})
    if res["status"] != "ok":
        return res
    return {"status": "ok", "url": res["data"].get("html_url"), "number": res["data"].get("number")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_github_connector_pr.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/github_connector.py tests/test_github_connector_pr.py
git commit -m "feat(github_connector): create_pr via GitHub API"
```

### Task 2.2: git_actions remote-parse + create_pr-orkestrering (API → gh-fallback)

**Files:**
- Modify: `core/services/git_actions.py`
- Test: `tests/test_git_actions.py`

- [ ] **Step 1: Write the failing test**

```python
def test_parse_remote_owner_repo():
    from core.services.git_actions import parse_owner_repo
    assert parse_owner_repo("git@github.com:Nickless-cmd/jarvis-v2.git") == "Nickless-cmd/jarvis-v2"
    assert parse_owner_repo("https://github.com/o/r.git") == "o/r"
    assert parse_owner_repo("https://github.com/o/r") == "o/r"
    assert parse_owner_repo("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_parse_remote_owner_repo -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/git_actions.py — tilføj:
import re


def parse_owner_repo(remote_url: str) -> str:
    u = (remote_url or "").strip()
    if not u:
        return ""
    u = re.sub(r"\.git$", "", u)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+)$", u)
    return m.group(1) if m else ""


def create_pr(target: dict, container_repo: str, uid: str, title: str, body: str) -> dict:
    """Commit → branch hvis på default → push → PR (API, ellers gh-fallback)."""
    kind = (target or {}).get("kind")
    ws = kind == "workstation"
    root = str((target or {}).get("root") or "") if ws else container_repo

    def g(args: str):
        if ws:
            return _ws_git(root, uid, args)
        cp = _git_container(root, *args.split())
        return (cp.returncode, cp.stdout, cp.stderr)

    # default-branch
    rc, out, _ = g("symbolic-ref --quiet refs/remotes/origin/HEAD")
    base = out.strip().rsplit("/", 1)[-1] if rc == 0 and out.strip() else "main"
    branch = g("branch --show-current")[1].strip()
    if not branch or branch == base:
        short = g("rev-parse --short HEAD")[1].strip() or "work"
        branch = f"jarvis/work-{short}"
        if g(f"switch -c {branch}")[0] != 0:
            return {"status": "error", "detail": "kunne ikke oprette branch"}
    g("add -A"); g(f"commit -m {(title or 'Ændringer fra code mode')!r}")
    if g(f"push -u origin {branch}")[0] != 0:
        return {"status": "error", "detail": "git push fejlede (creds?)"}

    # PR via API (foretrukket)
    from core.services import github_connector
    repo = parse_owner_repo(g("remote get-url origin")[1].strip())
    if repo:
        api = github_connector.create_pr(uid, repo, head=branch, base=base, title=title, body=body)
        if api["status"] == "ok":
            return {"status": "ok", "url": api.get("url"), "branch": branch, "via": "api"}
    # gh-fallback
    return _create_pr_gh(ws, root, uid, base, branch, title, body)


def _create_pr_gh(ws: bool, root: str, uid: str, base: str, branch: str, title: str, body: str) -> dict:
    args = f"pr create --base {base} --head {branch}"
    args += f" --title {title!r} --body {(body or title)!r}" if title.strip() else " --fill"
    if ws:
        rc, out, err = _ws_git_raw(root, uid, f"gh {args}")
    else:
        import subprocess
        cp = subprocess.run(["gh", *args.split()], cwd=root, capture_output=True, text=True, timeout=120)
        rc, out, err = cp.returncode, cp.stdout, cp.stderr
    if rc != 0:
        return {"status": "error", "detail": (err or out)[:250] or "gh utilgængelig"}
    url = next((w for w in (out or "").split() if w.startswith("http")), "")
    return {"status": "ok", "url": url, "branch": branch, "via": "gh"}


def _ws_git_raw(root: str, uid: str, cmd: str) -> tuple[int, str, str]:
    """Kør vilkårlig kommando i `root` på brugerens bro (til gh)."""
    full = f"cd {root!r} && {cmd}"
    res = _operator_exec("operator_bash", {"command": full, "_user_id": uid, "timeout_s": 120})
    if res.get("status") != "ok":
        return (1, "", res.get("error") or "bridge_not_connected")
    r = res.get("result") or {}
    return (int(r.get("exit_code") or 0), str(r.get("stdout") or ""), str(r.get("stderr") or ""))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_parse_remote_owner_repo -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/git_actions.py tests/test_git_actions.py
git commit -m "feat(git_actions): create_pr orkestrering (API + gh-fallback)"
```

### Task 2.3: Route /chat/git/create-pr gennem git_actions

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`

- [ ] **Step 1: Write the failing test**

```python
def test_create_pr_dispatch_calls_git_actions():
    from core.services import git_actions
    with patch.object(git_actions, "create_pr", return_value={"status": "ok", "url": "u"}) as p:
        git_actions.create_pr({"kind": "container", "root": "repo"}, "/repo", "u", "T", "B")
    p.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py::test_create_pr_dispatch_calls_git_actions -v`
Expected: PASS allerede (create_pr findes fra 2.2) — denne task er ren route-wiring; test verificerer signaturen.

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/jarvis_api/routes/chat.py — erstat create-pr endpoint:
class _CreatePrBody(BaseModel):
    target: dict = {"kind": "container", "root": "repo"}
    title: str = ""
    body: str = ""


@router.post("/git/create-pr")
async def chat_create_pr(body: _CreatePrBody) -> dict:
    import asyncio
    from core.identity.workspace_context import current_user_id
    from core.services import git_actions
    uid = current_user_id() or ""
    kind = (body.target or {}).get("kind")
    if kind == "container":
        base = _owner_repo_base("repo")
        return await asyncio.to_thread(git_actions.create_pr, body.target, str(base), uid, body.title, body.body)
    return await asyncio.to_thread(git_actions.create_pr, body.target, "", uid, body.title, body.body)
```

Fjern `_create_pr_sync` (erstattet).

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_git_actions.py -v && /opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/routes/chat.py`
Expected: PASS + compile OK.

- [ ] **Step 5: Commit + deploy backend**

```bash
git add apps/api/jarvis_api/routes/chat.py tests/test_git_actions.py
git commit -m "feat(git_actions): rolle-aware create-pr route dispatch"
git push origin main && git push target main && ssh bs@10.0.0.39 "sudo systemctl restart jarvis-api"
```

### Task 2.4: Desk — send target + workstation-knapper i EnvironmentPanel

**Files:**
- Modify: `apps/jarvis-desk/src/lib/api.ts`
- Modify: `apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx`
- Modify: `apps/jarvis-desk/src/views/CodeView.tsx` (send `kind`+`root` så panelet kan bygge `target`)

- [ ] **Step 1: Opdater api.ts-signaturer**

```typescript
// apps/jarvis-desk/src/lib/api.ts
export async function commitAllChanges(
  config: ApiConfig, target: { kind: string; root: string }, message = '',
): Promise<{ status: string; sha?: string; branch?: string }> {
  return apiFetch(config, '/chat/git/commit-all', { method: 'POST', body: { target, message } })
}
export async function createPullRequest(
  config: ApiConfig, target: { kind: string; root: string }, title = '', body = '',
): Promise<{ status: string; url?: string; branch?: string }> {
  return apiFetch(config, '/chat/git/create-pr', { method: 'POST', body: { target, title, body } })
}
```

- [ ] **Step 2: Opdater EnvironmentPanel — canGit + target**

```tsx
// EnvironmentPanel.tsx — props: tilføj `kind` bruges allerede; canGit ny:
// owner+container+repo  ELLER  workstation med git-repo (alle roller, egen bro).
const canGit = git?.is_git && (
  (isOwner && kind === 'container' && root === 'repo') || kind === 'workstation'
)
const target = { kind, root }
// doCommit/doPr kalder commitAllChanges(config, target) / createPullRequest(config, target)
```

- [ ] **Step 3: tsc + vitest**

Run (i `apps/jarvis-desk/`): `npx tsc -b && npx vitest run src/components/code src/views`
Expected: PASS.

- [ ] **Step 4: Commit + deploy desk**

```bash
# bump apps/jarvis-desk/package.json version
git add apps/jarvis-desk/src apps/jarvis-desk/package.json
git commit -m "feat(desk): rolle-aware git-knapper (server + workstation) i miljø-felt"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb
```

**CHECK-IN med Bjørn efter Fase 2** (git-actions end-to-end på server + workstation).

---

## Fase 3 — Auto-update (in-app prompt → opdatér + genstart)

### Task 3.1: electron-updater dep + publish-config

**Files:**
- Modify: `apps/jarvis-desk/package.json`

- [ ] **Step 1:** `cd apps/jarvis-desk && npm i electron-updater`
- [ ] **Step 2:** Tilføj i `package.json` `build`-blokken:

```json
"publish": [{ "provider": "github", "owner": "Nickless-cmd", "repo": "jarvis-v2" }]
```

- [ ] **Step 3:** `npx tsc -b` (ingen kode-ændring endnu — verificér dep installeret).
- [ ] **Step 4: Commit**

```bash
git add apps/jarvis-desk/package.json apps/jarvis-desk/package-lock.json
git commit -m "build(desk): electron-updater + github publish-config"
```

### Task 3.2: autoUpdate.ts — eksplicitte events + IPC

**Files:**
- Modify: `apps/jarvis-desk/electron/autoUpdate.ts`
- Modify: `apps/jarvis-desk/electron/main.ts` (send IPC til renderer), `preload.ts` (expose lyttere)
- Test: `apps/jarvis-desk/electron/autoUpdate.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/jarvis-desk/electron/autoUpdate.test.ts
import { describe, it, expect, vi } from 'vitest'
import { wireUpdater } from './autoUpdate'

function fakeUpdater() {
  const handlers: Record<string, (x: unknown) => void> = {}
  return {
    autoDownload: true,
    on: (ev: string, cb: (x: unknown) => void) => { handlers[ev] = cb },
    checkForUpdates: vi.fn(), downloadUpdate: vi.fn(), quitAndInstall: vi.fn(),
    _emit: (ev: string, x?: unknown) => handlers[ev]?.(x),
  }
}

it('update-available → send til renderer; download kun ved kald', () => {
  const up = fakeUpdater(); const sent: unknown[] = []
  const api = wireUpdater(up as never, (ch, p) => sent.push([ch, p]))
  expect(up.autoDownload).toBe(false)
  up._emit('update-available', { version: '0.3.0' })
  expect(sent).toContainEqual(['update:available', { version: '0.3.0' }])
  expect(up.downloadUpdate).not.toHaveBeenCalled()
  api.download()
  expect(up.downloadUpdate).toHaveBeenCalled()
})

it('update-downloaded → ready; installNow kalder quitAndInstall', () => {
  const up = fakeUpdater(); const sent: unknown[] = []
  const api = wireUpdater(up as never, (ch, p) => sent.push([ch, p]))
  up._emit('update-downloaded', { version: '0.3.0' })
  expect(sent).toContainEqual(['update:ready', { version: '0.3.0' }])
  api.installNow()
  expect(up.quitAndInstall).toHaveBeenCalled()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/autoUpdate.test.ts`
Expected: FAIL (`wireUpdater` findes ikke).

- [ ] **Step 3: Write minimal implementation**

```typescript
// apps/jarvis-desk/electron/autoUpdate.ts — tilføj (behold initAutoUpdate):
interface FullUpdater {
  autoDownload: boolean
  on: (ev: string, cb: (info: unknown) => void) => void
  checkForUpdates: () => unknown
  downloadUpdate: () => unknown
  quitAndInstall: () => unknown
}
type Send = (channel: string, payload: unknown) => void

export function wireUpdater(up: FullUpdater, send: Send) {
  up.autoDownload = false
  up.on('update-available', (info) => send('update:available', info))
  up.on('download-progress', (p) => send('update:progress', p))
  up.on('update-downloaded', (info) => send('update:ready', info))
  up.on('error', (e) => send('update:error', String(e)))
  return {
    check: () => { try { up.checkForUpdates() } catch { /* noop */ } },
    download: () => { try { up.downloadUpdate() } catch { /* noop */ } },
    installNow: () => { try { up.quitAndInstall() } catch { /* noop */ } },
  }
}
```

```typescript
// main.ts — i initAutoUpdate's succes-gren: erstat checkForUpdatesAndNotify-stien med:
//   const api = wireUpdater(up as never, (ch, p) => mainWindow?.webContents.send(ch, p))
//   ipcMain.handle('update:download', () => api.download())
//   ipcMain.handle('update:install', () => api.installNow())
//   api.check(); setInterval(api.check, hours*3_600_000)
// preload.ts — expose:
//   onUpdateAvailable: (cb) => ipcRenderer.on('update:available', (_e, i) => cb(i)),
//   onUpdateReady: (cb) => ipcRenderer.on('update:ready', (_e, i) => cb(i)),
//   updateDownload: () => ipcRenderer.invoke('update:download'),
//   updateInstall: () => ipcRenderer.invoke('update:install'),
```

- [ ] **Step 4: Run test to verify it passes**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/autoUpdate.test.ts && npx tsc -b`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/electron/autoUpdate.ts apps/jarvis-desk/electron/main.ts apps/jarvis-desk/electron/preload.ts apps/jarvis-desk/electron/autoUpdate.test.ts
git commit -m "feat(desk): auto-update event→IPC wiring (wireUpdater)"
```

### Task 3.3: UpdateCard — in-app prompt

**Files:**
- Create: `apps/jarvis-desk/src/components/shell/UpdateCard.tsx`
- Test: `apps/jarvis-desk/src/components/shell/UpdateCard.test.tsx`
- Modify: `apps/jarvis-desk/src/App.tsx` (mount kortet)

- [ ] **Step 1: Write the failing test**

```tsx
// UpdateCard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { UpdateCard } from './UpdateCard'

it('viser version + kalder onUpdate ved klik', () => {
  const onUpdate = vi.fn()
  render(<UpdateCard version="0.3.0" phase="available" onUpdate={onUpdate} onInstall={vi.fn()} onDismiss={vi.fn()} />)
  expect(screen.getByText(/0\.3\.0/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /opdat/i }))
  expect(onUpdate).toHaveBeenCalled()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (i `apps/jarvis-desk/`): `npx vitest run src/components/shell/UpdateCard.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```tsx
// UpdateCard.tsx
export function UpdateCard({ version, phase, onUpdate, onInstall, onDismiss }: {
  version: string
  phase: 'available' | 'ready'
  onUpdate: () => void
  onInstall: () => void
  onDismiss: () => void
}) {
  return (
    <div className="update-card" role="dialog" aria-label="App-opdatering">
      <span className="update-text">
        {phase === 'ready' ? `Version ${version} klar` : `Ny version ${version} tilgængelig`}
      </span>
      {phase === 'ready'
        ? <button type="button" onClick={onInstall}>Genstart &amp; opdatér</button>
        : <button type="button" onClick={onUpdate}>Opdatér</button>}
      <button type="button" className="update-dismiss" aria-label="Luk" onClick={onDismiss}>×</button>
    </div>
  )
}
```

I `App.tsx`: state `update: {version, phase} | null`; `useEffect` → `window.jarvis?.onUpdateAvailable(i => setUpdate({version:i.version, phase:'available'}))` + `onUpdateReady(...'ready')`; render `<UpdateCard ... onUpdate={() => window.jarvis.updateDownload()} onInstall={() => window.jarvis.updateInstall()} />`. (Guard `window.jarvis` for web-build.)

- [ ] **Step 4: Run test to verify it passes**

Run (i `apps/jarvis-desk/`): `npx vitest run src/components/shell/UpdateCard.test.tsx && npx tsc -b`
Expected: PASS.

- [ ] **Step 5: Commit + deploy desk**

```bash
# bump version
git add apps/jarvis-desk/src apps/jarvis-desk/package.json
git commit -m "feat(desk): in-app UpdateCard (prompt → opdatér/genstart)"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb
```

---

## Fase 4 — Dependency-doctor (git, gh, node, ripgrep · Linux/Mac/Windows)

### Task 4.1: depDoctor.detect

**Files:**
- Create: `apps/jarvis-desk/electron/depDoctor.ts`
- Test: `apps/jarvis-desk/electron/depDoctor.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// depDoctor.test.ts
import { describe, it, expect, vi } from 'vitest'
import { detectTools, REQUIRED_TOOLS } from './depDoctor'

it('markerer present=false når which fejler', async () => {
  const which = vi.fn(async (t: string) => t === 'git')  // kun git findes
  const res = await detectTools(which)
  const git = res.find(r => r.tool === 'git')!
  const node = res.find(r => r.tool === 'node')!
  expect(git.present).toBe(true)
  expect(node.present).toBe(false)
  expect(res.map(r => r.tool).sort()).toEqual([...REQUIRED_TOOLS].sort())
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/depDoctor.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// depDoctor.ts
import { execFile } from 'node:child_process'

export const REQUIRED_TOOLS = ['git', 'gh', 'node', 'rg'] as const
export type Tool = typeof REQUIRED_TOOLS[number]
export interface ToolStatus { tool: Tool; present: boolean }

/** which(tool) → findes værktøjet i PATH? Injicérbar for test. */
export async function defaultWhich(tool: string): Promise<boolean> {
  const probe = process.platform === 'win32' ? 'where' : 'command'
  const args = process.platform === 'win32' ? [tool] : ['-v', tool]
  return new Promise((resolve) => {
    execFile(probe === 'command' ? '/bin/sh' : 'where',
      probe === 'command' ? ['-c', `command -v ${tool}`] : args,
      (err) => resolve(!err))
  })
}

export async function detectTools(which: (t: string) => Promise<boolean> = defaultWhich): Promise<ToolStatus[]> {
  return Promise.all(REQUIRED_TOOLS.map(async (tool) => ({ tool, present: await which(tool) })))
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/depDoctor.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/electron/depDoctor.ts apps/jarvis-desk/electron/depDoctor.test.ts
git commit -m "feat(desk): depDoctor.detectTools"
```

### Task 4.2: depInstall — per-OS install-kommando

**Files:**
- Create: `apps/jarvis-desk/electron/depInstall.ts`
- Test: `apps/jarvis-desk/electron/depInstall.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// depInstall.test.ts
import { describe, it, expect } from 'vitest'
import { installCommand } from './depInstall'

it('linux apt → pkexec apt install', () => {
  const c = installCommand('git', { platform: 'linux', pkgManager: 'apt' })
  expect(c).toEqual({ cmd: 'pkexec', args: ['apt-get', 'install', '-y', 'git'] })
})
it('mac → brew install', () => {
  const c = installCommand('ripgrep', { platform: 'darwin' })
  expect(c).toEqual({ cmd: 'brew', args: ['install', 'ripgrep'] })
})
it('windows → winget install', () => {
  const c = installCommand('gh', { platform: 'win32' })
  expect(c!.cmd).toBe('winget')
  expect(c!.args).toContain('--accept-source-agreements')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/depInstall.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// depInstall.ts
export type PkgManager = 'apt' | 'dnf' | 'pacman'
export interface OsCtx { platform: NodeJS.Platform; pkgManager?: PkgManager }
export interface InstallCmd { cmd: string; args: string[] }

// Værktøj → pakkenavn pr. økosystem (rg-pakken hedder ripgrep; node ofltest nodejs).
const PKG: Record<string, { apt: string; dnf: string; pacman: string; brew: string; winget: string }> = {
  git: { apt: 'git', dnf: 'git', pacman: 'git', brew: 'git', winget: 'Git.Git' },
  gh: { apt: 'gh', dnf: 'gh', pacman: 'github-cli', brew: 'gh', winget: 'GitHub.cli' },
  node: { apt: 'nodejs', dnf: 'nodejs', pacman: 'nodejs', brew: 'node', winget: 'OpenJS.NodeJS' },
  ripgrep: { apt: 'ripgrep', dnf: 'ripgrep', pacman: 'ripgrep', brew: 'ripgrep', winget: 'BurntSushi.ripgrep.MSVC' },
}

export function installCommand(tool: string, ctx: OsCtx): InstallCmd | null {
  const p = PKG[tool === 'rg' ? 'ripgrep' : tool]
  if (!p) return null
  if (ctx.platform === 'darwin') return { cmd: 'brew', args: ['install', p.brew] }
  if (ctx.platform === 'win32') return { cmd: 'winget', args: ['install', '-e', '--id', p.winget, '--accept-source-agreements', '--accept-package-agreements'] }
  const pm = ctx.pkgManager ?? 'apt'
  if (pm === 'apt') return { cmd: 'pkexec', args: ['apt-get', 'install', '-y', p.apt] }
  if (pm === 'dnf') return { cmd: 'pkexec', args: ['dnf', 'install', '-y', p.dnf] }
  return { cmd: 'pkexec', args: ['pacman', '-S', '--noconfirm', p.pacman] }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (i `apps/jarvis-desk/`): `npx vitest run electron/depInstall.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/electron/depInstall.ts apps/jarvis-desk/electron/depInstall.test.ts
git commit -m "feat(desk): depInstall per-OS install-kommando"
```

### Task 4.3: IPC + DependencyCard

**Files:**
- Modify: `apps/jarvis-desk/electron/main.ts` (ipc `dep:detect`, `dep:install`) + `preload.ts`
- Create: `apps/jarvis-desk/src/components/shell/DependencyCard.tsx` + test
- Modify: `apps/jarvis-desk/src/App.tsx` (vis kort hvis manglende værktøjer)

- [ ] **Step 1: Write the failing test**

```tsx
// DependencyCard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DependencyCard } from './DependencyCard'

it('viser manglende værktøjer + installér kalder onInstall(tool)', () => {
  const onInstall = vi.fn()
  render(<DependencyCard missing={['git', 'gh']} onInstall={onInstall} onDismiss={vi.fn()} busy="" />)
  expect(screen.getByText(/git/)).toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button', { name: /installér/i })[0]!)
  expect(onInstall).toHaveBeenCalledWith('git')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (i `apps/jarvis-desk/`): `npx vitest run src/components/shell/DependencyCard.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```tsx
// DependencyCard.tsx
export function DependencyCard({ missing, onInstall, onDismiss, busy }: {
  missing: string[]; onInstall: (tool: string) => void; onDismiss: () => void; busy: string
}) {
  if (!missing.length) return null
  return (
    <div className="dep-card" role="dialog" aria-label="Manglende værktøjer">
      <div className="dep-head">Jarvis mangler nogle værktøjer</div>
      <ul className="dep-list">
        {missing.map((t) => (
          <li key={t} className="dep-row">
            <span>{t}</span>
            <button type="button" disabled={busy === t} onClick={() => onInstall(t)}>
              {busy === t ? 'Installerer…' : 'Installér'}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="dep-dismiss" aria-label="Luk" onClick={onDismiss}>×</button>
    </div>
  )
}
```

`main.ts`: `ipcMain.handle('dep:detect', () => detectTools())`; `ipcMain.handle('dep:install', async (_e, tool) => { const ctx = { platform: process.platform, pkgManager: await detectPkgManager() }; const c = installCommand(tool, ctx); if (!c) return { ok: false }; return runInstall(c) })` (runInstall = execFile-wrapper der returnerer {ok, log}). `preload.ts`: expose `depDetect`/`depInstall`. `App.tsx`: ved mount → `depDetect()` → sæt `missing` → render `<DependencyCard>`.

- [ ] **Step 4: Run test to verify it passes**

Run (i `apps/jarvis-desk/`): `npx vitest run src/components/shell/DependencyCard.test.tsx && npx tsc -b`
Expected: PASS.

- [ ] **Step 5: Commit + deploy desk**

```bash
# bump version
git add apps/jarvis-desk/src apps/jarvis-desk/electron apps/jarvis-desk/package.json
git commit -m "feat(desk): dependency-doctor IPC + DependencyCard"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb
```

**CHECK-IN med Bjørn efter Fase 4** (hele spec'en landet) → tilbage til hovedspec.

---

## Self-Review

- **Spec-dækning:** Modul 1 → Fase 1 (Task 1.1-1.3). Modul 2 → Fase 2 (2.1-2.4). Modul 4 → Fase 3 (3.1-3.3). Modul 3 → Fase 4 (4.1-4.3). Rolle-gate i 1.3/2.3 (container=owner, workstation=egen bro). Graceful "virker før git" via DependencyCard (4.3) + `no_repo`-status (1.3). ✓
- **Type-konsistens:** `target={kind,root}` ens i api.ts (2.4), routes (1.3/2.3), git_actions (1.3/2.2). `create_pr`-signatur ens i github_connector (2.1) og git_actions-kald (2.2). `wireUpdater(up, send)` ens i test+impl (3.2). `installCommand(tool, ctx)` ens (4.2). ✓
- **Bemærk:** `gh`-fallback + git-push på server kan fejle (gh ikke på target, push-creds) — derfor er API-stien primær og fejl er ærlige. Workstation-PR kræver brugerens egne git-creds + forbundet GitHub (token).
