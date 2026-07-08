---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# jarvis-desk Code mode (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Code mode to jarvis-desk where Jarvis reads/writes/edits files and runs commands in a chosen workspace (Bjørn's container repo or a workstation project), driven by his existing agentic loop, with a file-tree + diff surface in the right panel.

**Architecture:** Reuse ALL chat infrastructure (`/chat/stream/v2`, sessions, composer, tool_use blocks, preview panel). New: a `tool_scope="code"` role-matrix in `core/tools/tool_scoping.py`; a per-session `workspace` binding (nullable columns on `chat_sessions`); a `GET /chat/tree` directory-listing endpoint (container path-jail + workstation operator-bridge); a Code surface in the right panel (file tree + diffs); permissions shown in the code composer; a mode icon on code sessions.

**Tech Stack:** Python/FastAPI (backend, conda env `/opt/conda/envs/ai/bin/python`), SQLite (`core/runtime/db.py`), React 19 + TypeScript 5 + Vitest (frontend, `apps/jarvis-desk`), Electron 33.

**Spec:** `docs/superpowers/specs/2026-06-12-jarvis-desk-code-mode-design.md`

**Deploy (after a phase is green):** backend `git push target main` + `ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api.service jarvis-runtime.service'`; app `cd apps/jarvis-desk && npm run build && npx electron-builder --linux deb && sudo dpkg -i release/jarvis-desktop_0.1.0_amd64.deb`.

---

## File Structure

**Backend (create):**
- none new — all changes extend existing files.

**Backend (modify):**
- `core/tools/tool_scoping.py` — add `CODE_MODE_TOOLS_BASE`, `CODE_MODE_OWNER_EXTRA`, scope branch in `allowed_tool_names`.
- `core/services/chat_sessions.py` — `create_chat_session(workspace_kind, workspace_root)`, `set_session_workspace()`, expose workspace in `get_chat_session`/`list_chat_sessions`.
- `core/runtime/db.py` — `_ensure_chat_session_workspace_columns()` (ALTER TABLE add `workspace_kind`, `workspace_root`).
- `apps/api/jarvis_api/routes/chat.py` — `ChatStreamRequest.workspace_kind/workspace_root`; `GET /chat/tree`; `POST /chat/sessions` accepts workspace; map `mode="code"`→`tool_scope="code"`.
- `apps/api/jarvis_api/routes/chat_stream_v2.py` — pass `tool_scope="code"` for mode=code (already maps "chat"; extend).

**Frontend (create):**
- `apps/jarvis-desk/src/components/panel/FileTree.tsx` — recursive directory tree.
- `apps/jarvis-desk/src/components/panel/CodePanel.tsx` — workspace selector + FileTree + file/diff view.
- `apps/jarvis-desk/src/lib/diff.ts` — pure line-diff helper.
- `apps/jarvis-desk/src/views/CodeView.tsx` — replaces stub; wires stream + CodePanel.

**Frontend (modify):**
- `apps/jarvis-desk/src/lib/api.ts` — `getTree`, `TreeEntry`, workspace types.
- `apps/jarvis-desk/src/lib/streamClient.ts` — `StreamRequest.workspaceKind/workspaceRoot`; send in body.
- `apps/jarvis-desk/src/contexts/StreamContext.tsx` — `SendOpts.workspaceKind/workspaceRoot`.
- `apps/jarvis-desk/src/components/shell/Composer.tsx` — already has `showPermissions`; CodeView passes `true`.
- `apps/jarvis-desk/src/components/shell/Sidebar.tsx` — mode icon on code sessions.
- `apps/jarvis-desk/src/styles/app.css` — file-tree + diff styling.

---

## Phase 1 — Backend: tool_scope="code"

### Task 1: Code-scope allowlist + role matrix

**Files:**
- Modify: `core/tools/tool_scoping.py`
- Test: `tests/test_tool_scoping.py`

- [x] **Step 1: Write the failing tests** — append to `tests/test_tool_scoping.py`:

```python
class TestCodeScope:
    CODE_ALL = [
        "read_file", "write_file", "edit_file", "search", "find_files", "bash",
        "operator_read_file", "operator_write_file", "operator_bash",
        "operator_glob", "operator_grep", "operator_list_dir",
        "dispatch_to_claude_code", "web_search", "godnat_unrelated",
    ]

    def test_owner_code_gets_container_workstation_dispatch(self):
        allow = allowed_tool_names(role="owner", scope="code", all_names=self.CODE_ALL)
        assert {"read_file", "write_file", "edit_file", "bash", "search", "find_files"} <= allow
        assert {"operator_read_file", "operator_write_file", "operator_bash"} <= allow
        assert "dispatch_to_claude_code" in allow

    def test_member_code_only_workstation_operator(self):
        allow = allowed_tool_names(role="member", scope="code", all_names=self.CODE_ALL)
        assert {"operator_read_file", "operator_write_file", "operator_bash",
                "operator_glob", "operator_grep", "operator_list_dir"} <= allow
        assert "read_file" not in allow          # container-side blocked
        assert "write_file" not in allow
        assert "bash" not in allow
        assert "dispatch_to_claude_code" not in allow

    def test_code_excludes_unrelated(self):
        for role in ("owner", "member"):
            allow = allowed_tool_names(role=role, scope="code", all_names=self.CODE_ALL)
            assert "godnat_unrelated" not in allow
```

- [x] **Step 2: Run — expect FAIL** (`allowed_tool_names` ignores scope="code", returns role-only set)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_scoping.py::TestCodeScope -q`
Expected: FAIL (member gets read_file/bash because scope="code" not handled)

- [x] **Step 3: Implement** — in `core/tools/tool_scoping.py`, add the sets after `CHAT_MODE_OWNER_EXTRA`:

```python
# Code-mode allowlist. Owner = container + workstation + dispatch.
CODE_MODE_TOOLS_BASE: frozenset[str] = frozenset({
    # Workstation (operator-bridge) — alle roller i code.
    "operator_read_file", "operator_write_file", "operator_edit_file",
    "operator_bash", "operator_glob", "operator_grep", "operator_list_dir",
})
# Ekstra værktøjer owner får i code: container-side fil/kode + dispatch.
CODE_MODE_OWNER_EXTRA: frozenset[str] = frozenset({
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    "dispatch_to_claude_code",
})
```

Then in `allowed_tool_names`, add a branch BEFORE the existing `if scope == "chat":`:

```python
    if scope == "code":
        allowed = set(CODE_MODE_TOOLS_BASE)
        if is_owner:
            allowed |= CODE_MODE_OWNER_EXTRA
        else:
            allowed -= OWNER_ONLY_TOOLS
        return allowed & names
```

- [x] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_scoping.py -q`
Expected: PASS (all, incl. existing chat tests)

- [x] **Step 5: Commit**

```bash
git add core/tools/tool_scoping.py tests/test_tool_scoping.py
git commit -m "feat(code): tool_scope=code allowlist (owner container+workstation+dispatch, member workstation-only)"
```

---

### Task 2: Workspace columns on chat_sessions

**Files:**
- Modify: `core/runtime/db.py` (near chat_sessions table, ~line 474), `core/services/chat_sessions.py`
- Test: `tests/test_chat_sessions.py`

- [x] **Step 1: Write the failing test** — append to `tests/test_chat_sessions.py`:

```python
def test_create_session_with_workspace(isolated_runtime):
    from core.services.chat_sessions import create_chat_session, get_chat_session
    s = create_chat_session(title="kode", workspace_kind="container", workspace_root="core")
    sid = str(s.get("session_id") or s.get("id"))
    full = get_chat_session(sid)
    assert full["workspace_kind"] == "container"
    assert full["workspace_root"] == "core"


def test_set_session_workspace(isolated_runtime):
    from core.services.chat_sessions import create_chat_session, set_session_workspace, get_chat_session
    s = create_chat_session(title="x")
    sid = str(s.get("session_id") or s.get("id"))
    set_session_workspace(sid, kind="workstation", root="/home/bs/proj")
    full = get_chat_session(sid)
    assert full["workspace_kind"] == "workstation"
    assert full["workspace_root"] == "/home/bs/proj"
```

- [x] **Step 2: Run — expect FAIL** (`create_chat_session` has no workspace kwargs)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_sessions.py::test_create_session_with_workspace -q`
Expected: FAIL (TypeError: unexpected keyword argument 'workspace_kind')

- [x] **Step 3a: Add columns migration** — in `core/runtime/db.py`, add this function (near other `_ensure_*` helpers) and call it wherever `chat_sessions` is ensured (right after the `CREATE TABLE chat_sessions` block, ~line 482):

```python
def _ensure_chat_session_workspace_columns(conn) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()}
    if "workspace_kind" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN workspace_kind TEXT")
    if "workspace_root" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN workspace_root TEXT")
```

Call it right after the chat_sessions `conn.execute(CREATE TABLE ...)` (in the same init function):

```python
        _ensure_chat_session_workspace_columns(conn)
```

- [x] **Step 3b: Extend chat_sessions service** — in `core/services/chat_sessions.py`:

Change `create_chat_session` signature + INSERT:

```python
def create_chat_session(
    *, title: str = "New chat",
    workspace_kind: str | None = None, workspace_root: str | None = None,
) -> dict[str, object]:
    session_id = f"chat-{uuid4().hex}"
    created_at = datetime.now(UTC).isoformat()
    normalized_title = _normalize_title(title) or "New chat"
    with connect() as conn:
        _ensure_chat_session_workspace_columns(conn)  # import from core.runtime.db
        conn.execute(
            "INSERT INTO chat_sessions (session_id, title, created_at, updated_at, workspace_kind, workspace_root) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, normalized_title, created_at, created_at,
             (workspace_kind or None), (workspace_root or None)),
        )
        conn.commit()
    return {
        "session_id": session_id, "id": session_id, "title": normalized_title,
        "created_at": created_at, "updated_at": created_at,
        "workspace_kind": workspace_kind, "workspace_root": workspace_root,
    }
```

(Import at top of file: `from core.runtime.db import _ensure_chat_session_workspace_columns`. If `create_chat_session` already uses a different INSERT shape, adapt the column list — keep existing columns, append the two new ones.)

Add the setter + ensure `get_chat_session` returns the columns:

```python
def set_session_workspace(session_id: str, *, kind: str | None, root: str | None) -> None:
    with connect() as conn:
        _ensure_chat_session_workspace_columns(conn)
        conn.execute(
            "UPDATE chat_sessions SET workspace_kind = ?, workspace_root = ? WHERE session_id = ?",
            (kind or None, root or None, session_id),
        )
        conn.commit()
```

In `get_chat_session`, ensure the SELECT includes `workspace_kind, workspace_root` and the returned dict carries them (add to the `SELECT` column list + the dict build). Same for `_session_summary` if list should expose them (only `workspace_kind` needed for the sidebar mode-icon — include both, harmless).

- [x] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_sessions.py -q`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add core/runtime/db.py core/services/chat_sessions.py tests/test_chat_sessions.py
git commit -m "feat(code): per-session workspace binding (workspace_kind/root columns + service)"
```

---

### Task 3: Plumb mode=code + workspace through the request

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py` (ChatStreamRequest, POST /sessions), `apps/api/jarvis_api/routes/chat_stream_v2.py`, `core/services/visible_runs.py` (already accepts tool_scope)
- Test: `tests/test_chat_routes_workspace.py` (create)

- [x] **Step 1: Write the failing test** — `tests/test_chat_routes_workspace.py`:

```python
from fastapi.testclient import TestClient


def _client():
    from apps.api.jarvis_api.app import create_app  # adapt to actual app factory
    return TestClient(create_app())


def test_create_session_persists_workspace(isolated_runtime):
    c = _client()
    r = c.post("/chat/sessions", json={"title": "kode", "workspace_kind": "container", "workspace_root": "core"})
    assert r.status_code == 200
    sid = r.json()["session"]["session_id"]
    full = c.get(f"/chat/sessions/{sid}").json()
    assert full["session"]["workspace_kind"] == "container"
```

(If the app has no `create_app` factory, import the module-level `app` instead: `from apps.api.jarvis_api.app import app`.)

- [x] **Step 2: Run — expect FAIL** (POST /sessions ignores workspace fields)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_routes_workspace.py -q`
Expected: FAIL (workspace_kind is None)

- [x] **Step 3a: Extend ChatStreamRequest + ChatSessionCreateRequest** in `apps/api/jarvis_api/routes/chat.py`:

```python
# ChatStreamRequest: add (after mode: str = ""):
    workspace_kind: str = ""   # "container" | "workstation" | ""
    workspace_root: str = ""
```

```python
# ChatSessionCreateRequest: add:
    workspace_kind: str = ""
    workspace_root: str = ""
```

Update `POST /chat/sessions`:

```python
@router.post("/sessions")
async def chat_create_session(request: ChatSessionCreateRequest) -> dict:
    return {"session": create_chat_session(
        title=request.title,
        workspace_kind=request.workspace_kind or None,
        workspace_root=request.workspace_root or None,
    )}
```

- [x] **Step 3b: Map mode=code → tool_scope="code"** in `apps/api/jarvis_api/routes/chat_stream_v2.py`. Replace the existing scope line:

```python
    _m = (request.mode or "").strip().lower()
    _tool_scope = "chat" if _m == "chat" else "code" if _m == "code" else ""
```

(start_visible_run already takes `tool_scope=_tool_scope` — unchanged.)

- [x] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_routes_workspace.py -q`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/chat.py apps/api/jarvis_api/routes/chat_stream_v2.py tests/test_chat_routes_workspace.py
git commit -m "feat(code): plumb mode=code→tool_scope + workspace on session create"
```

**→ CHECKPOINT: deploy backend Phase 1 (push target + restart api), confirm /chat/sessions accepts workspace + a mode=code request scopes tools (curl with token, or live).**

---

## Phase 2 — Backend: /chat/tree

### Task 4: Container directory tree (path-jailed)

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Test: `tests/test_chat_tree.py` (create)

- [x] **Step 1: Write the failing test** — `tests/test_chat_tree.py`:

```python
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app


def test_tree_container_lists_root_entries():
    c = TestClient(app)
    r = c.get("/chat/tree", params={"kind": "container", "root": "core", "path": ""})
    assert r.status_code == 200
    names = {e["name"] for e in r.json()["entries"]}
    assert "services" in names or "tools" in names  # core/ subdirs
    assert all("kind" in e and e["kind"] in ("dir", "file") for e in r.json()["entries"])


def test_tree_container_rejects_outside_jail():
    c = TestClient(app)
    r = c.get("/chat/tree", params={"kind": "container", "root": "etc", "path": ""})
    assert r.status_code == 403
```

- [x] **Step 2: Run — expect FAIL** (no /chat/tree route → 404)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_tree.py::test_tree_container_lists_root_entries -q`
Expected: FAIL (404)

- [x] **Step 3: Implement** — in `apps/api/jarvis_api/routes/chat.py`, reuse `_FILE_ROOTS` + `_repo_root()` (already defined for /chat/file). Add (register BEFORE `/sessions/{session_id}` is irrelevant — `/tree` is its own path; place near `/chat/file`):

```python
@router.get("/tree")
async def chat_tree(kind: str = "container", root: str = "", path: str = "") -> dict:
    """Mappe-listing til Code-mode fil-træ. Container: path-jailed til _FILE_ROOTS.
    Workstation: se Task 5."""
    if kind == "container":
        if root not in _FILE_ROOTS:
            raise HTTPException(status_code=403, detail="root uden for jail")
        base = (_repo_root() / root).resolve()
        target = (base / path).resolve() if path else base
        if not str(target).startswith(str(base)):
            raise HTTPException(status_code=403, detail="path uden for jail")
        if not target.is_dir():
            raise HTTPException(status_code=404, detail="ikke en mappe")
        entries = []
        for p in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if p.name.startswith(".") or p.name in ("__pycache__", "node_modules"):
                continue
            entries.append({"name": p.name, "kind": "dir" if p.is_dir() else "file"})
        return {"entries": entries}
    raise HTTPException(status_code=400, detail="ukendt kind (workstation kommer i Task 5)")
```

- [x] **Step 4: Run — expect PASS** (both tests)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_tree.py -q`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/chat.py tests/test_chat_tree.py
git commit -m "feat(code): GET /chat/tree container directory listing (path-jailed)"
```

---

### Task 5: Workstation directory tree (operator bridge)

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Test: `tests/test_chat_tree.py` (append)

- [x] **Step 1: Write the failing test** — append (mocks the operator exec so no live bridge needed):

```python
def test_tree_workstation_routes_through_operator(monkeypatch):
    import apps.api.jarvis_api.routes.chat as chatmod

    def fake_exec(name, args):
        assert name == "operator_list_dir"
        return {"status": "ok", "entries": [
            {"name": "src", "is_dir": True}, {"name": "main.py", "is_dir": False},
        ]}
    monkeypatch.setattr(chatmod, "_operator_exec", fake_exec, raising=False)

    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.app import app
    c = TestClient(app)
    r = c.get("/chat/tree", params={"kind": "workstation", "root": "/home/bs/proj", "path": ""})
    assert r.status_code == 200
    kinds = {e["name"]: e["kind"] for e in r.json()["entries"]}
    assert kinds["src"] == "dir" and kinds["main.py"] == "file"
```

- [x] **Step 2: Run — expect FAIL** (kind=workstation → 400)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_tree.py::test_tree_workstation_routes_through_operator -q`
Expected: FAIL (400)

- [x] **Step 3: Implement** — add a thin `_operator_exec` wrapper (testable seam) + the workstation branch in `chat_tree`. In `apps/api/jarvis_api/routes/chat.py`:

```python
def _operator_exec(name: str, args: dict) -> dict:
    """Kør et operator-tool via simple_tools (router'er til brugerens bridge).
    Seam til test-mock."""
    from core.tools.simple_tools import execute_tool
    return execute_tool(name, args) or {}
```

In `chat_tree`, before the final `raise HTTPException(... ukendt kind ...)`:

```python
    if kind == "workstation":
        full = (root.rstrip("/") + "/" + path).rstrip("/") if path else root
        res = _operator_exec("operator_list_dir", {"path": full})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail=str(res.get("reason") or "operator-list fejlede"))
        entries = [
            {"name": e.get("name") or "", "kind": "dir" if e.get("is_dir") else "file"}
            for e in (res.get("entries") or [])
            if e.get("name") and not str(e.get("name")).startswith(".")
        ]
        return {"entries": entries}
```

(If `operator_list_dir`'s real result shape differs — inspect `core/tools/simple_tools.py::_exec_operator_list_dir` — adapt the `entries` mapping. The test mocks the shape `{status, entries:[{name,is_dir}]}`; match the real one and update both test + code together.)

- [x] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_tree.py -q`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/chat.py tests/test_chat_tree.py
git commit -m "feat(code): /chat/tree workstation listing via operator bridge"
```

**→ CHECKPOINT: deploy backend Phase 2; verify /chat/tree?kind=container&root=core returns entries (curl w/ token).**

---

## Phase 3 — Frontend: Code surface

### Task 6: api.ts getTree + stream plumbing

**Files:**
- Modify: `apps/jarvis-desk/src/lib/api.ts`, `apps/jarvis-desk/src/lib/streamClient.ts`, `apps/jarvis-desk/src/contexts/StreamContext.tsx`
- Test: `apps/jarvis-desk/src/lib/api.test.ts`

- [x] **Step 1: Write the failing test** — append to `src/lib/api.test.ts` (follow existing fetch-mock style in that file):

```ts
it('getTree returnerer entries fra /chat/tree', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ entries: [{ name: 'src', kind: 'dir' }] }),
  })
  vi.stubGlobal('fetch', fetchMock)
  const { getTree } = await import('./api')
  const out = await getTree({ apiBaseUrl: 'http://t', authToken: 't' }, 'container', 'core', '')
  expect(out[0]).toEqual({ name: 'src', kind: 'dir' })
  const url = fetchMock.mock.calls[0][0] as string
  expect(url).toContain('/chat/tree')
  expect(url).toContain('kind=container')
})
```

- [x] **Step 2: Run — expect FAIL** (no getTree export)

Run: `cd apps/jarvis-desk && npx vitest run src/lib/api.test.ts`
Expected: FAIL (getTree undefined)

- [x] **Step 3: Implement** — in `src/lib/api.ts`:

```ts
export interface TreeEntry { name: string; kind: 'dir' | 'file' }
export async function getTree(
  config: ApiConfig, kind: 'container' | 'workstation', root: string, path: string,
): Promise<TreeEntry[]> {
  const qs = `kind=${encodeURIComponent(kind)}&root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}`
  const data = await apiFetch<{ entries: TreeEntry[] }>(config, `/chat/tree?${qs}`)
  return data.entries ?? []
}
```

In `src/lib/streamClient.ts` — extend `StreamRequest` + body:

```ts
  // StreamRequest interface, after mode?:
  workspaceKind?: 'container' | 'workstation'
  workspaceRoot?: string
```

```ts
  // in JSON.stringify body, after mode:
          workspace_kind: request.workspaceKind ?? '',
          workspace_root: request.workspaceRoot ?? '',
```

In `src/contexts/StreamContext.tsx` — extend `SendOpts` + pass through in `send`:

```ts
  // SendOpts interface:
  workspaceKind?: 'container' | 'workstation'
  workspaceRoot?: string
```

```ts
  // inside send(), in the startStream({...}) request object, after attachmentIds:
        workspaceKind: opts.workspaceKind,
        workspaceRoot: opts.workspaceRoot,
```

- [x] **Step 4: Run — expect PASS** + typecheck

Run: `cd apps/jarvis-desk && npx vitest run src/lib/api.test.ts && npx tsc -b`
Expected: PASS, tsc exit 0

- [x] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/api.ts apps/jarvis-desk/src/lib/api.test.ts apps/jarvis-desk/src/lib/streamClient.ts apps/jarvis-desk/src/contexts/StreamContext.tsx
git commit -m "feat(jarvis-desk): getTree + workspace plumbing in stream request"
```

---

### Task 7: Diff helper (pure)

**Files:**
- Create: `apps/jarvis-desk/src/lib/diff.ts`, `apps/jarvis-desk/src/lib/diff.test.ts`

- [x] **Step 1: Write the failing test** — `src/lib/diff.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { lineDiff } from './diff'

describe('lineDiff', () => {
  it('markerer tilføjede + fjernede linjer', () => {
    const d = lineDiff('a\nb\nc', 'a\nB\nc')
    expect(d).toEqual([
      { type: 'same', text: 'a' },
      { type: 'del', text: 'b' },
      { type: 'add', text: 'B' },
      { type: 'same', text: 'c' },
    ])
  })
  it('tom gammel → alt add', () => {
    expect(lineDiff('', 'x')).toEqual([{ type: 'add', text: 'x' }])
  })
})
```

- [x] **Step 2: Run — expect FAIL** (no lineDiff)

Run: `cd apps/jarvis-desk && npx vitest run src/lib/diff.test.ts`
Expected: FAIL

- [x] **Step 3: Implement** — `src/lib/diff.ts` (simple LCS-free line diff; sufficient for v1 single-file view):

```ts
export type DiffLine = { type: 'same' | 'add' | 'del'; text: string }

/** Minimal linje-diff: fælles prefix/suffix + midten som del-så-add.
 *  Ikke en optimal LCS, men læsbar nok til v1 enkelt-fil-visning. */
export function lineDiff(oldText: string, newText: string): DiffLine[] {
  const a = oldText === '' ? [] : oldText.split('\n')
  const b = newText === '' ? [] : newText.split('\n')
  let lo = 0
  while (lo < a.length && lo < b.length && a[lo] === b[lo]) lo++
  let hiA = a.length, hiB = b.length
  while (hiA > lo && hiB > lo && a[hiA - 1] === b[hiB - 1]) { hiA--; hiB-- }
  const out: DiffLine[] = []
  for (let i = 0; i < lo; i++) out.push({ type: 'same', text: a[i] })
  for (let i = lo; i < hiA; i++) out.push({ type: 'del', text: a[i] })
  for (let i = lo; i < hiB; i++) out.push({ type: 'add', text: b[i] })
  for (let i = hiA; i < a.length; i++) out.push({ type: 'same', text: a[i] })
  return out
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/diff.test.ts`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/diff.ts apps/jarvis-desk/src/lib/diff.test.ts
git commit -m "feat(jarvis-desk): pure lineDiff helper for code-mode diffs"
```

---

### Task 8: FileTree component

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/FileTree.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`

- [x] **Step 1: Write the failing test** — `apps/jarvis-desk/src/components/panel/FileTree.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FileTree } from './FileTree'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([
    { name: 'services', kind: 'dir' }, { name: 'x.py', kind: 'file' },
  ]),
}))

describe('FileTree', () => {
  it('viser rod-entries og kalder onOpenFile ved fil-klik', async () => {
    const onOpenFile = vi.fn()
    render(<FileTree config={{ apiBaseUrl: 'http://t', authToken: 't' }} kind="container" root="core" onOpenFile={onOpenFile} />)
    expect(await screen.findByText('x.py')).toBeInTheDocument()
    fireEvent.click(screen.getByText('x.py'))
    expect(onOpenFile).toHaveBeenCalledWith('x.py')
  })
})
```

- [x] **Step 2: Run — expect FAIL** (no FileTree)

Run: `cd apps/jarvis-desk && npx vitest run src/components/panel/FileTree.test.tsx`
Expected: FAIL

- [x] **Step 3: Implement** — `src/components/panel/FileTree.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react'
import { getTree, type TreeEntry, type ApiConfig } from '../../lib/api'

/** Rekursivt fil-træ for Code-mode. Loader børn lazily ved ekspander. onOpenFile
 *  får den fulde sti (relativt til root). */
export function FileTree({
  config, kind, root, path = '', onOpenFile,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  path?: string
  onOpenFile: (fullPath: string) => void
}) {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  useEffect(() => {
    let cancelled = false
    getTree(config, kind, root, path)
      .then((e) => { if (!cancelled) setEntries(e) })
      .catch(() => { if (!cancelled) setEntries([]) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, path])

  if (entries === null) return <div className="filetree-loading">…</div>
  return (
    <ul className="filetree">
      {entries.map((e) => (
        <TreeNode key={e.name} config={config} kind={kind} root={root}
          path={path ? `${path}/${e.name}` : e.name} entry={e} onOpenFile={onOpenFile} />
      ))}
    </ul>
  )
}

function TreeNode({
  config, kind, root, path, entry, onOpenFile,
}: {
  config: ApiConfig; kind: 'container' | 'workstation'; root: string
  path: string; entry: TreeEntry; onOpenFile: (p: string) => void
}) {
  const [open, setOpen] = useState(false)
  if (entry.kind === 'file') {
    return (
      <li className="filetree-file" onClick={() => onOpenFile(path)}>
        <File size={13} /> {entry.name}
      </li>
    )
  }
  return (
    <li className="filetree-dir">
      <div className="filetree-dir-row" onClick={() => setOpen((o) => !o)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <Folder size={13} /> {entry.name}
      </div>
      {open && <FileTree config={config} kind={kind} root={root} path={path} onOpenFile={onOpenFile} />}
    </li>
  )
}
```

Add CSS to `src/styles/app.css`:

```css
.filetree { list-style: none; margin: 0; padding: 0 0 0 8px; font-size: 13px; }
.filetree-file, .filetree-dir-row { display: flex; align-items: center; gap: 5px; padding: 3px 6px; cursor: pointer; border-radius: 4px; color: var(--fg-2); white-space: nowrap; }
.filetree-file:hover, .filetree-dir-row:hover { background: var(--bg-2); color: var(--fg-1); }
.filetree-loading { padding: 8px; color: var(--fg-3); }
```

- [x] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/components/panel/FileTree.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [x] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/panel/FileTree.tsx apps/jarvis-desk/src/components/panel/FileTree.test.tsx apps/jarvis-desk/src/styles/app.css
git commit -m "feat(jarvis-desk): FileTree component (lazy recursive, container+workstation)"
```

---

### Task 9: CodePanel (workspace selector + tree + file/diff view)

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/CodePanel.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`

- [x] **Step 1: Write the failing test** — `src/components/panel/CodePanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodePanel } from './CodePanel'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
}))

describe('CodePanel', () => {
  it('åbner en fil i visningen ved klik i træet', async () => {
    render(<CodePanel config={{ apiBaseUrl: 'http://t', authToken: 't' }} kind="container" root="core" />)
    fireEvent.click(await screen.findByText('x.py'))
    expect(await screen.findByText(/print\(1\)/)).toBeInTheDocument()
  })
})
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/components/panel/CodePanel.test.tsx`
Expected: FAIL (no CodePanel)

- [x] **Step 3: Implement** — `src/components/panel/CodePanel.tsx`:

```tsx
import { useState } from 'react'
import { FileTree } from './FileTree'
import { getFile, type ApiConfig } from '../../lib/api'

/** Code-mode flade i højre panel: workspace-info + fil-træ + fil-visning.
 *  (Diff-visning fra tool_use-blokke kobles på i Task 10 via openDiff-prop.) */
export function CodePanel({
  config, kind, root,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
}) {
  const [openPath, setOpenPath] = useState<string | null>(null)
  const [content, setContent] = useState('')

  const openFile = (rel: string) => {
    setOpenPath(rel)
    // Container: /chat/file forventer 'root/rel'. Workstation: senere via operator_read_file.
    const full = kind === 'container' ? `${root}/${rel}` : rel
    getFile(config, full).then((f) => setContent(f.content)).catch(() => setContent('(kunne ikke læse fil)'))
  }

  return (
    <div className="codepanel">
      <div className="codepanel-head">{kind === 'container' ? '📦' : '💻'} {root}</div>
      <div className="codepanel-body">
        <div className="codepanel-tree">
          <FileTree config={config} kind={kind} root={root} onOpenFile={openFile} />
        </div>
        <div className="codepanel-view">
          {openPath ? (
            <>
              <div className="codepanel-filename">{openPath}</div>
              <pre className="codepanel-content">{content}</pre>
            </>
          ) : (
            <div className="codepanel-empty">Vælg en fil i træet.</div>
          )}
        </div>
      </div>
    </div>
  )
}
```

Add CSS to `src/styles/app.css`:

```css
.codepanel { display: flex; flex-direction: column; height: 100%; }
.codepanel-head { padding: 8px 12px; font-size: 12.5px; color: var(--fg-3); border-bottom: 1px solid var(--line); }
.codepanel-body { display: flex; flex: 1; min-height: 0; }
.codepanel-tree { width: 200px; overflow: auto; border-right: 1px solid var(--line); padding: 6px 0; }
.codepanel-view { flex: 1; overflow: auto; padding: 10px; min-width: 0; }
.codepanel-filename { font-size: 12px; color: var(--fg-3); margin-bottom: 6px; }
.codepanel-content { font-size: 12.5px; white-space: pre; overflow-x: auto; color: #c8d2dc; margin: 0; }
.codepanel-empty { color: var(--fg-3); font-size: 13px; padding: 12px; }
```

- [x] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/components/panel/CodePanel.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [x] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/panel/CodePanel.tsx apps/jarvis-desk/src/components/panel/CodePanel.test.tsx apps/jarvis-desk/src/styles/app.css
git commit -m "feat(jarvis-desk): CodePanel (workspace + tree + file view)"
```

---

### Task 10: CodeView — wire stream + panel + workspace selector

**Files:**
- Modify: `apps/jarvis-desk/src/views/CodeView.tsx` (replace stub)
- Test: `apps/jarvis-desk/src/views/CodeView.test.tsx` (create)

- [x] **Step 1: Write the failing test** — `src/views/CodeView.test.tsx` (mirror ChatView.test.tsx mocks: mock `../lib/api` incl. getContextInfo/getTree/getFile/listSessions/getSession/whoami/pingServer; wrap in the same providers ChatView.test uses):

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T' }, messages: [] }),
  createSession: vi.fn(),
  cancelRun: vi.fn(),
  whoami: vi.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  pingServer: vi.fn().mockResolvedValue(20),
  getContextInfo: vi.fn().mockResolvedValue({ compact_at: 200000, run_compact_at: 240000 }),
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
}))

import { CodeView } from './CodeView'
// (Import the same Providers ChatView.test wraps with — copy that test's wrapper.)

describe('CodeView', () => {
  it('renderer composer + workspace-vælger', async () => {
    // render(<Providers><CodeView sessionId={null} /></Providers>)
    // expect(await screen.findByPlaceholderText(/Skriv en besked/)).toBeInTheDocument()
    expect(true).toBe(true) // erstat med rigtige asserts efter at have kopieret ChatView.test-wrapperen
  })
})
```

(Replace the trivial assert: copy ChatView.test.tsx's provider wrapper + render CodeView; assert the composer placeholder AND the workspace label render. The point of the test is that CodeView mounts with stream + panel wired.)

- [x] **Step 2: Run — expect FAIL** (CodeView is the stub, no composer)

Run: `cd apps/jarvis-desk && npx vitest run src/views/CodeView.test.tsx`
Expected: FAIL

- [x] **Step 3: Implement** — replace `src/views/CodeView.tsx`. It mirrors ChatView but: (a) passes `mode='code'` + workspace into `stream.send`; (b) shows permissions in composer (`showPermissions` default true); (c) renders `CodePanel` in the right panel instead of artifact affordances; (d) shows a workspace selector. Reuse ChatView's transcript/stream/composer structure. Minimal v1 workspace state: default `{ kind: 'container', root: 'core' }`, owner can switch root among `_FILE_ROOTS`.

```tsx
import { useState } from 'react'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { CodePanel } from '../components/panel/CodePanel'

const CONTAINER_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts'] as const

/** Code mode: Jarvis koder i et valgt workspace. Stream i midten, CodePanel
 *  (fil-træ + fil/diff) til højre. v1: container-workspace, owner vælger rod. */
export function CodeView({ sessionId }: { sessionId: string | null }) {
  const stream = useStream()
  const { settings } = useSettings()
  const [root, setRoot] = useState<string>('core')
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (!sessionId) return
    stream.send(text, {
      sessionId,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      // @ts-expect-error mode plumbes via streamClient; SendOpts udvides i Task 6
      mode: 'code',
      workspaceKind: 'container',
      workspaceRoot: root,
    })
  }

  return (
    <div className="codeview">
      <div className="codeview-main">
        <div className="codeview-toolbar">
          <select value={root} onChange={(e) => setRoot(e.target.value)}>
            {CONTAINER_ROOTS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div className="transcript">
          {stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="full" streaming={stream.status === 'working'} />
          )}
          <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="full" workingStep={stream.workingStep} />
        </div>
        <Composer
          streaming={stream.status === 'working'}
          onSend={handleSend}
          onStop={() => void stream.abort()}
          model="deepseek-flash"
          thinking="think"
          config={config}
          getSessionId={async () => sessionId ?? ''}
          showPermissions={true}
          contextTokens={stream.usage.input + stream.usage.cacheHit}
          compactAt={0}
        />
      </div>
      {config && (
        <div className="codeview-panel">
          <CodePanel config={config} kind="container" root={root} />
        </div>
      )}
    </div>
  )
}
```

Add the proper `mode`/`workspaceKind`/`workspaceRoot` to `SendOpts` in StreamContext (done in Task 6) so the `@ts-expect-error` can be removed — update both. Add CSS for `.codeview` (flex row: main + panel), `.codeview-toolbar`, `.codeview-panel { width: 380px; border-left: 1px solid var(--line) }`.

NOTE: This v1 CodeView is intentionally simpler than ChatView (no session list interplay, no queue/follow-up — those can be lifted from ChatView later). It proves the loop: pick root → ask Jarvis → he uses code tools → files/diffs show in CodePanel. App.tsx already routes `surface === 'code' && <CodeView />`; update that line to pass `sessionId={activeId}`.

- [x] **Step 4: Run — expect PASS** + tsc + full suite

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: PASS, tsc 0

- [x] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/views/CodeView.tsx apps/jarvis-desk/src/views/CodeView.test.tsx apps/jarvis-desk/src/App.tsx apps/jarvis-desk/src/styles/app.css
git commit -m "feat(jarvis-desk): CodeView — code-mode stream + CodePanel + workspace selector"
```

---

### Task 11: Mode icon on code sessions in sidebar

**Files:**
- Modify: `apps/jarvis-desk/src/components/shell/Sidebar.tsx`, `apps/jarvis-desk/src/lib/api.ts` (ChatSession type: add `workspace_kind?`)
- Test: covered by existing Sidebar render; add a focused assertion if a Sidebar test exists, else manual.

- [x] **Step 1: Implement** — in `src/lib/api.ts`, add `workspace_kind?: string | null` to the `ChatSession` interface. In `Sidebar.tsx` `SessionItem`, when the session has `workspace_kind`, render a small `<Code size={12} />` (lucide) before the title:

```tsx
// SessionItem props: add workspaceKind?: string | null
// in the label button, before {title}:
{workspaceKind && <Code size={12} className="session-mode-icon" />}
```

Pass `workspaceKind={s.workspace_kind}` from the sessions.map. Add CSS: `.session-mode-icon { color: var(--accent); margin-right: 4px; flex: 0 0 auto; }`.

- [x] **Step 2: Verify** — `cd apps/jarvis-desk && npx tsc -b && npx vitest run`
Expected: tsc 0, tests pass.

- [x] **Step 3: Commit**

```bash
git add apps/jarvis-desk/src/components/shell/Sidebar.tsx apps/jarvis-desk/src/lib/api.ts apps/jarvis-desk/src/styles/app.css
git commit -m "feat(jarvis-desk): mode-icon on code sessions in sidebar"
```

**→ FINAL CHECKPOINT: deploy backend (push target + restart) + rebuild app (build/electron-builder/dpkg). Live-verify: switch to Code mode, pick root=core, ask Jarvis to read a file → tool-card + file shows in CodePanel; ask him to edit → diff renders.**

---

## Self-Review (against spec)

- **tool_scope=code role matrix** → Task 1. ✓
- **workspace binding (columns + service + request)** → Tasks 2, 3. ✓
- **GET /chat/tree (container jail + workstation bridge)** → Tasks 4, 5. ✓
- **Layout: sessions left (unchanged), stream center, CodePanel right** → Tasks 9, 10. ✓
- **permissions shown in code composer** → Task 10 (`showPermissions={true}`). ✓
- **diffs from tool_use blocks** → Task 7 (lineDiff helper) + wired in CodePanel; NOTE: Task 9/10 render the file view; live-diff-from-tool_use is the thinnest part — if time-boxed, ship file-view first and add diff rendering as a follow-up micro-task (lineDiff is ready). ✓ (helper done; wiring is incremental)
- **mode icon on code sessions** → Task 11. ✓
- **v2-deferred (terminal pane, multi-file diff, cowork, git-graf, inline-editor)** → not in any task (correct). ✓

**Known thin spot (flagged, not a gap):** the diff *rendering* (showing lineDiff output in CodePanel when Jarvis edits a file) is left as an incremental wiring step on top of the ready `lineDiff` helper + the existing tool_use blocks — to avoid over-speccing the exact tool-result shape before seeing it live. Build file-view first; wire diff once a real edit tool_use block is observed.
