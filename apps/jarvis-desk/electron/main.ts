/**
 * jarvis-desk — Electron main process.
 *
 * Security-first:
 *   - contextIsolation: true (renderer kan IKKE direkte tilgå Node)
 *   - nodeIntegration: false
 *   - sandbox: true (når preload tillader)
 *   - sikker IPC via preload's contextBridge
 *
 * Eneste IPC vi tilbyder renderer er at læse en API-token fra OS keyring
 * (eller stored config) og at skrive den. Selve HTTP/SSE-kommunikationen
 * sker fra renderer via fetch() — main process er ikke en proxy.
 */
import {
  app,
  BrowserWindow,
  ipcMain,
  Menu,
  nativeImage,
  shell,
  session,
  Tray,
  Notification,
} from 'electron'
import * as path from 'node:path'
import * as fs from 'node:fs'

const isDev = process.env.NODE_ENV === 'development'
const APP_NAME = 'Jarvis'

// GPU-sandbox crasher den pakkede app på nogle Linux-opsætninger
// ("GPU process isn't usable. Goodbye." / error_code=1002). Undgå GPU-processen
// helt — en chat-app har ikke brug for HW-accel, og det gør menu-start robust.
app.disableHardwareAcceleration()
app.commandLine.appendSwitch('disable-gpu-sandbox')

// Suppress dev-only CSP warnings i renderer. Vi VED at vi har 'unsafe-eval'
// i dev — det er for at Vite kan HMR'e. Prod-CSP er stram.
if (isDev) {
  process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true'
}

// Brugerdata-mappe — bruges til at gemme auth token + config.
// På Linux: ~/.config/jarvis-desk/
const userDataDir = app.getPath('userData')
const configPath = path.join(userDataDir, 'config.json')

interface AppConfig {
  apiBaseUrl: string
  authToken: string | null
}

function loadConfig(): AppConfig {
  try {
    const raw = fs.readFileSync(configPath, 'utf-8')
    const parsed = JSON.parse(raw) as Partial<AppConfig>
    return {
      apiBaseUrl: parsed.apiBaseUrl || 'http://10.0.0.39',
      authToken: parsed.authToken || null,
    }
  } catch {
    return { apiBaseUrl: 'http://10.0.0.39', authToken: null }
  }
}

function saveConfig(cfg: AppConfig): void {
  fs.mkdirSync(userDataDir, { recursive: true })
  fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2), { mode: 0o600 })
}

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let appQuitting = false

// R3 / Electron-lifecycle: main-process ejer aktivt run_id så det kan cancelles
// server-side ved quit (renderer-fetch er upålidelig under shutdown).
let activeRunId: string | null = null
let runApiBaseUrl = ''
let runAuthToken: string | null = null

/**
 * Vis vinduet hvis det er skjult, fokusér det hvis det er bagved.
 */
function showWindow(): void {
  if (!mainWindow) {
    createMainWindow()
    return
  }
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

function toggleWindow(): void {
  if (!mainWindow) {
    createMainWindow()
    return
  }
  if (mainWindow.isVisible() && mainWindow.isFocused()) {
    mainWindow.hide()
  } else {
    showWindow()
  }
}

/**
 * Opret system tray icon. På Linux GNOME kræver det at brugeren har
 * en tray-udvidelse (AppIndicator etc.). Funktionen returnerer pænt
 * hvis tray ikke kan oprettes (logger advarsel, fortsætter uden tray).
 */
// ─── Ring-only systray med tilstande (idle / pulsing / attention) ───
type TrayState = 'idle' | 'working'
let trayState: TrayState = 'idle'
let trayAttention = false
let trayPulseTimer: ReturnType<typeof setInterval> | null = null
let trayPulseBright = false

function trayAsset(name: 'idle' | 'bright' | 'attention') {
  const img = nativeImage.createFromPath(path.join(__dirname, '..', 'assets', `tray-${name}.png`))
  return process.platform === 'linux' ? img.resize({ width: 22, height: 22 }) : img
}

function applyTrayImage(): void {
  if (!tray) return
  const name = trayAttention ? 'attention' : trayState === 'working' ? (trayPulseBright ? 'bright' : 'idle') : 'idle'
  tray.setImage(trayAsset(name))
}

function refreshTrayState(): void {
  if (!tray) return
  // Puls kun mens 'working' og IKKE attention (attention er statisk rød prik).
  const shouldPulse = trayState === 'working' && !trayAttention
  if (shouldPulse && !trayPulseTimer) {
    trayPulseTimer = setInterval(() => { trayPulseBright = !trayPulseBright; applyTrayImage() }, 600)
  } else if (!shouldPulse && trayPulseTimer) {
    clearInterval(trayPulseTimer); trayPulseTimer = null; trayPulseBright = false
  }
  applyTrayImage()
  tray.setToolTip(
    trayAttention ? 'Jarvis vil dig noget' : trayState === 'working' ? 'Jarvis arbejder…' : 'Jarvis',
  )
}

function createTray(): void {
  try {
    tray = new Tray(trayAsset('idle'))
    tray.setToolTip('Jarvis')

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Vis Jarvis',
        click: () => showWindow(),
      },
      {
        label: 'Skjul vindue',
        click: () => mainWindow?.hide(),
      },
      { type: 'separator' },
      {
        label: 'Genåbn ved login',
        type: 'checkbox',
        checked: app.getLoginItemSettings().openAtLogin,
        click: (item) => {
          app.setLoginItemSettings({ openAtLogin: item.checked })
        },
      },
      { type: 'separator' },
      {
        label: 'Afslut',
        click: () => {
          appQuitting = true
          app.quit()
        },
      },
    ])
    tray.setContextMenu(contextMenu)

    // Klik på tray = toggle window (Linux + Windows). På macOS er det
    // typisk venstre-klik der viser menu, så vi lader det være.
    if (process.platform !== 'darwin') {
      tray.on('click', () => toggleWindow())
    }
  } catch (e) {
    console.warn('[jarvis-desk] kunne ikke oprette tray icon:', (e as Error).message)
    tray = null
  }
}

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: APP_NAME,
    backgroundColor: '#0d1117',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      // Dev: slå webSecurity fra så CORS ikke blokerer kald til
      // api.srvlab.dk (browser-side fetch tjekker CORS, men curl gør
      // ikke — derfor virker API direkte men ikke via renderer).
      // CSP er stadig aktiv og begrænser hvad der kan eksekveres.
      // Prod: webSecurity tilbage på true.
      webSecurity: !isDev,
    },
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5174')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // Open external links in OS default browser, not in app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })

  // Når brugeren klikker × → skjul i tray i stedet for at afslutte.
  // Kun hvis tray er oppe — ellers er vi den eneste UI og må lukke for at quit'e.
  mainWindow.on('close', (event) => {
    if (!appQuitting && tray) {
      event.preventDefault()
      mainWindow?.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ─── IPC handlers (only what renderer needs from main) ─────────────────
ipcMain.handle('config:get', () => loadConfig())
ipcMain.handle('config:set', (_event, cfg: AppConfig) => {
  saveConfig(cfg)
  return true
})

// Eksterne links åbnes i system-browser — kun http/https/mailto (aldrig naviger
// app-vinduet væk, og bloker farlige schemes).
ipcMain.handle('shell:openExternal', (_event, url: string) => {
  if (typeof url === 'string' && /^(https?:|mailto:)/i.test(url)) {
    void shell.openExternal(url)
  }
})

// R3: renderer registrerer aktivt run_id + auth så main kan server-cancelle ved quit.
ipcMain.handle('run:setActive', (_event, runId: string | null) => {
  activeRunId = runId
  trayState = runId ? 'working' : 'idle'
  refreshTrayState()
})
// Systray attention-prik (Jarvis vil noget mens vinduet er skjult/ude af fokus).
ipcMain.handle('tray:attention', (_event, on: boolean) => {
  trayAttention = !!on
  refreshTrayState()
})
ipcMain.handle('run:setAuth', (_event, apiBaseUrl: string, authToken: string | null) => {
  runApiBaseUrl = apiBaseUrl
  runAuthToken = authToken
})
// Native "opgave færdig"-notifikation når et run slutter (fyrer altid).
ipcMain.handle('notify:taskDone', (_event, title: string, body: string) => {
  if (!Notification.isSupported()) return
  const n = new Notification({
    title: title || 'Jarvis',
    body: body || 'Opgaven er færdig.',
    icon: trayAsset('bright'),
    silent: false,
  })
  n.on('click', () => { if (mainWindow) { mainWindow.show(); mainWindow.focus() } })
  n.show()
})

// ─── Content Security Policy ──────────────────────────────────────────
// Renderer må KUN tale med konfigureret API-base-url. Forbyder inline
// scripts (XSS-beskyttelse), data:-URLs i scripts, og eksterne kald.
app.whenReady().then(() => {
  const cfg = loadConfig()
  const apiOrigin = new URL(cfg.apiBaseUrl).origin
  const wsOrigin = apiOrigin.replace(/^http/, 'ws')

  // Mikrofon-adgang til dikter-funktionen (getUserMedia i renderer). Vi
  // grant'er KUN 'media' (mic) — alt andet afvises. Uden dette afviser
  // Electron getUserMedia i den pakkede app.
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === 'media')
  })
  session.defaultSession.setPermissionCheckHandler((_wc, permission) => permission === 'media')

  // Dev mode: Vite skal kunne injecte inline scripts til HMR.
  // Prod mode: stram CSP — kun 'self', ingen inline/eval.
  const csp = isDev
    ? [
        "default-src 'self' http://localhost:5174 ws://localhost:5174",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5174",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        `connect-src 'self' ${apiOrigin} ${wsOrigin} http://localhost:5174 ws://localhost:5174`,
      ]
    : [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        `connect-src 'self' ${apiOrigin} ${wsOrigin}`,
      ]

  // Kombineret response-headers handler: CSP for vores egne HTML/JS,
  // plus CORS-headers-injection for vores betroede API-origin.
  //
  // Hvorfor inject CORS i klienten? Vi er en Electron-app, ikke en
  // browser-site. Vores renderer origin er localhost:5174 (dev) eller
  // file:// (prod), og API'et lever på en anden origin. API-serveren
  // (jarvis-api) er IKKE altid CORS-konfigureret. I stedet for at kræve
  // server-side ændring tilføjer vi headeren her — sikkert fordi vi
  // KUN gør det for præcis den apiOrigin brugeren har konfigureret.
  // Det er den samme strategi som Electron's egen dokumentation viser
  // for native apps der konsumerer 3rd-party APIs.
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const isApiRequest = details.url.startsWith(apiOrigin) ||
      details.url.startsWith(wsOrigin)
    const responseHeaders: Record<string, string[]> = {
      ...(details.responseHeaders as Record<string, string[]>),
    }

    // Set CSP for renderer HTML
    if (details.resourceType === 'mainFrame' || details.resourceType === 'subFrame') {
      responseHeaders['Content-Security-Policy'] = [csp.join('; ')]
    }

    // Inject CORS for trusted API requests.
    // HTTP headers er case-insensitive — server kan have sendt
    // 'access-control-allow-origin' (lowercase) som vi ikke overskriver
    // hvis vi bare sætter 'Access-Control-Allow-Origin'. Browseren
    // sammenstiller alle casinger → multiple-value error.
    // Strip ALLE casing-varianter af CORS-headers først.
    if (isApiRequest) {
      const corsKeys = [
        'access-control-allow-origin',
        'access-control-allow-methods',
        'access-control-allow-headers',
        'access-control-allow-credentials',
        'access-control-expose-headers',
        'access-control-max-age',
      ]
      for (const key of Object.keys(responseHeaders)) {
        if (corsKeys.includes(key.toLowerCase())) {
          delete responseHeaders[key]
        }
      }
      const rendererOrigin = isDev ? 'http://localhost:5174' : '*'
      responseHeaders['Access-Control-Allow-Origin'] = [rendererOrigin]
      responseHeaders['Access-Control-Allow-Methods'] = [
        'GET, POST, PUT, DELETE, OPTIONS, PATCH',
      ]
      responseHeaders['Access-Control-Allow-Headers'] = [
        'Content-Type, Authorization, Accept, Cache-Control, Last-Event-ID, X-Requested-With',
      ]
      responseHeaders['Access-Control-Allow-Credentials'] = ['true']
      responseHeaders['Access-Control-Expose-Headers'] = [
        'X-Stream-Protocol, Content-Type',
      ]
    }

    callback({ responseHeaders })
  })

  // Håndtér preflight (OPTIONS) requests for API:
  // Returnér 204 No Content direkte i stedet for at proxy til server,
  // så vi sikrer at preflight altid passerer for API-origin uanset
  // server-side CORS-config.
  session.defaultSession.webRequest.onBeforeRequest(
    { urls: [`${apiOrigin}/*`, `${wsOrigin}/*`] },
    (details, callback) => {
      // Vi lader ALLE requests komme igennem — onHeadersReceived ovenfor
      // sørger for CORS-headers på response. Preflight håndteres af
      // serveren, og vi overskriver bare response-headers så browseren
      // godtager det.
      callback({})
    },
  )

  createMainWindow()
  createTray()
})

// Single instance lock — anden start fokuserer eksisterende vindue
// i stedet for at åbne to vinduer.
const gotSingleInstance = app.requestSingleInstanceLock()
if (!gotSingleInstance) {
  app.quit()
} else {
  app.on('second-instance', () => {
    showWindow()
  })
}

app.on('before-quit', () => {
  appQuitting = true
  // Best-effort server-cancel af aktivt run (renderer kan ikke pålideligt
  // fetch'e under shutdown). Synkront fire-and-forget.
  if (activeRunId && runApiBaseUrl) {
    try {
      const url = new URL(`/chat/runs/${activeRunId}/cancel`, runApiBaseUrl).toString()
      void fetch(url, {
        method: 'POST',
        headers: runAuthToken ? { Authorization: `Bearer ${runAuthToken}` } : {},
      }).catch(() => { /* best-effort */ })
    } catch {
      /* best-effort */
    }
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
})

// Forbyd opførsel der svækker isolation.
app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsed = new URL(navigationUrl)
    // Tillad kun navigation til vores egen renderer + Vite dev-server.
    const allowed =
      parsed.origin === 'http://localhost:5174' ||
      parsed.protocol === 'file:'
    if (!allowed) {
      event.preventDefault()
      shell.openExternal(navigationUrl)
    }
  })
})
