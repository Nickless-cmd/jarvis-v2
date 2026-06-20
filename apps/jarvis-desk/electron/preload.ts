/**
 * Preload — eneste bro mellem renderer og main process.
 *
 * Vi udsætter et MINIMALT API via contextBridge. Renderer kan ikke
 * tilgå Node.js, ipcRenderer eller noget andet uden via dette API.
 */
import { contextBridge, ipcRenderer } from 'electron'

export interface ChannelPluginConfig {
  id: string
  name: string
  botToken: string
  serverId: string
}

export interface JarvisDeskBridge {
  config: {
    get: () => Promise<{ apiBaseUrl: string; authToken: string | null; appId?: string; channelPlugins?: ChannelPluginConfig[] }>
    set: (cfg: { apiBaseUrl?: string; authToken?: string | null; channelPlugins?: ChannelPluginConfig[] }) => Promise<boolean>
  }
  /** Åbn et eksternt link i system-browseren (main filtrerer til http/https/mailto). */
  openExternal: (url: string) => Promise<void>
  /** Registrér aktivt run_id i main-process så det kan cancelles ved quit (R3). */
  setActiveRun: (runId: string | null) => Promise<void>
  /** Giv main-process auth så den kan kalde cancel-endpoint ved quit. */
  setRunAuth: (apiBaseUrl: string, authToken: string | null) => Promise<void>
  /** Registrér den aktuelt fremme session så operator_wakeup re-engagerer dér. */
  setActiveSession: (sessionId: string | null) => Promise<void>
  /** Tænd/sluk systray attention-prik (Jarvis vil noget mens vinduet er skjult). */
  setTrayAttention: (on: boolean) => Promise<void>
  /** Native OS-notifikation når et run slutter. */
  notifyTaskDone: (title: string, body: string) => Promise<void>
  /** Proaktiv device-awareness-notifikation (vises altid, også i fokus). */
  notifyShow: (kind: string, title: string, body: string) => Promise<void>
  /** Er maskinen vågen (ikke i sleep)? Til device-presence. */
  isAwake: () => Promise<boolean>
  /** Geolocation-opslag (Nominatim/ip-api) via main — sætter korrekt User-Agent. */
  geo: {
    geocode: (address: string) => Promise<{ lat: number; lon: number; label: string } | null>
    reverse: (lat: number, lon: number, precise: boolean) => Promise<string>
    ip: () => Promise<{ lat: number; lon: number; label: string } | null>
  }
  /** Åbn native mappe-vælger; returnerer valgt sti eller null. */
  pickFolder: () => Promise<string | null>
  /** Eksportér markdown til en fil via native gem-dialog; true hvis gemt. */
  exportMarkdown: (markdown: string, suggestedName: string) => Promise<boolean>
  /** Code-mode terminal (§17): kør én kommando lokalt, stream output via onTerminalData. */
  terminal: {
    run: (id: string, command: string, cwd?: string) => Promise<{ ok: boolean; error?: string }>
    signal: (id: string, signal?: NodeJS.Signals) => Promise<{ ok: boolean }>
    /** Abonnér på output-chunks. Returnerer unsubscribe. */
    onData: (cb: (e: { id: string; stream: 'stdout' | 'stderr'; chunk: string }) => void) => () => void
    /** Abonnér på proces-exit. Returnerer unsubscribe. */
    onExit: (cb: (e: { id: string; code: number }) => void) => () => void
  }
  /** App auto-update (§22.5): lyt på tilgængelig/klar + styr download/install. */
  updates: {
    onAvailable: (cb: (info: { version?: string }) => void) => () => void
    onReady: (cb: (info: { version?: string }) => void) => () => void
    download: () => Promise<void>
    install: () => Promise<void>
  }
  /** Dependency-doctor: detektér + installér manglende værktøjer (git/gh/node/rg). */
  deps: {
    detect: () => Promise<{ tool: string; present: boolean }[]>
    install: (tool: string) => Promise<{ ok: boolean; log?: string }>
  }
  platform: NodeJS.Platform
}

const bridge: JarvisDeskBridge = {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    set: (cfg) => ipcRenderer.invoke('config:set', cfg),
  },
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  setActiveRun: (runId) => ipcRenderer.invoke('run:setActive', runId),
  setRunAuth: (apiBaseUrl, authToken) => ipcRenderer.invoke('run:setAuth', apiBaseUrl, authToken),
  setActiveSession: (sessionId) => ipcRenderer.invoke('run:setSession', sessionId),
  setTrayAttention: (on) => ipcRenderer.invoke('tray:attention', on),
  notifyTaskDone: (title, body) => ipcRenderer.invoke('notify:taskDone', title, body),
  notifyShow: (kind, title, body) => ipcRenderer.invoke('notify:show', kind, title, body),
  isAwake: () => ipcRenderer.invoke('power:isAwake'),
  geo: {
    geocode: (address: string) => ipcRenderer.invoke('geo:geocode', address),
    reverse: (lat: number, lon: number, precise: boolean) => ipcRenderer.invoke('geo:reverse', lat, lon, precise),
    ip: () => ipcRenderer.invoke('geo:ip'),
  },
  pickFolder: () => ipcRenderer.invoke('dialog:pickFolder'),
  exportMarkdown: (markdown, suggestedName) => ipcRenderer.invoke('session:exportMarkdown', markdown, suggestedName),
  terminal: {
    run: (id, command, cwd) => ipcRenderer.invoke('terminal:run', { id, command, cwd }),
    signal: (id, signal) => ipcRenderer.invoke('terminal:signal', { id, signal }),
    onData: (cb) => {
      const handler = (_e: unknown, data: { id: string; stream: 'stdout' | 'stderr'; chunk: string }) => cb(data)
      ipcRenderer.on('terminal:data', handler)
      return () => ipcRenderer.removeListener('terminal:data', handler)
    },
    onExit: (cb) => {
      const handler = (_e: unknown, data: { id: string; code: number }) => cb(data)
      ipcRenderer.on('terminal:exit', handler)
      return () => ipcRenderer.removeListener('terminal:exit', handler)
    },
  },
  updates: {
    onAvailable: (cb) => {
      const handler = (_e: unknown, info: { version?: string }) => cb(info)
      ipcRenderer.on('update:available', handler)
      return () => ipcRenderer.removeListener('update:available', handler)
    },
    onReady: (cb) => {
      const handler = (_e: unknown, info: { version?: string }) => cb(info)
      ipcRenderer.on('update:ready', handler)
      return () => ipcRenderer.removeListener('update:ready', handler)
    },
    download: () => ipcRenderer.invoke('update:download'),
    install: () => ipcRenderer.invoke('update:install'),
  },
  deps: {
    detect: () => ipcRenderer.invoke('dep:detect'),
    install: (tool) => ipcRenderer.invoke('dep:install', tool),
  },
  platform: process.platform,
}

contextBridge.exposeInMainWorld('jarvisDesk', bridge)
