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
} from 'electron'
import * as path from 'node:path'
import * as fs from 'node:fs'

const isDev = process.env.NODE_ENV === 'development'
const APP_NAME = 'jarvis-desk'

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
function createTray(): void {
  try {
    const iconPath = path.join(__dirname, '..', 'assets', 'icon-48.png')
    const image = nativeImage.createFromPath(iconPath)
    // Linux: resize til 22x22 (standard panel-størrelse)
    const trayImage = process.platform === 'linux'
      ? image.resize({ width: 22, height: 22 })
      : image

    tray = new Tray(trayImage)
    tray.setToolTip('jarvis-desk')

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
      webSecurity: true,
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

// ─── Content Security Policy ──────────────────────────────────────────
// Renderer må KUN tale med konfigureret API-base-url. Forbyder inline
// scripts (XSS-beskyttelse), data:-URLs i scripts, og eksterne kald.
app.whenReady().then(() => {
  const cfg = loadConfig()
  const apiOrigin = new URL(cfg.apiBaseUrl).origin
  const wsOrigin = apiOrigin.replace(/^http/, 'ws')

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'", // tilladt for Vite HMR
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            `connect-src 'self' ${apiOrigin} ${wsOrigin}` +
              (isDev ? ' http://localhost:5174 ws://localhost:5174' : ''),
          ].join('; '),
        ],
      },
    })
  })

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
