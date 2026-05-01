# JarvisX — Phase 0 POC

Electron desktop app that wraps the existing Jarvis V2 React UI in a
ClawX-inspired shell. Phase 0 is the proof-of-concept: native shell,
embedded chat via iframe, no Python child process spawn.

## Architecture (Phase 0)

```
┌─ Electron Main ─────────────────────────────────┐
│  • BrowserWindow + lifecycle                    │
│  • Persists user config (userData/config.json)  │
│  • Pings backend every 8s                       │
│  • Injects X-JarvisX-User header on all reqs    │
└──────────────┬──────────────────────────────────┘
               │ IPC (preload bridge)
┌──────────────▼──────────────────────────────────┐
│  React 19 + Tailwind shell                       │
│  • Sidebar: Chat / Mission Control / Settings    │
│  • ChatView → <iframe src={apiBaseUrl}/>         │
│  • Status bar: backend up/down, latency, mode    │
└──────────────┬──────────────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────────────────┐
│  Existing Jarvis Python runtime (UNTOUCHED)      │
│  • FastAPI on port 80 (Bjørn's box)              │
│  • Existing apps/ui served at "/"                │
│  • SQLite at ~/.jarvis-v2/state/                 │
└──────────────────────────────────────────────────┘
```

## Modes

| Mode | apiBaseUrl points at | Use case |
|---|---|---|
| `dev` | `http://localhost` | Local development on the prod-runtime box |
| `thin-client` | e.g. `https://jarvis.srvlab.dk` | Remote — multi-device, same identity |
| `standalone` | (Phase 2+) | Local spawn with isolated state — not yet |

Set via Settings tab. Persisted in Electron's `userData/config.json`.

## User routing

Every outbound request from JarvisX (renderer + iframe) gets:

```
X-JarvisX-User: <discord_id>
X-JarvisX-User-Name: <url-encoded>
X-JarvisX-Client: jarvisx-electron/0.1.0-poc
```

The Python runtime side needs a small middleware that reads
`X-JarvisX-User` and binds the request to the right workspace before
routing. That's the next backend ticket — see "Backend follow-up" below.

## Run

```bash
cd apps/jarvisx
npm install
npm run dev:electron     # spawns Vite + Electron with hot reload
```

For a packaged build:

```bash
npm run package:linux    # → release/JarvisX-0.1.0-poc.deb + .AppImage
npm run package:win      # → release/JarvisX Setup 0.1.0-poc.exe
```

## Phase 0 — done

- [x] Electron 33 + React 19 + Vite + TypeScript scaffold
- [x] Tailwind dark theme matching ClawX palette
- [x] Sidebar: Chat / MC / Settings
- [x] Iframe chat with the existing apps/ui
- [x] Settings: mode, apiBaseUrl, identity, ping
- [x] Status bar with live backend health
- [x] X-JarvisX-User header injection
- [x] electron-builder config for `.deb` / `.AppImage` / `.exe`

## Phase 1 — next

- [ ] Backend middleware that respects `X-JarvisX-User`
- [ ] Replace the chat iframe with native React 19 components ported
  from `apps/ui/src/`
- [ ] System tray + native notifications
- [ ] Auto-update via electron-updater + GitHub releases
- [ ] Channel-status panel (Discord / Telegram / WhatsApp)

## Backend follow-up

The runtime currently resolves the workspace from Discord ID via
`find_user_by_discord_id`. We need a thin middleware in
`apps/api/jarvis_api/` that:

1. Reads `X-JarvisX-User` header
2. Looks up the user via `find_user_by_discord_id`
3. Binds `workspace_name` + `user_id` ContextVars for the request

This is the same pattern `discord_gateway.py` already does on its side.

## Code signing & notarization

JarvisX' build pipeline is wired for signed releases on macOS and
Windows. **It auto-skips signing when the required env vars are
missing**, so local `npm run package` builds work uncertified — but
distribution-ready releases need certificates and a one-time setup.

### macOS (`.dmg`, `.app`)

You need:
- An **Apple Developer Program** membership ($99/yr,
  developer.apple.com)
- A **Developer ID Application** certificate in your local Keychain
- An **app-specific password** (appleid.apple.com → Sign-In and
  Security → App-Specific Passwords)
- Your **Team ID** (developer.apple.com → Membership)

Then before `npm run package:mac`:

```bash
export APPLE_ID="you@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="abcd-efgh-ijkl-mnop"  # pragma: allowlist secret
export APPLE_TEAM_ID="ABCDE12345"
npm install --save-dev @electron/notarize  # one-time
npm run package
```

The `signing/notarize.cjs` afterSign hook submits the app to Apple's
notary service and staples the result. Without this, macOS users
see "developer cannot be verified" on first launch.

### Windows (`.exe`)

You need:
- An **EV (Extended Validation) Code-Signing Certificate** from a CA
  like DigiCert, Sectigo, or SSL.com. ~$300/year. EV is required for
  immediate SmartScreen reputation; standard OV certs work but new
  builds get a "downloaded few times, may not be safe" warning until
  they accumulate trust.
- The cert installed on the build machine (USB token for EV) or
  exported as `.pfx` for CI use.

Set env vars before `npm run package:win`:

```bash
export CSC_LINK="path/to/cert.pfx"           # or USB-token via WIN_CSC_LINK
export CSC_KEY_PASSWORD="…"
npm run package
```

`signingHashAlgorithms: ["sha256"]` and the digicert timestamp server
are pre-configured. Without these env vars, the build emits unsigned
`.exe` files — fine for testing, will trigger SmartScreen for users.

### Linux (`.deb`, `.AppImage`)

Linux signing is optional and conventionally handled per-distro. The
default `electron-builder` output is unsigned; AppImage users
typically don't care. If you want GPG-signed `.deb`, configure your
GPG key in `~/.gnupg` and add `electron-builder --linux deb -- --gpg-key=YOUR_KEY_ID` to your release flow.

### CI integration

For GitHub Actions, set the env vars above as repository secrets.
`scripts/release.sh` (TODO if you write one) can call
`electron-builder --publish always` with the right env loaded — see
`build.publish` in `package.json` for the GitHub Releases target.
Without `GH_TOKEN`, electron-builder won't actually upload, but a
local signed `.dmg`/`.exe` ends up under `release/`.

