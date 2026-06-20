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
  dialog,
  powerMonitor,
} from 'electron'
import * as path from 'node:path'
import * as fs from 'node:fs'
import * as os from 'node:os'
import { spawn, type ChildProcess } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import * as geo from './geo'

const isDev = process.env.NODE_ENV === 'development'
const APP_NAME = 'Jarvis'

// GPU-rendering: HW-acceleration er TIL (software-rendering gav glitchy grafik
// ved view-skift på Linux). disable-gpu-sandbox + ignore-gpu-blocklist gør den
// pakkede app robust på NVIDIA/Linux uden at ramme den gamle GPU-sandbox-crash
// ("GPU process isn't usable. Goodbye." / error_code=1002).
// Hvis den crasher igen: sæt app.disableHardwareAcceleration() tilbage som
// første linje og fjern de to ignore/blocklist-switches.
app.commandLine.appendSwitch('disable-gpu-sandbox')
app.commandLine.appendSwitch('ignore-gpu-blocklist')
// KRITISK for cross-device realtime (Bjørn 2026-06-20): Chromium throttler
// renderer-timere (setInterval) i ufokuserede/okkluderede vinduer → active-runs-
// pollet + transcript-refresh fryser til ~1/4s når desk-vinduet ikke er i fokus
// (netop når man tager over fra mobil). webPreferences.backgroundThrottling:false
// alene var IKKE nok på Linux. Disse switches slår throttlingen helt fra.
app.commandLine.appendSwitch('disable-background-timer-throttling')
app.commandLine.appendSwitch('disable-renderer-backgrounding')
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows')

// Suppress dev-only CSP warnings i renderer. Vi VED at vi har 'unsafe-eval'
// i dev — det er for at Vite kan HMR'e. Prod-CSP er stram.
if (isDev) {
  process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true'
}

// Brugerdata-mappe — bruges til at gemme auth token + config.
// På Linux: ~/.config/jarvis-desk/
const userDataDir = app.getPath('userData')
const configPath = path.join(userDataDir, 'config.json')

interface ChannelPluginConfig {
  id: string
  name: string
  botToken: string   // KLIENT-side, sendes aldrig til Jarvis-serveren (§5.2)
  serverId: string
}

interface AppConfig {
  apiBaseUrl: string
  authToken: string | null
  // UUID4 sat ved første launch (TOTP Fase 2). Binder denne installation
  // kryptografisk til owner-sessionen: owner i sin egen app (matchende app_id)
  // kræver ingen TOTP; fremmed kontekst gør. Persisteres så det er stabilt.
  appId: string
  // Lokale kanal-plugins (TOTP Fase 5): brugerens egne Discord-servere, token lokalt.
  channelPlugins: ChannelPluginConfig[]
}

function loadConfig(): AppConfig {
  let parsed: Partial<AppConfig> = {}
  try {
    parsed = JSON.parse(fs.readFileSync(configPath, 'utf-8')) as Partial<AppConfig>
  } catch {
    parsed = {}
  }
  const cfg: AppConfig = {
    apiBaseUrl: parsed.apiBaseUrl || 'http://10.0.0.39',
    authToken: parsed.authToken || null,
    appId: parsed.appId || randomUUID(),
    channelPlugins: Array.isArray(parsed.channelPlugins) ? parsed.channelPlugins : [],
  }
  // Persistér et nygenereret app-ID med det samme, så det overlever genstart.
  if (!parsed.appId) {
    try { saveConfig(cfg) } catch { /* non-fatal: regenereres næste gang */ }
  }
  return cfg
}

function saveConfig(cfg: AppConfig): void {
  fs.mkdirSync(userDataDir, { recursive: true })
  fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2), { mode: 0o600 })
}

let mainWindow: BrowserWindow | null = null
let lastNotification: Notification | null = null
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
let traySpinTimer: ReturnType<typeof setInterval> | null = null
let traySpinFrame = 0
const TRAY_ROT_FRAMES = 12

function trayAsset(name: 'idle' | 'bright' | 'attention') {
  const img = nativeImage.createFromPath(path.join(__dirname, '..', 'assets', `tray-${name}.png`))
  return process.platform === 'linux' ? img.resize({ width: 22, height: 22 }) : img
}

function trayRotAsset(frame: number) {
  const n = String(frame % TRAY_ROT_FRAMES).padStart(2, '0')
  const img = nativeImage.createFromPath(path.join(__dirname, '..', 'assets', `tray-rot-${n}.png`))
  return process.platform === 'linux' ? img.resize({ width: 22, height: 22 }) : img
}

function applyTrayImage(): void {
  if (!tray) return
  if (trayAttention) { tray.setImage(trayAsset('attention')); return }
  if (trayState === 'working') { tray.setImage(trayRotAsset(traySpinFrame)); return }
  tray.setImage(trayAsset('idle'))
}

function refreshTrayState(): void {
  if (!tray) return
  // Drej ringen mens 'working' og IKKE attention; ellers står den stille.
  const shouldSpin = trayState === 'working' && !trayAttention
  if (shouldSpin && !traySpinTimer) {
    traySpinTimer = setInterval(() => { traySpinFrame = (traySpinFrame + 1) % TRAY_ROT_FRAMES; applyTrayImage() }, 90)
  } else if (!shouldSpin && traySpinTimer) {
    clearInterval(traySpinTimer); traySpinTimer = null; traySpinFrame = 0
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

/** Markér + kopiér + højreklik i chat (Bjørn 2026-06-13: kunne markere men
 *  ikke kopiere). To rod-årsager, begge her:
 *  1) Uden en application-menu findes standard-acceleratorerne (Ctrl+C/V/X/A)
 *     ikke i Electron → Ctrl+C gjorde intet. En skjult Edit-menu (autoHideMenuBar)
 *     registrerer dem globalt uden at fylde i UI'et.
 *  2) Ingen højreklik-context-menu var wired. Vi viser Kopiér/Markér alt på
 *     markeret tekst, og Klip/Kopiér/Indsæt/Markér alt i redigerbare felter. */
function setupEditMenuAndContextMenu(win: BrowserWindow): void {
  // 1) Edit-roller → acceleratorer (skjult menubar, men funktionel).
  Menu.setApplicationMenu(Menu.buildFromTemplate([{ role: 'editMenu' }]))

  // 2) Højreklik-context-menu.
  win.webContents.on('context-menu', (_e, params) => {
    const items: Electron.MenuItemConstructorOptions[] = []
    if (params.isEditable) {
      items.push(
        { label: 'Klip', role: 'cut', enabled: params.editFlags.canCut },
        { label: 'Kopiér', role: 'copy', enabled: params.editFlags.canCopy },
        { label: 'Indsæt', role: 'paste', enabled: params.editFlags.canPaste },
        { type: 'separator' },
        { label: 'Markér alt', role: 'selectAll' },
      )
    } else if (params.selectionText && params.selectionText.trim()) {
      items.push(
        { label: 'Kopiér', role: 'copy' },
        { type: 'separator' },
        { label: 'Markér alt', role: 'selectAll' },
      )
    } else {
      items.push({ label: 'Markér alt', role: 'selectAll' })
    }
    Menu.buildFromTemplate(items).popup({ window: win })
  })
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
      // KRITISK for cross-device realtime (Bjørn 2026-06-20): uden dette
      // throttler Chromium renderer-timere (setInterval) til ~1/min når vinduet
      // er ufokuseret/i baggrunden — netop når man "tager over fra mobilen" og
      // desk-vinduet er i baggrunden. Det frøs active-runs-pollet + transcript-
      // refresh → mobil→desktop opdaterede aldrig. false = polls kører fuldt.
      backgroundThrottling: false,
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

  setupEditMenuAndContextMenu(mainWindow)

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

  // Når appen får fokus: ryd dock/launcher-badge'en og luk en evt. hængende
  // "opgave færdig"-notifikation. Ellers bliver det grønne tal (1) hængende på
  // ikonet selv efter man har åbnet appen.
  mainWindow.on('focus', () => {
    app.setBadgeCount(0)
    if (lastNotification) { try { lastNotification.close() } catch { /* ignore */ } lastNotification = null }
  })
}

// ─── IPC handlers (only what renderer needs from main) ─────────────────
ipcMain.handle('config:get', () => loadConfig())
ipcMain.handle('config:set', (_event, cfg: Partial<AppConfig>) => {
  // Bevar app-ID — renderer sender kun apiBaseUrl/authToken og må ikke kunne
  // nulstille installationens identitet.
  const existing = loadConfig()
  saveConfig({
    apiBaseUrl: cfg.apiBaseUrl ?? existing.apiBaseUrl,
    authToken: cfg.authToken ?? existing.authToken,
    appId: existing.appId,
    channelPlugins: cfg.channelPlugins ?? existing.channelPlugins,
  })
  // Genstart operator-broen + lokale kanal-gateways med de nye credentials/plugins.
  void bootstrapBridge()
  void bootstrapLocalDiscord()
  void bootstrapAppDispatch()
  return true
})

// ── Dependency-doctor (§ dep): detektér + installér manglende værktøjer ──
ipcMain.handle('dep:detect', async () => {
  const { detectTools } = await import('./depDoctor')
  return detectTools()
})
ipcMain.handle('dep:install', async (_e, tool: string) => {
  const { installCommand } = await import('./depInstall')
  const { execFile } = await import('node:child_process')
  let pkgManager: 'apt' | 'dnf' | 'pacman' | undefined
  if (process.platform === 'linux') {
    for (const pm of ['apt', 'dnf', 'pacman'] as const) {
      const ok = await new Promise<boolean>((res) =>
        execFile('/bin/sh', ['-c', `command -v ${pm === 'apt' ? 'apt-get' : pm}`], (err) => res(!err)))
      if (ok) { pkgManager = pm; break }
    }
  }
  const c = installCommand(tool, { platform: process.platform, pkgManager })
  if (!c) return { ok: false, log: 'ukendt værktøj' }
  return new Promise<{ ok: boolean; log?: string }>((resolve) => {
    execFile(c.cmd, c.args, { timeout: 300_000 }, (err, stdout, stderr) => {
      resolve({ ok: !err, log: ((stdout || '') + (stderr || '')).slice(-500) })
    })
  })
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
// Renderer pusher den aktuelt fremme session → main kan binde operator_wakeup
// til netop den desk-samtale (i stedet for en frisk/forkert).
ipcMain.handle('run:setSession', async (_event, sessionId: string | null) => {
  try {
    const m = await import('./bridge.js')
    m.setActiveSessionId(sessionId)
  } catch { /* bridge ikke loaded endnu — ignoreres */ }
})
// Native mappe-vælger til Code-mode workstation-workspace (brugerens computer).
ipcMain.handle('dialog:pickFolder', async () => {
  const res = await dialog.showOpenDialog({
    title: 'Vælg en mappe på din computer',
    properties: ['openDirectory', 'createDirectory'],
  })
  if (res.canceled || !res.filePaths.length) return null
  return res.filePaths[0]
})
// Native "opgave færdig"-notifikation når et run slutter. Springes over hvis
// vinduet allerede er i fokus (ingen grund til at notificere/badge når brugeren
// kigger på appen — det er netop dér det grønne tal blev hængende).
function showNativeNotification(title: string, body: string, opts?: { skipWhenFocused?: boolean }): void {
  if (!Notification.isSupported()) return
  if (opts?.skipWhenFocused && mainWindow?.isFocused()) return
  const n = new Notification({
    title: title || 'Jarvis',
    body: body || 'Jarvis vil dig noget.',
    icon: trayAsset('bright'),
    silent: false,
  })
  n.on('click', () => {
    app.setBadgeCount(0)
    if (mainWindow) { mainWindow.show(); mainWindow.focus() }
  })
  n.on('close', () => { if (lastNotification === n) lastNotification = null })
  lastNotification = n
  n.show()
}

ipcMain.handle('notify:taskDone', (_event, title: string, body: string) => {
  // Bagudkompat: spring over når vinduet er i fokus (det grønne tal hænger ellers).
  showNativeNotification(title, body || 'Opgaven er færdig.', { skipWhenFocused: true })
})

// Proaktiv device-awareness-notifikation (svar-klar/reminder/initiativ rutet hertil).
// Vis ALTID — også i fokus — for proaktive beskeder er pointen at nå brugeren.
ipcMain.handle('notify:show', (_event, _kind: string, title: string, body: string) => {
  showNativeNotification(title, body)
})

// Sleep/wake-tilstand til device-presence (sovende desktop = ikke routing-kandidat).
let _systemAwake = true
powerMonitor.on('suspend', () => { _systemAwake = false })
powerMonitor.on('resume', () => { _systemAwake = true })
ipcMain.handle('power:isAwake', () => _systemAwake)

// Geolocation-opslag (Nominatim/ip-api) fra main → renderer kan ikke sætte
// User-Agent som Nominatim kræver. Logikken bor i electron/geo.ts.
ipcMain.handle('geo:geocode', (_e, address: string) => geo.geocode(address))
ipcMain.handle('geo:reverse', (_e, lat: number, lon: number, precise: boolean) => geo.reverse(lat, lon, precise))
ipcMain.handle('geo:ip', () => geo.ipLookup())

// Eksportér en samtale som markdown — via native gem-dialog (renderer-side blob-
// download er upålidelig i Electron). Renderer bygger markdown'en, main skriver
// den til den valgte sti.
ipcMain.handle('session:exportMarkdown', async (_event, markdown: string, suggestedName: string) => {
  const res = await dialog.showSaveDialog({
    title: 'Eksportér samtale',
    defaultPath: suggestedName || 'samtale.md',
    filters: [{ name: 'Markdown', extensions: ['md'] }],
  })
  if (res.canceled || !res.filePath) return false
  await fs.promises.writeFile(res.filePath, markdown, 'utf-8')
  return true
})

// ─── Code-mode terminal (§17) ─────────────────────────────────────────
// Lokal kommando-runner til terminal-ruden i Code mode. Kører KUN på
// brugerens egen maskine (samme model som operator-bridgen) — én kommando
// pr. kald via login-shell, output streames linje-for-linje til renderer.
// Ingen node-pty (undgår native-build i pakning); dækker "kør kommando, se
// output" som spec'ens §17 beskriver. Interaktive TTY-programmer (vim, top)
// understøttes bevidst ikke i v1.
const terminalProcs = new Map<string, ChildProcess>()

function terminalShell(command: string): { cmd: string; args: string[] } {
  if (process.platform === 'win32') {
    return { cmd: 'powershell.exe', args: ['-NoProfile', '-NonInteractive', '-Command', command] }
  }
  const shell = process.env.SHELL || '/bin/bash'
  return { cmd: shell, args: ['-lc', command] }
}

ipcMain.handle('terminal:run', (_event, payload: { id: string; command: string; cwd?: string }) => {
  const { id, command } = payload || {}
  if (!id || typeof command !== 'string') return { ok: false, error: 'ugyldig terminal-anmodning' }
  // Genbrug ikke et kørende id; dræb det gamle først.
  terminalProcs.get(id)?.kill()
  let cwd = payload.cwd && fs.existsSync(payload.cwd) ? payload.cwd : os.homedir()
  try { if (!fs.statSync(cwd).isDirectory()) cwd = os.homedir() } catch { cwd = os.homedir() }
  const { cmd, args } = terminalShell(command)
  let child: ChildProcess
  try {
    child = spawn(cmd, args, { cwd, env: process.env, windowsHide: true })
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) }
  }
  terminalProcs.set(id, child)
  const send = (channel: string, data: unknown) => {
    if (!mainWindow || mainWindow.isDestroyed()) return
    mainWindow.webContents.send(channel, data)
  }
  child.stdout?.on('data', (b: Buffer) => send('terminal:data', { id, stream: 'stdout', chunk: b.toString('utf-8') }))
  child.stderr?.on('data', (b: Buffer) => send('terminal:data', { id, stream: 'stderr', chunk: b.toString('utf-8') }))
  child.on('error', (err) => {
    send('terminal:data', { id, stream: 'stderr', chunk: `\n[fejl] ${err.message}\n` })
    send('terminal:exit', { id, code: -1 })
    terminalProcs.delete(id)
  })
  child.on('close', (code) => {
    send('terminal:exit', { id, code: code ?? 0 })
    terminalProcs.delete(id)
  })
  return { ok: true }
})

ipcMain.handle('terminal:signal', (_event, payload: { id: string; signal?: NodeJS.Signals }) => {
  const child = terminalProcs.get(payload?.id)
  if (!child) return { ok: false }
  try { child.kill(payload.signal || 'SIGINT') } catch { /* allerede død */ }
  return { ok: true }
})

// Ryd op i kørende terminaler ved quit (ingen forældreløse processer).
app.on('before-quit', () => {
  for (const child of terminalProcs.values()) { try { child.kill() } catch { /* noop */ } }
  terminalProcs.clear()
})

// ─── Content Security Policy ──────────────────────────────────────────
// Renderer må KUN tale med konfigureret API-base-url. Forbyder inline
// scripts (XSS-beskyttelse), data:-URLs i scripts, og eksterne kald.
app.whenReady().then(() => {
  const cfg = loadConfig()
  const apiOrigin = new URL(cfg.apiBaseUrl).origin
  const wsOrigin = apiOrigin.replace(/^http/, 'ws')

  // §22.5: auto-update via electron-updater + GitHub releases. autoDownload er
  // FRA — renderer viser UpdateCard og brugeren beslutter (download/genstart).
  // Graceful: hvis dep/release-config mangler (fx dev) fanges alt og bliver no-op.
  void (async () => {
    try {
      const updMod = await import('electron-updater')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const up = (updMod as any)?.autoUpdater ?? (updMod as any)?.default?.autoUpdater
      if (!up) return
      const { wireUpdater } = await import('./autoUpdate')
      const api = wireUpdater(up, (ch, p) => mainWindow?.webContents.send(ch, p))
      ipcMain.handle('update:download', () => api.download())
      ipcMain.handle('update:install', () => api.installNow())
      api.check()
      setInterval(() => api.check(), 6 * 3_600_000)
    } catch { /* dep/release-config mangler → no-op */ }
  })()

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
  void bootstrapBridge()
  void bootstrapLocalDiscord()
  void bootstrapAppDispatch()
})

// ─── Operator-bro (JarvisX-bridge) ──────────────────────────────────────
// Outbound WS til Jarvis-runtime: lader Jarvis dispatche operator_*-tools
// (fil, bash, m.m.) tilbage til DENNE maskine. Uden den fejler operator-
// tools med bridge_not_connected. Port af apps/jarvisx/electron/bridge.ts.
let activeBridge: { stop(): void; start(): void } | null = null

async function bootstrapBridge(): Promise<void> {
  try {
    const cfg = loadConfig()
    if (!cfg.apiBaseUrl || !cfg.authToken) return // ikke konfigureret endnu
    // Hent userId via whoami (broen registrerer sig pr. bruger).
    let userId = ''
    try {
      const r = await fetch(new URL('/api/whoami', cfg.apiBaseUrl).toString(), {
        headers: { Authorization: `Bearer ${cfg.authToken}` },
      })
      if (r.ok) userId = String((await r.json() as { user_id?: string })?.user_id || '')
    } catch { /* serveren udleder user_id fra token-claims hvis tom */ }
    const bridgeMod = await import('./bridge.js')
    if (activeBridge) { try { activeBridge.stop() } catch { /* noop */ } }
    activeBridge = new bridgeMod.JarvisXBridge({
      apiBaseUrl: cfg.apiBaseUrl,
      userId,
      authToken: cfg.authToken ?? undefined,
      appId: cfg.appId,
      log: (m: string) => console.log(`[bridge] ${m}`),
    })
    activeBridge.start()
    // Resurrect any reminders/wakeups left over from previous runs.
    // Past-due ones fire immediately as catch-up; future ones get fresh
    // setTimeout entries. Safe to call multiple times — idempotent.
    try { bridgeMod.loadAndScheduleEvents?.() } catch (e) {
      console.warn('loadAndScheduleEvents failed:', e)
    }
  } catch (e) {
    console.warn('bridge bootstrap failed:', e)
  }
}

// ─── Lokal Discord-gateway (TOTP Fase 5 §5.2) ───────────────────────────
// Forbinder til brugerens EGNE Discord-servere (token lokalt). Native server
// uberørt (server-side). Genstartes ved config:set.
let activeLocalDiscord: { stop(): void; sendToChannel(c: string, t: string): Promise<boolean> } | null = null
let activeAppDispatch: { stop(): void } | null = null

async function bootstrapLocalDiscord(): Promise<void> {
  try {
    const cfg = loadConfig()
    if (activeLocalDiscord) { try { activeLocalDiscord.stop() } catch { /* noop */ } activeLocalDiscord = null }
    if (!cfg.channelPlugins.length || !cfg.apiBaseUrl) return
    const mod = await import('./localDiscordGateway.js')
    const gw = new mod.LocalDiscordGateway({
      apiBaseUrl: cfg.apiBaseUrl,
      authToken: cfg.authToken ?? undefined,
      log: (m: string) => console.log(`[localDiscord] ${m}`),
    })
    gw.start(cfg.channelPlugins)
    activeLocalDiscord = gw
  } catch (e) {
    console.warn('localDiscord bootstrap failed:', e)
  }
}

// §18.5 Fase 2: poll serveren for runtime→app instruktioner og udfør lokalt
// (notifikationer + proaktive Discord-beskeder). Genstartes ved config:set.
async function bootstrapAppDispatch(): Promise<void> {
  try {
    const cfg = loadConfig()
    if (activeAppDispatch) { try { activeAppDispatch.stop() } catch { /* noop */ } activeAppDispatch = null }
    if (!cfg.apiBaseUrl) return
    const mod = await import('./appDispatchWatcher.js')
    const w = new mod.AppDispatchWatcher({
      apiBaseUrl: cfg.apiBaseUrl,
      authToken: cfg.authToken ?? undefined,
      sendDiscord: (c: string, t: string) => activeLocalDiscord?.sendToChannel(c, t) ?? Promise.resolve(false),
      log: (m: string) => console.log(`[appDispatch] ${m}`),
    })
    w.start()
    activeAppDispatch = w
  } catch (e) {
    console.warn('appDispatch bootstrap failed:', e)
  }
}

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
  try { activeBridge?.stop() } catch { /* best-effort */ }
  try { activeLocalDiscord?.stop() } catch { /* best-effort */ }
  try { activeAppDispatch?.stop() } catch { /* best-effort */ }
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
