# Fælles Desk, web og PWA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve one Desk renderer as both Electron app and installable browser PWA, then retire `apps/ui`.

**Architecture:** `apps/jarvis-desk/src` remains the only renderer source. Vite emits separate Electron and web builds; a narrow host adapter supplies browser or preload capabilities. The API mounts the web build after existing routes and retains server-side authorization.

**Tech Stack:** React 18, TypeScript, Vite 5, Electron, FastAPI, Vitest, pytest, browser service worker APIs.

**Spec:** `docs/superpowers/specs/2026-10-08-faelles-desk-web-pwa-design.md`

## Global Constraints

- Preserve `/chat/stream/v2` and authenticated `/ws` as the shared chat paths.
- Preserve local-only unauthenticated access to static UI files. Keep `/chat/*` and `/mc/*` behind bearer authorization.
- Cache static build assets and app shell only; never cache API responses, events or approvals.
- Preserve Electron's figure, pointer overlay, local OS tools, packaging and update flow.
- Keep `apps/ui` available for rollback until browser parity and server cutover pass.
- Follow `AGENTS.md`: split a natural unit before changing logic in any file over 2,000 lines; stage only intended paths and use `scripts/commit_with_attribution.py`.
- Do not touch the existing untracked `apps/jarvis-desk/src/styles/message-rail.css` unless the user separately assigns it.

## Review Focus

1. Missing or corrupt browser token: show login without starting authenticated data requests (Task 2).
2. Token expires while the PWA is open: clear browser credentials and return to login (Task 2).
3. Browser lacks `window.jarvisDesk`: local terminal, folder picker and OS actions are hidden or explained, never dead buttons (Task 3).
4. Offline or interrupted stream: retain accurate run status and never claim a mutation succeeded (Tasks 3 and 4).
5. Service worker receives an API URL or new deployment: never cache API data; load current HTML and activate updates without silently interrupting a run (Task 4).

---

## File map and interfaces

- `apps/jarvis-desk/vite.config.ts`, `package.json`, `src/main.tsx`, `index.html`: select `web` or `desk` build; web output is `dist-web`, Desk output remains `dist`.
- `apps/jarvis-desk/src/lib/host.ts`: `hostKind(): 'desk' | 'web'`, `hasHostCapability(name: HostCapability): boolean`, and browser-safe `openAuthUrl(url: string): void`. Components use this instead of scattering new bridge checks.
- `apps/jarvis-desk/src/lib/browserConfig.ts`: `readBrowserConfig(): ApiConfig`, `writeBrowserConfig(config: ApiConfig): void`, `clearBrowserConfig(): void`; origin-scoped persistence only.
- `apps/jarvis-desk/src/lib/authEvents.ts`: `onUnauthorized(listener: () => void): () => void` and `reportUnauthorized(): void`; a 401 from shared clients invalidates browser login, while a role-based 403 does not.
- `apps/jarvis-desk/src/contexts/SettingsContext.tsx`, `src/views/SetupScreen.tsx`: select Electron or browser config source; authenticate before mounting data providers.
- `apps/jarvis-desk/src/pwa/service-worker.ts`, `public/manifest.webmanifest`, `public/icons/*`: browser-only installation and static caching.
- `apps/api/jarvis_api/app.py`, `middleware/jarvisx_user_routing.py`: mount `dist-web`, cache headers and local-only static-file allowlist.
- `apps/jarvis-desk/public/privatlivspolitik.html`: keep the existing public policy URL in the new build.
- `tests/test_ui_skal_lokalt.py`, `tests/test_ui_skal_cache.py`: security and HTTP cache boundaries.

## Task 1: Two builds from one renderer

**Files:** Create `apps/jarvis-desk/src/lib/buildTarget.ts`, `src/lib/buildTarget.test.ts`, `src/build-target.d.ts`; modify `apps/jarvis-desk/vite.config.ts`, `package.json`, `src/main.tsx`, `index.html`.

**Interfaces:** Produces `__WEB_BUILD__: boolean` and scripts `build:renderer` (Desk) and `build:web` (browser). `npm run build` remains the Electron release build. Browser assets are emitted into `dist-web` with root-relative URLs.

- [ ] Add a Vitest assertion for the target helper: `expect(buildTarget(true)).toBe('web')` and `expect(buildTarget(false)).toBe('desk')`; run `npx vitest run src/lib/buildTarget.test.ts` and see it fail.
- [ ] Create a tiny `src/lib/buildTarget.ts` with `export const buildTarget = (web: boolean) => web ? 'web' : 'desk'`; declare `__WEB_BUILD__` in `src/build-target.d.ts` and define it from Vite `mode === 'web'`. Set `base` to `/` for web and `./` for Desk; set `outDir` to `dist-web` or `dist`.

  ```ts
  export const buildTarget = (web: boolean): 'web' | 'desk' => web ? 'web' : 'desk'
  // vite.config.ts: define: { __WEB_BUILD__: JSON.stringify(mode === 'web') }
  ```
- [ ] In `main.tsx`, render the existing `App` for web; keep figure and pointer branches gated to Desk. Load those Electron-only modules through dynamic imports so web chunks omit them. Do not mount `Vinduesknapper` in web.
- [ ] Add `build:web: vite build --mode web` to `package.json`. Run `npm run build:web`, `npm run build:renderer`, `npx tsc --noEmit -p tsconfig.json`, and `npx vitest run src/lib/buildTarget.test.ts`; verify both output directories contain an `index.html` and Desk's existing `npm run build` still produces Electron output.
- [ ] Commit intended paths through the attribution wrapper with message `feat(desk): build browser renderer from Desk source`.

## Task 2: Persistent browser login using Desk's auth flow

**Files:** Create `apps/jarvis-desk/src/lib/browserConfig.ts`, `src/lib/browserConfig.test.ts`, `src/lib/authEvents.ts`, `src/lib/authEvents.test.ts`; modify `src/contexts/SettingsContext.tsx`, `src/contexts/SettingsContext.test.tsx`, `src/views/SetupScreen.tsx`, `src/views/SetupScreen.test.tsx`, `src/lib/api.ts`.

**Interfaces:** `readBrowserConfig()` returns `{ apiBaseUrl: window.location.origin + '/', authToken: string | null }`; `writeBrowserConfig` persists token for this origin; `clearBrowserConfig` removes it. Desk still uses `window.jarvisDesk.config`. No cached role is authoritative.

- [ ] Write failing tests for empty storage, malformed storage, save/reload, clear, and an origin mismatch. Example: after `localStorage.setItem('jarvis:web-auth', '{broken')`, `expect(readBrowserConfig().authToken).toBeNull()`. Run `npx vitest run src/lib/browserConfig.test.ts`.
- [ ] Implement `browserConfig.ts` with guarded `localStorage` access and an origin check. Never store a server URL different from `window.location.origin` in web mode.

  ```ts
  const origin = new URL('/', window.location.origin).toString()
  // Parse only { origin, authToken }; return { apiBaseUrl: origin, authToken: null }
  // when parsing fails or the stored origin differs.
  ```
- [ ] Add failing `SettingsContext` and `authEvents` tests proving browser config loads after reload, `update({ authToken: null })` persists logout, `whoami` or another API request receiving 401 clears the token, a 403 retains login, and Desk config still calls preload. Run `npx vitest run src/contexts/SettingsContext.test.tsx src/lib/authEvents.test.ts`.
- [ ] Route `SettingsProvider` to browser storage when `hostKind() === 'web'`; gate child data providers until `whoami` validates the browser token. Have `apiFetch` call `reportUnauthorized()` on 401 only; subscribe in SettingsProvider to clear browser config and show `SetupScreen`. A transient network failure retains the token and displays offline state. Set `X-Jarvis-Klient` to `web` for browser calls and `desk` for Electron.

  ```ts
  if (res.status === 401) reportUnauthorized()
  // 403 means insufficient role for one endpoint; it must not log out the user.
  ```
- [ ] Add `SetupScreen` tests for web Google login opening the returned authorization URL in the browser and for token login. Use the current origin in web, retain Desk's configured production URL in Electron. Run both affected test files, typecheck, lint, then both builds.
- [ ] Commit intended paths through the attribution wrapper with message `feat(desk): persist browser login safely`.

## Task 3: Browser capability boundary and chat parity

**Files:** Create `apps/jarvis-desk/src/lib/host.ts`, `src/lib/host.test.ts`; modify direct bridge call sites under `src/views/{ChatView,CodeView}.tsx`, `src/components/shell/{Sidebar,Vinduesknapper}.tsx`, `src/components/panel/TerminalPane.tsx`, and other files found by `rg -l 'jarvisDesk' apps/jarvis-desk/src --glob '!**/*.test.*'`. Extend their existing tests and `src/contexts/StreamContext.test.tsx`.

**Interfaces:** `HostCapability` is a union of `window`, `folder-picker`, `local-terminal`, `os-notification`, `screen-control`, `updater`, `figure`, `pointer`. `hasHostCapability` checks the actual bridge method, not merely a build flag. HTTP/API tools stay available when the server authorizes them.

- [ ] Test each capability with and without `window.jarvisDesk`, including a partial bridge; `expect(hasHostCapability('local-terminal')).toBe(false)` when the terminal method is missing. Run `npx vitest run src/lib/host.test.ts` to see failure.
- [ ] Implement `host.ts`; use it to hide local-only actions or show the explicit existing `TerminalPane` explanation where a user intentionally opens a local terminal. Audit every `jarvisDesk` occurrence with the command above and account for each call site in the task diff.

  ```ts
  export type HostCapability = 'window' | 'folder-picker' | 'local-terminal' |
    'os-notification' | 'screen-control' | 'updater' | 'figure' | 'pointer'
  export const hostKind = (): 'desk' | 'web' =>
    (window as Window & { jarvisDesk?: unknown }).jarvisDesk ? 'desk' : 'web'
  // hasHostCapability reads the corresponding preload method, not hostKind alone.
  ```
- [ ] Add a `ChatView`/stream test for v2 send, cancel, visible tool result and approval; assert a rejected or interrupted request does not mark a run complete. Add a browser `Sidebar`/`CodeView` test showing no folder-picker or local-terminal button without a bridge. Run the focused tests and fix failures.
- [ ] Run `npm run lint`, `npx tsc --noEmit -p tsconfig.json`, `npx vitest run`, `npm run build:web`, and `npm run build`. Open both builds; check chat, session switching and Desktop bridge actions manually.
- [ ] Commit intended paths through the attribution wrapper with message `feat(desk): gate OS actions by host capabilities`.

## Task 4: Installable PWA with static-only cache

**Files:** Create `apps/jarvis-desk/src/pwa/service-worker.ts`, `src/pwa/cachePolicy.ts`, `src/pwa/cachePolicy.test.ts`, `src/pwa/register.ts`, `src/components/PwaUpdateHost.tsx`, `scripts/build-service-worker.mjs`, `public/manifest.webmanifest`, `public/icons/icon-192.png`, `public/icons/icon-512.png`; modify `src/App.tsx`, `index.html`, `package.json`.

**Interfaces:** The worker may cache only `GET` requests whose path is `/` or `/index.html` or starts with `/assets/`, plus exact icon and manifest paths. All other requests bypass it. Registration occurs only in web mode. Updates wait for an explicit reload action after active runs finish.

- [ ] Write a failing route-policy test: `expect(shouldCache(new URL('/chat/stream/v2', location.origin))).toBe(false)` and the same for `/ws`, `/mc/runtime`, `/api/auth/login`; assert `/assets/app-hash.js` is true. Run `npx vitest run src/pwa/cachePolicy.test.ts`.
- [ ] Implement `shouldCache(url: URL)` in `cachePolicy.ts` and static-only worker fetch handling with versioned cache cleanup; bypass non-GET, API, authorization-bearing and cross-origin requests. Keep network-first HTML with a cached shell fallback and immutable asset caching. The worker must never synthesize a successful response to a mutation.
- [ ] Add `esbuild` as an explicit dev dependency. Bundle `service-worker.ts` through `scripts/build-service-worker.mjs` into `dist-web/sw.js` after `vite build --mode web`; make `build:web` run both commands in order. The script must not alter Electron output.

  ```js
  import { build } from 'esbuild'
  await build({ entryPoints: ['src/pwa/service-worker.ts'], outfile: 'dist-web/sw.js', bundle: true, format: 'iife', platform: 'browser' })
  ```
- [ ] Add manifest with `name: J.A.R.V.I.S.`, `display: standalone`, `start_url: /`, `scope: /`, theme/background colors matching Desk, and 192/512 icons. Mount `PwaUpdateHost` inside `StreamProvider` in `App.tsx`; it registers the worker only in web mode and uses stream state to defer the reload prompt until no run is active.
- [ ] Run focused tests and `npm run build:web`. Inspect `dist-web` for manifest, icons, service worker and valid start URL; test install and offline shell in a real browser. Test a running stream while an update becomes available: no forced reload.
- [ ] Commit intended paths through the attribution wrapper with message `feat(web): add installable PWA and static-only cache`.

## Task 5: API mount, local access and rollback

**Files:** Modify `apps/api/jarvis_api/app.py`, `middleware/jarvisx_user_routing.py`, `tests/test_ui_skal_lokalt.py`, `tests/test_ui_skal_cache.py`; copy `apps/ui/public/privatlivspolitik.html` to `apps/jarvis-desk/public/privatlivspolitik.html`; create `docs/ui/faelles-desk-web-deploy.md`; update the actual server build/deploy command when it is located.

**Interfaces:** API routes retain precedence. `dist-web` is the preferred UI directory; `apps/ui/dist` is fallback when the new build is absent during migration. Cache headers are `no-cache` for HTML, worker and manifest, `public, max-age=31536000, immutable` only for hashed assets.

- [ ] Add failing pytest cases for local access to exact `/manifest.webmanifest`, `/sw.js`, `/icons/icon-192.png`, `/icons/icon-512.png`; reject the same paths from public IPs and reject similar paths such as `/icons/../chat/sessions`. Keep tests that `/chat/*` and `/mc/*` require auth. Run `pytest -q tests/test_ui_skal_lokalt.py`.
- [ ] Update the narrow auth allowlist, preserving the special public privacy-policy route. Extend cache tests to assert no-cache on worker/manifest and immutable only on hash-named assets; run those tests red, then implement the header rule and preferred/fallback UI mount.

  ```python
  _UI_SKAL = ("/", "/index.html", "/manifest.webmanifest", "/sw.js", "/icons/icon-192.png", "/icons/icon-512.png")
  # /assets/ keeps its existing prefix rule; no /chat/ or /mc/ prefix is added.
  ```
- [ ] Find the active server deployment build command by checking service configuration and current deployment documentation; change it to run `npm ci && npm run build:web` in `apps/jarvis-desk` before restarting the API. Record the exact rollback command/path in `docs/ui/faelles-desk-web-deploy.md`. Do not claim a production cutover from a local test.
- [ ] Run `pytest -q tests/test_ui_skal_lokalt.py tests/test_ui_skal_cache.py tests/test_jarvisx_user_routing.py`, `python -m compileall core apps/api scripts`, and a local FastAPI smoke check for `/`, assets, PWA files, privacy policy and protected routes.
- [ ] Commit intended paths through the attribution wrapper with message `feat(api): serve Desk web build with PWA auth boundaries`.

## Task 6: Cutover verification and old UI removal

**Files:** Remove `apps/ui/**` after production parity; update `scripts/docs_audit.py`, `docs/architecture/OVERVIEW.md`, current UI deployment documentation and any live references found with `rg -l 'apps/ui|jarvis-unified-ui' apps scripts .github docs --glob '!**/historical/**'`. Preserve history documents rather than rewriting past events.

**Interfaces:** After removal, `/` serves only `apps/jarvis-desk/dist-web`. Privacy policy remains at `/privatlivspolitik.html`. Electron `npm run build` remains unchanged.

- [ ] Run a browser parity checklist against the running server for login, token renewal, session list, send/stream/cancel/steer, tool results, approvals, WebSocket reconnect, offline state, installation and refresh after a new build. Capture results in a short dated verification note. If any critical item fails, repair it before this task continues.
- [ ] Verify rollback works by temporarily selecting the old build and returning to the web build in the deployment environment. Record the commands and observations; do not remove fallback until this passes.
- [ ] Remove `apps/ui` and fallback mount, update live docs/scripts, then run repository searches for references that still drive an active build. Run UI, Python and build gates from Tasks 3 and 5 again.
- [ ] Commit only intended removals and references through the attribution wrapper with message `chore(web): retire legacy UI after Desk PWA cutover`.

## Completion gate

Verify `git status --short` contains only pre-existing user work, Desk and web builds pass, relevant Python tests pass, the browser is installable, current server serves the shared UI, and old `apps/ui` no longer has an active route or build. Report any production checks that could not be performed with their exact reason.
