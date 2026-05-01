/**
 * Bridge surface exposed by electron/preload.ts via contextBridge.
 * Renderer reads/writes runtime config (server URL, identity) and listens
 * to backend health pings. We deliberately keep this small — Phase 0
 * doesn't need much from main.
 */
export interface JarvisXBridge {
  getConfig: () => Promise<{
    apiBaseUrl: string
    userId: string
    userName: string
    mode: 'dev' | 'thin-client' | 'standalone'
    projectRoot: string
    recentProjects: string[]
  }>
  setConfig: (cfg: {
    apiBaseUrl?: string
    userId?: string
    userName?: string
    mode?: 'dev' | 'thin-client' | 'standalone'
    projectRoot?: string
    recentProjects?: string[]
  }) => Promise<void>
  pingBackend: (url?: string) => Promise<{ ok: boolean; latencyMs: number; error?: string }>
  pickProjectRoot: () => Promise<{ projectRoot: string; recentProjects: string[] } | null>
  listScreenSources: () => Promise<
    Array<{
      id: string
      name: string
      display_id: string
      thumbnail: string
    }>
    | { error: string }
  >
  onBackendStatus: (cb: (status: { up: boolean; latencyMs?: number }) => void) => () => void
}

declare global {
  interface Window {
    jarvisx: JarvisXBridge
  }
}

export {}
