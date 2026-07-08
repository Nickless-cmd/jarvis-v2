---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Mobil Auto-updater Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mobilappen detekterer en nyere version fra et eget srvlab.dk-endpoint, viser en banner, og installerer den hentede APK via systemets install-dialog — så manuel adb-bygge/installer-smerte forsvinder.

**Architecture:** Backend tilføjer to auth-scopede routes (`/mobile/latest` manifest + `/mobile/download` FileResponse) der læser fra `~/.jarvis-v2/mobile/`. Mobilklienten får ren testbar logik (`appUpdate.ts`), tynd native-wiring (`installApk.ts`), en banner (`UpdateBanner.tsx`), og et app-niveau-check ved opstart + foreground i `App.tsx`. Bootstrap: første version MED updateren installeres manuelt én gang via adb; derefter OTA.

**Tech Stack:** Backend: FastAPI, `FileResponse`, pytest + TestClient (conda `ai`). Mobil: React Native/Expo bare, jest (jest-expo) + `tsc --noEmit`, tre nye Expo-moduler (`expo-application`, `expo-file-system`, `expo-intent-launcher`).

**Vigtige stier:**
- Hovedrepo (backend): `/media/projects/jarvis-v2` — kør med `conda activate ai`.
- Worktree (mobil): `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile` — gren `codex/jarvis-mobile-companion-v1`. Commit her ALTID via `git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 ...`.
- Spec: `docs/superpowers/specs/2026-06-20-mobile-auto-updater-design.md`.

**Constraints:**
- De eksisterende ~94 jest-tests SKAL forblive grønne; `tsc --noEmit` clean.
- Backend-routes følger `presence.py`-mønstret (`_current_user()` via `current_user_id()`).
- `~/.jarvis-v2/mobile/`-stien resolves ved KALD-tid via `JARVIS_HOME`-env, så pytest kan override med `monkeypatch.setenv("JARVIS_HOME", tmp)`.

---

## File Structure

**Backend (hovedrepo):**
- Create: `apps/api/jarvis_api/routes/mobile_update.py` — de to routes + `_mobile_dir()` helper.
- Create: `tests/test_mobile_update_routes.py` — TestClient-tests for begge endpoints.
- Modify: `apps/api/jarvis_api/app.py` — registrér routeren.

**Mobil (worktree, alt under `apps/mobile/`):**
- Create: `src/lib/appUpdate.ts` — `compareVersion` + `checkForUpdate` (ren logik).
- Create: `src/lib/appUpdate.test.ts` — jest for begge.
- Create: `src/lib/installApk.ts` — `downloadAndInstall` (tynd native-wiring).
- Create: `src/components/UpdateBanner.tsx` — banner-UI.
- Modify: `src/App.tsx` — check ved opstart + foreground, montér banner.
- Modify: `android/app/src/main/AndroidManifest.xml` — `REQUEST_INSTALL_PACKAGES`.
- Modify: `package.json` — tre nye deps.
- Modify: `jest.setup.js` — mocks for de tre nye Expo-moduler.
- Modify: `app.json` + `android/app/build.gradle` — versions-bump ved bootstrap.

---

## Task 1: Backend `/mobile/latest` manifest-endpoint

**Files:**
- Create: `apps/api/jarvis_api/routes/mobile_update.py`
- Test: `tests/test_mobile_update_routes.py`

- [ ] **Step 1: Write the failing test**

`tests/test_mobile_update_routes.py`:

```python
"""Tests for mobil auto-updater routes (/mobile/latest + /mobile/download)."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.mobile_update as mod


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # auth: lad enhver kalder være en gyldig bruger
    monkeypatch.setattr(mod, "_current_user", lambda: "1246415163603816499")
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def test_latest_empty_when_no_manifest(monkeypatch, tmp_path) -> None:
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/latest")
    assert r.status_code == 200
    assert r.json() == {}


def test_latest_returns_manifest(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {
                "version": "0.1.29",
                "version_code": 30,
                "notes": "Test-noter",
                "filename": "jarvis-mobile-30.apk",
            }
        ),
        encoding="utf-8",
    )
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["version_code"] == 30
    assert body["filename"] == "jarvis-mobile-30.apk"


def test_latest_unauthenticated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr(mod, "_current_user", lambda: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)
    assert c.get("/mobile/latest").json() == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_mobile_update_routes.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.api.jarvis_api.routes.mobile_update'`

- [ ] **Step 3: Write minimal implementation**

`apps/api/jarvis_api/routes/mobile_update.py`:

```python
"""Mobil auto-updater: manifest + APK-download. Auth-scopet til en bruger.

Læser fra ~/.jarvis-v2/mobile/ (latest.json + APK-fil). Stien resolves ved
kald-tid via JARVIS_HOME, så tests kan override med monkeypatch.setenv.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["mobile-update"])


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


def _mobile_dir() -> Path:
    home = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(home) / "mobile"


@router.get("/mobile/latest")
async def mobile_latest() -> dict:
    if not _current_user():
        return {}
    manifest = _mobile_dir() / "latest.json"
    if not manifest.exists():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mobile_update_routes.py -q`
Expected: PASS (3 tests — `test_latest_*`)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/routes/mobile_update.py tests/test_mobile_update_routes.py
git commit -m "feat(api): /mobile/latest manifest-endpoint for auto-updater"
```

---

## Task 2: Backend `/mobile/download` APK-endpoint

**Files:**
- Modify: `apps/api/jarvis_api/routes/mobile_update.py`
- Test: `tests/test_mobile_update_routes.py`

- [ ] **Step 1: Write the failing test (append to test file)**

```python
def test_download_serves_apk(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {"version": "0.1.29", "version_code": 30, "notes": "", "filename": "jarvis-mobile-30.apk"}
        ),
        encoding="utf-8",
    )
    (mobile / "jarvis-mobile-30.apk").write_bytes(b"PK\x03\x04 fake apk bytes")
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/download")
    assert r.status_code == 200
    assert r.content == b"PK\x03\x04 fake apk bytes"
    assert r.headers["content-type"] == "application/vnd.android.package-archive"


def test_download_404_when_missing(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {"version": "0.1.29", "version_code": 30, "notes": "", "filename": "jarvis-mobile-30.apk"}
        ),
        encoding="utf-8",
    )
    # APK-filen mangler bevidst
    c = _client(monkeypatch, tmp_path)
    assert c.get("/mobile/download").status_code == 404


def test_download_404_when_no_manifest(monkeypatch, tmp_path) -> None:
    c = _client(monkeypatch, tmp_path)
    assert c.get("/mobile/download").status_code == 404


def test_download_unauthenticated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr(mod, "_current_user", lambda: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)
    assert c.get("/mobile/download").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mobile_update_routes.py -k download -q`
Expected: FAIL with 404/405 (route ikke defineret endnu — faktisk 404 from FastAPI for unknown path; assertions på content-type fejler)

- [ ] **Step 3: Write minimal implementation (append to mobile_update.py)**

```python
@router.get("/mobile/download")
async def mobile_download() -> FileResponse:
    if not _current_user():
        raise HTTPException(status_code=401, detail="auth required")
    manifest = _mobile_dir() / "latest.json"
    if not manifest.exists():
        raise HTTPException(status_code=404, detail="no manifest")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        filename = Path(str(data.get("filename") or "")).name
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="bad manifest")
    if not filename:
        raise HTTPException(status_code=404, detail="no filename")
    apk = _mobile_dir() / filename
    if not apk.exists():
        raise HTTPException(status_code=404, detail="apk missing")
    return FileResponse(
        path=apk,
        filename=filename,
        media_type="application/vnd.android.package-archive",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mobile_update_routes.py -q`
Expected: PASS (alle 7 tests)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/routes/mobile_update.py tests/test_mobile_update_routes.py
git commit -m "feat(api): /mobile/download APK FileResponse for auto-updater"
```

---

## Task 3: Registrér routeren i app.py

**Files:**
- Modify: `apps/api/jarvis_api/app.py` (nær linje 487-488, hvor `presence_router` registreres)

- [ ] **Step 1: Tilføj import + include_router**

Find blokken (omkring linje 487):

```python
    from apps.api.jarvis_api.routes.presence import router as presence_router
    app.include_router(presence_router)
```

Tilføj umiddelbart efter `app.include_router(presence_router)`:

```python
    from apps.api.jarvis_api.routes.mobile_update import router as mobile_update_router
    app.include_router(mobile_update_router)
```

- [ ] **Step 2: Verificér at app importerer rent**

Run: `cd /media/projects/jarvis-v2 && python -c "from apps.api.jarvis_api.app import app; print('routes:', any(getattr(r,'path','')=='/mobile/latest' for r in app.routes))"`
Expected: `routes: True`

- [ ] **Step 3: Kør hele backend-test-suiten for de nye routes igen mod den rigtige app er ikke nødvendig (testen bygger sin egen app). Smoke-compile:**

Run: `python -m compileall apps/api/jarvis_api/routes/mobile_update.py apps/api/jarvis_api/app.py`
Expected: ingen fejl

- [ ] **Step 4: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/api/jarvis_api/app.py
git commit -m "feat(api): registrér mobile_update-router"
```

---

## Task 4: Mobil `compareVersion` (ren logik)

**Files:**
- Create: `src/lib/appUpdate.ts`
- Test: `src/lib/appUpdate.test.ts`

Alle kommandoer kører fra `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`.

- [ ] **Step 1: Write the failing test**

`src/lib/appUpdate.test.ts`:

```typescript
import { compareVersion } from './appUpdate'

describe('compareVersion', () => {
  it('true når manifest er nyere', () => {
    expect(compareVersion(28, { version_code: 30 })).toBe(true)
  })
  it('false når manifest er samme', () => {
    expect(compareVersion(30, { version_code: 30 })).toBe(false)
  })
  it('false når manifest er ældre', () => {
    expect(compareVersion(31, { version_code: 30 })).toBe(false)
  })
  it('false når version_code mangler', () => {
    expect(compareVersion(28, {})).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest src/lib/appUpdate.test.ts`
Expected: FAIL — `Cannot find module './appUpdate'`

- [ ] **Step 3: Write minimal implementation**

`src/lib/appUpdate.ts`:

```typescript
import type { ApiConfig } from './types'

export interface UpdateManifest {
  version: string
  version_code: number
  notes: string
  filename: string
}

/** true hvis manifestets version_code er strengt højere end den installerede. */
export function compareVersion(installedVc: number, manifest: { version_code?: number }): boolean {
  const remote = manifest.version_code
  if (typeof remote !== 'number') return false
  return remote > installedVc
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/lib/appUpdate.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/appUpdate.ts apps/mobile/src/lib/appUpdate.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): compareVersion for auto-updater"
```

---

## Task 5: Mobil `checkForUpdate` (fetch-logik)

**Files:**
- Modify: `src/lib/appUpdate.ts`
- Test: `src/lib/appUpdate.test.ts`

- [ ] **Step 1: Write the failing test (append)**

```typescript
import { checkForUpdate } from './appUpdate'

const cfg = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'tok' }

function mockFetch(status: number, body: unknown) {
  return jest.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })) as unknown as typeof fetch
}

describe('checkForUpdate', () => {
  afterEach(() => jest.restoreAllMocks())

  it('returnerer manifest når nyere', async () => {
    global.fetch = mockFetch(200, { version: '0.1.29', version_code: 30, notes: 'n', filename: 'a.apk' })
    const r = await checkForUpdate(cfg, 28)
    expect(r?.version_code).toBe(30)
  })

  it('returnerer null når samme version', async () => {
    global.fetch = mockFetch(200, { version: '0.1.29', version_code: 30, notes: 'n', filename: 'a.apk' })
    expect(await checkForUpdate(cfg, 30)).toBeNull()
  })

  it('returnerer null på tomt manifest', async () => {
    global.fetch = mockFetch(200, {})
    expect(await checkForUpdate(cfg, 28)).toBeNull()
  })

  it('returnerer null ved fetch-fejl', async () => {
    global.fetch = jest.fn(async () => { throw new Error('network') }) as unknown as typeof fetch
    expect(await checkForUpdate(cfg, 28)).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest src/lib/appUpdate.test.ts -t checkForUpdate`
Expected: FAIL — `checkForUpdate is not a function` / import-fejl

- [ ] **Step 3: Write minimal implementation (append to appUpdate.ts)**

```typescript
/**
 * Henter /mobile/latest og returnerer manifestet hvis det er nyere end
 * `installedVc`, ellers null. Alle fejl (netværk, ikke-ok, malformet) → null.
 */
export async function checkForUpdate(
  config: ApiConfig,
  installedVc: number
): Promise<UpdateManifest | null> {
  try {
    const url = new URL('/mobile/latest', config.apiBaseUrl).toString()
    const r = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
    })
    if (!r.ok) return null
    const data = (await r.json()) as Partial<UpdateManifest>
    if (!compareVersion(installedVc, data)) return null
    return data as UpdateManifest
  } catch {
    return null
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/lib/appUpdate.test.ts`
Expected: PASS (8 tests total)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/appUpdate.ts apps/mobile/src/lib/appUpdate.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): checkForUpdate fetch-logik"
```

---

## Task 6: Tilføj de tre Expo-deps + jest-mocks

**Files:**
- Modify: `package.json`
- Modify: `jest.setup.js`

- [ ] **Step 1: Installér de tre moduler (autolinker via Expo config-plugin)**

Run (fra `apps/mobile`):
```bash
npx expo install expo-application expo-file-system expo-intent-launcher
```
Expected: tre nye linjer i `package.json` `dependencies` (versioner styret af Expo SDK).

Hvis `npx expo install` ikke er tilgængeligt i miljøet, tilføj manuelt til `package.json` `dependencies` (matchende eksisterende `~56`-linje for de andre expo-moduler):
```json
    "expo-application": "~56.0.0",
    "expo-file-system": "~56.0.0",
    "expo-intent-launcher": "~56.0.0",
```
og kør `npm install`.

- [ ] **Step 2: Tilføj jest-mocks (så App/UpdateBanner kan loades i jest)**

Append til `jest.setup.js`:

```javascript
jest.mock('expo-application', () => ({
  __esModule: true,
  nativeBuildVersion: '28',
}))

jest.mock('expo-file-system', () => ({
  __esModule: true,
  documentDirectory: 'file:///doc/',
  createDownloadResumable: jest.fn(() => ({
    downloadAsync: jest.fn(async () => ({ uri: 'file:///doc/app.apk' })),
  })),
  getContentUriAsync: jest.fn(async () => 'content://app.apk'),
}))

jest.mock('expo-intent-launcher', () => ({
  __esModule: true,
  startActivityAsync: jest.fn(async () => undefined),
}))
```

- [ ] **Step 3: Verificér at eksisterende tests stadig loader**

Run: `npx jest 2>&1 | tail -15`
Expected: alle eksisterende suites grønne (mocks brækker ikke noget)

- [ ] **Step 4: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/package.json apps/mobile/package-lock.json apps/mobile/jest.setup.js
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "build(mobile): expo-application/file-system/intent-launcher + jest-mocks"
```

---

## Task 7: Mobil `installApk.ts` (native-wiring)

**Files:**
- Create: `src/lib/installApk.ts`

Dette er tynd native-wiring (ingen ren logik at unit-teste — mocks i jest.setup dækker importerbarhed). Vi tilføjer en lille importerbarheds-test for at fange syntaks/typefejl.

- [ ] **Step 1: Write the implementation**

`src/lib/installApk.ts`:

```typescript
import * as FileSystem from 'expo-file-system'
import * as IntentLauncher from 'expo-intent-launcher'
import type { ApiConfig } from './types'
import type { UpdateManifest } from './appUpdate'

const GRANT_READ_URI_PERMISSION = 1

/**
 * Henter APK'en fra /mobile/download (med auth-header, progress via onProgress)
 * og fyrer systemets install-intent. Kaster ved fejl (UI viser fejl-toast).
 */
export async function downloadAndInstall(
  config: ApiConfig,
  manifest: UpdateManifest,
  onProgress?: (fraction: number) => void
): Promise<void> {
  const url = new URL('/mobile/download', config.apiBaseUrl).toString()
  const dest = `${FileSystem.documentDirectory}${manifest.filename}`
  const task = FileSystem.createDownloadResumable(
    url,
    dest,
    { headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {} },
    (p) => {
      if (onProgress && p.totalBytesExpectedToWrite > 0) {
        onProgress(p.totalBytesWritten / p.totalBytesExpectedToWrite)
      }
    }
  )
  const result = await task.downloadAsync()
  if (!result?.uri) throw new Error('download gav ingen fil')
  const contentUri = await FileSystem.getContentUriAsync(result.uri)
  await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
    data: contentUri,
    flags: GRANT_READ_URI_PERMISSION,
    type: 'application/vnd.android.package-archive',
  })
}
```

- [ ] **Step 2: Write importerbarheds-test**

`src/lib/installApk.test.ts`:

```typescript
import { downloadAndInstall } from './installApk'

it('downloadAndInstall er en funktion (importerbar + mocks loader)', () => {
  expect(typeof downloadAndInstall).toBe('function')
})

it('kalder install-intent efter download', async () => {
  const IntentLauncher = require('expo-intent-launcher')
  await downloadAndInstall(
    { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' },
    { version: '0.1.29', version_code: 30, notes: '', filename: 'a.apk' }
  )
  expect(IntentLauncher.startActivityAsync).toHaveBeenCalled()
})
```

- [ ] **Step 3: Run test**

Run: `npx jest src/lib/installApk.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 4: tsc check**

Run: `npx tsc --noEmit`
Expected: ingen fejl

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/installApk.ts apps/mobile/src/lib/installApk.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): installApk download + install-intent"
```

---

## Task 8: `UpdateBanner.tsx` (UI)

**Files:**
- Create: `src/components/UpdateBanner.tsx`

Følger token-stilen fra `SaveRail.tsx`/`SidePanel.tsx` (`tokens.color.*`, `accessibilityRole`).

- [ ] **Step 1: Write the component**

`src/components/UpdateBanner.tsx`:

```typescript
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import type { UpdateManifest } from '../lib/appUpdate'

/** Banner i toppen når en opdatering er fundet. Viser version + noter +
 *  "Opdatér"/"Senere". `busy` viser progress mens download/install kører. */
export function UpdateBanner({
  manifest,
  busy,
  progress,
  onUpdate,
  onDismiss,
}: {
  manifest: UpdateManifest
  busy: boolean
  progress: number
  onUpdate: () => void
  onDismiss: () => void
}) {
  return (
    <View style={styles.root}>
      <View style={styles.textCol}>
        <Text style={styles.title}>Ny version {manifest.version}</Text>
        {manifest.notes ? (
          <Text style={styles.notes} numberOfLines={2}>
            {manifest.notes}
          </Text>
        ) : null}
        {busy ? (
          <Text style={styles.notes}>Henter… {Math.round(progress * 100)}%</Text>
        ) : null}
      </View>
      {busy ? (
        <ActivityIndicator color={tokens.color.accent} />
      ) : (
        <View style={styles.btnRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Senere"
            onPress={onDismiss}
            hitSlop={8}
            style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
          >
            <Text style={styles.btnGhost}>Senere</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Opdatér"
            onPress={onUpdate}
            hitSlop={8}
            style={({ pressed }) => [styles.btn, styles.btnPrimary, pressed && styles.pressed]}
          >
            <Text style={styles.btnPrimaryText}>Opdatér</Text>
          </Pressable>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.bg2,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1,
  },
  textCol: { flex: 1 },
  title: { color: tokens.color.fg1, fontWeight: '700' },
  notes: { color: tokens.color.fg3, fontSize: 12, marginTop: tokens.spacing.xs },
  btnRow: { flexDirection: 'row', gap: tokens.spacing.xs },
  btn: { minHeight: 36, paddingHorizontal: tokens.spacing.md, borderRadius: tokens.radius.md, alignItems: 'center', justifyContent: 'center' },
  btnPrimary: { backgroundColor: tokens.color.accent },
  btnPrimaryText: { color: tokens.color.bg0, fontWeight: '700' },
  btnGhost: { color: tokens.color.fg2 },
  pressed: { opacity: 0.7 },
})
```

- [ ] **Step 2: tsc check**

Run: `npx tsc --noEmit`
Expected: ingen fejl. (Hvis `tokens.radius.md` eller en farve-token ikke findes, slå op i `src/theme/tokens.ts` og brug nærmeste eksisterende — `SaveRail.tsx` bruger `tokens.color.bg2/fg1/line` og `SidePanel.tsx` bruger `tokens.radius.md`.)

- [ ] **Step 3: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/UpdateBanner.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): UpdateBanner-komponent"
```

---

## Task 9: Wire opdaterings-check i `App.tsx`

**Files:**
- Modify: `src/App.tsx`

App-niveau (i `AppBody`, altid monteret mens logget ind — samme sted som push/presence). Check ved opstart + når `AppState` → 'active'.

- [ ] **Step 1: Tilføj imports**

Øverst i `src/App.tsx`, tilføj til de eksisterende imports:

```typescript
import { useEffect, useState } from 'react'
import { ActivityIndicator, AppState, StatusBar, StyleSheet, View } from 'react-native'
import * as Application from 'expo-application'
import { checkForUpdate, type UpdateManifest } from './lib/appUpdate'
import { downloadAndInstall } from './lib/installApk'
import { UpdateBanner } from './components/UpdateBanner'
```

(Bemærk: `useState` tilføjes til den eksisterende `react`-import; `AppState` + `View` til den eksisterende `react-native`-import.)

- [ ] **Step 2: Tilføj state + check-logik i `AppBody`**

I `AppBody()`, efter `const { config, loading } = useAuth()`:

```typescript
  const [update, setUpdate] = useState<UpdateManifest | null>(null)
  const [updBusy, setUpdBusy] = useState(false)
  const [updProgress, setUpdProgress] = useState(0)
  const [updDismissed, setUpdDismissed] = useState(false)

  useEffect(() => {
    if (!config?.authToken) return
    const installedVc = Number(Application.nativeBuildVersion ?? '0') || 0
    const run = () => {
      void checkForUpdate(config, installedVc).then((m) => {
        if (m) setUpdate(m)
      })
    }
    run()
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') run()
    })
    return () => sub.remove()
  }, [config?.authToken])

  const onUpdate = () => {
    if (!config || !update) return
    setUpdBusy(true)
    setUpdProgress(0)
    void downloadAndInstall(config, update, setUpdProgress)
      .catch(() => setUpdBusy(false))
  }
```

- [ ] **Step 3: Montér banneren over indholdet**

Erstat `AppBody`'s `return (...)`-blok for den logget-ind-tilstand. Find:

```typescript
  return (
    <SessionProvider key={JSON.stringify([config.apiBaseUrl, config.authToken])}>
      <StreamProvider>
        <ChatScreen />
      </StreamProvider>
    </SessionProvider>
  )
```

Erstat med:

```typescript
  return (
    <SessionProvider key={JSON.stringify([config.apiBaseUrl, config.authToken])}>
      <StreamProvider>
        {update && !updDismissed ? (
          <UpdateBanner
            manifest={update}
            busy={updBusy}
            progress={updProgress}
            onUpdate={onUpdate}
            onDismiss={() => setUpdDismissed(true)}
          />
        ) : null}
        <ChatScreen />
      </StreamProvider>
    </SessionProvider>
  )
```

- [ ] **Step 4: tsc + jest**

Run: `npx tsc --noEmit && npx jest 2>&1 | tail -15`
Expected: tsc ren; alle jest-suites grønne (App.test loader med de nye mocks)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/App.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): wire auto-update-check + banner i App"
```

---

## Task 10: AndroidManifest `REQUEST_INSTALL_PACKAGES`

**Files:**
- Modify: `android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Tilføj permission**

Find linjen med de eksisterende `<uses-permission .../>` (fx `INTERNET`). Tilføj:

```xml
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
```

- [ ] **Step 2: Verificér XML er velformet**

Run: `python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('android/app/src/main/AndroidManifest.xml'); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/android/app/src/main/AndroidManifest.xml
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): REQUEST_INSTALL_PACKAGES for auto-updater"
```

---

## Task 11: Bootstrap — version-bump, build, manuel install + publicér manifest

Dette er den manuelle bootstrap-runde: byg DENNE version (med updateren) og installér den via adb én gang. Server-manifestet sættes til at pege på selvsamme version (så intet prompter), klar til at en FREMTIDIG release udløser den første OTA.

**Files:**
- Modify: `app.json` (`version` + `expo.android.versionCode`)
- Modify: `android/app/build.gradle` (`versionCode` + `versionName`)

- [ ] **Step 1: Bump versioner**

Nuværende: `build.gradle` versionCode 28 / versionName "0.1.27"; `app.json` version "0.1.27", versionCode 24.

Sæt KONSISTENT til den nye bootstrap-version:
- `android/app/build.gradle`: `versionCode 29`, `versionName "0.1.28"`.
- `app.json`: `"version": "0.1.28"`, `"versionCode": 29`.
- `package.json`: `"version": "0.1.28"`.

- [ ] **Step 2: Build release-APK**

Run (fra `apps/mobile/android`):
```bash
./gradlew assembleRelease
```
Expected: APK i `android/app/build/outputs/apk/release/app-release.apk` (debug-signeret, samme nøgle → in-place opgradering).

- [ ] **Step 3: Installér på S24 (telefonen skal være tilkoblet)**

Run:
```bash
adb install -r android/app/build/outputs/apk/release/app-release.apk
```
Expected: `Success`. (Hvis "no devices/emulators found" → telefonen er afbrudt; genopret USB/adb og prøv igen.)

- [ ] **Step 4: Publicér manifest + APK på serveren (peger på bootstrap-versionen selv)**

```bash
mkdir -p ~/.jarvis-v2/mobile
cp android/app/build/outputs/apk/release/app-release.apk ~/.jarvis-v2/mobile/jarvis-mobile-29.apk
cat > ~/.jarvis-v2/mobile/latest.json <<'JSON'
{
  "version": "0.1.28",
  "version_code": 29,
  "notes": "Auto-updater introduceret",
  "filename": "jarvis-mobile-29.apk"
}
JSON
```

(Med `version_code: 29` og installeret vc 29 → `compareVersion(29,{29})=false` → ingen banner. Næste release bumper til vc 30 og opdaterer `latest.json` → første ægte OTA-prompt.)

- [ ] **Step 5: E2E-røgtest af endpointet**

Genstart `jarvis-api` (så routeren er live), og verificér mod den kørende server med et gyldigt token:
```bash
curl -s -H "Authorization: Bearer <gyldigt-token>" https://api.srvlab.dk/mobile/latest
```
Expected: `{"version":"0.1.28","version_code":29,"notes":"...","filename":"jarvis-mobile-29.apk"}`

- [ ] **Step 6: Commit version-bump**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/app.json apps/mobile/android/app/build.gradle apps/mobile/package.json
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "release(mobile): 0.1.28 (vc29) — auto-updater bootstrap"
```

---

## Final verification

- [ ] **Backend:** `conda activate ai && cd /media/projects/jarvis-v2 && python -m pytest tests/test_mobile_update_routes.py -q` → alle grønne.
- [ ] **Mobil jest:** fra `apps/mobile`: `npx jest 2>&1 | tail -5` → alle suites grønne (eksisterende ~94 + de nye).
- [ ] **Mobil tsc:** `npx tsc --noEmit` → ingen fejl.
- [ ] **På enhed:** efter bootstrap-install åbner appen uden update-banner (samme version). Bekræft med Bjørn at en efterfølgende publiceret højere version udløser banneren + at "Opdatér" henter og åbner systemets install-dialog.

---

## Notes / kendte forbehold

- **versionCode-drift:** `app.json` (24) og `build.gradle` (28) var ude af sync før denne plan. `Application.nativeBuildVersion` returnerer build.gradle's versionCode (kilden til runtime-sandheden), derfor aligner Task 11 begge til 29. Hold dem konsistente fremover.
- **Auth på download:** `createDownloadResumable` bærer auth via `options.headers` (ikke en rå arg) — implementeret i Task 7.
- **expo-file-system API:** I nyere Expo-SDK'er er den klassiske download-API (`documentDirectory`, `createDownloadResumable`, `getContentUriAsync`) flyttet til `expo-file-system/legacy`. Hvis Task 7's import (`import * as FileSystem from 'expo-file-system'`) giver "undefined"-fejl på `createDownloadResumable` ved build, skift til `import * as FileSystem from 'expo-file-system/legacy'` og opdatér jest-mock-modulnavnet tilsvarende. Verificér mod den faktisk installerede version i `node_modules/expo-file-system`.
- **YAGNI:** ingen expo-updates (kan ikke levere native), ingen baggrunds/silent install (kræver device-owner), ingen rollback/kanaler.
