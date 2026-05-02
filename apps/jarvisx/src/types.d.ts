/**
 * Bridge surface exposed by electron/preload.ts via contextBridge.
 * Renderer reads/writes runtime config (server URL, identity) and listens
 * to backend health pings. We deliberately keep this small — Phase 0
 * doesn't need much from main.
 */
export type UpdaterStatus =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'available'; info: { version: string; releaseDate?: string; releaseName?: string } }
  | { kind: 'not-available'; current: string }
  | { kind: 'downloading'; percent: number }
  | { kind: 'downloaded'; info: { version: string; releaseDate?: string; releaseName?: string } }
  | { kind: 'error'; error: string }

export interface GitCommit {
  sha: string
  short: string
  subject: string
  author: string
  date: string
}

export type GitUpdateStatus =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'up-to-date'; head: string; checkedAt: string }
  | { kind: 'behind'; commits: GitCommit[]; head: string; checkedAt: string }
  | { kind: 'updating'; phase: string; output: string }
  | { kind: 'updated'; head: string }
  | { kind: 'error'; error: string }

export interface JarvisXBridge {
  getConfig: () => Promise<{
    apiBaseUrl: string
    userId: string
    userName: string
    mode: 'dev' | 'thin-client' | 'standalone'
    projectRoot: string
    recentProjects: string[]
    authToken?: string
    authTokenUserId?: string
    authTokenRole?: string
    authTokenExpiresAt?: string
  }>
  setConfig: (cfg: {
    apiBaseUrl?: string
    userId?: string
    userName?: string
    mode?: 'dev' | 'thin-client' | 'standalone'
    projectRoot?: string
    recentProjects?: string[]
    authToken?: string
    authTokenUserId?: string
    authTokenRole?: string
    authTokenExpiresAt?: string
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
  // Auto-updater (electron-updater — release-based, dormant for now)
  updaterCheck: () => Promise<{ ok: boolean; version?: string; error?: string }>
  updaterDownload: () => Promise<{ ok: boolean; error?: string }>
  updaterInstall: () => Promise<{ ok: boolean }>
  updaterStatus: () => Promise<UpdaterStatus>
  onUpdaterStatus: (cb: (status: UpdaterStatus) => void) => () => void
  // Git-based updater (run-from-source)
  gitUpdateCheck: () => Promise<GitUpdateStatus>
  gitUpdateStatus: () => Promise<GitUpdateStatus>
  gitUpdatePullAndRebuild: () => Promise<{ ok: boolean; error?: string }>
  gitUpdateRestartNow: () => Promise<{ ok: boolean }>
  onGitUpdateStatus: (cb: (status: GitUpdateStatus) => void) => () => void
}

declare global {
  interface Window {
    jarvisx: JarvisXBridge
  }
}

export {}
