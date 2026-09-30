// §22.5 auto-update via electron-updater + GitHub releases.
//
// RETTET 1/10-2026: kommentaren her sagde «ikke gjort endnu — derfor graceful
// no-op nu» om alle tre aktiverings-krav. Det var sandt da den blev skrevet,
// men ikke længere — den modsagde koden og sendte en fejljagt i gang 30/9.
// De tre krav er opfyldt: (1) `electron-updater ^6.8.9` i package.json,
// (2) publish-config (github/Nickless-cmd/jarvis-v2), (3) releases med
// latest.yml/latest-linux.yml/latest-mac.yml.
//
// Den RELLE no-op-betingelse i dag er derfor ikke længere de tre krav, men:
//   · `cfg.enabled` er ikke sat (initAutoUpdate returnerer false straks), eller
//   · `electron-updater` kan ikke importeres i den kørende build.
// Bemærk også: opdagelsen af en ny release er forsinket — electron-updater
// poller GitHub, og kilden kan ikke skubbe ned i klienten. En knap der ikke
// reagerer STRAKS er derfor ikke det samme som en knap der er i stykker.

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
