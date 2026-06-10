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
import { app, BrowserWindow, ipcMain, shell, session } from 'electron'
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
