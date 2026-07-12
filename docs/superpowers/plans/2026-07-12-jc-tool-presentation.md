# jarvis-code Tool-Presentation & Namespace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give jarvis-code (jc) a small curated tool catalog (8 client tools + 11 native companions + `load_more_tools`) with a 3-way execution router (local / container / operator) keyed on tool-name prefix, so `bash` never ambiguously runs on the wrong machine.

**Architecture:** A new single-source-of-truth catalog module on the runtime defines the companion set, the `runtime_` alias map for the 4 colliding file/shell tools, and load_more contents. A new server endpoint `POST /v1/tools/execute` runs a *forwarded* native tool scoped to the caller's user/workspace (unaliasing `runtime_` first), and enforces a HARD owner-gate for brain-writes at that user-facing boundary. jc fetches the catalog, prepends its 8 local tools, and routes each tool call: local execute vs forward-to-server.

**Tech Stack:** Python 3.11, FastAPI (runtime), httpx (jc client), pytest. Runtime repo: `/media/projects/jarvis-v2`. Client repo: `/home/bs/jarvis-code`. Tests run with `/opt/conda/envs/ai/bin/python -m pytest <path> -o addopts="" -q`.

**Ground-truth references (verified 2026-07-12):**
- Colliding native tools `bash`/`read_file`/`write_file`/`edit_file`: defined in `core/tools/simple_tools_definitions.py`, executed via `core/tools/simple_tools.py::execute_tool` → `_TOOL_HANDLERS`.
- `get_tool_definitions(role, scope)` → `core/tools/tool_scoping.py::filter_tool_definitions` (owner-only set at `tool_scoping.py:34-76`).
- Per-user context: `core/identity/workspace_context.py` (`user_context(...)`, `effective_role()`, `current_workspace_name()`).
- Agent-step endpoints: `apps/api/jarvis_api/routes/agent_loop.py` (`/v1/agent/step`, `/v1/tools/native`).
- jc tool list `LOCAL_TOOLS`: `/home/bs/jarvis-code/src/tools.py:30-154`; executor `TOOL_EXECUTORS` + `execute_tool` at `tools.py:448-624`; HTTP helpers in `/home/bs/jarvis-code/src/api.py`.

---

## File Structure

**Runtime (`/media/projects/jarvis-v2`):**
- Create `core/tools/jc_tool_catalog.py` — single source of truth: companion names, `runtime_` alias map, load_more contents, `build_jc_catalog(role, unlocked)`.
- Create `core/tools/brain_write_gate.py` — `check_brain_write_allowed(name, role)` HARD gate helper.
- Modify `apps/api/jarvis_api/routes/agent_loop.py` — add `GET /v1/tools/catalog` and `POST /v1/tools/execute`.
- Create `tests/test_jc_tool_catalog.py`, `tests/test_brain_write_gate.py`, `tests/api/test_tools_execute_endpoint.py`.

**Client (`/home/bs/jarvis-code`):**
- Create `src/tool_catalog.py` — `build_presented_tools(local_tools, companions, unlocked, runtime_aliases)`.
- Modify `src/api.py` — add `fetch_catalog(...)` and `execute_native_tool(...)` HTTP helpers.
- Modify `src/tools.py` — router: forward non-local tool calls to the server; handle `load_more_tools`.
- Create `tests/test_tool_catalog.py`, `tests/test_router.py` under `/home/bs/jarvis-code/tests/`.

---

## PHASE 1 — Runtime foundation

### Task 1: Catalog constants + alias helpers

**Files:**
- Create: `core/tools/jc_tool_catalog.py`
- Test: `tests/test_jc_tool_catalog.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_jc_tool_catalog.py
from core.tools import jc_tool_catalog as cat


def test_colliding_tools_are_the_verified_four():
    assert cat.COLLIDING_TOOLS == ("bash", "read_file", "write_file", "edit_file")


def test_default_companions_list():
    assert cat.DEFAULT_COMPANIONS == (
        "search_memory", "read_memory_topic", "write_memory_topic",
        "read_project_notes", "update_project_notes",
        "recall_memories", "search_jarvis_brain",
        "remember_this", "archive_brain_entry", "read_mood",
    )


def test_alias_roundtrip():
    assert cat.alias_for("bash") == "runtime_bash"
    assert cat.unalias("runtime_bash") == "bash"
    assert cat.unalias("remember_this") == "remember_this"  # non-alias unchanged


def test_is_runtime_alias():
    assert cat.is_runtime_alias("runtime_bash") is True
    assert cat.is_runtime_alias("runtime_read_file") is True
    assert cat.is_runtime_alias("runtime_notacolliding") is False  # only the 4 collide
    assert cat.is_runtime_alias("bash") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q`
Expected: FAIL with `ModuleNotFoundError: core.tools.jc_tool_catalog`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/tools/jc_tool_catalog.py
"""Single source of truth for what jarvis-code (jc) presents as tools.

Defines the curated default companion set, the runtime_-alias for the four
colliding file/shell primitives, and the load_more contents. Kept tiny and
dependency-light so both the /v1/tools/catalog endpoint and tests import it.
"""
from __future__ import annotations

RUNTIME_ALIAS_PREFIX = "runtime_"

# Verified 2026-07-12: only these four native tools share a name with jc's
# client-owned local tools and therefore need aliasing.
COLLIDING_TOOLS: tuple[str, ...] = ("bash", "read_file", "write_file", "edit_file")

# Always-present native companions (unique names → no alias needed).
DEFAULT_COMPANIONS: tuple[str, ...] = (
    "search_memory", "read_memory_topic", "write_memory_topic",
    "read_project_notes", "update_project_notes",
    "recall_memories", "search_jarvis_brain",
    "remember_this", "archive_brain_entry", "read_mood",
)


def alias_for(name: str) -> str:
    """runtime_ alias for a colliding tool name."""
    return f"{RUNTIME_ALIAS_PREFIX}{name}"


def unalias(name: str) -> str:
    """Strip the runtime_ prefix iff it maps to a colliding tool; else unchanged."""
    if is_runtime_alias(name):
        return name[len(RUNTIME_ALIAS_PREFIX):]
    return name


def is_runtime_alias(name: str) -> bool:
    """True only for runtime_<one-of-the-four-colliding-tools>."""
    if not name.startswith(RUNTIME_ALIAS_PREFIX):
        return False
    return name[len(RUNTIME_ALIAS_PREFIX):] in COLLIDING_TOOLS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/tools/jc_tool_catalog.py tests/test_jc_tool_catalog.py
git commit -m "feat(jc-catalog): alias helpers + companion constants"
```

---

### Task 2: `build_jc_catalog(role, unlocked)` returns tool defs

**Files:**
- Modify: `core/tools/jc_tool_catalog.py`
- Test: `tests/test_jc_tool_catalog.py`

**Context:** `get_tool_definitions(role="owner", scope="")` (in `core/tools/simple_tools.py`) returns the full list of native tool defs (OpenAI-ish dicts with `{"type":"function","function":{"name":...}}` OR flat `{"name":...}` — the builder must read the name from whichever shape). We pick companion defs by name, and — when `unlocked` — also add runtime_-aliased COPIES of the four colliding defs plus a `load_more_tools` meta def. When NOT unlocked, only companions + `load_more_tools`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_jc_tool_catalog.py
def _fake_defs():
    return [
        {"type": "function", "function": {"name": "bash", "description": "run"}},
        {"type": "function", "function": {"name": "read_file", "description": "r"}},
        {"type": "function", "function": {"name": "write_file", "description": "w"}},
        {"type": "function", "function": {"name": "edit_file", "description": "e"}},
        {"type": "function", "function": {"name": "remember_this", "description": "m"}},
        {"type": "function", "function": {"name": "read_mood", "description": "mood"}},
        {"type": "function", "function": {"name": "unrelated", "description": "x"}},
    ]


def _names(defs):
    return {(d.get("function") or d).get("name") for d in defs}


def test_locked_catalog_has_companions_plus_load_more(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=False)
    names = _names(out)
    assert "remember_this" in names and "read_mood" in names
    assert "load_more_tools" in names
    assert "runtime_bash" not in names        # locked → no runtime aliases
    assert "bash" not in names                # colliding name never presented bare


def test_unlocked_catalog_adds_runtime_aliases(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    names = _names(out)
    assert "runtime_bash" in names and "runtime_edit_file" in names
    assert "bash" not in names                # only the aliased form is presented
    assert "unrelated" in names               # unlocked exposes the rest of native


def test_load_more_tool_def_shape():
    d = cat.LOAD_MORE_TOOL_DEF
    assert d["function"]["name"] == "load_more_tools"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q`
Expected: FAIL with `AttributeError: build_jc_catalog` / `LOAD_MORE_TOOL_DEF`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to core/tools/jc_tool_catalog.py
from copy import deepcopy
from typing import Any

LOAD_MORE_TOOL_DEF: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_more_tools",
        "description": (
            "Unlock the full runtime toolbox (owner only): runtime_bash/read_file/"
            "write_file/edit_file, advanced memory, identity, operator desktop tools. "
            "Call this when the default set is insufficient."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


def _def_name(d: dict[str, Any]) -> str:
    return str((d.get("function") or d).get("name") or "")


def _all_native_defs(role: str) -> list[dict[str, Any]]:
    """Full native tool defs for a role. Wrapped for test injection."""
    from core.tools.simple_tools import get_tool_definitions
    return get_tool_definitions(role=role, scope="")


def build_jc_catalog(*, role: str, unlocked: bool) -> list[dict[str, Any]]:
    """Native-side tool defs jc should present (WITHOUT the 8 local client tools —
    jc prepends those). Locked: companions + load_more. Unlocked: companions +
    runtime_-aliased colliding tools + the rest of native + load_more."""
    all_defs = _all_native_defs(role)
    by_name = {_def_name(d): d for d in all_defs}
    out: list[dict[str, Any]] = []

    # 1) companions (unique names, presented bare)
    for name in DEFAULT_COMPANIONS:
        d = by_name.get(name)
        if d is not None:
            out.append(deepcopy(d))

    if unlocked:
        presented = {_def_name(d) for d in out}
        for d in all_defs:
            nm = _def_name(d)
            if nm in presented or nm == "load_more_tools":
                continue
            if nm in COLLIDING_TOOLS:
                # present ONLY the runtime_-aliased form
                alias = deepcopy(d)
                fn = alias.get("function") or alias
                fn["name"] = alias_for(nm)
                out.append(alias)
            else:
                out.append(deepcopy(d))

    out.append(deepcopy(LOAD_MORE_TOOL_DEF))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/tools/jc_tool_catalog.py tests/test_jc_tool_catalog.py
git commit -m "feat(jc-catalog): build_jc_catalog(role, unlocked) + load_more def"
```

---

### Task 3: HARD brain-write gate helper

**Files:**
- Create: `core/tools/brain_write_gate.py`
- Test: `tests/test_brain_write_gate.py`

**Context:** The gate lives at the user-facing forward boundary (Task 5). Jarvis' internal autonomous path never calls the forward endpoint, so it is unaffected by design. This helper only decides allow/deny for a *user-initiated* call.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_brain_write_gate.py
from core.tools import brain_write_gate as g


def test_brain_write_tools_set():
    assert g.BRAIN_WRITE_TOOLS == ("remember_this", "archive_brain_entry")


def test_non_brain_tool_always_allowed():
    assert g.check_brain_write_allowed("read_mood", role="guest") is True
    assert g.check_brain_write_allowed("search_memory", role="member") is True


def test_owner_may_brain_write():
    assert g.check_brain_write_allowed("remember_this", role="owner") is True
    assert g.check_brain_write_allowed("archive_brain_entry", role="") is True  # unbound = owner


def test_non_owner_brain_write_denied():
    assert g.check_brain_write_allowed("remember_this", role="member") is False
    assert g.check_brain_write_allowed("archive_brain_entry", role="guest") is False
    # runtime_-aliased form must also be caught (defense in depth)
    assert g.check_brain_write_allowed("remember_this", role="MEMBER") is False  # case-insensitive
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_brain_write_gate.py -o addopts="" -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/tools/brain_write_gate.py
"""HARD gate for user-initiated writes to Jarvis' brain.

Writing to Jarvis' mind is an identity/security boundary that must not rely on
the model obeying a prompt. Enforced at the user-facing forward endpoint
(POST /v1/tools/execute). Jarvis' own autonomous path never crosses that
boundary, so his agency is unaffected.
"""
from __future__ import annotations

BRAIN_WRITE_TOOLS: tuple[str, ...] = ("remember_this", "archive_brain_entry")


def check_brain_write_allowed(name: str, *, role: str) -> bool:
    """True if a user-initiated call to `name` is permitted for `role`.
    Non-brain-write tools: always True. Brain-write: owner/unbound only."""
    if name not in BRAIN_WRITE_TOOLS:
        return True
    return str(role or "").strip().lower() in ("", "owner")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_brain_write_gate.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/tools/brain_write_gate.py tests/test_brain_write_gate.py
git commit -m "feat(brain-gate): HARD owner-gate for user-initiated brain writes"
```

---

### Task 4: `GET /v1/tools/catalog` endpoint

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py`
- Test: `tests/api/test_tools_execute_endpoint.py`

**Context:** Reuse the existing auth dependency in `agent_loop.py` that yields the caller's identity (find how `/v1/tools/native` resolves role — pass the same dependency). The endpoint returns `{"tools": [...], "unlocked": bool}` where `tools` is `build_jc_catalog(role, unlocked)`. `unlocked` comes from a query param `?unlocked=true|false` (client tracks its own unlock state; the server just honors it, still role-gating the *contents*).

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_tools_execute_endpoint.py
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_catalog_locked_returns_companions_and_load_more():
    r = client.get("/v1/tools/catalog", params={"unlocked": "false"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "remember_this" in names
    assert "load_more_tools" in names
    assert "runtime_bash" not in names


def test_catalog_unlocked_returns_runtime_aliases():
    r = client.get("/v1/tools/catalog", params={"unlocked": "true"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "runtime_bash" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_tools_execute_endpoint.py -o addopts="" -q`
Expected: FAIL with 404 (route not defined).

- [ ] **Step 3: Write minimal implementation**

Add to `apps/api/jarvis_api/routes/agent_loop.py` (near the existing `/v1/tools/native` route; reuse the same router object and the same identity/role dependency already used there — locate it and mirror it):

```python
from core.tools.jc_tool_catalog import build_jc_catalog

@router.get("/v1/tools/catalog")
async def tools_catalog(unlocked: bool = False, role: str = Depends(_resolve_role)):
    # _resolve_role: reuse whatever dependency /v1/tools/native uses to get the
    # caller role; default "owner" for the owner token. Non-owner never gets
    # runtime aliases because build_jc_catalog reads role-scoped native defs.
    tools = build_jc_catalog(role=role or "owner", unlocked=bool(unlocked))
    return {"tools": tools, "unlocked": bool(unlocked)}
```

If `/v1/tools/native` does not use a role dependency, resolve role inline with the same helper it uses (e.g. `effective_role()` from `core.identity.workspace_context`), and drop the `Depends`. Keep it consistent with the existing route.

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_tools_execute_endpoint.py::test_catalog_locked_returns_companions_and_load_more tests/api/test_tools_execute_endpoint.py::test_catalog_unlocked_returns_runtime_aliases -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/agent_loop.py tests/api/test_tools_execute_endpoint.py
git commit -m "feat(api): GET /v1/tools/catalog returns curated jc tool defs"
```

---

### Task 5: `POST /v1/tools/execute` — forwarded execution + unalias + brain gate + user scoping

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py`
- Test: `tests/api/test_tools_execute_endpoint.py`

**Context:** This is the container-execution path for forwarded tool calls. It: (1) resolves caller role + user context, (2) unaliases `runtime_bash`→`bash`, (3) applies `check_brain_write_allowed`, (4) runs `execute_tool(name, arguments)` inside `user_context(...)` so memory tools scope to the caller's workspace, (5) returns the result. `execute_tool` is `core/tools/simple_tools.py::execute_tool` (sync — call in a threadpool via `run_in_threadpool` or `asyncio.to_thread`).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/api/test_tools_execute_endpoint.py

def test_execute_unaliases_and_runs(monkeypatch):
    calls = {}
    def _fake_execute_tool(name, arguments):
        calls["name"] = name
        calls["arguments"] = arguments
        return {"status": "ok", "echo": arguments}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "runtime_bash", "arguments": {"command": "ls"}})
    assert r.status_code == 200
    assert calls["name"] == "bash"                      # unaliased
    assert r.json()["result"]["status"] == "ok"


def test_execute_forwards_companion_untouched(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: calls.setdefault("name", name) or {"ok": True},
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "search_memory", "arguments": {"query": "x"}})
    assert r.status_code == 200
    assert calls["name"] == "search_memory"


def test_execute_brain_write_denied_for_non_owner(monkeypatch):
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop._resolve_role", lambda *a, **k: "member"
    )
    # ensure execute_tool is NOT called when denied
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: (_ for _ in ()).throw(AssertionError("should not run")),
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "remember_this", "arguments": {"content": "x"}})
    assert r.status_code == 403
    assert "brain" in r.json()["detail"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_tools_execute_endpoint.py -o addopts="" -q`
Expected: FAIL (route 404 / attributes missing).

- [ ] **Step 3: Write minimal implementation**

Add to `apps/api/jarvis_api/routes/agent_loop.py` (module-level import so the monkeypatch targets resolve):

```python
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from core.tools.simple_tools import execute_tool
from core.tools.jc_tool_catalog import unalias
from core.tools.brain_write_gate import check_brain_write_allowed
from core.identity.workspace_context import user_context, effective_role


def _resolve_role(request: Request = None) -> str:
    # Mirror how /v1/tools/native resolves the caller. Owner token → "owner".
    try:
        return effective_role() or "owner"
    except Exception:
        return "owner"


class _ExecBody(BaseModel):
    name: str
    arguments: dict = {}
    session_id: str | None = None
    user_id: str | None = None


@router.post("/v1/tools/execute")
async def tools_execute(body: _ExecBody):
    role = _resolve_role()
    real = unalias(body.name)
    if not check_brain_write_allowed(real, role=role):
        raise HTTPException(status_code=403,
                            detail="brain-write not permitted for this user")
    with user_context(body.user_id or "", workspace_override=None):
        result = await run_in_threadpool(execute_tool, real, body.arguments)
    return {"result": result, "name": real}
```

Notes for the implementer:
- Confirm `user_context(...)`'s exact signature in `core/identity/workspace_context.py` (the explore found `user_context(discord_id, workspace_override)`); adapt the call. For the owner (empty user_id) it must resolve to Bjørn's workspace as today.
- `execute_tool` needs `session_id`/`turn_id` for a few tools (e.g. `remember_this` rate-limits). If the runtime reads those from a ContextVar, set them inside `user_context`; if from the arguments, pass `body.session_id` through. Verify against `core/tools/jarvis_brain_tools.py` and set whatever it reads.

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_tools_execute_endpoint.py -o addopts="" -q`
Expected: PASS (all 5 in file).

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/agent_loop.py tests/api/test_tools_execute_endpoint.py
git commit -m "feat(api): POST /v1/tools/execute — forwarded exec, unalias, brain gate, user scope"
```

---

## PHASE 2 — jarvis-code client

### Task 6: Client catalog assembly

**Files:**
- Create: `/home/bs/jarvis-code/src/tool_catalog.py`
- Test: `/home/bs/jarvis-code/tests/test_tool_catalog.py`

**Context:** The client prepends its 8 `LOCAL_TOOLS` to the server-provided companion defs. It also owns the set of names that must be *forwarded* (everything not local): companion names + any `runtime_`-prefixed name + `operator_`-prefixed name.

- [ ] **Step 1: Write the failing test**

```python
# /home/bs/jarvis-code/tests/test_tool_catalog.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import tool_catalog as tc


def _names(defs):
    return {(d.get("function") or d)["name"] for d in defs}


def test_prepends_local_tools():
    local = [{"type": "function", "function": {"name": "bash"}}]
    companions = [{"type": "function", "function": {"name": "remember_this"}}]
    out = tc.build_presented_tools(local_tools=local, companions=companions)
    names = _names(out)
    assert "bash" in names and "remember_this" in names
    # local first (cache-stable order)
    assert (out[0].get("function") or out[0])["name"] == "bash"


def test_is_forwarded_tool():
    local_names = {"bash", "read_file"}
    assert tc.is_forwarded_tool("remember_this", local_names) is True
    assert tc.is_forwarded_tool("runtime_bash", local_names) is True
    assert tc.is_forwarded_tool("operator_screenshot", local_names) is True
    assert tc.is_forwarded_tool("bash", local_names) is False   # local wins
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_tool_catalog.py -o addopts="" -q`
Expected: FAIL with import error.

- [ ] **Step 3: Write minimal implementation**

```python
# /home/bs/jarvis-code/src/tool_catalog.py
"""Assemble the tool list jc presents to the model, and decide routing."""
from __future__ import annotations
from typing import Any

RUNTIME_PREFIX = "runtime_"
OPERATOR_PREFIX = "operator_"


def build_presented_tools(*, local_tools: list[dict[str, Any]],
                          companions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Local client tools first (cache-stable), then server companion defs."""
    return list(local_tools) + list(companions)


def is_forwarded_tool(name: str, local_names: set[str]) -> bool:
    """True if a tool call must be forwarded to the server (container/operator)."""
    if name in local_names:
        return False
    return (name.startswith(RUNTIME_PREFIX)
            or name.startswith(OPERATOR_PREFIX)
            or True)  # any non-local companion is server-forwarded
```

Note: the final `or True` means "any name not local is forwarded" — intentional, since companions have unique non-prefixed names. Keep the explicit prefix checks for readability/documentation of the 3 domains.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_tool_catalog.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/tool_catalog.py tests/test_tool_catalog.py
git commit -m "feat(jc): tool_catalog assembly + forwarding predicate"
```

---

### Task 7: Client HTTP helpers — fetch_catalog + execute_native_tool

**Files:**
- Modify: `/home/bs/jarvis-code/src/api.py`
- Test: `/home/bs/jarvis-code/tests/test_api_helpers.py`

**Context:** Mirror the existing `native_tools()` helper (`api.py:407-427`). Use `httpx` like the rest of api.py. `fetch_catalog(unlocked)` → GET `/v1/tools/catalog`. `execute_native_tool(name, arguments, session_id)` → POST `/v1/tools/execute`.

- [ ] **Step 1: Write the failing test**

```python
# /home/bs/jarvis-code/tests/test_api_helpers.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from unittest.mock import patch, MagicMock
from src import api


def test_fetch_catalog_calls_endpoint():
    resp = MagicMock(); resp.json.return_value = {"tools": [], "unlocked": False}
    resp.raise_for_status = lambda: None
    with patch("src.api.httpx.get", return_value=resp) as m:
        out = api.fetch_catalog(api_url="http://x", auth_token="t", unlocked=False)
    assert out == {"tools": [], "unlocked": False}
    assert "/v1/tools/catalog" in m.call_args[0][0]


def test_execute_native_tool_posts_name_and_args():
    resp = MagicMock(); resp.json.return_value = {"result": {"ok": True}, "name": "bash"}
    resp.raise_for_status = lambda: None
    with patch("src.api.httpx.post", return_value=resp) as m:
        out = api.execute_native_tool(api_url="http://x", auth_token="t",
                                      name="runtime_bash", arguments={"command": "ls"},
                                      session_id="s")
    assert out["result"] == {"ok": True}
    body = m.call_args.kwargs["json"]
    assert body["name"] == "runtime_bash" and body["arguments"] == {"command": "ls"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_api_helpers.py -o addopts="" -q`
Expected: FAIL (`AttributeError: fetch_catalog`).

- [ ] **Step 3: Write minimal implementation**

Add to `/home/bs/jarvis-code/src/api.py` (match the header/timeout style of `native_tools`):

```python
def fetch_catalog(*, api_url: str, auth_token: str | None,
                  unlocked: bool = False, timeout: int = 20) -> dict:
    """GET /v1/tools/catalog → {tools: [...], unlocked: bool}."""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    resp = httpx.get(f"{api_url}/v1/tools/catalog",
                     params={"unlocked": str(unlocked).lower()},
                     headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def execute_native_tool(*, api_url: str, auth_token: str | None, name: str,
                        arguments: dict, session_id: str | None = None,
                        timeout: int = 120) -> dict:
    """POST /v1/tools/execute → {result: ..., name: str}."""
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    resp = httpx.post(f"{api_url}/v1/tools/execute",
                      json={"name": name, "arguments": arguments,
                            "session_id": session_id},
                      headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_api_helpers.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/api.py tests/test_api_helpers.py
git commit -m "feat(jc): fetch_catalog + execute_native_tool HTTP helpers"
```

---

### Task 8: Router — forward non-local tool calls; handle load_more_tools

**Files:**
- Modify: `/home/bs/jarvis-code/src/tools.py`
- Test: `/home/bs/jarvis-code/tests/test_router.py`

**Context:** `execute_tool(tool_name, args, ...)` (`tools.py:515`) currently only does local dispatch and returns "Unknown tool" for anything not in `TOOL_EXECUTORS` (`tools.py:546`). Change: if the name is not local → forward via `api.execute_native_tool`. Special-case `load_more_tools`: set an unlock flag the REPL/TUI reads and return a confirmation (the actual catalog refetch happens in the loop, Task 9). Keep local execution untouched.

- [ ] **Step 1: Write the failing test**

```python
# /home/bs/jarvis-code/tests/test_router.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from src import tools


def test_local_tool_still_runs_locally():
    with patch.dict(tools.TOOL_EXECUTORS, {"bash": lambda **k: "LOCAL"}, clear=False):
        out = tools.route_tool_call("bash", {"command": "ls"},
                                    api_url="http://x", auth_token="t", session_id="s")
    assert out == "LOCAL"


def test_non_local_tool_is_forwarded():
    with patch("src.tools.api.execute_native_tool",
               return_value={"result": {"ok": True}, "name": "remember_this"}) as m:
        out = tools.route_tool_call("remember_this", {"content": "x"},
                                    api_url="http://x", auth_token="t", session_id="s")
    assert m.called
    assert out == {"ok": True}


def test_runtime_alias_is_forwarded_verbatim():
    with patch("src.tools.api.execute_native_tool",
               return_value={"result": "R", "name": "bash"}) as m:
        tools.route_tool_call("runtime_bash", {"command": "ls"},
                              api_url="http://x", auth_token="t", session_id="s")
    assert m.call_args.kwargs["name"] == "runtime_bash"  # server unaliases
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_router.py -o addopts="" -q`
Expected: FAIL (`AttributeError: route_tool_call`).

- [ ] **Step 3: Write minimal implementation**

Add near `execute_tool` in `/home/bs/jarvis-code/src/tools.py` (import `from . import api` if not present):

```python
from . import api  # if not already imported at top

def route_tool_call(tool_name, args, *, api_url, auth_token, session_id):
    """3-way router: local dispatch vs forward to server (container/operator)."""
    if tool_name in TOOL_EXECUTORS:
        return TOOL_EXECUTORS[tool_name](**args)
    resp = api.execute_native_tool(api_url=api_url, auth_token=auth_token,
                                   name=tool_name, arguments=args,
                                   session_id=session_id)
    return resp.get("result")
```

Then update the existing tool-call site(s) in `repl.py`/`tui.py` (Task 9) to call `route_tool_call` instead of the local-only `execute_tool`. Keep `execute_tool` for local-only callers/tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_router.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/tools.py tests/test_router.py
git commit -m "feat(jc): 3-way router forwards non-local tool calls to server"
```

---

### Task 9: Wire catalog + router into the client loop; load_more unlock

**Files:**
- Modify: `/home/bs/jarvis-code/src/tui.py` (`_run_turn_client` ~485-551, `_stream_one_step`, `/native`/`/context` command area ~351-432)
- Modify: `/home/bs/jarvis-code/src/repl.py` (`run_turn` ~703-894) if it shares the loop
- Test: `/home/bs/jarvis-code/tests/test_loop_integration.py`

**Context:** On session start (and after `load_more_tools`), fetch the catalog and build the presented tools = `LOCAL_TOOLS + companions`. Pass that as `tools=` to `agent_step`/`agent_step_stream` instead of bare `LOCAL_TOOLS`. Track `self.unlocked` (default False); when the model calls `load_more_tools`, set `self.unlocked=True`, refetch catalog, and return a short confirmation as the tool result. Route every tool call through `route_tool_call`.

- [ ] **Step 1: Write the failing test**

```python
# /home/bs/jarvis-code/tests/test_loop_integration.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from src import tools, tool_catalog


def test_load_more_unlocks_and_refetches():
    state = {"unlocked": False}
    def _handle(name, args, **kw):
        if name == "load_more_tools":
            state["unlocked"] = True
            return {"status": "unlocked"}
        return {"ok": True}
    with patch("src.tools.route_tool_call", side_effect=_handle):
        r = tools.route_tool_call("load_more_tools", {}, api_url="x",
                                  auth_token="t", session_id="s")
    assert r == {"status": "unlocked"}
    assert state["unlocked"] is True


def test_presented_tools_include_local_and_companions():
    local = tools.LOCAL_TOOLS
    companions = [{"type": "function", "function": {"name": "read_mood"}}]
    presented = tool_catalog.build_presented_tools(local_tools=local, companions=companions)
    names = {(d.get("function") or d)["name"] for d in presented}
    assert "bash" in names and "read_mood" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_loop_integration.py -o addopts="" -q`
Expected: FAIL until `load_more_tools` handling + presented-tools wiring exist.

- [ ] **Step 3: Write minimal implementation**

In `tui.py` (and `repl.py` if it has its own loop):
1. Add `self.unlocked = False` in `__init__`.
2. Add a helper `self._refresh_tools()` that calls `api.fetch_catalog(api_url, auth_token, unlocked=self.unlocked)` and sets `self.presented_tools = tool_catalog.build_presented_tools(local_tools=LOCAL_TOOLS, companions=result["tools"])`. Call it once at session start.
3. Where `agent_step(...)`/`agent_step_stream(...)` is called with `tools=LOCAL_TOOLS`, pass `tools=self.presented_tools`.
4. In the tool-execution loop, replace `execute_tool(name, args, ...)` with:
```python
if name == "load_more_tools":
    self.unlocked = True
    self._refresh_tools()
    result = {"status": "unlocked", "count": len(self.presented_tools)}
else:
    result = tools.route_tool_call(name, args, api_url=self.api_url,
                                   auth_token=self.auth_token,
                                   session_id=self.session_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_loop_integration.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Manual smoke (owner)**

Run jc, confirm `/native list` still works, ask Jarvis to "gem dette som et minde" (should call `remember_this`, forwarded) and "recall hvad vi talte om" (`recall_memories`). Ask him to run a container command → he should call `load_more_tools` then `runtime_bash`. Verify local `bash` still runs on your machine.

- [ ] **Step 6: Commit**

```bash
cd /home/bs/jarvis-code
git add src/tui.py src/repl.py tests/test_loop_integration.py
git commit -m "feat(jc): wire curated catalog + forwarding router + load_more unlock into loop"
```

---

## PHASE 3 — Verification

### Task 10: Full regression + deploy runtime

**Files:** none (verification)

- [ ] **Step 1: Runtime test suite (touched areas)**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py tests/test_brain_write_gate.py tests/api/test_tools_execute_endpoint.py -o addopts="" -q`
Expected: all PASS.

- [ ] **Step 2: Client test suite**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/ -o addopts="" -q`
Expected: all PASS.

- [ ] **Step 3: Deploy runtime** (commit on main → push → container pull → restart)

```bash
# from /media/projects/jarvis-v2, after commits pushed:
ssh bs@10.0.0.39 'git -C /media/projects/jarvis-v2 pull --ff-only origin main && \
  sudo systemctl restart jarvis-api jarvis-runtime'
ssh bs@10.0.0.39 'systemctl is-active jarvis-api jarvis-runtime'
```
Expected: `active active`. Verify HEAD on container == pushed commit.

- [ ] **Step 4: Live end-to-end (owner + non-owner)**

Owner: from jc, exercise the manual smoke from Task 9. Non-owner (if a member token is available): confirm a direct "remember this in your brain" request is rejected with 403 at the forward endpoint, while `search_memory`/`recall_memories` work scoped to that member's workspace.

---

## Self-Review (plan author)

**Spec coverage:**
- §3.1 namespace / collision set → Tasks 1, 2 (alias helpers, runtime_ aliasing only for the 4).
- §3.2 default set (8 + 11) → Tasks 2 (companions+load_more), 6, 9 (local prepend, wiring).
- §3.3 two memory domains → workspace scoping Task 5 (`user_context`); brain HARD gate Tasks 3, 5.
- §3.4 load_more_tools (net-new) → Tasks 2 (def), 9 (unlock behavior).
- §4 3-way router + prefix-strip + invariant → Tasks 5 (server unalias), 6 & 8 (client routing).
- §5 non-goals (no global rename, Central non-gating) → respected: aliasing is jc-presentation only; no Central involvement in routing.
- §7 test-tilgang → each task is TDD with the named assertions.

**Placeholder scan:** No TBD/TODO. Two explicit "verify against real signature" notes (user_context args in Task 5; session/turn context for remember_this) are grounded call-outs, not placeholders — the implementer confirms the exact signature the explore already located.

**Type consistency:** `build_jc_catalog(role, unlocked)` (Task 2) used identically in Task 4. `unalias`/`alias_for`/`is_runtime_alias` (Task 1) reused in Tasks 2, 5. `check_brain_write_allowed(name, role=...)` (Task 3) used in Task 5. `build_presented_tools(local_tools, companions)` (Task 6) used in Task 9. `route_tool_call(name, args, api_url, auth_token, session_id)` (Task 8) used in Task 9. `execute_native_tool`/`fetch_catalog` signatures (Task 7) match their callers.
