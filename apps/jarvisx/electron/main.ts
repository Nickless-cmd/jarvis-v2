/**
 * Electron main process for JarvisX.
 *
 * Phase 0 responsibilities:
 *   - Single BrowserWindow with our React shell
 *   - Loads vite dev server in dev mode, dist/index.html in production
 *   - Persists per-user config (apiBaseUrl, userId, userName, mode) to a
 *     small JSON file under app userData
 *   - Pings the configured backend on a timer and forwards status to the
 *     renderer
 *   - Injects an X-JarvisX-User header on all outgoing requests so the
 *     Python runtime knows who is talking (per Jarvis' note about
 *     multi-user routing)
 *
 * Standalone mode (Phase 2+) would also spawn a child Python uvicorn here.
 * We deliberately do NOT spawn one in Phase 0 — it would corrupt the
 * shared SQLite db on Bjørn's box.
 */
import { app, BrowserWindow, desktopCapturer, dialog, ipcMain, Menu, MenuItem, session } from 'electron'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve as pathResolve } from 'node:path'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { spawn, execFile } from 'node:child_process'

// electron-updater is CommonJS — import via createRequire pattern so
// it works under our type:module package.json without breaking dev.
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
type UpdateInfo = { version: string; releaseDate?: string; releaseName?: string }
type UpdaterStatus =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'available'; info: UpdateInfo }
  | { kind: 'not-available'; current: string }
  | { kind: 'downloading'; percent: number }
  | { kind: 'downloaded'; info: UpdateInfo }
  | { kind: 'error'; error: string }

const __dirname = dirname(fileURLToPath(import.meta.url))

interface AppConfig {
  apiBaseUrl: string
  userId: string
  userName: string
  mode: 'dev' | 'thin-client' | 'standalone'
  projectRoot: string
  recentProjects: string[]
  // Bearer token (signed JWT) issued by the backend. When present,
  // every outbound request to apiBaseUrl carries Authorization: Bearer.
  // Stored in app userData/config.json — same security boundary as
  // the rest of the config. Future: move to OS keychain.
  authToken?: string
  authTokenUserId?: string  // for UI to show whose token this is
  authTokenRole?: string    // for UI to show role granted by token
  authTokenExpiresAt?: string
}

const DEFAULT_CONFIG: AppConfig = {
  apiBaseUrl: 'http://localhost',
  userId: '1246415163603816499',
  userName: 'Bjørn',
  mode: 'dev',
  projectRoot: '',
  recentProjects: [],
}

let mainWindow: BrowserWindow | null = null
let pingTimer: NodeJS.Timeout | null = null

function configPath(): string {
  return join(app.getPath('userData'), 'config.json')
}

function loadConfig(): AppConfig {
  try {
    const p = configPath()
    if (!existsSync(p)) return DEFAULT_CONFIG
    const data = JSON.parse(readFileSync(p, 'utf8'))
    return { ...DEFAULT_CONFIG, ...data }
  } catch {
    return DEFAULT_CONFIG
  }
}

function saveConfig(cfg: AppConfig): void {
  const p = configPath()
  mkdirSync(dirname(p), { recursive: true })
  writeFileSync(p, JSON.stringify(cfg, null, 2), 'utf8')
}

let currentConfig: AppConfig = DEFAULT_CONFIG

async function pingBackend(
  url?: string,
): Promise<{ ok: boolean; latencyMs: number; error?: string }> {
  const target = (url ?? currentConfig.apiBaseUrl).replace(/\/$/, '') + '/openapi.json'
  const start = Date.now()
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 4000)
    const res = await fetch(target, { signal: controller.signal })
    clearTimeout(timeout)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return { ok: true, latencyMs: Date.now() - start }
  } catch (e: unknown) {
    return {
      ok: false,
      latencyMs: Date.now() - start,
      error: e instanceof Error ? e.message : String(e),
    }
  }
}

function startPingLoop(): void {
  if (pingTimer) clearInterval(pingTimer)
  const tick = async () => {
    if (!mainWindow || mainWindow.isDestroyed()) return
    const result = await pingBackend()
    mainWindow.webContents.send('backend-status', {
      up: result.ok,
      latencyMs: result.ok ? result.latencyMs : undefined,
    })
  }
  void tick()
  pingTimer = setInterval(tick, 8000)
}

// ── Auto-update plumbing ──────────────────────────────────────────
// Uses electron-updater; the publish target is set via electron-builder's
// `build.publish` in package.json (GitHub Releases by default in our
// config). When no publish target is configured, all check-* calls
// no-op gracefully — fine for dev / unsigned local builds.
//
// Renderer subscribes to 'updater-status' events and calls
// 'updater-check' / 'updater-install' via IPC.

let updaterStatus: UpdaterStatus = { kind: 'idle' }

function emitUpdaterStatus(s: UpdaterStatus) {
  updaterStatus = s
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('updater-status', s)
  }
}

function setupAutoUpdater(): void {
  // Only run in packaged production builds — no point pinging GitHub
  // when running `npm run dev:electron` against vite.
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    return
  }
  let autoUpdater: any
  try {
    // electron-updater is CJS, so destructure off the require() result
    autoUpdater = require('electron-updater').autoUpdater
  } catch (e) {
    console.warn('[updater] electron-updater not available:', e)
    return
  }
  // Don't auto-download — let the user decide. We just notify when
  // an update is available, and they click "Install" to proceed.
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  autoUpdater.on('checking-for-update', () => emitUpdaterStatus({ kind: 'checking' }))
  autoUpdater.on('update-available', (info: UpdateInfo) =>
    emitUpdaterStatus({ kind: 'available', info }),
  )
  autoUpdater.on('update-not-available', () =>
    emitUpdaterStatus({ kind: 'not-available', current: app.getVersion() }),
  )
  autoUpdater.on('error', (err: Error) =>
    emitUpdaterStatus({ kind: 'error', error: err.message }),
  )
  autoUpdater.on('download-progress', (p: { percent: number }) =>
    emitUpdaterStatus({ kind: 'downloading', percent: Math.round(p.percent) }),
  )
  autoUpdater.on('update-downloaded', (info: UpdateInfo) =>
    emitUpdaterStatus({ kind: 'downloaded', info }),
  )

  // Initial check 30s after startup so we don't compete with first-paint
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((e: Error) => {
      console.warn('[updater] initial check failed:', e.message)
    })
  }, 30_000)
  // And every 6 hours after that — keep it light
  setInterval(() => {
    autoUpdater.checkForUpdates().catch(() => undefined)
  }, 6 * 60 * 60 * 1000)

  // IPC handlers — renderer requests check / download / install
  ipcMain.handle('jarvisx:updater-check', async () => {
    try {
      const result = await autoUpdater.checkForUpdates()
      return { ok: true, version: result?.updateInfo?.version }
    } catch (e: unknown) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) }
    }
  })
  ipcMain.handle('jarvisx:updater-download', async () => {
    try {
      await autoUpdater.downloadUpdate()
      return { ok: true }
    } catch (e: unknown) {
      return { ok: false, error: e instanceof Error ? e.message : String(e) }
    }
  })
  ipcMain.handle('jarvisx:updater-install', () => {
    // quit + install. App will restart at the new version.
    autoUpdater.quitAndInstall(false, true)
    return { ok: true }
  })
  ipcMain.handle('jarvisx:updater-status', () => updaterStatus)
}

// ── Git-based updater ────────────────────────────────────────────
// Run-from-source update flow: poll origin/main, surface "X commits
// behind", let the user pull + rebuild + restart from the UI.
//
// Why this instead of electron-updater: Bjørn's actual workflow is
// "I push to main, my desktop should pick it up" — not "I tag a
// release, CI builds an installer". For solo desktop use the git-
// poll approach matches reality.
//
// Repo root resolution: __dirname is dist-electron/, parent paths
// climb to the repo root.

type GitUpdateState =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'up-to-date'; head: string; checkedAt: string }
  | { kind: 'behind'; commits: GitCommit[]; head: string; checkedAt: string }
  | { kind: 'updating'; phase: string; output: string }
  | { kind: 'updated'; head: string }
  | { kind: 'error'; error: string }

interface GitCommit {
  sha: string
  short: string
  subject: string
  author: string
  date: string
}

let gitUpdateState: GitUpdateState = { kind: 'idle' }
let gitPollTimer: NodeJS.Timeout | null = null

function repoRoot(): string {
  // dist-electron/ is two levels under apps/jarvisx/, three under repo root.
  return pathResolve(__dirname, '..', '..', '..')
}

function emitGitUpdateState(s: GitUpdateState): void {
  gitUpdateState = s
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('git-update-status', s)
  }
}

function runGit(args: string[], cwd: string, timeoutMs = 15_000): Promise<{ ok: boolean; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    execFile('git', args, { cwd, timeout: timeoutMs, maxBuffer: 4 * 1024 * 1024 }, (err, stdout, stderr) => {
      resolve({
        ok: !err,
        stdout: String(stdout || '').trimEnd(),
        stderr: String(stderr || '').trimEnd(),
      })
    })
  })
}

async function checkGitUpdates(): Promise<void> {
  const root = repoRoot()
  if (!existsSync(join(root, '.git'))) {
    // No repo here — installed pkg, not run-from-source. Stay idle.
    return
  }
  emitGitUpdateState({ kind: 'checking' })
  // Determine the upstream branch we should track. Default to origin/main
  // but respect whatever the current branch tracks if configured.
  const branchInfo = await runGit(['rev-parse', '--abbrev-ref', 'HEAD'], root)
  const branch = branchInfo.ok ? branchInfo.stdout.trim() || 'main' : 'main'
  const upstream = `origin/${branch}`
  // Fetch quietly. Network failure here = "checking" → "error" with a
  // message so the UI can show the user.
  const fetchRes = await runGit(['fetch', 'origin', branch, '--quiet'], root, 30_000)
  if (!fetchRes.ok) {
    emitGitUpdateState({
      kind: 'error',
      error: `git fetch failed: ${fetchRes.stderr || 'unknown error'}`,
    })
    return
  }
  // Count commits behind
  const countRes = await runGit(['rev-list', '--count', `HEAD..${upstream}`], root)
  if (!countRes.ok) {
    emitGitUpdateState({ kind: 'error', error: `rev-list failed: ${countRes.stderr}` })
    return
  }
  const count = parseInt(countRes.stdout, 10) || 0
  const headRes = await runGit(['rev-parse', '--short', 'HEAD'], root)
  const head = headRes.ok ? headRes.stdout : '?'
  if (count === 0) {
    emitGitUpdateState({
      kind: 'up-to-date', head, checkedAt: new Date().toISOString(),
    })
    return
  }
  // Pull commit summaries — most recent first, capped so a long-
  // sleeping repo doesn't dump 500 entries to the renderer.
  const logRes = await runGit(
    ['log', `HEAD..${upstream}`, '--pretty=format:%H%x09%h%x09%an%x09%aI%x09%s', '-n', '20'],
    root,
  )
  const commits: GitCommit[] = []
  if (logRes.ok && logRes.stdout) {
    for (const line of logRes.stdout.split('\n')) {
      const [sha, short, author, date, ...subj] = line.split('\t')
      if (!sha) continue
      commits.push({
        sha, short, author, date,
        subject: subj.join('\t'),
      })
    }
  }
  emitGitUpdateState({
    kind: 'behind',
    commits,
    head,
    checkedAt: new Date().toISOString(),
  })
}

function startGitPollLoop(): void {
  if (gitPollTimer) clearInterval(gitPollTimer)
  // First check 8s after window-ready so it doesn't compete with first paint.
  setTimeout(() => { void checkGitUpdates() }, 8_000)
  // Then every 5 minutes — git fetch is cheap, network is the only cost.
  gitPollTimer = setInterval(() => { void checkGitUpdates() }, 5 * 60 * 1000)
}

function setupGitUpdater(): void {
  const root = repoRoot()
  if (!existsSync(join(root, '.git'))) {
    // Not a git checkout — no-op (packaged install). UpdateBanner
    // will see kind='idle' forever and stay hidden.
    return
  }
  startGitPollLoop()

  ipcMain.handle('jarvisx:git-update-check', async () => {
    await checkGitUpdates()
    return gitUpdateState
  })
  ipcMain.handle('jarvisx:git-update-status', () => gitUpdateState)
  ipcMain.handle('jarvisx:git-update-pull-and-rebuild', async () => {
    return runPullAndRebuild()
  })
  ipcMain.handle('jarvisx:git-update-restart-now', () => {
    manualRelaunch()
    return { ok: true }
  })
}

async function runPullAndRebuild(): Promise<{ ok: boolean; error?: string }> {
  const root = repoRoot()
  const jarvisxDir = pathResolve(__dirname, '..', '..')  // apps/jarvisx
  // Phase 1: git pull
  emitGitUpdateState({ kind: 'updating', phase: 'pull', output: '' })
  const pull = await runGit(['pull', '--ff-only'], root, 60_000)
  if (!pull.ok) {
    emitGitUpdateState({
      kind: 'error',
      error: `git pull failed: ${pull.stderr || pull.stdout || 'unknown'}`,
    })
    return { ok: false, error: pull.stderr || pull.stdout }
  }
  emitGitUpdateState({ kind: 'updating', phase: 'pulled', output: pull.stdout })

  // Phase 2: npm install + build (streamed). We accept that this may
  // take 30–90s; the renderer shows the live tail of stdout.
  const ok = await runShellStreaming(
    'sh',
    ['-c', 'npm install --silent && npm run build'],
    jarvisxDir,
    'install + build',
  )
  if (!ok) {
    return { ok: false, error: 'install/build failed — see banner output' }
  }

  // Phase 3: signal complete — but DO NOT auto-restart.
  // Bjørn is explicit: never restart Jarvis without his go-ahead.
  // Build artifacts are now on disk; the renderer is still running
  // the OLD bundle until the user clicks "Restart now". This is
  // important because mid-conversation work shouldn't be yanked.
  const headRes = await runGit(['rev-parse', '--short', 'HEAD'], root)
  emitGitUpdateState({
    kind: 'updated',
    head: headRes.ok ? headRes.stdout : '?',
  })
  return { ok: true }
}

// Manual relaunch — only fires when the user clicks "Restart now"
// in the GitUpdateBanner. Separate from the update flow so the
// build phase and the restart phase have explicit consent boundaries.
function manualRelaunch(): void {
  app.relaunch()
  app.exit(0)
}

function runShellStreaming(
  cmd: string,
  args: string[],
  cwd: string,
  phase: string,
): Promise<boolean> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { cwd, env: process.env })
    let buf = ''
    const onChunk = (data: Buffer) => {
      buf += data.toString('utf8')
      // Cap buffer to last 4KB so we don't accumulate gigabytes
      if (buf.length > 4096) buf = buf.slice(-4096)
      emitGitUpdateState({ kind: 'updating', phase, output: buf })
    }
    child.stdout.on('data', onChunk)
    child.stderr.on('data', onChunk)
    child.on('error', (err) => {
      emitGitUpdateState({
        kind: 'error',
        error: `${phase} spawn failed: ${err.message}`,
      })
      resolve(false)
    })
    child.on('close', (code) => {
      if (code === 0) {
        resolve(true)
      } else {
        emitGitUpdateState({
          kind: 'error',
          error: `${phase} exited with code ${code}\n\n${buf}`,
        })
        resolve(false)
      }
    })
  })
}

// API paths that must be redirected to the Jarvis backend in packaged
// builds (file:// has no proxy). In dev these are also intercepted by
// vite proxy first, but the Electron rewrite is harmless either way.
const API_PATH_PREFIXES = [
  '/chat',
  '/attachments',
  '/files',
  '/mc',
  '/api',
  '/health',
  '/status',
  '/sensory',
  '/ws',
  '/live',
]

function shouldProxyToBackend(url: string): boolean {
  // file:// renderer: rewrite ./assets stays local; /chat etc rewrite to
  // backend. http://localhost:5173 (vite): vite handles it via its proxy
  // — no rewrite needed but applying one here doesn't hurt.
  try {
    const u = new URL(url)
    if (u.protocol === 'file:') {
      return API_PATH_PREFIXES.some((p) => u.pathname.startsWith(p))
    }
    if (u.host === 'localhost:5173' || u.host === '127.0.0.1:5173') {
      return false // vite dev server handles it
    }
    return false
  } catch {
    return false
  }
}

function installRequestHooks(): void {
  const ses = session.defaultSession

  // 1. Rewrite relative /chat etc. to currentConfig.apiBaseUrl in
  // packaged builds. Without this, file:// loads can't reach the API.
  ses.webRequest.onBeforeRequest((details, callback) => {
    if (shouldProxyToBackend(details.url)) {
      const u = new URL(details.url)
      const target = currentConfig.apiBaseUrl.replace(/\/$/, '') + u.pathname + u.search
      callback({ redirectURL: target })
      return
    }
    callback({})
  })

  // 2. Inject X-JarvisX-User + identity headers on every outbound
  // request to the configured backend. Disambiguates Bjørn from Mikkel
  // — runtime middleware uses it to bind workspace. Plus
  // X-JarvisX-Project so the runtime knows where the user is "rooted"
  // (current working directory in the desktop app sense).
  ses.webRequest.onBeforeSendHeaders((details, callback) => {
    const url = details.url
    const isApiCall =
      url.startsWith(currentConfig.apiBaseUrl) ||
      url.startsWith('http://localhost') ||
      url.startsWith('http://127.0.0.1')
    if (isApiCall) {
      // Always carry the project anchor (no identity claim, just routing)
      if (currentConfig.projectRoot) {
        details.requestHeaders['X-JarvisX-Project'] = currentConfig.projectRoot
      }
      details.requestHeaders['X-JarvisX-Client'] = 'jarvisx-electron/0.1.0-poc'

      if (currentConfig.authToken) {
        // Preferred: signed bearer token. Backend's middleware will
        // verify the signature and bind identity from the claims —
        // X-JarvisX-User would be ignored even if we sent it.
        details.requestHeaders['Authorization'] = `Bearer ${currentConfig.authToken}`
      } else if (currentConfig.userId) {
        // Legacy fallback for localhost dev where auth_required() is false.
        // Will be rejected with 401 the moment the backend enforces auth.
        details.requestHeaders['X-JarvisX-User'] = currentConfig.userId
        details.requestHeaders['X-JarvisX-User-Name'] = encodeURIComponent(
          currentConfig.userName,
        )
      }
    }
    callback({ requestHeaders: details.requestHeaders })
  })
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 920,
    minHeight: 600,
    backgroundColor: '#0d1117',
    title: 'JarvisX',
    // No native menu bar — JarvisX has its own in-window toolbar.
    // autoHideMenuBar = true also hides Alt-toggleable variants.
    autoHideMenuBar: true,
    webPreferences: {
      // preload is emitted as .cjs (see scripts/build-preload.cjs) so
      // Electron loads it as CommonJS — package.json says
      // "type": "module" which would otherwise force .js → ESM and
      // break contextBridge.exposeInMainWorld silently.
      preload: join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      // Iframes embedding the localhost FastAPI need permissive policy.
      // We narrow this in production via CSP if required.
      webSecurity: process.env.NODE_ENV !== 'development',
    },
  })

  if (process.env.NODE_ENV === 'development') {
    await mainWindow.loadURL('http://localhost:5173')
    // DevTools opens on-demand only — toggle with F12 or Cmd/Ctrl-Shift-I.
    // Set JARVISX_DEVTOOLS=1 to auto-open at launch when actually debugging.
    if (process.env.JARVISX_DEVTOOLS === '1') {
      mainWindow.webContents.openDevTools({ mode: 'detach' })
    }
  } else {
    await mainWindow.loadFile(join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // We hid the application menu (Menu.setApplicationMenu(null)) so the
  // built-in F12 / Ctrl-Shift-I shortcuts no longer fire. Wire them
  // back manually so DevTools is always one keystroke away when needed.
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown') return
    const isToggle =
      input.key === 'F12' ||
      ((input.control || input.meta) && input.shift && input.key.toLowerCase() === 'i')
    if (isToggle) {
      event.preventDefault()
      if (mainWindow?.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools()
      } else {
        mainWindow?.webContents.openDevTools({ mode: 'detach' })
      }
    }
  })

  // Right-click context menu — Electron has none by default.
  // Build it dynamically based on what's under the cursor:
  //   - Selected text → Copy
  //   - Editable input/textarea → Cut/Copy/Paste/Select All
  //   - Link → Copy Link
  //   - Image → Save Image
  //   - Always (in dev) → Inspect Element
  mainWindow.webContents.on('context-menu', (_event, params) => {
    const menu = new Menu()
    const wc = mainWindow?.webContents
    const flags = params.editFlags

    // Misspelling suggestions (only on inputs/textareas with spell-check)
    if (params.misspelledWord && params.dictionarySuggestions.length > 0) {
      for (const suggestion of params.dictionarySuggestions.slice(0, 5)) {
        menu.append(new MenuItem({
          label: suggestion,
          click: () => wc?.replaceMisspelling(suggestion),
        }))
      }
      menu.append(new MenuItem({ type: 'separator' }))
    }

    if (params.linkURL) {
      menu.append(new MenuItem({
        label: 'Kopiér link',
        click: () => {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          require('electron').clipboard.writeText(params.linkURL)
        },
      }))
      menu.append(new MenuItem({ type: 'separator' }))
    }

    if (params.hasImageContents) {
      menu.append(new MenuItem({
        label: 'Kopiér billede',
        click: () => wc?.copyImageAt(params.x, params.y),
      }))
      menu.append(new MenuItem({ type: 'separator' }))
    }

    // Standard edit actions — visibility driven by editFlags so we
    // don't show "Paste" on read-only content etc.
    if (flags.canCut) menu.append(new MenuItem({ role: 'cut', label: 'Klip' }))
    if (flags.canCopy) menu.append(new MenuItem({ role: 'copy', label: 'Kopiér' }))
    if (flags.canPaste) menu.append(new MenuItem({ role: 'paste', label: 'Indsæt' }))
    if (flags.canSelectAll) {
      menu.append(new MenuItem({ role: 'selectAll', label: 'Markér alt' }))
    }

    if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
      if (menu.items.length > 0) {
        menu.append(new MenuItem({ type: 'separator' }))
      }
      menu.append(new MenuItem({
        label: 'Inspect Element',
        click: () => wc?.inspectElement(params.x, params.y),
      }))
    }

    if (menu.items.length > 0 && mainWindow) {
      menu.popup({ window: mainWindow })
    }
  })

  startPingLoop()
}

app.whenReady().then(async () => {
  currentConfig = loadConfig()
  installRequestHooks()
  // Remove the application menu entirely (File / Edit / View / Window /
  // Help). JarvisX is its own toolbar; the OS chrome would clutter it.
  Menu.setApplicationMenu(null)

  ipcMain.handle('jarvisx:get-config', () => currentConfig)
  ipcMain.handle('jarvisx:set-config', (_evt, patch: Partial<AppConfig>) => {
    currentConfig = { ...currentConfig, ...patch }
    saveConfig(currentConfig)
    // Restart ping loop in case URL changed
    startPingLoop()
  })
  ipcMain.handle('jarvisx:ping-backend', (_evt, url?: string) => pingBackend(url))

  // Screen capture — list available sources (screens + windows). The
  // renderer presents a picker UI, then calls capture-source with the
  // chosen sourceId via getUserMedia (handled in the renderer because
  // MediaStream APIs only exist there).
  ipcMain.handle('jarvisx:list-screen-sources', async () => {
    try {
      const sources = await desktopCapturer.getSources({
        types: ['screen', 'window'],
        thumbnailSize: { width: 320, height: 200 },
        fetchWindowIcons: true,
      })
      return sources.map((s) => ({
        id: s.id,
        name: s.name,
        display_id: s.display_id,
        thumbnail: s.thumbnail.toDataURL(),
      }))
    } catch (e: unknown) {
      return { error: e instanceof Error ? e.message : String(e) }
    }
  })

  // Project anchor — let the renderer pick a directory natively.
  // We focus the main window first so the dialog reliably surfaces in
  // front on Linux/Wayland where unfocused windows can spawn dialogs
  // behind the active window. We pass mainWindow as parent so the
  // dialog is modal-on-window (correct UX) but only when it exists.
  ipcMain.handle('jarvisx:pick-project-root', async () => {
    try {
      if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore()
        mainWindow.focus()
      }
      const opts = {
        title: 'Anchor Jarvis to a project',
        defaultPath: currentConfig.projectRoot || app.getPath('home'),
        properties: ['openDirectory', 'createDirectory'] as Array<
          'openDirectory' | 'createDirectory'
        >,
      }
      const result = mainWindow
        ? await dialog.showOpenDialog(mainWindow, opts)
        : await dialog.showOpenDialog(opts)
      if (result.canceled || result.filePaths.length === 0) return null
      const picked = result.filePaths[0]
      const recents = [picked, ...currentConfig.recentProjects.filter((p) => p !== picked)]
      currentConfig = {
        ...currentConfig,
        projectRoot: picked,
        recentProjects: recents.slice(0, 8),
      }
      saveConfig(currentConfig)
      return { projectRoot: picked, recentProjects: currentConfig.recentProjects }
    } catch (e: unknown) {
      console.error('[jarvisx] pick-project-root failed:', e)
      throw e
    }
  })

  await createWindow()
  setupAutoUpdater()
  setupGitUpdater()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) void createWindow()
  })
})

app.on('window-all-closed', () => {
  if (pingTimer) {
    clearInterval(pingTimer)
    pingTimer = null
  }
  if (process.platform !== 'darwin') app.quit()
})
