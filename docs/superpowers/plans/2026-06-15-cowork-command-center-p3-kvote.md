# Cowork Command Center — Plan 3: Indstillinger → Kvote

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps bruger checkbox (`- [ ]`).

**Goal:** Tilføj en Kvote-sektion i cowork-indstillinger der viser den aktuelle brugers tier + forbrug pr. kvote-type (chat/code/cowork/agent) som forbrugs-bjælker — wired til det eksisterende `quota_store`.

**Architecture:** `core/services/quota_store.check_quota(user_id, kind)` returnerer allerede `{allowed, tier, used, limit, remaining, warn}` for hver `kind ∈ {chat, code, cowork, agent}`. Vi tilføjer ét self-scope-endpoint (`GET /account/quota`) der samler de fire typer + tier, og en `KvoteSection`-komponent. Self-scope: en bruger ser kun sit eget forbrug.

**Tech Stack:** FastAPI + pytest (`/opt/conda/envs/ai`), React + vitest (`apps/jarvis-desk`).

---

## File Structure

**Backend:**
- Modify: `apps/api/jarvis_api/routes/account.py` — `build_quota_overview()` + `GET /account/quota`.
- Test: `tests/test_account_quota.py`

**Frontend:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts` — `QuotaOverview`/`QuotaItem` + `getAccountQuota()`.
- Create: `apps/jarvis-desk/src/components/settings/KvoteSection.tsx`
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx` — vis KvoteSection i indstillingszonen.
- Modify: `apps/jarvis-desk/src/styles/app.css` — forbrugs-bjælke-styles.
- Test: `apps/jarvis-desk/src/components/settings/KvoteSection.test.tsx`

---

## Task 1: Backend — quota-overblik

**Files:**
- Modify: `apps/api/jarvis_api/routes/account.py`
- Test: `tests/test_account_quota.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_account_quota.py
from apps.api.jarvis_api.routes.account import build_quota_overview


def _fake_check(user_id, kind):
    table = {
        "chat": {"tier": "plus", "used": 5, "limit": None, "remaining": None, "warn": False},
        "code": {"tier": "plus", "used": 30, "limit": 180, "remaining": 150, "warn": False},
        "cowork": {"tier": "plus", "used": 9, "limit": 10, "remaining": 1, "warn": True},
        "agent": {"tier": "plus", "used": 0, "limit": 2, "remaining": 2, "warn": False},
    }
    return table[kind]


def test_overview_collects_all_kinds():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    assert ov["tier"] == "plus"
    kinds = {i["kind"] for i in ov["items"]}
    assert kinds == {"chat", "code", "cowork", "agent"}


def test_overview_item_shape():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    cowork = next(i for i in ov["items"] if i["kind"] == "cowork")
    assert cowork["used"] == 9
    assert cowork["limit"] == 10
    assert cowork["warn"] is True


def test_overview_unlimited_limit_is_none():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    chat = next(i for i in ov["items"] if i["kind"] == "chat")
    assert chat["limit"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_account_quota.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_quota_overview'`

- [ ] **Step 3: Write minimal implementation**

I `apps/api/jarvis_api/routes/account.py` — tilføj import + ren funktion + endpoint:

```python
from typing import Any, Callable

_QUOTA_KINDS = ("chat", "code", "cowork", "agent")


def build_quota_overview(
    user_id: str,
    *,
    check_quota: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Self-scope kvote-overblik: tier + forbrug pr. type. Ren — testbar uden HTTP."""
    items: list[dict[str, Any]] = []
    tier = ""
    for kind in _QUOTA_KINDS:
        q = check_quota(user_id, kind) or {}
        tier = tier or str(q.get("tier") or "")
        items.append({
            "kind": kind,
            "used": int(q.get("used") or 0),
            "limit": q.get("limit"),  # None = ubegrænset
            "remaining": q.get("remaining"),
            "warn": bool(q.get("warn")),
        })
    return {"tier": tier or "free", "items": items}


@router.get("/quota")
async def account_quota() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    from core.services.quota_store import check_quota
    return await asyncio.to_thread(build_quota_overview, user_id, check_quota=check_quota)
```

(Note: `asyncio`, `current_context_snapshot` og `router` er allerede importeret/defineret i filen fra Plan 1. `Callable` skal måske tilføjes til den eksisterende `from typing import`-linje — tjek og flet.)

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_account_quota.py -v && /opt/conda/envs/ai/bin/python -m compileall -q apps/api/jarvis_api/routes/account.py`
Expected: PASS (3 passed) + compile OK

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/routes/account.py tests/test_account_quota.py
git commit -m "feat(account): GET /account/quota self-scope kvote-overblik (§4.9)"
```

---

## Task 2: Frontend — getAccountQuota

**Files:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts`
- Test: `apps/jarvis-desk/src/lib/coworkApi.quota.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/jarvis-desk/src/lib/coworkApi.quota.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => fetchMock(...a) }))

import { getAccountQuota } from './coworkApi'

describe('getAccountQuota', () => {
  beforeEach(() => fetchMock.mockReset())

  it('henter /account/quota', async () => {
    fetchMock.mockResolvedValue({ tier: 'plus', items: [{ kind: 'chat', used: 5, limit: null, remaining: null, warn: false }] })
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const ov = await getAccountQuota(cfg)
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/account/quota')
    expect(ov.tier).toBe('plus')
    expect(ov.items[0].kind).toBe('chat')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.quota.test.ts`
Expected: FAIL — eksport mangler

- [ ] **Step 3: Write minimal implementation**

Tilføj nederst i `apps/jarvis-desk/src/lib/coworkApi.ts`:
```typescript
export interface QuotaItem {
  kind: 'chat' | 'code' | 'cowork' | 'agent'
  used: number
  limit: number | null
  remaining: number | null
  warn: boolean
}
export interface QuotaOverview { tier: string; items: QuotaItem[] }

export async function getAccountQuota(config: ApiConfig): Promise<QuotaOverview> {
  return apiFetch<QuotaOverview>(config, '/account/quota')
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.quota.test.ts`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/lib/coworkApi.quota.test.ts
git commit -m "feat(desk): getAccountQuota + QuotaOverview-typer"
```

---

## Task 3: Frontend — KvoteSection

**Files:**
- Create: `apps/jarvis-desk/src/components/settings/KvoteSection.tsx`
- Test: `apps/jarvis-desk/src/components/settings/KvoteSection.test.tsx`

Henter overblikket ved mount. Viser tier-badge + én række pr. type med dansk label, forbrug/limit og en forbrugs-bjælke. Ubegrænset (`limit===null`) vises som "ubegrænset" uden bjælke. `warn`-rækker får en advarsels-klasse.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/settings/KvoteSection.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getAccountQuota = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountQuota: (...a: unknown[]) => getAccountQuota(...a) }))

import { KvoteSection } from './KvoteSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('KvoteSection', () => {
  beforeEach(() => getAccountQuota.mockReset())

  it('viser tier og forbrug pr. type', async () => {
    getAccountQuota.mockResolvedValue({
      tier: 'plus',
      items: [
        { kind: 'chat', used: 5, limit: null, remaining: null, warn: false },
        { kind: 'cowork', used: 9, limit: 10, remaining: 1, warn: true },
      ],
    })
    render(<KvoteSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/plus/i)).toBeTruthy())
    expect(screen.getByText(/ubegrænset/i)).toBeTruthy()   // chat
    expect(screen.getByText('9 / 10')).toBeTruthy()        // cowork
  })

  it('markerer warn-rækker', async () => {
    getAccountQuota.mockResolvedValue({
      tier: 'free',
      items: [{ kind: 'cowork', used: 0, limit: 0, remaining: 0, warn: true }],
    })
    const { container } = render(<KvoteSection config={cfg} />)
    await waitFor(() => expect(container.querySelector('.quota-row.warn')).toBeTruthy())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/settings/KvoteSection.test.tsx`
Expected: FAIL — module findes ikke

- [ ] **Step 3: Write minimal implementation**

```tsx
// apps/jarvis-desk/src/components/settings/KvoteSection.tsx
import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountQuota, type QuotaOverview, type QuotaItem } from '../../lib/coworkApi'

const LABELS: Record<QuotaItem['kind'], string> = {
  chat: 'Chat-beskeder',
  code: 'Code-minutter',
  cowork: 'Cowork-godkendelser',
  agent: 'Agent-dispatches',
}

export function KvoteSection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<QuotaOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountQuota(config)
      .then((d) => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente kvoten.</div>
  if (!data) return <div className="settings-section">Indlæser kvote…</div>

  return (
    <div className="settings-section kvote-section">
      <h3>Kvote <span className="badge badge-ok">{data.tier}</span></h3>
      <div className="quota-list">
        {data.items.map((it) => {
          const unlimited = it.limit == null
          const pct = unlimited || !it.limit ? 0 : Math.min(100, Math.round((it.used / it.limit) * 100))
          return (
            <div key={it.kind} className={`quota-row${it.warn ? ' warn' : ''}`}>
              <div className="quota-head">
                <span>{LABELS[it.kind]}</span>
                <span className="quota-num">{unlimited ? 'ubegrænset' : `${it.used} / ${it.limit}`}</span>
              </div>
              {!unlimited && (
                <div className="quota-bar"><div className="quota-fill" style={{ width: `${pct}%` }} /></div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/settings/KvoteSection.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/settings/KvoteSection.tsx apps/jarvis-desk/src/components/settings/KvoteSection.test.tsx
git commit -m "feat(desk): KvoteSection — tier + forbrugs-bjælker"
```

---

## Task 4: Wire + styles + suite + deploy

**Files:**
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`

- [ ] **Step 1: Vis KvoteSection i indstillingszonen**

I `CoworkView.tsx` — importér og indsæt i `settingsZone` (efter `AccountSection`):
```tsx
import { KvoteSection } from '../components/settings/KvoteSection'
```
```tsx
  const settingsZone = (
    <div className="cowork-settings">
      <AccountSection config={config} />
      <KvoteSection config={config} />
      {auth?.role === 'owner' && <TotpSetup config={config} />}
      {auth?.role === 'owner' && <PluginsPanel config={config} />}
    </div>
  )
```

- [ ] **Step 2: Styles** — i `apps/jarvis-desk/src/styles/app.css`:
```css
.quota-list { display: flex; flex-direction: column; gap: 12px; }
.quota-row .quota-head { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.quota-num { color: var(--fg-3); }
.quota-bar { height: 6px; background: var(--bg-3); border-radius: 4px; overflow: hidden; }
.quota-fill { height: 100%; background: var(--accent, #5b8def); }
.quota-row.warn .quota-fill { background: var(--danger, #e06c75); }
.quota-row.warn .quota-num { color: var(--danger, #e06c75); }
```

- [ ] **Step 3: Test for CoworkView (KvoteSection mounter i settings-zonen)**

Den eksisterende `CoworkView.test.tsx` mocker `../lib/coworkApi` med spread af originalen + override af `getAccountMe`. KvoteSection kalder `getAccountQuota` (ægte → netværk i jsdom = rejection, men fanget i `.catch`). For at undgå støj: tilføj `getAccountQuota` til mock-overrides i `CoworkView.test.tsx`:
```tsx
const getAccountQuota = vi.fn().mockResolvedValue({ tier: 'owner', items: [] })
```
og i `vi.mock('../lib/coworkApi', ...)`-objektet:
```tsx
  getAccountQuota: (...a: unknown[]) => getAccountQuota(...a),
```

- [ ] **Step 4: Hele suiten + typecheck**

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: alle grønne, exit 0

- [ ] **Step 5: Commit + byg + deploy**

```bash
git add apps/jarvis-desk/src/views/CoworkView.tsx apps/jarvis-desk/src/views/CoworkView.test.tsx apps/jarvis-desk/src/styles/app.css
git commit -m "feat(desk): vis KvoteSection i cowork-indstillinger + styling"
cd apps/jarvis-desk && npm run package:linux && sudo dpkg -i release/jarvis-desktop_*_amd64.deb
cd ../.. && git push target main && ssh 10.0.0.39 'sudo systemctl restart jarvis-api && sleep 3 && systemctl is-active jarvis-api'
```

---

## Self-Review

**1. Spec-coverage (§4.9 Kvote):** nuværende forbrug pr. type (T1/T3), tier (T1/T3), self-scope (T1 bruger current_context_snapshot). Stripe-opgradering er IKKE i scope her (separat — kræver betalings-flow; noteret). ✓
**2. Placeholder-scan:** ingen TBD; al kode konkret. ✓
**3. Type-konsistens:** `build_quota_overview(user_id, *, check_quota)` ens i T1. `QuotaItem`/`QuotaOverview` ens i T2/T3. `getAccountQuota(config)` ens i T2/T3/T4. `LABELS`-nøgler = `QuotaItem['kind']`-union. ✓
