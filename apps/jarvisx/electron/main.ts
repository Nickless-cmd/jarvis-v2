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
import { app, BrowserWindow, desktopCapturer, dialog, ipcMain, Menu, session } from 'electron'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs'

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
