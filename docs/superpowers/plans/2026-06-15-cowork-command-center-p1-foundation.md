---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Cowork Command Center — Plan 1: Foundation (to-zone-skal + Account)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Omdan cowork fra et fladt rude-dashboard til et to-zone command center (Mission Control | Indstillinger) med en navigations-skinne, og lever den første indstillings-sektion (Account) wired til et nyt self-profile-endpoint — som bevis-på-mønster for de resterende sektioner.

**Architecture:** Cowork er allerede en surface (`CoworkView`) med 6 Mission Control-ruder, og der findes en separat `settings`-surface. Denne plan indfører en zone-skinne i cowork: "Mission Control" rummer det eksisterende rude-grid uændret; "Indstillinger" rummer en sektions-liste hvor Account er første konkrete sektion, og de eksisterende `TotpSetup`/`PluginsPanel` genbruges som sektioner. Backend tilføjer ét lille self-profile-endpoint (`GET /account/me`) så en bruger kan se sin egen email/verifikation/sprog/rolle/tier uden owner-only `/api/users/{id}`.

**Tech Stack:** React 18 + TypeScript (Electron, `apps/jarvis-desk`), vitest + @testing-library/react. FastAPI backend (`apps/api/jarvis_api`), pytest, conda-miljø `/opt/conda/envs/ai`.

---

## Scope & roadmap (denne plan er #1 af flere)

Spec'en (`docs/superpowers/specs/2026-06-15-cowork-command-center-design.md`) dækker mange uafhængige subsystemer. Den dekomponeres i separate planer; **denne plan leverer kun fundamentet + Account**. Opfølgnings-planer (skrives separat, hver for sig):

- **Plan 2 — Mission Control interaktiv:** todo-CRUD + TTL + pause/prioritér fra UI (spec §3.1), backend `agent_todos` er i dag read-only mod cowork.
- **Plan 3 — Indstillinger: Jarvis + Memory + Kvote** (spec §4.2/§4.3/§4.9) — overflader model-lanes, memory-søgning, `quota_store`.
- **Plan 4 — Indstillinger: Permissions + Workspace + Plugins-marketplace** (spec §4.4/§4.7/§4.8).
- **Plan 5 — Indstillinger: Apps + MCP + Sprog + Tema** (spec §4.5/§4.6/§4.10/§4.11).
- **Plan 6 — Jarvis navigerer appen:** `open_ui_panel panel=settings` + `request_app_action request_full_access` (spec §5).

**Vigtig korrektion til spec'en:** §1 påstår "cowork er et tomt panel uden struktur" og §9 lister nye `core/routes/cowork.py` + `core/routes/mc.py`. Det er forældet: `apps/jarvis-desk/src/views/CoworkView.tsx` har allerede alle 6 MC-ruder, og `apps/api/jarvis_api/routes/cowork.py` findes med `/queue /plans /todos /channels /agents /share-guard`. Routes ligger i `apps/api/jarvis_api/routes/`, ikke `core/routes/`. Denne plan bygger oven på det eksisterende.

---

## File Structure

**Backend:**
- Create: `apps/api/jarvis_api/routes/account.py` — self-profile-route (`GET /account/me`). Én ansvarlighed: den aktuelle brugers egen profil-projektion (email, verifikation, sprog, rolle, tier). Ingen owner-only krav (enhver autentificeret bruger ser sin egen).
- Modify: `apps/api/jarvis_api/app.py` — registrér den nye router.
- Test: `tests/test_account_me.py`

**Frontend:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts` — tilføj `AccountProfile`-type + `getAccountMe()`.
- Create: `apps/jarvis-desk/src/components/cowork/CoworkZones.tsx` — zone-skinne (nav-rail + zone-switch). Én ansvarlighed: vælg mellem "Mission Control" og "Indstillinger".
- Create: `apps/jarvis-desk/src/components/settings/AccountSection.tsx` — Account-sektionen.
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx` — wrap eksisterende grid i Mission Control-zonen + tilføj Indstillinger-zonen.
- Modify: `apps/jarvis-desk/src/styles.css` (eller den aktuelle css-fil) — zone-rail + sektions-styles.
- Test: `apps/jarvis-desk/src/components/cowork/CoworkZones.test.tsx`, `apps/jarvis-desk/src/components/settings/AccountSection.test.tsx`

---

## Task 1: Backend — `GET /account/me` self-profile

**Files:**
- Create: `apps/api/jarvis_api/routes/account.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_account_me.py`

Profil-projektionen bygges af en ren funktion `build_account_profile(user_id)` så den kan testes uden HTTP. Owner (`user_id == ""`) har ingen `user_db`-række → returnér owner-defaults. En member slår op i `user_db.get_user(user_id)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_account_me.py
from apps.api.jarvis_api.routes.account import build_account_profile


def test_owner_profile_defaults():
    prof = build_account_profile("", get_user=lambda uid: None, get_tier=lambda uid: "owner")
    assert prof == {
        "user_id": "",
        "email": "",
        "email_verified": True,
        "language": "da",
        "role": "owner",
        "tier": "owner",
    }


def test_member_profile_from_user_db():
    row = {"user_id": "u_mikkel", "email": "m@x.dk", "email_verified": False,
           "role": "member", "tier": "plus", "language": "en"}
    prof = build_account_profile("u_mikkel", get_user=lambda uid: row, get_tier=lambda uid: "plus")
    assert prof["email"] == "m@x.dk"
    assert prof["email_verified"] is False
    assert prof["language"] == "en"
    assert prof["role"] == "member"
    assert prof["tier"] == "plus"


def test_member_missing_language_defaults_to_da():
    row = {"user_id": "u_a", "email": "a@x.dk", "email_verified": True, "role": "member"}
    prof = build_account_profile("u_a", get_user=lambda uid: row, get_tier=lambda uid: "free")
    assert prof["language"] == "da"
    assert prof["tier"] == "free"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_account_me.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'build_account_profile'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/jarvis_api/routes/account.py
"""Self-profile-route for cowork command center (spec §4.1 Account).

Enhver autentificeret bruger kan hente SIN EGEN profil-projektion — modsat
routes/users.py som er owner-only (/api/users/{id}). Privatlivs-reglen: en
bruger ser kun sig selv; ingen cross-bruger-opslag her.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import APIRouter

from core.identity import user_db
from core.services import quota_store
from core.identity.workspace_context import current_context_snapshot

router = APIRouter(prefix="/account", tags=["account"])


def build_account_profile(
    user_id: str,
    *,
    get_user: Callable[[str], dict[str, Any] | None],
    get_tier: Callable[[str], str],
) -> dict[str, Any]:
    """Ren projektion — testbar uden HTTP. Owner (uid='') har ingen række."""
    if not user_id:
        return {
            "user_id": "",
            "email": "",
            "email_verified": True,
            "language": "da",
            "role": "owner",
            "tier": get_tier("") or "owner",
        }
    row = get_user(user_id) or {}
    return {
        "user_id": user_id,
        "email": row.get("email", "") or "",
        "email_verified": bool(row.get("email_verified")),
        "language": row.get("language") or "da",
        "role": row.get("role") or "member",
        "tier": get_tier(user_id) or (row.get("tier") or "free"),
    }


@router.get("/me")
async def account_me() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    return await asyncio.to_thread(
        build_account_profile,
        user_id,
        get_user=user_db.get_user,
        get_tier=quota_store.get_tier,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_account_me.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Register the router**

Find hvor de øvrige routers inkluderes i `apps/api/jarvis_api/app.py` (søg efter `include_router`). Tilføj ved siden af de andre route-imports:

```python
from apps.api.jarvis_api.routes import account as account_routes
# ... ved de andre app.include_router(...)-kald:
app.include_router(account_routes.router)
```

- [ ] **Step 6: Verify import + compile**

Run: `/opt/conda/envs/ai/bin/python -m compileall apps/api/jarvis_api/routes/account.py apps/api/jarvis_api/app.py`
Expected: ingen fejl

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/routes/account.py apps/api/jarvis_api/app.py tests/test_account_me.py
git commit -m "feat(account): GET /account/me self-profile (cowork command center §4.1)"
```

---

## Task 2: Frontend — `getAccountMe()` API-klient

**Files:**
- Modify: `apps/jarvis-desk/src/lib/coworkApi.ts`
- Test: `apps/jarvis-desk/src/lib/coworkApi.account.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/jarvis-desk/src/lib/coworkApi.account.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({
  apiFetch: (...args: unknown[]) => fetchMock(...args),
}))

import { getAccountMe } from './coworkApi'

describe('getAccountMe', () => {
  beforeEach(() => fetchMock.mockReset())

  it('henter /account/me og returnerer profilen', async () => {
    fetchMock.mockResolvedValue({
      user_id: 'u1', email: 'a@x.dk', email_verified: true,
      language: 'da', role: 'owner', tier: 'owner',
    })
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const prof = await getAccountMe(cfg)
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/account/me')
    expect(prof.email).toBe('a@x.dk')
    expect(prof.role).toBe('owner')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.account.test.ts`
Expected: FAIL — `getAccountMe is not a function` / export mangler

- [ ] **Step 3: Write minimal implementation**

Tilføj nederst i `apps/jarvis-desk/src/lib/coworkApi.ts` (efter de øvrige eksports; `apiFetch` er allerede importeret øverst i filen):

```typescript
export interface AccountProfile {
  user_id: string
  email: string
  email_verified: boolean
  language: string
  role: 'owner' | 'member' | 'guest'
  tier: string
}

export async function getAccountMe(config: ApiConfig): Promise<AccountProfile> {
  return apiFetch<AccountProfile>(config, '/account/me')
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/coworkApi.account.test.ts`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/coworkApi.ts apps/jarvis-desk/src/lib/coworkApi.account.test.ts
git commit -m "feat(desk): getAccountMe API-klient for /account/me"
```

---

## Task 3: Frontend — AccountSection-komponent

**Files:**
- Create: `apps/jarvis-desk/src/components/settings/AccountSection.tsx`
- Test: `apps/jarvis-desk/src/components/settings/AccountSection.test.tsx`

Account-sektionen henter profilen ved mount og viser email + verifikations-badge + sprog + rolle + tier. Members ser samme felter for sig selv (det er deres egne data). TOTP/API-nøgler hører til senere under denne sektion, men leveres i Plan 1 kun som genbrug af eksisterende `TotpSetup` (owner-only) i Task 5 — ikke her.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/settings/AccountSection.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getAccountMe = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountMe: (...a: unknown[]) => getAccountMe(...a) }))

import { AccountSection } from './AccountSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('AccountSection', () => {
  beforeEach(() => getAccountMe.mockReset())

  it('viser email og rolle fra profilen', async () => {
    getAccountMe.mockResolvedValue({
      user_id: 'u1', email: 'bjorn@x.dk', email_verified: true,
      language: 'da', role: 'owner', tier: 'owner',
    })
    render(<AccountSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('bjorn@x.dk')).toBeTruthy())
    expect(screen.getByText(/owner/i)).toBeTruthy()
  })

  it('viser "ikke verificeret" når email_verified=false', async () => {
    getAccountMe.mockResolvedValue({
      user_id: 'u2', email: 'm@x.dk', email_verified: false,
      language: 'en', role: 'member', tier: 'plus',
    })
    render(<AccountSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/ikke verificeret/i)).toBeTruthy())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/settings/AccountSection.test.tsx`
Expected: FAIL — module `./AccountSection` findes ikke

- [ ] **Step 3: Write minimal implementation**

```tsx
// apps/jarvis-desk/src/components/settings/AccountSection.tsx
import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMe, type AccountProfile } from '../../lib/coworkApi'

/** Account-sektion (cowork command center §4.1). Viser den aktuelle brugers
 *  egen profil — henter via /account/me (self-scope, ikke owner-only). */
export function AccountSection({ config }: { config: ApiConfig | undefined }) {
  const [profile, setProfile] = useState<AccountProfile | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMe(config)
      .then((p) => { if (alive) setProfile(p) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente kontoen.</div>
  if (!profile) return <div className="settings-section">Indlæser konto…</div>

  return (
    <div className="settings-section account-section">
      <h3>Konto</h3>
      <dl className="account-fields">
        <dt>Email</dt>
        <dd>
          {profile.email || '–'}{' '}
          {profile.email
            ? (profile.email_verified
                ? <span className="badge badge-ok">verificeret ✓</span>
                : <span className="badge badge-warn">ikke verificeret</span>)
            : null}
        </dd>
        <dt>Sprog</dt><dd>{profile.language}</dd>
        <dt>Rolle</dt><dd>{profile.role}</dd>
        <dt>Tier</dt><dd>{profile.tier}</dd>
      </dl>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/settings/AccountSection.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/settings/AccountSection.tsx apps/jarvis-desk/src/components/settings/AccountSection.test.tsx
git commit -m "feat(desk): AccountSection — self-profil i cowork-indstillinger"
```

---

## Task 4: Frontend — CoworkZones zone-skinne

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/CoworkZones.tsx`
- Test: `apps/jarvis-desk/src/components/cowork/CoworkZones.test.tsx`

Ren præsentations-komponent: en venstre nav-rail med to knapper ("Mission Control", "Indstillinger") + et indholds-område der viser den valgte zones `children`. Tilstanden (valgt zone) holdes internt med `useState`, default "mc". Members ser begge zoner (Indstillinger filtreres på sektions-niveau, ikke zone-niveau).

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/components/cowork/CoworkZones.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CoworkZones } from './CoworkZones'

describe('CoworkZones', () => {
  it('viser Mission Control som default og skifter til Indstillinger', () => {
    render(
      <CoworkZones
        missionControl={<div>MC-INDHOLD</div>}
        settings={<div>SETTINGS-INDHOLD</div>}
      />,
    )
    // Default = Mission Control synlig
    expect(screen.getByText('MC-INDHOLD')).toBeTruthy()
    expect(screen.queryByText('SETTINGS-INDHOLD')).toBeNull()

    // Klik på Indstillinger-rail-knappen
    fireEvent.click(screen.getByRole('button', { name: /indstillinger/i }))
    expect(screen.getByText('SETTINGS-INDHOLD')).toBeTruthy()
    expect(screen.queryByText('MC-INDHOLD')).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/CoworkZones.test.tsx`
Expected: FAIL — module `./CoworkZones` findes ikke

- [ ] **Step 3: Write minimal implementation**

```tsx
// apps/jarvis-desk/src/components/cowork/CoworkZones.tsx
import { useState, type ReactNode } from 'react'

type Zone = 'mc' | 'settings'

/** To-zone-skal for cowork command center (spec §2). Venstre nav-rail vælger
 *  mellem Mission Control (fælles arbejdsrum) og Indstillinger (konfiguration). */
export function CoworkZones({
  missionControl, settings,
}: { missionControl: ReactNode; settings: ReactNode }) {
  const [zone, setZone] = useState<Zone>('mc')
  return (
    <div className="cowork-zones">
      <nav className="cowork-rail">
        <button
          type="button"
          className={zone === 'mc' ? 'rail-btn active' : 'rail-btn'}
          onClick={() => setZone('mc')}
        >Mission Control</button>
        <button
          type="button"
          className={zone === 'settings' ? 'rail-btn active' : 'rail-btn'}
          onClick={() => setZone('settings')}
        >Indstillinger</button>
      </nav>
      <div className="cowork-zone-body">
        {zone === 'mc' ? missionControl : settings}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/components/cowork/CoworkZones.test.tsx`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/components/cowork/CoworkZones.tsx apps/jarvis-desk/src/components/cowork/CoworkZones.test.tsx
git commit -m "feat(desk): CoworkZones — to-zone-skal (Mission Control | Indstillinger)"
```

---

## Task 5: Integrér zoner i CoworkView

**Files:**
- Modify: `apps/jarvis-desk/src/views/CoworkView.tsx`
- Test: `apps/jarvis-desk/src/views/CoworkView.test.tsx`

Mission Control-zonen = det eksisterende rude-grid (uændret). Indstillinger-zonen = `AccountSection` + de eksisterende `TotpSetup`/`PluginsPanel` (owner-only). Det eksisterende grid flyttes ind som `missionControl`-prop uden ændringer i ruderne selv.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/jarvis-desk/src/views/CoworkView.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))
vi.mock('../hooks/useCoworkData', () => ({
  useCoworkData: () => ({
    queue: [], plans: [], todos: [], channels: [], shareGuard: [], agents: [],
    resolve: vi.fn(), resolveShare: vi.fn(),
  }),
}))
const getAccountMe = vi.fn().mockResolvedValue({
  user_id: 'u1', email: 'bjorn@x.dk', email_verified: true, language: 'da', role: 'owner', tier: 'owner',
})
vi.mock('../lib/coworkApi', async (orig) => ({
  ...(await orig<typeof import('../lib/coworkApi')>()),
  getAccountMe: (...a: unknown[]) => getAccountMe(...a),
}))
// TotpSetup/PluginsPanel laver netværkskald ved mount — stub dem til tomme noder.
vi.mock('../components/settings/TotpSetup', () => ({ TotpSetup: () => <div>totp</div> }))
vi.mock('../components/settings/PluginsPanel', () => ({ PluginsPanel: () => <div>plugins</div> }))

import { CoworkView } from './CoworkView'

describe('CoworkView command center', () => {
  it('viser Mission Control-grid default og Account under Indstillinger', async () => {
    render(<CoworkView role="owner" />)
    // Mission Control default: rude-overskriften "Godkendelser" findes
    expect(screen.getByText(/godkendelser/i)).toBeTruthy()
    // Skift til Indstillinger
    fireEvent.click(screen.getByRole('button', { name: /indstillinger/i }))
    await waitFor(() => expect(screen.getByText('bjorn@x.dk')).toBeTruthy())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/jarvis-desk && npx vitest run src/views/CoworkView.test.tsx`
Expected: FAIL — Account-data vises ikke (ingen zone-skinne endnu)

- [ ] **Step 3: Write minimal implementation**

Erstat `CoworkView.tsx` med zone-versionen. Det eksisterende grid bevares ord-for-ord inde i en `missionControl`-variabel:

```tsx
// apps/jarvis-desk/src/views/CoworkView.tsx
import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { ApprovalQueue } from '../components/cowork/ApprovalQueue'
import { PlansPane } from '../components/cowork/PlansPane'
import { TodoPane } from '../components/cowork/TodoPane'
import { ChannelsPane } from '../components/cowork/ChannelsPane'
import { ShareGuardPane } from '../components/cowork/ShareGuardPane'
import { AgentDispatchPane } from '../components/cowork/AgentDispatchPane'
import { CoworkZones } from '../components/cowork/CoworkZones'
import { AccountSection } from '../components/settings/AccountSection'
import { TotpSetup } from '../components/settings/TotpSetup'
import { PluginsPanel } from '../components/settings/PluginsPanel'
import { activeAgentsToView } from '../lib/coworkApi'

/** Cowork command center: to zoner. Mission Control = rolle-bevidst rude-grid
 *  (uændret); Indstillinger = konto + (owner) TOTP/plugins. */
export function CoworkView({ role = 'owner' }: { role?: 'owner' | 'member' | 'guest' }) {
  const { settings, auth } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, todos, channels, shareGuard, agents, resolve, resolveShare } = useCoworkData(config, isOwner)

  const missionControl = (
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
        <TodoPane todos={todos} />
      </section>
      {isOwner && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">Kanaler</div>
          <ChannelsPane channels={channels} />
        </section>
      )}
      {isOwner && agents.length > 0 && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">Agenter <span className="cowork-count">{agents.length}</span></div>
          <AgentDispatchPane view={activeAgentsToView(agents)} />
        </section>
      )}
      {isOwner && shareGuard.length > 0 && (
        <section className="cowork-pane">
          <div className="cowork-pane-head">Deling-guard <span className="cowork-count">{shareGuard.length}</span></div>
          <ShareGuardPane items={shareGuard} onResolve={resolveShare} />
        </section>
      )}
    </div>
  )

  const settingsZone = (
    <div className="cowork-settings">
      <AccountSection config={config} />
      {auth?.role === 'owner' && <TotpSetup config={config} />}
      {auth?.role === 'owner' && <PluginsPanel config={config} />}
    </div>
  )

  return (
    <div className="coworkview">
      <CoworkZones missionControl={missionControl} settings={settingsZone} />
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/jarvis-desk && npx vitest run src/views/CoworkView.test.tsx`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full frontend suite + typecheck**

Run: `cd apps/jarvis-desk && npx vitest run && npx tsc -b`
Expected: alle tests grønne, ingen type-fejl

- [ ] **Step 6: Commit**

```bash
git add apps/jarvis-desk/src/views/CoworkView.tsx apps/jarvis-desk/src/views/CoworkView.test.tsx
git commit -m "feat(desk): cowork to-zone command center — MC-grid + indstillingszone"
```

---

## Task 6: Styles + byg + installér

**Files:**
- Modify: `apps/jarvis-desk/src/styles.css` (find den faktiske globale css-fil — søg efter `.cowork-grid` for at finde den)

- [ ] **Step 1: Tilføj zone-styles**

Find filen der allerede definerer `.cowork-grid` (grep: `grep -rl "cowork-grid" apps/jarvis-desk/src`). Tilføj i samme fil:

```css
.cowork-zones { display: flex; height: 100%; }
.cowork-rail { display: flex; flex-direction: column; gap: 4px; padding: 12px 8px;
  border-right: 1px solid var(--border, #2a2a2a); min-width: 160px; }
.cowork-rail .rail-btn { text-align: left; padding: 8px 12px; border: none; border-radius: 8px;
  background: transparent; color: inherit; cursor: pointer; font-size: 0.95em; }
.cowork-rail .rail-btn.active { background: var(--accent-soft, #2a3550); font-weight: 600; }
.cowork-zone-body { flex: 1; overflow: auto; padding: 12px; }
.cowork-settings { display: flex; flex-direction: column; gap: 18px; max-width: 720px; }
.settings-section h3 { margin: 0 0 8px; }
.account-fields { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; }
.account-fields dt { opacity: 0.7; }
.account-fields dd { margin: 0; }
.badge { padding: 1px 8px; border-radius: 10px; font-size: 0.8em; }
.badge-ok { background: #1d3a24; color: #6ee7a0; }
.badge-warn { background: #3a2a1d; color: #e7b96e; }
```

- [ ] **Step 2: Byg + installér appen**

Run:
```bash
cd apps/jarvis-desk && npm run package:linux
sudo dpkg -i release/jarvis-desktop_*_amd64.deb
```
Expected: build færdig, deb installeret

- [ ] **Step 3: Commit**

```bash
git add apps/jarvis-desk/src/styles.css
git commit -m "style(desk): cowork zone-rail + account-sektion styling"
```

- [ ] **Step 4: Deploy backend til target**

Run:
```bash
git push target main
ssh 10.0.0.39 'sudo systemctl restart jarvis-api && sleep 3 && systemctl is-active jarvis-api'
```
Expected: `active`

---

## Self-Review

**1. Spec coverage (Plan 1's afgrænsede del):**
- §2 to zoner → Task 4 (CoworkZones) + Task 5 (integration). ✓
- §3 Mission Control → bevaret uændret som zone-indhold (Task 5). ✓ (interaktiv todo-CRUD er eksplicit Plan 2.)
- §4.1 Account (email, verifikation, sprog) → Task 1 (endpoint) + Task 3 (UI). ✓ TOTP/API-nøgler: TOTP genbruges (Task 5); API-nøgle-CRUD er Plan 3-scope (noteret).
- §7 member skjuler owner-only → Task 5 gater TotpSetup/PluginsPanel på `auth.role==='owner'`. ✓
- Øvrige §4-sektioner + §5 navigation → eksplicit andre planer (roadmap øverst). ✓

**2. Placeholder-scan:** Ingen TBD/TODO. Hvert kode-trin har fuld kode. Test-koden er konkret. ✓

**3. Type-konsistens:** `AccountProfile` defineres i Task 2 og bruges identisk i Task 3 og Task 5-test. `build_account_profile(user_id, *, get_user, get_tier)`-signaturen er ens i test (Task 1 step 1) og impl (step 3). `CoworkZones`-props (`missionControl`, `settings`) matcher mellem Task 4 og Task 5. ✓
