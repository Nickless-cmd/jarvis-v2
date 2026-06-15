# Cowork Command Center — Plan 2b: Todo TTL + Pause

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps bruger checkbox (`- [ ]`).

**Goal:** Giv cowork-todos opt-in udløb (TTL) og pause — på en måde der IKKE roder Jarvis' agentiske arbejdshukommelse: pausede og udløbne todos er synlige i cowork-UI'et men skjult fra Jarvis' prompt.

**Architecture:** Beslutninger (Bjørn, 15. jun): (1) pause = skjult fra Jarvis' prompt til genoptaget; (2) TTL = opt-in pr. todo; (3) udløb = mærket 'expired', synlig i UI, skjult for Jarvis. For at undgå dual-truth (CLAUDE.md) **gemmer vi `expires_at` og udleder 'expired'** ved læsning — vi gemmer ikke en separat 'expired'-status der kan drive fra tidsstemplet. 'paused' er en ægte brugerhandling og gemmes. Jarvis' `todos_prompt_section` filtrerer paused+expired væk; cowork-feed'et viser dem (med udledt status).

**Tech Stack:** FastAPI + pytest (`/opt/conda/envs/ai`), React + vitest (`apps/jarvis-desk`).

---

## Datamodel-ændring

- `_VALID_STATUSES`: tilføj `"paused"` → `("pending", "in_progress", "completed", "paused")`. 'expired' er IKKE en gemt status.
- Todo-felt: valgfrit `expires_at` (ISO-streng eller fraværende = intet udløb).
- Udledt: `effective_status(todo, now)` returnerer `"expired"` hvis `expires_at <= now` og gemt status ∈ {pending, in_progress, paused}; ellers den gemte status.

## File Structure

**Backend:**
- Modify: `core/services/agent_todos.py` — 'paused' i `_VALID_STATUSES`; `effective_status()`; `set_todo_expiry_anywhere()`; bevar `expires_at` i `set_todos`; filtrér paused+expired i `todos_prompt_section`.
- Modify: `core/services/cowork_feed.py` — `_all_todos()` inkluderer `expires_at` + udledt status.
- Modify: `apps/api/jarvis_api/routes/cowork.py` — 'paused' i `_VALID_TODO_STATUSES`; nyt `POST /cowork/todos/{id}/expiry`.
- Test: `tests/test_agent_todos_ttl_pause.py`

**Frontend:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts` — `CoworkTodo.expires_at?`; `setCoworkTodoExpiry()`.
- Modify: `apps/jarvis-desk/src/components/cowork/TodoPane.tsx` — pause/genoptag-knap, TTL-vælger, paused/expired-rendering.
- Test: `apps/jarvis-desk/src/components/cowork/TodoPane.ttl.test.tsx`

---

## Task 1: Backend — effective_status, pause, expiry i agent_todos

**Files:**
- Modify: `core/services/agent_todos.py`
- Test: `tests/test_agent_todos_ttl_pause.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_todos_ttl_pause.py
import core.services.agent_todos as at


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(at, "_load_all", lambda: {k: list(v) for k, v in store.items()})
    monkeypatch.setattr(at, "_save_all", lambda data: store.update({k: list(v) for k, v in data.items()}))
    return store


def test_paused_is_valid_status(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("x")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    res = at.update_todo_status_anywhere(tid, "paused")
    assert res["status"] == "ok"
    assert at.list_todos(at.COWORK_SESSION)[0]["status"] == "paused"


def test_effective_status_expired_when_past():
    t = {"status": "pending", "expires_at": "2000-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "expired"


def test_effective_status_not_expired_when_future():
    t = {"status": "pending", "expires_at": "2099-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "pending"


def test_effective_status_completed_never_expires():
    t = {"status": "completed", "expires_at": "2000-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "completed"


def test_set_expiry_anywhere(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("x")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    at.set_todo_expiry_anywhere(tid, "2099-01-01T00:00:00+00:00")
    assert at.list_todos(at.COWORK_SESSION)[0]["expires_at"] == "2099-01-01T00:00:00+00:00"
    at.set_todo_expiry_anywhere(tid, None)
    assert at.list_todos(at.COWORK_SESSION)[0].get("expires_at") in (None, "")


def test_prompt_section_hides_paused_and_expired(monkeypatch):
    _reset(monkeypatch)
    at.add_todo("s", "synlig opgave")
    at.add_todo("s", "pauset opgave")
    at.add_todo("s", "udløbet opgave")
    items = at.list_todos("s")
    at.update_todo_status_anywhere(items[1]["id"], "paused")
    at.set_todo_expiry_anywhere(items[2]["id"], "2000-01-01T00:00:00+00:00")
    section = at.todos_prompt_section("s")
    assert "synlig opgave" in section
    assert "pauset opgave" not in section
    assert "udløbet opgave" not in section
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_todos_ttl_pause.py -v`
Expected: FAIL — `effective_status`/`set_todo_expiry_anywhere` mangler; 'paused' afvises.

- [ ] **Step 3: Write minimal implementation**

I `core/services/agent_todos.py`:

(a) Udvid statuses:
```python
_VALID_STATUSES = ("pending", "in_progress", "completed", "paused")
# Ikke-terminale statuser kan udløbe (paused tæller med — en pauset todo kan stadig løbe ud).
_EXPIRABLE_STATUSES = ("pending", "in_progress", "paused")
```

(b) Tilføj `effective_status` (efter `_session_key`):
```python
def effective_status(todo: dict[str, Any], now_iso: str) -> str:
    """Udledt status: 'expired' hvis expires_at er passeret og todo'en ikke er
    terminal. Vi GEMMER ikke 'expired' (undgår dual-truth med expires_at) —
    den udledes ved læsning."""
    stored = str(todo.get("status") or "pending")
    exp = str(todo.get("expires_at") or "")
    if exp and stored in _EXPIRABLE_STATUSES and exp <= now_iso:
        return "expired"
    return stored
```

(c) Bevar `expires_at` i `set_todos` — i append-blokken hvor cleaned-item bygges, tilføj feltet (efter `"plan_step_index"`-linjen):
```python
            "expires_at": raw.get("expires_at") or "",
```

(d) Tilføj `set_todo_expiry_anywhere` (efter `remove_todo_anywhere`):
```python
def set_todo_expiry_anywhere(todo_id: str, expires_at: str | None) -> dict[str, Any]:
    """Sæt/ryd udløbstidspunkt (ISO) på en todo uanset session. None = intet udløb."""
    sid = _find_session_for_todo(todo_id)
    if sid is None:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    data = _load_all()
    items = data.get(sid, [])
    for it in items:
        if str(it.get("id")) == str(todo_id):
            it["expires_at"] = expires_at or ""
            it["updated_at"] = datetime.now(UTC).isoformat()
            break
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "todo_id": todo_id, "expires_at": expires_at or ""}
```

(e) Filtrér paused+expired i `todos_prompt_section` — erstat løkken der bygger `lines`:
```python
    now_iso = datetime.now(UTC).isoformat()
    lines = []
    for it in sorted_items[:12]:
        eff = effective_status(it, now_iso)
        if eff in ("paused", "expired"):
            continue  # skjult fra Jarvis' arbejdshukommelse
        g = glyph.get(eff, "?")
        c = str(it.get("content", "")).strip()
        lines.append(f"{g} {c}")
    if not lines:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_todos_ttl_pause.py tests/test_agent_todos_cowork.py -v`
Expected: PASS (begge filer grønne — ingen regression)

- [ ] **Step 5: Commit**

```bash
git add core/services/agent_todos.py tests/test_agent_todos_ttl_pause.py
git commit -m "feat(todos): opt-in TTL (udledt 'expired') + pause; skjult fra Jarvis-prompt (§3.1)"
```

---

## Task 2: Backend — feed + expiry-endpoint

**Files:**
- Modify: `core/services/cowork_feed.py`
- Modify: `apps/api/jarvis_api/routes/cowork.py`
- Test: `tests/test_cowork_todo_routes.py` (udvid)

- [ ] **Step 1: Write the failing test (udvid eksisterende fil)**

Tilføj i `tests/test_cowork_todo_routes.py`:
```python
def test_set_expiry_owner(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    captured = {}
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "set_todo_expiry_anywhere",
                        lambda tid, exp: captured.update(tid=tid, exp=exp) or {"status": "ok"})
    res = asyncio.run(cw.cowork_set_todo_expiry("td-1", {"expires_at": "2099-01-01T00:00:00+00:00"}))
    assert res["status"] == "ok"
    assert captured["exp"] == "2099-01-01T00:00:00+00:00"


def test_pause_is_accepted_status(monkeypatch):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    import core.services.agent_todos as at
    monkeypatch.setattr(at, "update_todo_status_anywhere", lambda tid, s: {"status": "ok", "to": s})
    res = asyncio.run(cw.cowork_set_todo_status("td-1", {"status": "paused"}))
    assert res["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_todo_routes.py -v`
Expected: FAIL — `cowork_set_todo_expiry` mangler; 'paused' afvises af route-validering.

- [ ] **Step 3: Write minimal implementation**

(a) `apps/api/jarvis_api/routes/cowork.py` — udvid status-listen + nyt endpoint. Ret:
```python
_VALID_TODO_STATUSES = ("pending", "in_progress", "completed", "paused")
```
Tilføj efter `cowork_delete_todo`:
```python
@router.post("/todos/{todo_id}/expiry")
async def cowork_set_todo_expiry(todo_id: str, payload: dict = Body(default={})) -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    raw = (payload or {}).get("expires_at")
    expires_at = str(raw).strip() if raw else None
    from core.services.agent_todos import set_todo_expiry_anywhere
    return await asyncio.to_thread(set_todo_expiry_anywhere, todo_id, expires_at)
```

(b) `core/services/cowork_feed.py` — `_all_todos()` skal vise udledt status + expires_at. Erstat append-blokken:
```python
        from core.services.agent_todos import _load_all, effective_status
        from datetime import UTC, datetime
        now_iso = datetime.now(UTC).isoformat()
        out: list[dict[str, Any]] = []
        for _sid, items in (_load_all() or {}).items():
            for t in items:
                out.append({
                    "id": str(t.get("id") or ""),
                    "content": str(t.get("content") or ""),
                    "status": effective_status(t, now_iso),
                    "expires_at": str(t.get("expires_at") or ""),
                })
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_todo_routes.py -v && /opt/conda/envs/ai/bin/python -m compileall -q core/services/cowork_feed.py apps/api/jarvis_api/routes/cowork.py`
Expected: PASS (5 passed) + compile OK

- [ ] **Step 5: Commit**

```bash
git add core/services/cowork_feed.py apps/api/jarvis_api/routes/cowork.py tests/test_cowork_todo_routes.py
git commit -m "feat(cowork): expiry-endpoint + feed viser udledt status/expires_at + 'paused'"
```

---

## Task 3: Frontend — coworkApi expiry + type

**Files:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts`
- Test: `apps/jarvis-desk/src/lib/coworkApi.todos.test.ts` (udvid)

- [ ] **Step 1: Write the failing test (tilføj i eksisterende describe)**

```typescript
  it('setCoworkTodoExpiry POSTer expires_at', async () => {
    await setCoworkTodoExpiry(cfg, 'td-1', '2099-01-01T00:00:00+00:00')
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1/expiry', { method: 'POST', body: { expires_at: '2099-01-01T00:00:00+00:00' } })
  })
  it('setCoworkTodoExpiry med null rydder', async () => {
    await setCoworkTodoExpiry(cfg, 'td-1', null)
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/cowork/todos/td-1/expiry', { method: 'POST', body: { expires_at: null } })
  })
```
Tilføj `setCoworkTodoExpiry` til import-linjen i testen.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.todos.test.ts`
Expected: FAIL — eksport mangler

- [ ] **Step 3: Write minimal implementation**

I `apps/jarvis-desk/src/lib/coworkApi.ts`: opdatér `CoworkTodo`-interfacet (find `export interface CoworkTodo`) til at inkludere `expires_at?: string`, og tilføj nederst:
```typescript
export async function setCoworkTodoExpiry(config: ApiConfig, id: string, expiresAt: string | null): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}/expiry`, { method: 'POST', body: { expires_at: expiresAt } })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.todos.test.ts`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/lib/coworkApi.todos.test.ts
git commit -m "feat(desk): setCoworkTodoExpiry + CoworkTodo.expires_at"
```

---

## Task 4: Frontend — TodoPane pause + TTL

**Files:**
- Modify: `apps/jarvis-desk/src/components/cowork/TodoPane.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/TodoPane.ttl.test.tsx`

`TodoItem` får `expires_at?`. Hver todo (i editable-mode) får: pause/genoptag-knap (toggler mellem 'paused' og 'pending'), og en TTL-`<select>` (Ingen / 1 time / 1 dag / 1 uge). Udløbne todos (`status==='expired'`) vises mutede med en "udløbet"-label; pause-knappen skjules for dem.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/cowork/TodoPane.ttl.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const setCoworkTodoStatus = vi.fn().mockResolvedValue(undefined)
const setCoworkTodoExpiry = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  createCoworkTodo: vi.fn().mockResolvedValue(undefined),
  setCoworkTodoStatus: (...a: unknown[]) => setCoworkTodoStatus(...a),
  deleteCoworkTodo: vi.fn().mockResolvedValue(undefined),
  setCoworkTodoExpiry: (...a: unknown[]) => setCoworkTodoExpiry(...a),
}))

import { TodoPane } from './TodoPane'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('TodoPane TTL + pause', () => {
  beforeEach(() => { setCoworkTodoStatus.mockClear(); setCoworkTodoExpiry.mockClear() })

  it('pause-knap sætter status=paused', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /pause/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'paused'))
  })

  it('genoptag-knap på pauset todo sætter status=pending', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'paused' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /genoptag/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'pending'))
  })

  it('TTL-vælger "1 dag" sætter et expires_at', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.change(screen.getByLabelText(/udløb/i), { target: { value: 'day' } })
    await waitFor(() => expect(setCoworkTodoExpiry).toHaveBeenCalled())
    const [, id, iso] = setCoworkTodoExpiry.mock.calls[0]
    expect(id).toBe('td-1')
    expect(typeof iso).toBe('string')
  })

  it('TTL-vælger "Ingen" rydder expires_at', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending', expires_at: '2099-01-01T00:00:00+00:00' }]} config={cfg} />)
    fireEvent.change(screen.getByLabelText(/udløb/i), { target: { value: 'none' } })
    await waitFor(() => expect(setCoworkTodoExpiry).toHaveBeenCalledWith(cfg, 'td-1', null))
  })

  it('udløbet todo vises mutet med "udløbet"', () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'expired' }]} config={cfg} />)
    expect(screen.getByText(/udløbet/i)).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoPane.ttl.test.tsx`
Expected: FAIL — pause-knap/TTL-vælger findes ikke

- [ ] **Step 3: Write minimal implementation**

Erstat `apps/jarvis-desk/src/components/cowork/TodoPane.tsx`:
```tsx
import { useState } from 'react'
import { CircleCheck, CircleDot, Circle, Trash2, Pause, Play } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo, setCoworkTodoExpiry } from '../../lib/coworkApi'

export interface TodoItem { id: string; content: string; status: string; expires_at?: string }

const NEXT: Record<string, string> = { pending: 'in_progress', in_progress: 'completed', completed: 'pending' }
const TTL_MS: Record<string, number | null> = { none: null, hour: 3600e3, day: 86400e3, week: 604800e3 }

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
    await createCoworkTodo(config, c); after()
  }
  const cycle = async (t: TodoItem) => {
    if (!config || t.status === 'expired') return
    await setCoworkTodoStatus(config, t.id, NEXT[t.status] || 'pending'); after()
  }
  const togglePause = async (t: TodoItem) => {
    if (!config) return
    await setCoworkTodoStatus(config, t.id, t.status === 'paused' ? 'pending' : 'paused'); after()
  }
  const remove = async (t: TodoItem) => {
    if (!config) return
    await deleteCoworkTodo(config, t.id); after()
  }
  const setTtl = async (t: TodoItem, key: string) => {
    if (!config) return
    const ms = TTL_MS[key]
    const iso = ms == null ? null : new Date(Date.now() + ms).toISOString()
    await setCoworkTodoExpiry(config, t.id, iso); after()
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
        const expired = t.status === 'expired'
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            {editable && !expired
              ? <button type="button" className="todo-status-btn" aria-label="Skift status" onClick={() => void cycle(t)}><Icon size={15} /></button>
              : <Icon size={15} />}
            <span>{t.content}</span>
            {expired && <span className="todo-expired-tag">udløbet</span>}
            {editable && !expired && (
              <>
                <button type="button" className="todo-pause-btn"
                  aria-label={t.status === 'paused' ? 'Genoptag' : 'Pause'} onClick={() => void togglePause(t)}>
                  {t.status === 'paused' ? <Play size={13} /> : <Pause size={13} />}
                </button>
                <select className="todo-ttl" aria-label="Udløb"
                  value={t.expires_at ? 'custom' : 'none'} onChange={(e) => void setTtl(t, e.target.value)}>
                  <option value="none">Intet udløb</option>
                  {t.expires_at && <option value="custom">Udløber…</option>}
                  <option value="hour">1 time</option>
                  <option value="day">1 dag</option>
                  <option value="week">1 uge</option>
                </select>
              </>
            )}
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

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoPane.ttl.test.tsx src/components/cowork/TodoPane.test.tsx`
Expected: PASS (begge filer — ingen regression på den eksisterende TodoPane-test)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/TodoPane.tsx apps/jarvis-desk/src/components/cowork/TodoPane.ttl.test.tsx
git commit -m "feat(desk): TodoPane pause/genoptag + opt-in TTL-vælger + expired-visning"
```

---

## Task 5: Styles + suite + build + deploy

- [ ] **Step 1: Styles** — i `apps/jarvis-desk/src/styles/app.css` ved de øvrige `.todo-*`-regler:
```css
.todo-pause-btn { background: transparent; border: none; cursor: pointer; color: var(--fg-2); padding: 2px; display: inline-flex; }
.todo-ttl { background: var(--bg-2); border: 1px solid var(--line); border-radius: 6px; color: var(--fg-2); font-size: 11px; padding: 1px 4px; }
.todo-expired-tag { font-size: 10.5px; color: var(--fg-3); background: var(--bg-3); border-radius: 8px; padding: 1px 6px; }
.cowork-todo.status-paused { opacity: 0.6; }
.cowork-todo.status-expired { opacity: 0.45; }
```

- [ ] **Step 2: Hele suiten + typecheck**

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: alle grønne, ingen type-fejl

- [ ] **Step 3: Commit + byg + deploy**

```bash
git add apps/jarvis-desk/src/styles/app.css
git commit -m "style(desk): paused/expired/TTL todo-styling"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_*_amd64.deb
cd ../.. && git push target main && ssh 10.0.0.39 'sudo systemctl restart jarvis-api && sleep 3 && systemctl is-active jarvis-api'
```

---

## Self-Review

**1. Spec-coverage (§3.1 TTL+pause):** opt-in TTL (T1 `set_todo_expiry_anywhere` + T4 vælger), udledt 'expired' (T1 `effective_status`), pause (T1 'paused'-status + T4 knap), skjult fra Jarvis (T1 `todos_prompt_section`-filter), synlig i UI (T2 feed + T4 rendering). ✓
**2. Placeholder-scan:** ingen TBD; al kode konkret. ✓
**3. Type-konsistens:** `effective_status(todo, now_iso)`, `set_todo_expiry_anywhere(todo_id, expires_at|None)` ens i T1/T2. `setCoworkTodoExpiry(config,id,iso|null)` ens i T3/T4. `_VALID_STATUSES`/`_VALID_TODO_STATUSES` begge inkluderer 'paused'; 'expired' er udledt, ikke gemt — konsistent overalt. `CoworkTodo.expires_at?`/`TodoItem.expires_at?` matcher. ✓
**4. No dual-truth:** 'expired' gemmes aldrig — kun `expires_at`; status udledes. ✓
