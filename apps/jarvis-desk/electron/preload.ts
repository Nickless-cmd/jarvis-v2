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
  platform: process.platform,
}

contextBridge.exposeInMainWorld('jarvisDesk', bridge)
