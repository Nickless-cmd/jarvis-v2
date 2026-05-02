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
  // Auto-updater (electron-updater — release-based, dormant for now)
  updaterCheck: () => ipcRenderer.invoke('jarvisx:updater-check'),
  updaterDownload: () => ipcRenderer.invoke('jarvisx:updater-download'),
  updaterInstall: () => ipcRenderer.invoke('jarvisx:updater-install'),
  updaterStatus: () => ipcRenderer.invoke('jarvisx:updater-status'),
  onUpdaterStatus: (cb: (status: unknown) => void) => {
    const listener = (_evt: unknown, status: unknown) => cb(status)
    ipcRenderer.on('updater-status', listener)
    return () => {
      ipcRenderer.removeListener('updater-status', listener)
    }
  },
  // Git-based updater (run-from-source — what Bjørn actually uses)
  gitUpdateCheck: () => ipcRenderer.invoke('jarvisx:git-update-check'),
  gitUpdateStatus: () => ipcRenderer.invoke('jarvisx:git-update-status'),
  gitUpdatePullAndRebuild: () => ipcRenderer.invoke('jarvisx:git-update-pull-and-rebuild'),
  onGitUpdateStatus: (cb: (status: unknown) => void) => {
    const listener = (_evt: unknown, status: unknown) => cb(status)
    ipcRenderer.on('git-update-status', listener)
    return () => {
      ipcRenderer.removeListener('git-update-status', listener)
    }
  },
})
