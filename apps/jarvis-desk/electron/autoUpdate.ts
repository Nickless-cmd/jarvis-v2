// §22.5 auto-update via electron-updater + GitHub releases.
//
// AKTIVERING kræver tre ting (ikke gjort endnu — derfor graceful no-op nu):
//   1) npm i electron-updater
//   2) electron-builder publish-config i package.json: "publish": [{ "provider": "github",
//      "owner": "Nickless-cmd", "repo": "jarvis-v2" }]
//   3) uploadede GitHub-releases (.deb/.exe/.dmg med latest.yml)
// Indtil da er initAutoUpdate en no-op (dynamisk import fejler → fanges).

export interface AutoUpdateConfig {
  enabled?: boolean
  channel?: string
  checkIntervalHours?: number
  forceSecurityUpdates?: boolean
}

interface Updater { checkForUpdatesAndNotify: () => unknown }

interface FullUpdater {
  autoDownload: boolean
  on: (ev: string, cb: (info: unknown) => void) => void
  checkForUpdates: () => unknown
  downloadUpdate: () => unknown
  quitAndInstall: () => unknown
}
type Send = (channel: string, payload: unknown) => void

/** Kobl electron-updater's events til IPC mod renderer, og returnér handlers
 *  til bruger-styret download/install. autoDownload slås FRA — vi spørger først
 *  (in-app UpdateCard), og downloader/genstarter kun ved bruger-ja. */
export function wireUpdater(up: FullUpdater, send: Send) {
  up.autoDownload = false
  up.on('update-available', (info) => send('update:available', info))
  up.on('download-progress', (p) => send('update:progress', p))
  up.on('update-downloaded', (info) => send('update:ready', info))
  up.on('error', (e) => send('update:error', String(e)))
  return {
    check: () => { try { up.checkForUpdates() } catch { /* noop */ } },
    download: () => { try { up.downloadUpdate() } catch { /* noop */ } },
    installNow: () => { try { up.quitAndInstall() } catch { /* noop */ } },
  }
}

export async function initAutoUpdate(cfg?: AutoUpdateConfig): Promise<boolean> {
  if (!cfg?.enabled) return false
  const moduleName = 'electron-updater'  // ikke-literal → tsc resolver ikke statisk
  let up: Updater | undefined
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mod = (await import(/* @vite-ignore */ moduleName)) as any
    up = mod?.autoUpdater as Updater | undefined
  } catch {
    return false  // dep ikke installeret → no-op
  }
  if (!up) return false
  try {
    void up.checkForUpdatesAndNotify()
    const hours = cfg.checkIntervalHours && cfg.checkIntervalHours > 0 ? cfg.checkIntervalHours : 24
    setInterval(() => {
      try { void up!.checkForUpdatesAndNotify() } catch { /* noop */ }
    }, hours * 3_600_000)
    return true
  } catch {
    return false
  }
}
