/**
 * Preload bridge — minimal surface exposed to the renderer via
 * contextBridge. Keep this small. Anything we add here needs a typing
 * counterpart in src/types.d.ts.
 */
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('jarvisx', {
  getConfig: () => ipcRenderer.invoke('jarvisx:get-config'),
  setConfig: (patch: Record<string, unknown>) =>
    ipcRenderer.invoke('jarvisx:set-config', patch),
  pingBackend: (url?: string) => ipcRenderer.invoke('jarvisx:ping-backend', url),
  pickProjectRoot: () => ipcRenderer.invoke('jarvisx:pick-project-root'),
  listScreenSources: () => ipcRenderer.invoke('jarvisx:list-screen-sources'),
  onBackendStatus: (cb: (status: { up: boolean; latencyMs?: number }) => void) => {
    const listener = (_evt: unknown, status: { up: boolean; latencyMs?: number }) =>
      cb(status)
    ipcRenderer.on('backend-status', listener)
    return () => {
      ipcRenderer.removeListener('backend-status', listener)
    }
  },
})
