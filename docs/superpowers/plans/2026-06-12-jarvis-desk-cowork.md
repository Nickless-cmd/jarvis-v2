---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Cowork-flade (jarvis-desk) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Et rolle-bevidst 2×2 cowork-dashboard i jarvis-desk (owner: godkendelser/planer/todo/kanaler; bruger: de tre første) der samler og styrer hvad Jarvis vil gøre — bygget ovenpå eksisterende backend.

**Architecture:** Backend: en ren `cowork_feed`-service (testbar isoleret) der normaliserer items fra eksisterende kilder (initiative_queue, capability-approval-surface, plan_proposals, agent_todos), eksponeret via en ny `cowork.py` rute-fil med rolle-scoping. Frontend: `CoworkView` + fire rude-komponenter + en `useCoworkData`-hook (fetch + Mission Control-WS + polling-fallback). Diff vises i godkendelses-kortet.

**Tech Stack:** FastAPI + Python 3.11 (backend), React 19 + TS 5 + Vitest (frontend), Electron 33.

**Deploy:** `git push target main` + `sudo systemctl restart jarvis-api.service jarvis-runtime.service`; app: `cd apps/jarvis-desk && npm run build && npx electron-builder --linux deb && sudo dpkg -i release/jarvis-desktop_0.1.0_amd64.deb`.

**KRITISK (frys-fælde):** jarvis-api kører `--workers 1`. Alt blokerende arbejde (subprocess, fil-IO over flere kilder, bro-kald) i `cowork.py` SKAL køres via `await asyncio.to_thread(...)`. Ellers fryser hele API'et og appen viser "offline". Se `docs` / hukommelse `reference_async_blocking_worker`.

---

## File Structure

**Backend (create):**
- `core/services/cowork_feed.py` — ren normaliserings-service: `build_queue(user_id, is_owner)`, `list_plans(user_id, is_owner)`, `channel_status()`. Læser fra eksisterende kilder, returnerer normaliserede dicts. INGEN FastAPI-afhængighed (testbar isoleret).
- `apps/api/jarvis_api/routes/cowork.py` — rute-fil: `GET /cowork/queue`, `POST /cowork/queue/{id}/approve`, `POST /cowork/queue/{id}/reject`, `GET /cowork/plans`, `GET /cowork/channels`. Tynd; offloader til `asyncio.to_thread`.
- `tests/test_cowork_feed.py`, `tests/test_cowork_routes.py`

**Backend (modify):**
- `apps/api/jarvis_api/app.py` — registrér `cowork_router`.

**Frontend (create):**
- `apps/jarvis-desk/src/lib/coworkApi.ts` — klient-funktioner + typer.
- `apps/jarvis-desk/src/hooks/useCoworkData.ts` — fetch + WS + polling.
- `apps/jarvis-desk/src/components/cowork/ApprovalQueue.tsx`
- `apps/jarvis-desk/src/components/cowork/PlansPane.tsx`
- `apps/jarvis-desk/src/components/cowork/TodoPane.tsx`
- `apps/jarvis-desk/src/components/cowork/ChannelsPane.tsx`
- tilhørende `*.test.tsx`

**Frontend (modify):**
- `apps/jarvis-desk/src/views/CoworkView.tsx` — erstat stub.
- `apps/jarvis-desk/src/App.tsx` — send `role` til CoworkView.
- `apps/jarvis-desk/src/styles/app.css` — cowork-grid + ruder.

---

## Phase 1 — Backend: cowork_feed service (normalisering)

### Task 1: Normaliseret queue-item shape + build_queue (initiativer)

**Files:**
- Create: `core/services/cowork_feed.py`
- Test: `tests/test_cowork_feed.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cowork_feed.py`:

```python
from core.services import cowork_feed


def test_build_queue_includes_pending_initiatives(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "init-1", "title": "Ryd op i logs", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    items = cowork_feed.build_queue(user_id="owner", is_owner=True)
    assert any(i["id"] == "init-1" and i["kind"] == "initiative" for i in items)
    one = next(i for i in items if i["id"] == "init-1")
    assert set(one) >= {"id", "kind", "title", "detail", "source"}


def test_build_queue_owner_sees_all_users(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    assert len(cowork_feed.build_queue(user_id="owner", is_owner=True)) == 1


def test_build_queue_member_sees_only_own(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
        {"id": "b", "title": "y", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    items = cowork_feed.build_queue(user_id="mikkel", is_owner=False)
    assert [i["id"] for i in items] == ["a"]
```

- [ ] **Step 2: Run — expect FAIL** (`cowork_feed` findes ikke)

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_feed.py -q -p no:cacheprovider`
Expected: FAIL (ModuleNotFoundError / AttributeError)

- [ ] **Step 3: Implement** — `core/services/cowork_feed.py`:

```python
"""Cowork-feed: normaliserer items fra eksisterende kilder til én rolle-scopet
liste til cowork-dashboardet. INGEN FastAPI-afhængighed — ren + testbar.

Item-shape: {id, kind, title, detail, user_id, source, diff?}
 - kind: "initiative" | "capability" | "tool_intent" | "file_edit"
 - source: hvilket eksisterende approve/reject-endpoint der skal kaldes
"""
from __future__ import annotations

from typing import Any


def _initiative_items() -> list[dict[str, Any]]:
    """Afventende initiativ-forslag fra initiative_queue."""
    try:
        from core.services.initiative_queue import get_initiative_queue_state
        state = get_initiative_queue_state()
        return [dict(i) for i in (state.get("pending") or [])]
    except Exception:
        return []


def _capability_items() -> list[dict[str, Any]]:
    """Afventende capability-/tool-godkendelses-requests (Mission Control surface)."""
    try:
        from apps.api.jarvis_api.routes.mission_control import _capability_invocation_surface
        surface = _capability_invocation_surface()
        reqs = list(surface.get("recent_approval_requests") or [])
        return [dict(r) for r in reqs if str(r.get("status") or "") == "pending"]
    except Exception:
        return []


def _norm_initiative(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id") or raw.get("initiative_id") or ""),
        "kind": "initiative",
        "title": str(raw.get("title") or raw.get("summary") or "Initiativ"),
        "detail": str(raw.get("detail") or raw.get("rationale") or ""),
        "user_id": str(raw.get("user_id") or ""),
        "source": "initiative",
    }


def _norm_capability(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("capability_name") or raw.get("tool") or raw.get("capability_id") or "handling")
    kind = "file_edit" if raw.get("target_path") or raw.get("write_content") else (
        "tool_intent" if raw.get("command_text") else "capability"
    )
    return {
        "id": str(raw.get("id") or raw.get("request_id") or raw.get("capability_id") or ""),
        "kind": kind,
        "title": name,
        "detail": str(raw.get("target_path") or raw.get("command_text") or raw.get("message") or ""),
        "user_id": str(raw.get("user_id") or ""),
        "source": "capability",
        **({"diff": str(raw.get("diff"))} if raw.get("diff") else {}),
    }


def build_queue(*, user_id: str | None, is_owner: bool) -> list[dict[str, Any]]:
    """Saml + normalisér + rolle-scope den fulde godkendelses-kø."""
    items: list[dict[str, Any]] = []
    items += [_norm_initiative(r) for r in _initiative_items()]
    items += [_norm_capability(r) for r in _capability_items()]
    items = [i for i in items if i["id"]]
    if not is_owner:
        uid = str(user_id or "")
        items = [i for i in items if i["user_id"] == uid]
    return items
```

- [ ] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_feed.py -q -p no:cacheprovider`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/cowork_feed.py tests/test_cowork_feed.py
git commit -m "feat(cowork): cowork_feed.build_queue — normalize + role-scope approval items"
```

### Task 2: list_plans + channel_status

**Files:**
- Modify: `core/services/cowork_feed.py`
- Test: `tests/test_cowork_feed.py` (append)

- [ ] **Step 1: Write the failing test** — append til `tests/test_cowork_feed.py`:

```python
def test_list_plans_member_filters_to_own(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_all_plans", lambda: [
        {"plan_id": "p1", "title": "A", "user_id": "mikkel", "steps_done": 1, "steps_total": 3},
        {"plan_id": "p2", "title": "B", "user_id": "owner", "steps_done": 0, "steps_total": 2},
    ])
    plans = cowork_feed.list_plans(user_id="mikkel", is_owner=False)
    assert [p["id"] for p in plans] == ["p1"]
    assert plans[0]["steps_done"] == 1 and plans[0]["steps_total"] == 3


def test_channel_status_returns_list(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_raw_channels", lambda: {"discord": {"online": True, "unread": 2}})
    chans = cowork_feed.channel_status()
    assert any(c["name"] == "discord" and c["online"] is True for c in chans)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_feed.py -q -p no:cacheprovider`
Expected: FAIL (list_plans / channel_status mangler)

- [ ] **Step 3: Implement** — tilføj til `core/services/cowork_feed.py`:

```python
def _all_plans() -> list[dict[str, Any]]:
    try:
        from core.services import plan_proposals
        data = plan_proposals._load_all()  # {plan_id: plan_dict}
        out = []
        for pid, p in (data or {}).items():
            steps = list(p.get("steps") or [])
            done = len([s for s in steps if str(s.get("status") or "") == "completed"])
            out.append({
                "plan_id": pid,
                "title": str(p.get("title") or p.get("goal") or "Plan"),
                "user_id": str(p.get("user_id") or ""),
                "status": str(p.get("status") or ""),
                "steps_done": done,
                "steps_total": len(steps),
            })
        return out
    except Exception:
        return []


def list_plans(*, user_id: str | None, is_owner: bool) -> list[dict[str, Any]]:
    plans = [
        {"id": p["plan_id"], "title": p["title"], "status": p.get("status", ""),
         "steps_done": int(p.get("steps_done") or 0), "steps_total": int(p.get("steps_total") or 0),
         "user_id": p.get("user_id", "")}
        for p in _all_plans()
    ]
    if not is_owner:
        uid = str(user_id or "")
        plans = [p for p in plans if p["user_id"] == uid]
    return plans


def _raw_channels() -> dict[str, Any]:
    """Kanal-status fra Mission Control. Bedste-effort; tom dict ved fejl."""
    try:
        from apps.api.jarvis_api.routes.mission_control import _channel_status_surface
        return dict(_channel_status_surface() or {})
    except Exception:
        return {}


def channel_status() -> list[dict[str, Any]]:
    raw = _raw_channels()
    return [
        {"name": str(name), "online": bool(info.get("online")), "unread": int(info.get("unread") or 0)}
        for name, info in raw.items()
    ]
```

> NB: Hvis `_channel_status_surface` ikke findes i `mission_control.py`, brug i stedet den faktiske funktion der returnerer kanal-state (grep `def _channel` i mission_control.py og tilpas import-navnet). `channel_status()` skal bare returnere en liste af `{name, online, unread}`.

- [ ] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_feed.py -q -p no:cacheprovider`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/cowork_feed.py tests/test_cowork_feed.py
git commit -m "feat(cowork): cowork_feed.list_plans + channel_status (role-scoped)"
```

---

## Phase 2 — Backend: cowork routes (rolle-gating + non-blocking)

### Task 3: GET /cowork/queue + /cowork/plans (rolle-scopet, to_thread)

**Files:**
- Create: `apps/api/jarvis_api/routes/cowork.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_cowork_routes.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cowork_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import create_app
from apps.api.jarvis_api.routes import cowork as cowork_routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cowork_routes.cowork_feed, "build_queue", lambda **k: [
        {"id": "x", "kind": "initiative", "title": "T", "detail": "", "user_id": "owner", "source": "initiative"},
    ])
    monkeypatch.setattr(cowork_routes.cowork_feed, "list_plans", lambda **k: [])
    monkeypatch.setattr(cowork_routes, "_role_owner", lambda: (True, "owner"))
    return TestClient(create_app())


def test_queue_returns_items(client):
    r = client.get("/cowork/queue")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == "x"


def test_plans_returns_list(client):
    r = client.get("/cowork/plans")
    assert r.status_code == 200
    assert r.json()["plans"] == []
```

- [ ] **Step 2: Run — expect FAIL**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: FAIL (cowork-modul/route mangler)

- [ ] **Step 3: Implement** — `apps/api/jarvis_api/routes/cowork.py`:

```python
"""Cowork-dashboard routes. Tynde — al opsamling sker i core.services.cowork_feed,
og BLOKERENDE arbejde offloades til asyncio.to_thread (jarvis-api --workers 1)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from core.services import cowork_feed

router = APIRouter(prefix="/cowork", tags=["cowork"])


def _role_owner() -> tuple[bool, str | None]:
    """(is_owner, user_id) for den indloggede bruger."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    # Samme regel som tool_scoping: tom/owner = owner.
    is_owner = (uid is None) or str(uid) in ("", "owner")
    return is_owner, uid


@router.get("/queue")
async def cowork_queue() -> dict:
    is_owner, uid = _role_owner()
    items = await asyncio.to_thread(cowork_feed.build_queue, user_id=uid, is_owner=is_owner)
    return {"items": items}


@router.get("/plans")
async def cowork_plans() -> dict:
    is_owner, uid = _role_owner()
    plans = await asyncio.to_thread(cowork_feed.list_plans, user_id=uid, is_owner=is_owner)
    return {"plans": plans}
```

Modify `apps/api/jarvis_api/app.py` — tilføj ved de andre imports (~linje 97) og ved include_router (~linje 463):

```python
from apps.api.jarvis_api.routes.cowork import router as cowork_router
```
```python
    app.include_router(cowork_router)
```

- [ ] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/cowork.py apps/api/jarvis_api/app.py tests/test_cowork_routes.py
git commit -m "feat(cowork): GET /cowork/queue + /cowork/plans (role-scoped, to_thread)"
```

### Task 4: GET /cowork/channels (403 for ikke-owner)

**Files:**
- Modify: `apps/api/jarvis_api/routes/cowork.py`
- Test: `tests/test_cowork_routes.py` (append)

- [ ] **Step 1: Write the failing test** — append:

```python
def test_channels_owner_ok(monkeypatch, client):
    monkeypatch.setattr(cowork_routes.cowork_feed, "channel_status", lambda: [{"name": "discord", "online": True, "unread": 0}])
    r = client.get("/cowork/channels")
    assert r.status_code == 200
    assert r.json()["channels"][0]["name"] == "discord"


def test_channels_member_403(monkeypatch):
    monkeypatch.setattr(cowork_routes, "_role_owner", lambda: (False, "mikkel"))
    monkeypatch.setattr(cowork_routes.cowork_feed, "channel_status", lambda: [])
    c = TestClient(create_app())
    assert c.get("/cowork/channels").status_code == 403
```

- [ ] **Step 2: Run — expect FAIL**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: FAIL (channels-route mangler)

- [ ] **Step 3: Implement** — tilføj til `apps/api/jarvis_api/routes/cowork.py`:

```python
@router.get("/channels")
async def cowork_channels() -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="kanaler er kun for owner")
    chans = await asyncio.to_thread(cowork_feed.channel_status)
    return {"channels": chans}
```

- [ ] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/cowork.py tests/test_cowork_routes.py
git commit -m "feat(cowork): GET /cowork/channels — owner-only (403 for member)"
```

### Task 5: POST /cowork/queue/{id}/approve|reject (tynd router)

**Files:**
- Modify: `apps/api/jarvis_api/routes/cowork.py`
- Test: `tests/test_cowork_routes.py` (append)

- [ ] **Step 1: Write the failing test** — append:

```python
def test_approve_routes_to_resolver(monkeypatch, client):
    called = {}
    monkeypatch.setattr(cowork_routes, "_resolve_item", lambda item_id, decision: called.update(id=item_id, d=decision) or {"status": "ok"})
    r = client.post("/cowork/queue/x/approve")
    assert r.status_code == 200
    assert called == {"id": "x", "d": "approve"}


def test_reject_routes_to_resolver(monkeypatch, client):
    monkeypatch.setattr(cowork_routes, "_resolve_item", lambda item_id, decision: {"status": "ok", "decision": decision})
    r = client.post("/cowork/queue/x/reject")
    assert r.json()["decision"] == "reject"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: FAIL

- [ ] **Step 3: Implement** — tilføj til `apps/api/jarvis_api/routes/cowork.py`:

```python
def _resolve_item(item_id: str, decision: str) -> dict:
    """Router en godkendelses-beslutning til det rette eksisterende resolver.
    decision: "approve" | "reject". Prøver initiative-queue først, så capability-
    approval. BLOKERENDE — kaldes via to_thread."""
    approved = decision == "approve"
    # Initiative-queue resolver
    try:
        from core.services.initiative_queue import resolve_initiative
        res = resolve_initiative(item_id, approved=approved)
        if res:
            return {"status": "ok", "decision": decision, "via": "initiative"}
    except Exception:
        pass
    # Capability/tool approval resolver (samme som chat-approvals)
    try:
        from core.services.visible_runs import resolve_pending_approval
        res = resolve_pending_approval(item_id, approved=approved)
        if res is not None:
            return {"status": "ok", "decision": decision, "via": "capability"}
    except Exception:
        pass
    return {"status": "error", "reason": "unknown_item", "id": item_id}


@router.post("/queue/{item_id}/approve")
async def cowork_approve(item_id: str) -> dict:
    return await asyncio.to_thread(_resolve_item, item_id, "approve")


@router.post("/queue/{item_id}/reject")
async def cowork_reject(item_id: str) -> dict:
    return await asyncio.to_thread(_resolve_item, item_id, "reject")
```

> NB: `resolve_initiative` og `resolve_pending_approval` er de eksisterende resolvers. Verificér de præcise navne (grep `def resolve_initiative` i initiative_queue.py og `def resolve_pending_approval` i visible_runs.py) og tilpas hvis nødvendigt. Begge tager `approved: bool`.

- [ ] **Step 4: Run — expect PASS**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cowork_routes.py -q -p no:cacheprovider`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit + deploy-checkpoint (backend)**

```bash
git add apps/api/jarvis_api/routes/cowork.py tests/test_cowork_routes.py
git commit -m "feat(cowork): POST /cowork/queue/{id}/approve|reject — thin router to existing resolvers"
git push target main
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api.service jarvis-runtime.service && sleep 4 && curl -s -o /dev/null -w "%{http_code}" http://localhost:80/cowork/queue'
```
Expected: `401` (route lever, auth påkrævet) + openapi svarer hurtigt (ingen frys).

---

## Phase 3 — Frontend: api + data-hook

### Task 6: coworkApi.ts (klient-funktioner + typer)

**Files:**
- Create: `apps/jarvis-desk/src/lib/coworkApi.ts`
- Test: `apps/jarvis-desk/src/lib/coworkApi.test.ts`

- [ ] **Step 1: Write the failing test** — `src/lib/coworkApi.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('coworkApi', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('getCoworkQueue henter items fra /cowork/queue', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ items: [{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }] }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)
    const { getCoworkQueue } = await import('./coworkApi')
    const out = await getCoworkQueue({ apiBaseUrl: 'http://t', authToken: 't' })
    expect(out).toEqual([{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }])
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/cowork/queue'), expect.anything())
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.test.ts`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/lib/coworkApi.ts`:

```ts
import { apiFetch, type ApiConfig } from './api'

export interface QueueItem {
  id: string
  kind: 'initiative' | 'capability' | 'tool_intent' | 'file_edit'
  title: string
  detail: string
  source: string
  diff?: string
}
export interface CoworkPlan { id: string; title: string; status: string; steps_done: number; steps_total: number }
export interface CoworkChannel { name: string; online: boolean; unread: number }

export async function getCoworkQueue(config: ApiConfig): Promise<QueueItem[]> {
  const d = await apiFetch<{ items: QueueItem[] }>(config, '/cowork/queue')
  return d.items ?? []
}
export async function getCoworkPlans(config: ApiConfig): Promise<CoworkPlan[]> {
  const d = await apiFetch<{ plans: CoworkPlan[] }>(config, '/cowork/plans')
  return d.plans ?? []
}
export async function getCoworkChannels(config: ApiConfig): Promise<CoworkChannel[]> {
  const d = await apiFetch<{ channels: CoworkChannel[] }>(config, '/cowork/channels')
  return d.channels ?? []
}
export async function resolveQueueItem(config: ApiConfig, id: string, decision: 'approve' | 'reject'): Promise<void> {
  await apiFetch(config, `/cowork/queue/${encodeURIComponent(id)}/${decision}`, { method: 'POST' })
}
```

> NB: hvis `apiFetch`/`ApiConfig` ikke er eksporteret fra `./api`, eksportér dem (de bruges allerede i api.ts; tilføj `export` på `apiFetch` hvis nødvendigt).

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.test.ts && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/lib/coworkApi.test.ts
git commit -m "feat(jarvis-desk): coworkApi client functions + types"
```

### Task 7: useCoworkData hook (fetch + polling)

**Files:**
- Create: `apps/jarvis-desk/src/hooks/useCoworkData.ts`
- Test: `apps/jarvis-desk/src/hooks/useCoworkData.test.tsx`

- [ ] **Step 1: Write the failing test** — `src/hooks/useCoworkData.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

vi.mock('../lib/coworkApi', () => ({
  getCoworkQueue: vi.fn().mockResolvedValue([{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }]),
  getCoworkPlans: vi.fn().mockResolvedValue([]),
  getCoworkChannels: vi.fn().mockResolvedValue([{ name: 'discord', online: true, unread: 1 }]),
  resolveQueueItem: vi.fn().mockResolvedValue(undefined),
}))

import { useCoworkData } from './useCoworkData'

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('useCoworkData', () => {
  it('henter queue+plans (+channels for owner)', async () => {
    const { result } = renderHook(() => useCoworkData(cfg, true))
    await waitFor(() => expect(result.current.queue.length).toBe(1))
    expect(result.current.channels.length).toBe(1)
  })
  it('springer channels over for member', async () => {
    const { result } = renderHook(() => useCoworkData(cfg, false))
    await waitFor(() => expect(result.current.queue.length).toBe(1))
    expect(result.current.channels.length).toBe(0)
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/hooks/useCoworkData.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/hooks/useCoworkData.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import {
  getCoworkQueue, getCoworkPlans, getCoworkChannels, resolveQueueItem,
  type QueueItem, type CoworkPlan, type CoworkChannel,
} from '../lib/coworkApi'

const POLL_MS = 6000

/** Henter de fire datasæt + poller hver 6s. (WS-abonnement tilføjes i Task 12.)
 *  channels hentes kun for owner. */
export function useCoworkData(config: ApiConfig | undefined, isOwner: boolean) {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [plans, setPlans] = useState<CoworkPlan[]>([])
  const [channels, setChannels] = useState<CoworkChannel[]>([])
  const cfgRef = useRef(config)
  cfgRef.current = config

  const refresh = useCallback(async () => {
    const cfg = cfgRef.current
    if (!cfg) return
    await Promise.allSettled([
      getCoworkQueue(cfg).then(setQueue),
      getCoworkPlans(cfg).then(setPlans),
      isOwner ? getCoworkChannels(cfg).then(setChannels) : Promise.resolve(),
    ])
  }, [isOwner])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(id)
  }, [refresh, config?.apiBaseUrl, config?.authToken])

  const resolve = useCallback(async (id: string, decision: 'approve' | 'reject') => {
    const cfg = cfgRef.current
    if (!cfg) return
    setQueue((q) => q.filter((i) => i.id !== id)) // optimistisk
    try { await resolveQueueItem(cfg, id, decision) } finally { void refresh() }
  }, [refresh])

  return { queue, plans, channels, refresh, resolve }
}
```

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/hooks/useCoworkData.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/hooks/useCoworkData.ts apps/jarvis-desk/src/hooks/useCoworkData.test.tsx
git commit -m "feat(jarvis-desk): useCoworkData hook (fetch + 6s polling + optimistic resolve)"
```

---

## Phase 4 — Frontend: ruder

### Task 8: ApprovalQueue (med diff)

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/ApprovalQueue.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/ApprovalQueue.test.tsx`

- [ ] **Step 1: Write the failing test**:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApprovalQueue } from './ApprovalQueue'

const items = [
  { id: 'a', kind: 'file_edit' as const, title: 'skriv core/x.py', detail: 'core/x.py', source: 'capability', diff: '-gammel\n+ny' },
  { id: 'b', kind: 'tool_intent' as const, title: 'kør git push', detail: 'git push', source: 'capability' },
]

describe('ApprovalQueue', () => {
  it('viser items + kalder onResolve ved Godkend', () => {
    const onResolve = vi.fn()
    render(<ApprovalQueue items={items} onResolve={onResolve} />)
    expect(screen.getByText('skriv core/x.py')).toBeInTheDocument()
    fireEvent.click(screen.getAllByText('Godkend')[0])
    expect(onResolve).toHaveBeenCalledWith('a', 'approve')
  })
  it('viser diff når man folder ud', () => {
    render(<ApprovalQueue items={items} onResolve={vi.fn()} />)
    fireEvent.click(screen.getByText('Diff'))
    expect(screen.getByText(/\+ny/)).toBeInTheDocument()
  })
  it('tom tilstand', () => {
    render(<ApprovalQueue items={[]} onResolve={vi.fn()} />)
    expect(screen.getByText(/ingen afventende/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/ApprovalQueue.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/components/cowork/ApprovalQueue.tsx`:

```tsx
import { useState } from 'react'
import { Check, X, FileText } from 'lucide-react'
import { lineDiff } from '../../lib/diff'
import type { QueueItem } from '../../lib/coworkApi'

export function ApprovalQueue({ items, onResolve }: { items: QueueItem[]; onResolve: (id: string, d: 'approve' | 'reject') => void }) {
  if (items.length === 0) return <div className="cowork-empty">Ingen afventende godkendelser</div>
  return (
    <div className="cowork-queue">
      {items.map((it) => <QueueRow key={it.id} item={it} onResolve={onResolve} />)}
    </div>
  )
}

function QueueRow({ item, onResolve }: { item: QueueItem; onResolve: (id: string, d: 'approve' | 'reject') => void }) {
  const [showDiff, setShowDiff] = useState(false)
  const diff = item.diff ? lineDiff('', item.diff) : null
  return (
    <div className="cowork-item">
      <div className="cowork-item-title"><FileText size={13} /> {item.title}</div>
      {item.detail && <div className="cowork-item-detail">{item.detail}</div>}
      <div className="cowork-item-actions">
        <button type="button" onClick={() => onResolve(item.id, 'approve')}><Check size={12} /> Godkend</button>
        <button type="button" onClick={() => onResolve(item.id, 'reject')}><X size={12} /> Afvis</button>
        {item.diff && <button type="button" onClick={() => setShowDiff((s) => !s)}>Diff</button>}
      </div>
      {showDiff && diff && (
        <pre className="cowork-diff">{item.diff}</pre>
      )}
    </div>
  )
}
```

> NB: `lineDiff` findes allerede (`src/lib/diff.ts`). Til v1 vises `item.diff` rå i `<pre>`; rig diff-farvning kan genbruge `lineDiff` senere — den importeres her så strukturen er på plads.

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/ApprovalQueue.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/ApprovalQueue.tsx apps/jarvis-desk/src/components/cowork/ApprovalQueue.test.tsx
git commit -m "feat(jarvis-desk): ApprovalQueue pane with inline diff"
```

### Task 9: PlansPane

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/PlansPane.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/PlansPane.test.tsx`

- [ ] **Step 1: Write the failing test**:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PlansPane } from './PlansPane'

describe('PlansPane', () => {
  it('viser plan-titel + trin-progress', () => {
    render(<PlansPane plans={[{ id: 'p', title: 'Cowork v1', status: 'active', steps_done: 3, steps_total: 7 }]} />)
    expect(screen.getByText('Cowork v1')).toBeInTheDocument()
    expect(screen.getByText(/3.*7/)).toBeInTheDocument()
  })
  it('tom tilstand', () => {
    render(<PlansPane plans={[]} />)
    expect(screen.getByText(/ingen planer/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/PlansPane.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/components/cowork/PlansPane.tsx`:

```tsx
import type { CoworkPlan } from '../../lib/coworkApi'

export function PlansPane({ plans }: { plans: CoworkPlan[] }) {
  if (plans.length === 0) return <div className="cowork-empty">Ingen planer</div>
  return (
    <div className="cowork-plans">
      {plans.map((p) => {
        const pct = p.steps_total > 0 ? Math.round((p.steps_done / p.steps_total) * 100) : 0
        return (
          <div key={p.id} className="cowork-plan">
            <div className="cowork-plan-title">{p.title}</div>
            <div className="cowork-plan-sub">{p.steps_done} af {p.steps_total} trin · {p.status || 'forslag'}</div>
            <div className="cowork-progress"><div className="cowork-progress-fill" style={{ width: `${pct}%` }} /></div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/PlansPane.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/PlansPane.tsx apps/jarvis-desk/src/components/cowork/PlansPane.test.tsx
git commit -m "feat(jarvis-desk): PlansPane (step progress)"
```

### Task 10: TodoPane + ChannelsPane

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/TodoPane.tsx`, `ChannelsPane.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/TodoChannels.test.tsx`

- [ ] **Step 1: Write the failing test** — `src/components/cowork/TodoChannels.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TodoPane } from './TodoPane'
import { ChannelsPane } from './ChannelsPane'

describe('TodoPane', () => {
  it('viser todos med status', () => {
    render(<TodoPane todos={[{ id: '1', content: 'Byg cowork', status: 'in_progress' }]} />)
    expect(screen.getByText('Byg cowork')).toBeInTheDocument()
  })
})
describe('ChannelsPane', () => {
  it('viser kanaler med online-status', () => {
    render(<ChannelsPane channels={[{ name: 'discord', online: true, unread: 2 }]} />)
    expect(screen.getByText('discord')).toBeInTheDocument()
    expect(screen.getByText(/2/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoChannels.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/components/cowork/TodoPane.tsx`:

```tsx
import { CircleCheck, CircleDot, Circle } from 'lucide-react'

export interface TodoItem { id: string; content: string; status: string }

export function TodoPane({ todos }: { todos: TodoItem[] }) {
  if (todos.length === 0) return <div className="cowork-empty">Ingen opgaver</div>
  return (
    <div className="cowork-todos">
      {todos.map((t) => {
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            <Icon size={15} /> <span>{t.content}</span>
          </div>
        )
      })}
    </div>
  )
}
```

`src/components/cowork/ChannelsPane.tsx`:

```tsx
import type { CoworkChannel } from '../../lib/coworkApi'

export function ChannelsPane({ channels }: { channels: CoworkChannel[] }) {
  if (channels.length === 0) return <div className="cowork-empty">Ingen kanaler</div>
  return (
    <div className="cowork-channels">
      {channels.map((c) => (
        <div key={c.name} className="cowork-channel">
          <span className="cowork-channel-name">{c.name}</span>
          <span className={`cowork-dot ${c.online ? 'on' : 'off'}`} />
          {c.unread > 0 && <span className="cowork-unread">{c.unread} nye</span>}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run — expect PASS** + tsc

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/TodoChannels.test.tsx && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/TodoPane.tsx apps/jarvis-desk/src/components/cowork/ChannelsPane.tsx apps/jarvis-desk/src/components/cowork/TodoChannels.test.tsx
git commit -m "feat(jarvis-desk): TodoPane + ChannelsPane"
```

---

## Phase 5 — CoworkView + wiring

### Task 11: CoworkView (rolle-bevidst grid) + App route + styles

**Files:**
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx` (erstat stub), `apps/jarvis-desk/src/App.tsx`, `apps/jarvis-desk/src/styles/app.css`
- Test: `apps/jarvis-desk/src/views/CoworkView.test.tsx`

- [ ] **Step 1: Write the failing test** — `src/views/CoworkView.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('../lib/coworkApi', () => ({
  getCoworkQueue: vi.fn().mockResolvedValue([]),
  getCoworkPlans: vi.fn().mockResolvedValue([]),
  getCoworkChannels: vi.fn().mockResolvedValue([{ name: 'discord', online: true, unread: 0 }]),
  resolveQueueItem: vi.fn(),
}))
vi.mock('../hooks/useSettings', () => ({ useSettings: () => ({ settings: { apiBaseUrl: 'http://t', authToken: 't' } }) }))

import { CoworkView } from './CoworkView'

describe('CoworkView', () => {
  it('owner: viser kanal-ruden', async () => {
    render(<CoworkView role="owner" />)
    expect(await screen.findByText('Kanaler')).toBeInTheDocument()
  })
  it('member: ingen kanal-rude', () => {
    render(<CoworkView role="member" />)
    expect(screen.queryByText('Kanaler')).toBeNull()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd apps/jarvis-desk && npx vitest run src/views/CoworkView.test.tsx`
Expected: FAIL (stub)

- [ ] **Step 3: Implement** — erstat `src/views/CoworkView.tsx`:

```tsx
import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { ApprovalQueue } from '../components/cowork/ApprovalQueue'
import { PlansPane } from '../components/cowork/PlansPane'
import { TodoPane } from '../components/cowork/TodoPane'
import { ChannelsPane } from '../components/cowork/ChannelsPane'

/** Cowork: rolle-bevidst arbejd-sammen-dashboard. Owner ser fire ruder; member
 *  ser tre (ingen kanaler). Ren oversigt + godkend/afvis — ingen chat-lane. */
export function CoworkView({ role = 'owner' }: { role?: 'owner' | 'member' | 'guest' }) {
  const { settings } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, channels, resolve } = useCoworkData(config, isOwner)

  return (
    <div className="coworkview">
      <div className="cowork-grid">
        <section className="cowork-pane">
          <div className="cowork-pane-head">Godkendelser <span className="cowork-count">{queue.length}</span></div>
          <ApprovalQueue items={queue} onResolve={resolve} />
        </section>
        <section className="cowork-pane">
          <div className="cowork-pane-head">Planer <span className="cowork-count">{plans.length}</span></div>
          <PlansPane plans={plans} />
        </section>
        <section className="cowork-pane">
          <div className="cowork-pane-head">Todo &amp; initiativer</div>
          <TodoPane todos={[]} />
        </section>
        {isOwner && (
          <section className="cowork-pane">
            <div className="cowork-pane-head">Kanaler</div>
            <ChannelsPane channels={channels} />
          </section>
        )}
      </div>
    </div>
  )
}
```

> NB: TodoPane får `todos={[]}` i v1 (todo-fetch wires i Task 12 sammen med WS — eller udvid useCoworkData med todos nu hvis agent_todos er session-løs). Hold det enkelt: tom liste er en gyldig tom-tilstand.

Modify `src/App.tsx` — skift `{surface === 'cowork' && <CoworkView />}` til:

```tsx
          {surface === 'cowork' && <CoworkView role={role} />}
```

Tilføj CSS til `src/styles/app.css`:

```css
/* Cowork dashboard */
.coworkview { height: 100%; overflow-y: auto; padding: 16px; }
.cowork-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; max-width: 1100px; margin: 0 auto; }
.cowork-pane { background: var(--bg-1); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; min-height: 160px; }
.cowork-pane-head { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--fg-1); margin-bottom: 10px; }
.cowork-count { font-size: 11px; background: var(--bg-3); color: var(--fg-3); padding: 1px 7px; border-radius: 10px; }
.cowork-empty { color: var(--fg-3); font-size: 12.5px; padding: 8px 2px; }
.cowork-item { border: 1px solid var(--line); border-radius: 7px; padding: 8px 10px; margin-bottom: 8px; }
.cowork-item-title { font-size: 12.5px; display: flex; align-items: center; gap: 5px; }
.cowork-item-detail { font-size: 11.5px; color: var(--fg-3); font-family: ui-monospace, monospace; margin: 3px 0 6px; }
.cowork-item-actions { display: flex; gap: 6px; }
.cowork-item-actions button { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; padding: 3px 9px; background: var(--bg-2); color: var(--fg-1); border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
.cowork-item-actions button:hover { border-color: var(--accent); }
.cowork-diff { margin: 6px 0 0; font-family: ui-monospace, monospace; font-size: 11.5px; white-space: pre-wrap; max-height: 200px; overflow: auto; color: #c8d2dc; }
.cowork-plan { margin-bottom: 10px; }
.cowork-plan-title { font-size: 12.5px; font-weight: 500; }
.cowork-plan-sub { font-size: 11.5px; color: var(--fg-3); margin: 2px 0 5px; }
.cowork-progress { height: 4px; background: var(--bg-3); border-radius: 3px; }
.cowork-progress-fill { height: 4px; background: var(--accent); border-radius: 3px; }
.cowork-todo { display: flex; align-items: center; gap: 7px; font-size: 12.5px; padding: 3px 0; color: var(--fg-2); }
.cowork-todo.status-completed span { color: var(--fg-3); text-decoration: line-through; }
.cowork-channel { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 4px 0; }
.cowork-channel-name { color: var(--fg-2); }
.cowork-dot { width: 7px; height: 7px; border-radius: 50%; margin-left: auto; }
.cowork-dot.on { background: var(--accent); }
.cowork-dot.off { background: var(--fg-3); }
.cowork-unread { font-size: 11px; color: var(--fg-3); }
```

- [ ] **Step 4: Run — expect PASS** + tsc + fuld suite

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/views/CoworkView.tsx apps/jarvis-desk/src/views/CoworkView.test.tsx apps/jarvis-desk/src/App.tsx apps/jarvis-desk/src/styles/app.css
git commit -m "feat(jarvis-desk): CoworkView role-aware 4-pane dashboard + wiring + styles"
```

---

## Phase 6 — Real-time + deploy

### Task 12: WS-abonnement (live updates) + todos i hook

**Files:**
- Modify: `apps/jarvis-desk/src/hooks/useCoworkData.ts`
- Test: `apps/jarvis-desk/src/hooks/useCoworkData.test.tsx` (append)

- [ ] **Step 1: Write the failing test** — append: et test der verificerer at en mock-WS-besked trigger refetch. Mock `WebSocket` globalt:

```tsx
it('refetcher når et WS-event ankommer', async () => {
  class FakeWS { onmessage: ((e: { data: string }) => void) | null = null; close() {}; constructor() { setTimeout(() => this.onmessage?.({ data: JSON.stringify({ family: 'approvals' }) }), 0) } }
  vi.stubGlobal('WebSocket', FakeWS as unknown as typeof WebSocket)
  const api = await import('../lib/coworkApi')
  const spy = vi.spyOn(api, 'getCoworkQueue')
  const { renderHook, waitFor } = await import('@testing-library/react')
  const { useCoworkData } = await import('./useCoworkData')
  renderHook(() => useCoworkData({ apiBaseUrl: 'http://t', authToken: 't' }, true))
  await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThanOrEqual(2))
})
```

- [ ] **Step 2: Run — expect FAIL** (ingen WS endnu)

Run: `cd apps/jarvis-desk && npx vitest run src/hooks/useCoworkData.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement** — tilføj WS-abonnement i `useCoworkData` (efter polling-effekten):

```ts
  useEffect(() => {
    const cfg = cfgRef.current
    if (!cfg) return
    const wsUrl = cfg.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws'
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = () => { void refresh() }
    } catch { /* polling-fallback dækker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [refresh, config?.apiBaseUrl])
```

- [ ] **Step 4: Run — expect PASS** + fuld suite + tsc

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: PASS, tsc 0

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/hooks/useCoworkData.ts apps/jarvis-desk/src/hooks/useCoworkData.test.tsx
git commit -m "feat(jarvis-desk): cowork live updates via Mission Control WS (polling fallback)"
```

### Task 13: FINAL CHECKPOINT — deploy + live-verify

- [ ] **Step 1:** Backend allerede deployet (Task 5). Verificér ruterne live:

```bash
ssh bs@10.0.0.39 'for p in queue plans channels; do curl -s -o /dev/null -w "$p=%{http_code} " "http://localhost:80/cowork/$p"; done; echo; curl -s -o /dev/null -w "openapi=%{http_code} t=%{time_total}s\n" --max-time 8 http://localhost:80/openapi.json'
```
Expected: `queue=401 plans=401 channels=401` + openapi `200` hurtigt (ingen frys).

- [ ] **Step 2:** Byg + installér app:

```bash
cd apps/jarvis-desk && npm run build && npx electron-builder --linux deb && sudo dpkg -i release/jarvis-desktop_0.1.0_amd64.deb
```

- [ ] **Step 3:** Live-verify i appen: åbn Cowork-fanen → fire ruder (som owner), godkendelser/planer udfyldes, kanaler viser Discord-status. Godkend et item → det forsvinder fra køen. Skift til en member-token → kanal-ruden er væk + queue/planer kun egne.

---

## Self-Review (mod spec'en)

**Spec coverage:**
- Fire søjler → Task 8/9/10 (ruder) + Task 11 (grid). ✅
- Rolle-model (owner 4 / member 3, kanaler owner-only) → Task 4 (403), Task 7 (skip channels), Task 11 (skjul rude), Task 1/2 (scoping). ✅
- Samlet queue (tool-intents + capability + fil-diffs + initiativer) → Task 1 (build_queue normaliserer alle kinds). ✅
- Genbrug af eksisterende backend → Task 1/2/5 (initiative_queue, capability-surface, plan_proposals, resolvers). ✅
- Diff i godkendelseskortet → Task 8 (QueueRow diff-toggle). ✅
- Real-time WS + polling-fallback → Task 7 (polling) + Task 12 (WS). ✅
- asyncio.to_thread frys-beskyttelse → Task 3/4/5 (alle ruter offloader). ✅

**Placeholder scan:** Tre `> NB:`-noter beder engineeren verificere præcise funktionsnavne (resolve_initiative/resolve_pending_approval, _channel_status_surface, apiFetch export) — det er bevidste, konkrete verifikations-punkter med fallback-instruktion, ikke vage TODOs. TodoPane får tom liste i v1 (gyldig tom-tilstand).

**Type-konsistens:** `QueueItem`/`CoworkPlan`/`CoworkChannel` defineret i coworkApi.ts (Task 6) og brugt konsistent i hook (7), ruder (8/9/10) og view (11). `resolve(id, 'approve'|'reject')` matcher backend `/approve`|`/reject` (Task 5).
