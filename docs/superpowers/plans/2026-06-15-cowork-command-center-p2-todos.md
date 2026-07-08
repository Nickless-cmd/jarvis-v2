---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Cowork Command Center — Plan 2: Interaktiv Mission Control (todos)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (eller subagent-driven-development) til at implementere task-for-task. Steps bruger checkbox (`- [ ]`).

**Goal:** Gør cowork-todo-ruden interaktiv — owner kan oprette, skifte status (pending→in_progress→completed) og slette todos direkte fra Mission Control, oven på det eksisterende session-keyede `agent_todos`-system.

**Architecture:** `core/services/agent_todos.py` er session-keyed og load-bearing for den agentiske loop (Jarvis ser sine todos i prompten). Vi rører IKKE dens status-vokabular. Vi tilføjer (a) en stabil cowork-session-nøgle til UI-oprettede todos, og (b) cross-session helpers så en mutation fra cowork kan ramme en todo uanset hvilken chat-session den blev født i. Backend eksponerer tre nye owner-only cowork-endpoints; frontend gør `TodoPane` redigerbar.

**Tech Stack:** FastAPI + pytest (conda `/opt/conda/envs/ai`), React + vitest (`apps/jarvis-desk`).

---

## Bevidst udskudt (kræver din beslutning)

Spec §3.1 nævner også **TTL/auto-expire**, **pause** og en **'expired'-status**. De udskydes til en separat Plan 2b, fordi de udvider `_VALID_STATUSES` og dermed ændrer hvad Jarvis ser i sin arbejdshukommelse-prompt (`todos_prompt_section`). Det er en adfærds-ændring på den agentiske loop og bør designes bevidst — ikke smugles ind under en UI-opgave.

## File Structure

**Backend:**
- Modify: `core/services/agent_todos.py` — tilføj `COWORK_SESSION`-konstant + `add_cowork_todo()`, `update_todo_status_anywhere()`, `remove_todo_anywhere()`.
- Modify: `apps/api/jarvis_api/routes/cowork.py` — tilføj `POST /todos`, `POST /todos/{id}/status`, `DELETE /todos/{id}` (owner-only).
- Test: `tests/test_agent_todos_cowork.py`

**Frontend:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts` — `createCoworkTodo`, `setCoworkTodoStatus`, `deleteCoworkTodo`.
- Modify: `apps/jarvis-desk/src/components/cowork/TodoPane.tsx` — redigerbar (input + status-cyklus + slet).
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx` — giv `config` til `TodoPane`.
- Test: `apps/jarvis-desk/src/lib/coworkApi.todos.test.ts`, `apps/jarvis-desk/src/components/cowork/TodoPane.test.tsx`

---

## Task 1: Backend — cowork-helpers i agent_todos

**Files:**
- Modify: `core/services/agent_todos.py`
- Test: `tests/test_agent_todos_cowork.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_todos_cowork.py
import core.services.agent_todos as at


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(at, "_load_all", lambda: {k: list(v) for k, v in store.items()})
    monkeypatch.setattr(at, "_save_all", lambda data: store.update({k: list(v) for k, v in data.items()}))
    return store


def test_add_cowork_todo_lands_in_cowork_session(monkeypatch):
    _reset(monkeypatch)
    res = at.add_cowork_todo("ring til mekanikeren")
    assert res["status"] == "ok"
    todos = at.list_todos(at.COWORK_SESSION)
    assert len(todos) == 1
    assert todos[0]["content"] == "ring til mekanikeren"
    assert todos[0]["status"] == "pending"


def test_update_status_anywhere_finds_todo_in_any_session(monkeypatch):
    _reset(monkeypatch)
    at.add_todo("sess-A", "opgave fra chat")
    tid = at.list_todos("sess-A")[0]["id"]
    res = at.update_todo_status_anywhere(tid, "completed")
    assert res["status"] == "ok"
    assert at.list_todos("sess-A")[0]["status"] == "completed"


def test_update_status_anywhere_unknown_id(monkeypatch):
    _reset(monkeypatch)
    res = at.update_todo_status_anywhere("td-nope", "completed")
    assert res["status"] == "error"


def test_remove_anywhere_deletes_from_owning_session(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("slet mig")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    res = at.remove_todo_anywhere(tid)
    assert res["status"] == "ok"
    assert at.list_todos(at.COWORK_SESSION) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_todos_cowork.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'COWORK_SESSION'`

- [ ] **Step 3: Write minimal implementation**

Tilføj i `core/services/agent_todos.py` (efter `_VALID_STATUSES`-definitionen for konstanten, og nye funktioner efter `remove_todo`):

```python
# Stabil session-nøgle for todos oprettet fra cowork-UI'et (ikke en chat-tråd).
COWORK_SESSION = "_cowork"


def add_cowork_todo(content: str) -> dict[str, Any]:
    """Opret en todo i den delte cowork-session (Mission Control UI)."""
    return add_todo(COWORK_SESSION, content)


def _find_session_for_todo(todo_id: str) -> str | None:
    for sid, items in (_load_all() or {}).items():
        if any(str(t.get("id")) == str(todo_id) for t in items):
            return sid
    return None


def update_todo_status_anywhere(todo_id: str, new_status: str) -> dict[str, Any]:
    """Skift status på en todo uanset hvilken session den lever i (cowork kender
    ikke session-nøglen). Genbruger update_todo_status' invarianter."""
    sid = _find_session_for_todo(todo_id)
    if sid is None:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    return update_todo_status(sid, todo_id, new_status)


def remove_todo_anywhere(todo_id: str) -> dict[str, Any]:
    """Slet en todo uanset hvilken session den lever i."""
    sid = _find_session_for_todo(todo_id)
    if sid is None:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    return remove_todo(sid, todo_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_todos_cowork.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Sikr test-coverage-gate**

`core/services/agent_todos.py` forventer `tests/test_agent_todos.py`. Hvis den IKKE findes (tjek: `ls tests/test_agent_todos.py`), tilføj en mapping i `scripts/enforce_test_coverage.py` i `KNOWN_MAPPINGS`:

```python
    "core/services/agent_todos.py": "tests/test_agent_todos_cowork.py",
```

Hvis `tests/test_agent_todos.py` allerede findes, spring dette trin over.

- [ ] **Step 6: Commit**

```bash
git add core/services/agent_todos.py tests/test_agent_todos_cowork.py scripts/enforce_test_coverage.py
git commit -m "feat(todos): cowork-session + cross-session todo-helpers (command center §3.1)"
```

---

## Task 2: Backend — cowork mutations-endpoints

**Files:**
- Modify: `apps/api/jarvis_api/routes/cowork.py`
- Test: `tests/test_cowork_todo_routes.py`

Endpoints er owner-only (todos er owner-scopet i feed'et). Body parses som dict. Status valideres til de tre gyldige værdier.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cowork_todo_routes.py
import asyncio
import apps.api.jarvis_api.routes.cowork as cw


def test_create_todo_owner(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    captured = {}
    monkeypatch.setattr(cw.cowork_feed, "list_todos_feed", lambda **k: [])
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "add_cowork_todo", lambda c: captured.update(content=c) or {"status": "ok"})
    res = asyncio.run(cw.cowork_create_todo({"content": "ny opgave"}))
    assert res["status"] == "ok"
    assert captured["content"] == "ny opgave"


def test_create_todo_member_forbidden(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_create_todo({"content": "x"}))
    assert ei.value.status_code == 403


def test_set_status_validates(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    res = asyncio.run(cw.cowork_set_todo_status("td-1", {"status": "bogus"}))
    assert res["status"] == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_todo_routes.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'cowork_create_todo'`

- [ ] **Step 3: Write minimal implementation**

Tilføj i `apps/api/jarvis_api/routes/cowork.py` (efter `cowork_todos`-endpointet). Importér `Body`:

```python
from fastapi import APIRouter, Body, HTTPException
```

```python
_VALID_TODO_STATUSES = ("pending", "in_progress", "completed")


@router.post("/todos")
async def cowork_create_todo(payload: dict = Body(default={})) -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    content = str((payload or {}).get("content") or "").strip()
    if not content:
        return {"status": "error", "error": "content er påkrævet"}
    from core.services.agent_todos import add_cowork_todo
    return await asyncio.to_thread(add_cowork_todo, content)


@router.post("/todos/{todo_id}/status")
async def cowork_set_todo_status(todo_id: str, payload: dict = Body(default={})) -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    status = str((payload or {}).get("status") or "").strip().lower()
    if status not in _VALID_TODO_STATUSES:
        return {"status": "error", "error": f"status skal være en af {_VALID_TODO_STATUSES}"}
    from core.services.agent_todos import update_todo_status_anywhere
    return await asyncio.to_thread(update_todo_status_anywhere, todo_id, status)


@router.delete("/todos/{todo_id}")
async def cowork_delete_todo(todo_id: str) -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    from core.services.agent_todos import remove_todo_anywhere
    return await asyncio.to_thread(remove_todo_anywhere, todo_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_todo_routes.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/cowork.py tests/test_cowork_todo_routes.py
git commit -m "feat(cowork): POST/DELETE todo-endpoints (owner-only)"
```

---

## Task 3: Frontend — coworkApi todo-mutationer

**Files:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts`
- Test: `apps/jarvis-desk/src/lib/coworkApi.todos.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/jarvis-desk/src/lib/coworkApi.todos.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => fetchMock(...a) }))

import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo } from './coworkApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('cowork todo mutations', () => {
  beforeEach(() => fetchMock.mockReset().mockResolvedValue({ status: 'ok' }))

  it('createCoworkTodo POSTer content', async () => {
    await createCoworkTodo(cfg, 'ny')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos', { method: 'POST', body: { content: 'ny' } })
  })
  it('setCoworkTodoStatus POSTer status', async () => {
    await setCoworkTodoStatus(cfg, 'td-1', 'completed')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1/status', { method: 'POST', body: { status: 'completed' } })
  })
  it('deleteCoworkTodo DELETEr', async () => {
    await deleteCoworkTodo(cfg, 'td-1')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1', { method: 'DELETE' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.todos.test.ts`
Expected: FAIL — eksports mangler

- [ ] **Step 3: Write minimal implementation**

Tilføj nederst i `apps/jarvis-desk/src/lib/coworkApi.ts`:

```typescript
export async function createCoworkTodo(config: ApiConfig, content: string): Promise<void> {
  await apiFetch(config, '/cowork/todos', { method: 'POST', body: { content } })
}

export async function setCoworkTodoStatus(config: ApiConfig, id: string, status: string): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}/status`, { method: 'POST', body: { status } })
}

export async function deleteCoworkTodo(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}`, { method: 'DELETE' })
}
```

Bemærk: `apiFetch`'s `body`-option serialiseres til JSON af klient-laget (samme som øvrige POST-kald). Verificér at `FetchOptions.body` findes i `src/lib/api.ts`; gør den ikke, send `body: JSON.stringify({...})` i stedet og matchende i testen.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.todos.test.ts`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/lib/coworkApi.todos.test.ts
git commit -m "feat(desk): coworkApi todo-mutationer (create/status/delete)"
```

---

## Task 4: Frontend — redigerbar TodoPane

**Files:**
- Modify: `apps/jarvis-desk/src/components/cowork/TodoPane.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/TodoPane.test.tsx`

`TodoPane` får en valgfri `config`. Uden config (test af read-only legacy) opfører den sig som før. Med config: input til ny todo, klik på status-ikon cykler pending→in_progress→completed→pending, slet-knap. Efter hver mutation kalder den `onChanged?.()` så forælderen kan refetche; lokalt opdateres optimistisk ikke (poll'en på 6s henter sandheden — enkelt og korrekt).

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/cowork/TodoPane.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const createCoworkTodo = vi.fn().mockResolvedValue(undefined)
const setCoworkTodoStatus = vi.fn().mockResolvedValue(undefined)
const deleteCoworkTodo = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  createCoworkTodo: (...a: unknown[]) => createCoworkTodo(...a),
  setCoworkTodoStatus: (...a: unknown[]) => setCoworkTodoStatus(...a),
  deleteCoworkTodo: (...a: unknown[]) => deleteCoworkTodo(...a),
}))

import { TodoPane } from './TodoPane'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('TodoPane interaktiv', () => {
  beforeEach(() => { createCoworkTodo.mockClear(); setCoworkTodoStatus.mockClear(); deleteCoworkTodo.mockClear() })

  it('opretter en todo via input + Enter', async () => {
    const onChanged = vi.fn()
    render(<TodoPane todos={[]} config={cfg} onChanged={onChanged} />)
    const input = screen.getByPlaceholderText(/ny opgave/i)
    fireEvent.change(input, { target: { value: 'køb mælk' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(createCoworkTodo).toHaveBeenCalledWith(cfg, 'køb mælk'))
    expect(onChanged).toHaveBeenCalled()
  })

  it('cykler status ved klik på status-knap', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /skift status/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'in_progress'))
  })

  it('sletter en todo', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /slet/i }))
    await waitFor(() => expect(deleteCoworkTodo).toHaveBeenCalledWith(cfg, 'td-1'))
  })

  it('uden config: read-only (ingen input)', () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} />)
    expect(screen.queryByPlaceholderText(/ny opgave/i)).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoPane.test.tsx`
Expected: FAIL — input/knapper findes ikke

- [ ] **Step 3: Write minimal implementation**

```tsx
// apps/jarvis-desk/src/components/cowork/TodoPane.tsx
import { useState } from 'react'
import { CircleCheck, CircleDot, Circle, Trash2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo } from '../../lib/coworkApi'

export interface TodoItem { id: string; content: string; status: string }

const NEXT: Record<string, string> = { pending: 'in_progress', in_progress: 'completed', completed: 'pending' }

export function TodoPane({
  todos, config, onChanged,
}: { todos: TodoItem[]; config?: ApiConfig; onChanged?: () => void }) {
  const [draft, setDraft] = useState('')
  const editable = !!config

  const after = () => { onChanged?.() }

  const submit = async () => {
    const c = draft.trim()
    if (!c || !config) return
    setDraft('')
    await createCoworkTodo(config, c)
    after()
  }
  const cycle = async (t: TodoItem) => {
    if (!config) return
    await setCoworkTodoStatus(config, t.id, NEXT[t.status] || 'pending')
    after()
  }
  const remove = async (t: TodoItem) => {
    if (!config) return
    await deleteCoworkTodo(config, t.id)
    after()
  }

  return (
    <div className="cowork-todos">
      {editable && (
        <input
          className="cowork-todo-input"
          placeholder="Ny opgave…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void submit() }}
        />
      )}
      {todos.length === 0 && <div className="cowork-empty">Ingen opgaver</div>}
      {todos.map((t) => {
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            {editable
              ? <button type="button" className="todo-status-btn" aria-label="Skift status" onClick={() => void cycle(t)}><Icon size={15} /></button>
              : <Icon size={15} />}
            <span>{t.content}</span>
            {editable && (
              <button type="button" className="todo-del-btn" aria-label="Slet" onClick={() => void remove(t)}>
                <Trash2 size={13} />
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoPane.test.tsx`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/TodoPane.tsx apps/jarvis-desk/src/components/cowork/TodoPane.test.tsx
git commit -m "feat(desk): redigerbar TodoPane (opret/status/slet)"
```

---

## Task 5: Wire config+refresh i CoworkView + suite + deploy

**Files:**
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx`
- Modify: `apps/jarvis-desk/src/hooks/useCoworkData.ts` (kun hvis den ikke allerede eksponerer en refetch — se step 1)

- [ ] **Step 1: Find ud af om useCoworkData kan refetche**

Run: `grep -n "return {" apps/jarvis-desk/src/hooks/useCoworkData.ts`
Hvis retur-objektet IKKE har en `refresh`/`reload`-funktion: tilføj en. Hooket har allerede en intern fetch-funktion (poll'en kalder den) — eksportér den som `refresh`. Hvis den allerede har én, brug det navn i step 2.

- [ ] **Step 2: Giv TodoPane config + onChanged**

I `CoworkView.tsx`, hent `refresh` fra `useCoworkData` og send til TodoPane:

```tsx
  const { queue, plans, todos, channels, shareGuard, agents, resolve, resolveShare, refresh } = useCoworkData(config, isOwner)
```

```tsx
      <section className="cowork-pane">
        <div className="cowork-pane-head">Todo &amp; initiativer</div>
        <TodoPane todos={todos} config={isOwner ? config : undefined} onChanged={refresh} />
      </section>
```

(Hvis hooket ikke kan give en `refresh`, send `onChanged={() => {}}` — 6s-poll'en opdaterer alligevel. Men foretræk en ægte refresh.)

- [ ] **Step 3: Tilføj input/knap-styles**

I `apps/jarvis-desk/src/styles/app.css` (ved de øvrige `.cowork-todo`-regler):

```css
.cowork-todo-input { width: 100%; box-sizing: border-box; margin-bottom: 8px; padding: 6px 9px;
  background: var(--bg-2); border: 1px solid var(--line); border-radius: 7px; color: var(--fg-1); font-size: 12.5px; }
.cowork-todo { display: flex; align-items: center; gap: 6px; }
.todo-status-btn, .todo-del-btn { background: transparent; border: none; cursor: pointer;
  color: var(--fg-2); padding: 2px; display: inline-flex; }
.todo-del-btn { margin-left: auto; color: var(--fg-3); }
.todo-del-btn:hover { color: var(--danger, #e06c75); }
```

- [ ] **Step 4: Kør hele suiten + typecheck**

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: alle grønne, ingen type-fejl

- [ ] **Step 5: Commit + byg + deploy**

```bash
git add apps/jarvis-desk/src/views/CoworkView.tsx apps/jarvis-desk/src/hooks/useCoworkData.ts apps/jarvis-desk/src/styles/app.css
git commit -m "feat(desk): wire redigerbar TodoPane i cowork + refresh"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_*_amd64.deb
cd ../.. && git push target main && ssh 10.0.0.39 'sudo systemctl restart jarvis-api && sleep 3 && systemctl is-active jarvis-api'
```

---

## Self-Review

**1. Spec coverage (§3.1, afgrænset):** opret (T1/T2/T3/T4), rediger-status (T2/T4), slet (T2/T4), Jarvis+bruger samme liste (cowork-session + cross-session helpers). TTL/pause/expired eksplicit udskudt (Plan 2b) — begrundet. ✓
**2. Placeholder-scan:** ingen TBD; al kode konkret; step 1/step 2 i T5 har eksplicit fallback hvis hooket ikke kan refetche. ✓
**3. Type-konsistens:** `TodoItem{id,content,status}` uændret; `createCoworkTodo(config,content)`, `setCoworkTodoStatus(config,id,status)`, `deleteCoworkTodo(config,id)` ens i T3-impl, T3-test og T4-impl. `update_todo_status_anywhere`/`remove_todo_anywhere`/`add_cowork_todo`/`COWORK_SESSION` ens i T1 og T2. ✓
