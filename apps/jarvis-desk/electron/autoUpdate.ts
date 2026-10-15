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

import { chmodSync, copyFileSync, existsSync, renameSync, unlinkSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'

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
  checkForUpdates: () => unknown | Promise<unknown>
  downloadUpdate: () => unknown | Promise<unknown>
  quitAndInstall: () => unknown
}
type Send = (channel: string, payload: unknown) => void

/** electron-updater kraever APPIMAGE for at kunne erstatte den koerende fil.
 * Nogle Linux-launchere taber variablen, selv om processen faktisk er startet
 * fra AppImage-mountet. Genfind den faste installersti uden at overskrive en
 * gyldig launcher-vaerdi. */
export function findLinuxAppImage(
  env: Partial<NodeJS.ProcessEnv>, exists: (path: string) => boolean,
): string | undefined {
  const fraLauncher = env.APPIMAGE
  if (fraLauncher && isAbsolute(fraLauncher) && exists(fraLauncher)) return fraLauncher
  const home = env.HOME
  if (!home || !isAbsolute(home)) return undefined
  const installeret = join(home, 'Applications', 'J.A.R.V.I.S.AppImage')
  return exists(installeret) ? installeret : undefined
}

/** De filhandlinger `sikkerSwap` bruger. Injicerbare, saa vejen kan testes uden
 *  at roere disken. */
export interface SwapFs {
  existsSync: (p: string) => boolean
  copyFileSync: (fra: string, til: string) => void
  chmodSync: (p: string, mode: number) => void
  renameSync: (fra: string, til: string) => void
  unlinkSync: (p: string) => void
}

const nodeFs: SwapFs = { existsSync, copyFileSync, chmodSync, renameSync, unlinkSync }

export type SwapResultat = { ok: true; sti: string } | { ok: false; fejl: string }

/** Læg den hentede AppImage på plads UDEN at der opstår et øjeblik hvor målet
 *  ikke findes.
 *
 *  Hvorfor ikke electron-updater's egen install (målt 15/10-2026):
 *  `AppImageUpdater.doInstall` gør `unlinkSync(appImageFile)` UBETINGET, og
 *  tjekker først derefter om der overhovedet er en ny fil at flytte
 *  (`installerPath == null` → fejl og retur). Fejler den bagefter, står maskinen
 *  uden AppImage: appen kan ikke starte, og `.desktop` peger på et hul. Det skete
 *  for Bjørn — og Mikkel ville ikke kunne genskabe filen selv.
 *
 *  Her kopieres den nye fil til en temp-fil i SAMME mappe, gøres executable, og
 *  `rename` flytter den atomisk over målet. Samme filsystem, så det er ét
 *  atomisk trin: målet findes i hvert eneste øjeblik, og fejler noget undervejs,
 *  er den gamle AppImage urørt og appen kan stadig starte.
 */
export function sikkerSwap(
  hentet: string | null | undefined, maal: string, fs: SwapFs = nodeFs,
): SwapResultat {
  if (!hentet || !fs.existsSync(hentet)) {
    return { ok: false, fejl: `den hentede fil findes ikke: ${hentet ?? '(ingen sti)'}` }
  }
  const midlertidig = `${maal}.ny`
  try {
    fs.copyFileSync(hentet, midlertidig)
    fs.chmodSync(midlertidig, 0o755)
    fs.renameSync(midlertidig, maal)
    return { ok: true, sti: maal }
  } catch (e) {
    // Oprydning må ikke kaste — fejlen vi allerede har er den vigtige.
    try { fs.unlinkSync(midlertidig) } catch { /* noop */ }
    return { ok: false, fejl: String(e) }
  }
}

/** Kobl electron-updater's events til IPC mod renderer, og returnér handlers
 *  til bruger-styret download/install. autoDownload slås FRA — vi spørger først
 *  (in-app UpdateCard), og downloader/genstarter kun ved bruger-ja.
 *
 *  `genstart` kaldes med stien til den AppImage der nu ligger på plads. Den skal
 *  starte den NYE fil som en selvstændig proces: `app.relaunch()` duer ikke her,
 *  fordi den genstarter processen fra det GAMLE AppImage-mount og dermed ville
 *  starte den version vi netop erstattede. */
export function wireUpdater(
  up: FullUpdater,
  send: Send,
  genstart?: (appImageSti: string) => void,
  fs: SwapFs = nodeFs,
) {
  up.autoDownload = false
  // Stien til den hentede fil. `update-downloaded` bærer den, og vi gemmer den
  // her, så «installér nu» kan bruge den uden at hente en gang til.
  let hentetFil: string | null = null
  up.on('update-available', (info) => send('update:available', info))
  up.on('download-progress', (p) => send('update:progress', p))
  up.on('update-downloaded', (info) => {
    const sti = (info as { downloadedFile?: unknown } | null)?.downloadedFile
    if (typeof sti === 'string' && sti) hentetFil = sti
    send('update:ready', info)
  })
  up.on('error', (e) => send('update:error', String(e)))

  /** Læg den hentede AppImage sikkert på plads og genstart.
   *
   *  En fejlet opdatering må ALDRIG kunne ødelægge en kørende app: fejler noget
   *  her, kastes en fejl (renderer viser den) og installationen er urørt. */
  const installerSikkert = async (): Promise<void> => {
    const maal = process.env.APPIMAGE
    if (!maal) throw new Error('APPIMAGE-stien er ikke sat — kan ikke installere sikkert.')
    let fil = hentetFil
    if (!fil) {
      const filer = await up.downloadUpdate()
      fil = Array.isArray(filer) ? filer.find((f): f is string => typeof f === 'string') ?? null : null
    }
    const s = sikkerSwap(fil, maal, fs)
    if (!s.ok) throw new Error(`opdateringen blev ikke lagt på plads: ${s.fejl}`)
    genstart?.(s.sti)
  }

  return {
    check: () => { try { up.checkForUpdates() } catch { /* noop */ } },
    download: () => Promise.resolve(up.downloadUpdate()),
    installNow: () => installerSikkert(),
    downloadAndInstall: async () => {
      const available = await up.checkForUpdates()
      if (!available) throw new Error('Ingen ny app-version er klar til installation.')
      if (!hentetFil) await up.downloadUpdate()
      await installerSikkert()
    },
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
