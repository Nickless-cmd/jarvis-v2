# Connectors / Marketplace v1 (GitHub) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levér en privat connector/Marketplace-oplevelse i jarvis-desk — bygget på det
allerede-live OAuth-fundament — med GitHub som første ende-til-ende connector, plus
token-renew, provider-revoke, mode-bevidst sidebar, Marketplace-zone og tids-bevidst
greeting-widget med connector-forslag.

**Architecture:** Backend (FastAPI + core/services) udvider det eksisterende
`oauth_store`/`oauth_flow`/`routes/oauth.py` med refresh+revoke, en connectors-registry
(`connectors.py` + `routes/connectors.py`), og GitHub-tools registreret gennem den
eksisterende tool-scoping (Spor A). Desk (React/Electron i `apps/jarvis-desk`) gør den
eksisterende `Sidebar` mode-bevidst (cowork-menu i stedet for 2. panel), tilføjer
`MarketplacePane`, og en greeting-widget i `ChatView`'s tom-state.

**Tech Stack:** Python 3.11 (conda `/opt/conda/envs/ai`, pytest, httpx) · React 19 +
TypeScript + Vite + lucide-react (vitest, tsc) · Electron (`shell.openExternal`).

**Konventioner:**
- Backend-test: `/opt/conda/envs/ai/bin/python -m pytest <fil> -q`
- Desk-test: `cd apps/jarvis-desk && npx vitest run <fil>` + `npx tsc -b`
- Deploy backend: `git push target main` + `ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api jarvis-runtime'`
- Deploy desk: **BUMP `apps/jarvis-desk/package.json` version FØR build** (dpkg no-op-fælde!) → `npm run package:linux` → `sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb`
- Secrets (github/google client id+secret) ligger ALLEREDE i `~/.jarvis-v2/config/runtime.json` på target.

---

## File Structure

**Backend — opret:**
- `core/services/connectors.py` — connector-katalog (v1: github + de lokale "findes-allerede") + per-bruger status (connected/enabled), enable/disable, delete (revoke+wipe).
- `core/services/github_connector.py` — GitHub API-klient + tool-handlers (list issues/PRs), bruger token fra oauth_store.
- `apps/api/jarvis_api/routes/connectors.py` — `GET /api/connectors`, `POST /api/connectors/{id}/enabled`, `DELETE /api/connectors/{id}`.

**Backend — modificér:**
- `core/services/oauth_flow.py` — tilføj `refresh_token()`, `revoke_remote()`, scope-eksponering; gem `expires_at` ved exchange.
- `core/services/oauth_store.py` — `get_fresh_token()` (auto-refresh on expiry).
- `apps/api/jarvis_api/app.py` — registrér connectors_router.
- `core/tools/simple_tools.py` — registrér github-tools i `_TOOL_HANDLERS` + tool-defs (gated af permission_engine; tilføj til member code-mode-sæt i `permission_engine.py` hvis members skal kunne).

**Desk — opret:**
- `src/lib/greeting.ts` — ren tids-bevidst greeting + random-pulje (testbar).
- `src/components/cowork/MarketplacePane.tsx` — Marketplace-zonen.
- `src/components/chat/GreetingHero.tsx` — tom-session greeting + connector-forslag.
- `src/lib/connectorsApi.ts` — fetch-wrappere (`getConnectors`, `setEnabled`, `deleteConnector`, `startConnect`).

**Desk — modificér:**
- `src/components/shell/Sidebar.tsx` — mode-bevidst: cowork → vis cowork-menu (ikoner) i stedet for session-liste.
- `src/components/cowork/CoworkZones.tsx` — drop intern `cowork-rail`; zone drives fra Sidebar via `lib/coworkZone.ts` (eksisterende `onZone`/`emitZone`), tilføj `'marketplace'` til `Zone`.
- `src/lib/coworkZone.ts` — udvid `Zone`-type med `'marketplace'`.
- `src/views/ChatView.tsx` — render `GreetingHero` i tom-state.
- `apps/jarvis-desk/package.json` — version-bump ved build.

---

## Phase A — Backend: renew + revoke

### Task A1: Gem expires_at ved code-exchange

**Files:**
- Modify: `core/services/oauth_flow.py` (`exchange_code`)
- Test: `tests/test_oauth_flow.py`

- [ ] **Step 1: Failing test** — exchange beriger token med `obtained_at`+`expires_at`.

```python
def test_exchange_code_adds_expiry(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "a", "expires_in": 3600, "refresh_token": "r"}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    tok = of.exchange_code("google", "c", now=1000.0)
    assert tok["expires_at"] == 1000.0 + 3600 and tok["refresh_token"] == "r"
```

- [ ] **Step 2: Run** `/opt/conda/envs/ai/bin/python -m pytest tests/test_oauth_flow.py::test_exchange_code_adds_expiry -q` → FAIL (now-param findes ikke).

- [ ] **Step 3: Implement** — `exchange_code(provider, code, *, now=None)`: efter `tok = r.json()`, hvis `expires_in` i tok → `tok["obtained_at"] = float(now or time.time()); tok["expires_at"] = tok["obtained_at"] + float(tok["expires_in"])`. Returnér tok.

- [ ] **Step 4: Run** → PASS. Kør hele filen: `pytest tests/test_oauth_flow.py -q`.

- [ ] **Step 5: Commit** `git add core/services/oauth_flow.py tests/test_oauth_flow.py && git commit -m "feat(oauth): gem expires_at ved code-exchange"`

### Task A2: refresh_token() i oauth_flow

**Files:**
- Modify: `core/services/oauth_flow.py`
- Test: `tests/test_oauth_flow.py`

- [ ] **Step 1: Failing test**

```python
def test_refresh_token(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "new", "expires_in": 3600}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    tok = of.refresh_token("google", "refresh-abc", now=1000.0)
    assert tok["access_token"] == "new" and tok["expires_at"] == 4600.0
    assert tok["refresh_token"] == "refresh-abc"  # bevares hvis provider ikke returnerer ny
```

- [ ] **Step 2: Run** → FAIL (no attribute refresh_token).

- [ ] **Step 3: Implement**

```python
def refresh_token(provider: str, refresh: str, *, now=None) -> dict | None:
    prov = (provider or "").strip().lower()
    p = _PROVIDERS.get(prov)
    if not p or not (refresh or "").strip():
        return None
    data = {"client_id": _secret(p["id_key"]), "client_secret": _secret(p["secret_key"]),
            "grant_type": "refresh_token", "refresh_token": refresh}
    try:
        import httpx
        r = httpx.post(p["token_url"], data=data, headers={"Accept": "application/json"}, timeout=20)
        if r.status_code != 200:
            return None
        tok = r.json()
        if not isinstance(tok, dict) or not tok.get("access_token"):
            return None
        tok.setdefault("refresh_token", refresh)  # GitHub/Google sender ikke altid ny
        if tok.get("expires_in"):
            base = float(now if now is not None else time.time())
            tok["obtained_at"] = base
            tok["expires_at"] = base + float(tok["expires_in"])
        return tok
    except Exception:
        return None
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(oauth): refresh_token via grant_type=refresh_token"`

### Task A3: revoke_remote() i oauth_flow

**Files:** Modify `core/services/oauth_flow.py` · Test `tests/test_oauth_flow.py`

- [ ] **Step 1: Failing test**

```python
def test_revoke_remote_google(monkeypatch):
    calls = {}
    import httpx
    def _post(url, **k): calls["url"] = url; calls["data"] = k.get("data") or k.get("params")
    class _R: status_code = 200
    monkeypatch.setattr(httpx, "post", lambda url, **k: (_post(url, **k), _R())[1])
    assert of.revoke_remote("google", {"access_token": "tok"}) is True
    assert "oauth2.googleapis.com/revoke" in calls["url"]
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — `revoke_remote(provider, token: dict) -> bool`:
  - Google: `httpx.post("https://oauth2.googleapis.com/revoke", data={"token": token.get("access_token")}, timeout=15)` → True hvis 200.
  - GitHub: `httpx.delete(f"https://api.github.com/applications/{client_id}/grant", auth=(client_id, client_secret), json={"access_token": token.get("access_token")}, timeout=15)` → True hvis status i (204, 404). (404 = allerede væk.)
  - Ukendt/fejl → return False (lokal wipe sker alligevel i kalderen).

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(oauth): revoke_remote — tilbagekald token hos provider"`

### Task A4: get_fresh_token() i oauth_store (auto-refresh on expiry)

**Files:** Modify `core/services/oauth_store.py` · Test `tests/test_oauth_store.py`

- [ ] **Step 1: Failing test**

```python
def test_get_fresh_token_refreshes_when_expired(monkeypatch):
    _setup(monkeypatch)  # in-memory store + distinkt nøgle
    import core.services.oauth_flow as of
    ov.save_token("alice", "google", {"access_token": "old", "refresh_token": "r", "expires_at": 100.0})
    monkeypatch.setattr(of, "refresh_token", lambda prov, refresh, now=None: {"access_token": "new", "refresh_token": refresh, "expires_at": 9999.0})
    tok = ov.get_fresh_token("alice", "google", now=200.0)  # 200 > 100 → udløbet
    assert tok["access_token"] == "new"
    assert ov.get_token("alice", "google")["access_token"] == "new"  # re-saved
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — `get_fresh_token(user_id, provider, *, now=None) -> dict | None`:
  - `tok = get_token(...)`; hvis None → None.
  - hvis `tok.get("expires_at")` og `float(now or time.time()) >= float(expires_at) - 60` og `tok.get("refresh_token")`:
    - `from core.services.oauth_flow import refresh_token as _rt`
    - `new = _rt(provider, tok["refresh_token"], now=now)`; hvis new → `save_token(user_id, provider, new); return new`.
  - return tok (gyldig eller ikke-refreshbar).

- [ ] **Step 4: Run** → PASS. Kør `pytest tests/test_oauth_store.py -q`.
- [ ] **Step 5: Commit** `git commit -am "feat(oauth): get_fresh_token — auto-refresh ved udløb"`

---

## Phase B — Backend: connectors-registry + API

### Task B1: connectors-katalog + status

**Files:** Create `core/services/connectors.py` · Test `tests/test_connectors.py`

- [ ] **Step 1: Failing test**

```python
import core.services.connectors as cx
def test_catalog_status(monkeypatch):
    store = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))
    monkeypatch.setattr(dbc, "set_runtime_state_value", lambda k, v, **kw: store.__setitem__(k, v))
    import core.services.oauth_store as ov
    monkeypatch.setattr(cx, "has_token", lambda uid, pid: pid == "github")
    items = cx.list_for_user("alice")
    gh = next(i for i in items if i["id"] == "github")
    assert gh["connected"] is True and gh["kind"] == "oauth"
    assert gh["enabled"] is True  # default on
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — `_CATALOG` (v1: liste af dicts: github (oauth, scopes ["repo","read:user"]) + de lokale findes-allerede: computer-use/browser/read-aloud/superpowers (kind="local")). `list_for_user(user_id)` returnerer hver med `connected` (oauth: `oauth_store.has_token`; local: True), `enabled` (runtime_state `connector_enabled.{uid}.{id}`, default True), `scopes`, `category`, `icon`, `kind`, `desc`. `set_enabled(uid, id, enabled)` + `is_enabled(uid, id)` (runtime_state). Importér `has_token` på modul-niveau (så testen kan monkeypatche `cx.has_token`).

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(connectors): katalog + per-bruger status/enable"`

### Task B2: delete = provider-revoke + lokal wipe

**Files:** Modify `core/services/connectors.py` · Test `tests/test_connectors.py`

- [ ] **Step 1: Failing test**

```python
def test_delete_revokes_then_wipes(monkeypatch):
    calls = {}
    monkeypatch.setattr(cx, "get_fresh_token", lambda uid, pid: {"access_token": "t"})
    import core.services.oauth_flow as of
    monkeypatch.setattr(of, "revoke_remote", lambda prov, tok: calls.setdefault("revoked", True) or True)
    import core.services.oauth_store as ov
    monkeypatch.setattr(ov, "revoke_token", lambda uid, pid: calls.setdefault("wiped", True) or True)
    assert cx.delete_for_user("alice", "github") is True
    assert calls == {"revoked": True, "wiped": True}
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `delete_for_user(uid, id)`: hent token (get_fresh_token); hvis token → `oauth_flow.revoke_remote(id, token)` (best-effort); så `oauth_store.revoke_token(uid, id)` + ryd enabled-flag. Audit-log (`_audit`). Return True.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(connectors): delete revoker hos provider + wiper lokalt (GDPR)"`

### Task B3: connectors-routes

**Files:** Create `apps/api/jarvis_api/routes/connectors.py` · Modify `app.py` · Test `tests/test_connectors_routes.py`

- [ ] **Step 1: Failing test** (TestClient + monkeypatch current_user_id + cx.list_for_user)

```python
def test_get_connectors_requires_auth(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    assert client.get("/api/connectors").status_code == 401

def test_get_connectors_lists(monkeypatch):
    import core.identity.workspace_context as wc
    import apps.api.jarvis_api.routes.connectors as cr
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    monkeypatch.setattr(cr, "list_for_user", lambda uid: [{"id": "github", "connected": True}])
    r = client.get("/api/connectors")
    assert r.status_code == 200 and r.json()["connectors"][0]["id"] == "github"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `GET /api/connectors` (auth: current_user_id eller 401 → `{connectors: list_for_user(uid)}`), `POST /api/connectors/{id}/enabled` body `{enabled: bool}` → `set_enabled`, `DELETE /api/connectors/{id}` → `delete_for_user`. Registrér i `app.py` (`from ...routes.connectors import router as connectors_router; app.include_router(connectors_router)`).
- [ ] **Step 4: Run** → PASS. Compile: `python -m compileall apps/api/jarvis_api/routes/connectors.py apps/api/jarvis_api/app.py -q`.
- [ ] **Step 5: Commit** `git commit -am "feat(connectors): GET/POST-enabled/DELETE routes"`

### Task B4: GitHub-connector-tools (Spor A-scopet)

**Files:** Create `core/services/github_connector.py` · Modify `core/tools/simple_tools.py` + `core/services/permission_engine.py` · Test `tests/test_github_connector.py`

- [ ] **Step 1: Failing test** — `github_list_issues` bruger fresh token + kalder GitHub.

```python
import core.services.github_connector as gh
def test_list_issues(monkeypatch):
    monkeypatch.setattr(gh, "get_fresh_token", lambda uid, pid="github": {"access_token": "t"})
    import httpx
    class _R:
        status_code = 200
        def json(self): return [{"number": 1, "title": "Bug", "state": "open"}]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    out = gh.list_issues("alice", repo="o/r")
    assert out["status"] == "ok" and out["issues"][0]["title"] == "Bug"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `github_connector.list_issues(user_id, repo)` (GET `https://api.github.com/repos/{repo}/issues` m. `Authorization: Bearer <token>`); fejl → `{"status":"error","error":"github_not_connected"}` hvis intet token. Tilsvarende `list_prs`. Tool-wrappere i `simple_tools` (`github_list_issues`-handler resolverer `_operator_user_id(args)` → kalder connector). Registrér i `_TOOL_HANDLERS` + tool-def. Tilføj `github_list_issues`/`github_list_prs` til member code-mode-sættet i `permission_engine._MEMBER_CODE` (så members kan bruge deres egen connector; gated yderligere af enabled+connected).
- [ ] **Step 4: Run** → PASS + `pytest tests/test_permission_engine.py tests/test_tool_enforcement.py -q` (ingen regression).
- [ ] **Step 5: Commit** `git commit -am "feat(connectors): GitHub-tools (issues/PRs) scopet til Spor A"`

### Task B5: Deploy backend + live-verifikation (CHECK-IN)

- [ ] `git push origin main && git push target main`
- [ ] `ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api jarvis-runtime && sleep 4 && systemctl is-active jarvis-api jarvis-runtime'`
- [ ] Live: `curl -H "Authorization: Bearer <member-token>" http://localhost:8080/api/connectors` → 200 m. github connected=false. **STOP og check ind med Bjørn.**

---

## Phase C — Desk: Sidebar mode-bevidst (fjern dobbelt-panel)

### Task C1: Udvid Zone-type + cowork-menu-konstant

**Files:** Modify `src/lib/coworkZone.ts` · Test `src/lib/coworkZone.test.ts`

- [ ] **Step 1: Failing test** — `'marketplace'` er en gyldig Zone (type-niveau: tilføj en runtime-liste `COWORK_ZONES` at teste mod).

```ts
import { COWORK_ZONES } from './coworkZone'
it('har marketplace-zone', () => { expect(COWORK_ZONES.map(z => z.id)).toContain('marketplace') })
```

- [ ] **Step 2: Run** `npx vitest run src/lib/coworkZone.test.ts` → FAIL.
- [ ] **Step 3: Implement** — udvid `Zone = 'mc' | 'marketplace' | 'settings'`; eksportér `COWORK_ZONES = [{id:'mc',label:'Mission Control',icon:'LayoutDashboard'},{id:'marketplace',label:'Marketplace',icon:'Blocks'},{id:'settings',label:'Indstillinger',icon:'Settings'}]`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): marketplace-zone + COWORK_ZONES m. ikoner"`

### Task C2: Sidebar viser cowork-menu i cowork-surface

**Files:** Modify `src/components/shell/Sidebar.tsx` · Test `src/components/shell/Sidebar.cowork.test.tsx`

- [ ] **Step 1: Failing test** — i cowork-surface render Sidebar menu-punkterne (Mission Control/Marketplace/Indstillinger), IKKE session-listen.

```tsx
it('viser cowork-menu i cowork-surface', () => {
  render(<Sidebar surface="cowork" onSurface={() => {}} userName="Bjørn" />)
  expect(screen.getByText('Marketplace')).toBeInTheDocument()
  expect(screen.queryByText('Ny samtale')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — i `Sidebar`, efter `<ModeSlider>`: hvis `surface === 'cowork'` render en `<nav className="cowork-menu">` der mapper `COWORK_ZONES` til knapper (lucide-ikon + label) der kalder `emitZone(z.id)` (fra `lib/coworkZone`) + lokal active-state; ELLERS render den eksisterende `.sessions`-blok. (Behold alt session-relateret uændret i else-grenen.)
- [ ] **Step 4: Run** → PASS + `npx tsc -b`.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): Sidebar mode-bevidst — cowork-menu m. ikoner i eksisterende panel"`

### Task C3: Fjern CoworkZones intern rail

**Files:** Modify `src/components/cowork/CoworkZones.tsx` · Test `src/components/cowork/CoworkZones.test.tsx`

- [ ] **Step 1: Failing test** — CoworkZones renderer IKKE længere sin egen rail (ingen 'rail-btn'); zone styres via `onZone`.

```tsx
it('har ingen intern rail', () => {
  const { container } = render(<CoworkZones>{(z) => <div>{z}</div>}</CoworkZones>)
  expect(container.querySelector('.cowork-rail')).toBeNull()
})
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — fjern `<nav className="cowork-rail">`-blokken; behold `useState<Zone>('mc')` + `useEffect(() => onZone(setZone), [])` + render-prop/children for den aktive zone. (Zone-skift kommer nu fra Sidebar via `emitZone`.)
- [ ] **Step 4: Run** → PASS + `npx tsc -b`.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): fjern CoworkZones intern rail (ét panel)"`

---

## Phase D — Desk: Marketplace-zone

### Task D1: connectorsApi.ts

**Files:** Create `src/lib/connectorsApi.ts` · Test `src/lib/connectorsApi.test.ts`

- [ ] **Step 1: Failing test** — `getConnectors` kalder `/api/connectors` og returnerer listen (mock fetch via apiFetch).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `getConnectors(config)`, `setEnabled(config,id,enabled)`, `deleteConnector(config,id)`, `startConnect(config,id)` (GET `/api/oauth/{id}/start` → `{authorize_url}`). Genbrug `apiFetch` fra `lib/api.ts`.
- [ ] **Step 4: Run** → PASS + tsc.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): connectorsApi-wrappere"`

### Task D2: MarketplacePane

**Files:** Create `src/components/cowork/MarketplacePane.tsx` · Test `MarketplacePane.test.tsx`

- [ ] **Step 1: Failing test** — viser "Forbundet"-sektion + grid; klik "Forbind" kalder `startConnect` + `window.jarvisDesk.openExternal(url)`; ⋯→slet kalder `deleteConnector`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — fetch `getConnectors` ved mount; render forbundne øverst (grøn ●) + grid; "Forbind" → `startConnect` → `openExternal` → poll `getConnectors` til connected; status-pills (forbundet/forbind/aktiv); ⋯-menu (slå fra → `setEnabled`; afbryd & slet → `deleteConnector`); vis `scopes` i en tooltip/linje ("beder om: repo, read:user"). Søgefelt-filter.
- [ ] **Step 4: Run** → PASS + tsc.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): MarketplacePane — forbind/til-fra/slet + scope-transparens"`

### Task D3: Wire MarketplacePane i CoworkZones

**Files:** Modify `src/views/CoworkView.tsx` / `CoworkZones.tsx`

- [ ] **Step 1:** zone `'marketplace'` → render `<MarketplacePane config={config}/>`; `'mc'` → eksisterende grid; `'settings'` → eksisterende settings. **Step 2:** `npx tsc -b` + relevante vitest grønne. **Step 3:** Commit.

---

## Phase E — Desk: greeting-widget + post-connect-hook

### Task E1: greeting.ts (ren, testbar)

**Files:** Create `src/lib/greeting.ts` · Test `src/lib/greeting.test.ts`

- [ ] **Step 1: Failing test**

```ts
import { greetingFor } from './greeting'
it('aften → måne + Godaften', () => {
  const g = greetingFor(new Date('2026-06-16T20:00:00'), 0)  // seed 0 = deterministisk
  expect(g.glyph).toBe('🌙'); expect(g.hello).toBe('Godaften')
})
it('morgen → soldopgang', () => {
  expect(greetingFor(new Date('2026-06-16T07:00:00'), 0).glyph).toBe('🌅')
})
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `greetingFor(now: Date, seed: number)`: bucket fra `now.getHours()` (5-10 morgen 🌅 Godmorgen / 10-14 dag ☀️ "God dag" / 14-18 eftermiddag 🌆 "God eftermiddag" / 18-23 aften 🌙 Godaften / ellers 🌙 nat); vælg `line` fra en pulje pr. bucket via `seed % pool.length`; returnér `{glyph, hello, line, tint}` (tint = hex til presence-ring pr. bucket).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): tids-bevidst greeting m. random-pulje + tint"`

### Task E2: GreetingHero + connector-forslag

**Files:** Create `src/components/chat/GreetingHero.tsx` · Modify `src/views/ChatView.tsx` · Test `GreetingHero.test.tsx`

- [ ] **Step 1: Failing test** — tom session: viser greeting (glyph+hello) + op til 3 *ikke-forbundne* connector-forslag + "Flere apps →" der kalder `emitZone('marketplace')` + skifter surface til cowork.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — `GreetingHero`: `greetingFor(new Date(), Math.floor(Math.random()*1000))`, presence-ring tonet med `tint`; fetch `getConnectors`, filtrér `!connected && kind==='oauth'`, vis 3; "Forbind" → samme flow som MarketplacePane; "Flere apps →" → skift til cowork + `emitZone('marketplace')`. Render i `ChatView` når sessionen er tom (ingen beskeder).
- [ ] **Step 4: Run** → PASS + tsc.
- [ ] **Step 5: Commit** `git commit -am "feat(desk): GreetingHero — tids-greeting + connector-forslag i tom session"`

### Task E3: Post-connect-hook (delight)

**Files:** Modify backend `routes/oauth.py` (allerede emitter `oauth.connected`) + desk `MarketplacePane`/`GreetingHero`

- [ ] **Step 1:** Efter succesfuld connect (poll ser `connected`), vis toast "✅ Forbundet til GitHub" + sæt en lokal flag der ved næste chat-fokus indsætter et **forslag** i composeren: *"Nu kan jeg kigge i dine GitHub-issues — skal jeg?"* (connector-specifik tekst fra katalog-feltet `post_connect_hint`). **Step 2:** vitest for at hint vises. **Step 3:** Commit.

---

## Phase F — Build, deploy, verifikation

### Task F1: Desk build + deploy (HUSK version-bump)

- [ ] `cd apps/jarvis-desk && npx vitest run && npx tsc -b` → alt grønt.
- [ ] **Bump `package.json` version** (fx 0.2.25 → 0.2.26) — ELLERS no-op'er dpkg.
- [ ] `npm run package:linux`
- [ ] `sudo dpkg -i release/jarvis-desktop_<v>_amd64.deb` → verificér output viser **"Udpakker ... over ..."** (ikke kun "Sætter op") + `ls -la /opt/Jarvis/jarvis-desktop` (frisk mtime).
- [ ] Commit version-bump.

### Task F2: Manuel e2e (med Bjørn)

- [ ] Bjørn åbner cowork → Marketplace → "Forbind GitHub" → browser-OAuth → godkend → vindue lukker → connector viser ●&nbsp;forbundet.
- [ ] Tom session → greeting m. korrekt tidspunkt-glyf + forslag.
- [ ] Bed Jarvis: "vis mine github-issues" → tool kører (token fra hvælvet).
- [ ] ⋯ → afbryd & slet → token revokes hos GitHub + forsvinder.

---

## Self-Review

**Spec-dækning:** §3.1 connectors-API → B1-B3 ✓ · §3.2 sidebar-mode → C2-C3 ✓ · §3.3
Marketplace → D1-D3 ✓ · §3.4 greeting → E1-E2 ✓ · §10A renew → A1-A2,A4 ✓ · §10B revoke
→ A3,B2 ✓ · §10D scope-transparens → D2 ✓ · §12 post-connect-hook → E3 ✓. **v2+ (egne
MCP, Google-pakke, øvrige connectors, §10C state-single-use, §10E owner-gating-global,
§10G audit-udvidelse): IKKE i denne plan** — noteret som opfølgning.
**Placeholders:** ingen "TBD". **Type-konsistens:** `get_fresh_token`, `refresh_token`,
`revoke_remote`, `list_for_user`, `set_enabled`, `delete_for_user`, `Zone`/`COWORK_ZONES`,
`greetingFor` brugt konsistent på tværs af tasks.

**Note:** §10C (state single-use) + §10E (global owner-gating) + §10G (audit) er små og
hører til v1.1 — tilføj som hurtige opfølgnings-tasks hvis Bjørn vil have dem i v1.
