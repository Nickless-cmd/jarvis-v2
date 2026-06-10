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
  platform: NodeJS.Platform
}

const bridge: JarvisDeskBridge = {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    set: (cfg) => ipcRenderer.invoke('config:set', cfg),
  },
  platform: process.platform,
}

contextBridge.exposeInMainWorld('jarvisDesk', bridge)
