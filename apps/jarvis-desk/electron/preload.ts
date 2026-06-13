/**
 * Preload — eneste bro mellem renderer og main process.
 *
 * Vi udsætter et MINIMALT API via contextBridge. Renderer kan ikke
 * tilgå Node.js, ipcRenderer eller noget andet uden via dette API.
 */
import { contextBridge, ipcRenderer } from 'electron'

export interface JarvisDeskBridge {
  config: {
    get: () => Promise<{ apiBaseUrl: string; authToken: string | null }>
    set: (cfg: { apiBaseUrl: string; authToken: string | null }) => Promise<boolean>
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
  platform: process.platform,
}

contextBridge.exposeInMainWorld('jarvisDesk', bridge)
