/**
 * Markør-laget — viser HVOR Jarvis peger, mens han styrer musen.
 *
 * Bygget 21/9-2026 efter Bjørns ønske: «bare man kan se du flytter mussen».
 * Claude Desktop gør noget lignende, men i to adskilte modes — en vindues-halo
 * bag den app agenten arbejder i (app-scoped), og en virtuel markør under
 * fuld-skærms-kontrol (`request_full_control`). Deres halo er et native modul
 * der kun findes på macOS (`halo_* is macOS-only`), så den kan ikke lånes.
 *
 * Vi har ikke brug for en virtuel markør: Jarvis flytter Bjørns RIGTIGE mus
 * gennem nut.js, så cursoren er der allerede. Det der mangler er at kunne se
 * at det er HAM der styrer og ikke Bjørn. Derfor tegner vi ikke en markør —
 * vi tegner et mærke omkring den markør der ER, i det øjeblik han flytter den.
 *
 * Vinduet følger opskriften fra `figur.ts`: gennemsigtigt, rammeløst, altid
 * øverst, på alle arbejdsområder, ikke i opgavelinjen. To forskelle:
 *
 * - Det dækker HELE det virtuelle skrivebord (unionen af alle tilsluttede
 *   skærme), ikke et lille hjørne. Målt 21/9: Bjørns skrivebord er 5760x1080
 *   fordelt på tre skærme, og musen flyttes i virtuelle koordinater — et
 *   vindue der kun dækkede den primære skærm ville tegne forkert på de to
 *   andre.
 * - `setIgnoreMouseEvents(true)` er ikke et kompromis her, som det er for
 *   figuren, men selve pointen: vinduet må ALDRIG tage et klik. Bjørn skal
 *   kunne arbejde videre gennem det mens Jarvis peger. På Linux kan Electron
 *   ikke både slippe tryk igennem og se musen (`forward` er macOS/Windows),
 *   men det er ligegyldigt — positionen kommer fra broen, ikke fra vinduet.
 */
import { BrowserWindow, ipcMain, screen } from 'electron'
import { unionAf } from './markoerOmraade'

let markoer: BrowserWindow | null = null

/** Hele det virtuelle skrivebord — unionen af alle tilsluttede skærme.
 *  Selve beregningen bor i markoerOmraade.ts, så den kan testes uden skærm. */
export function samletOmraade(): { x: number; y: number; width: number; height: number } {
  return unionAf(screen.getAllDisplays().map((d) => d.bounds))
}

export function opretMarkoer(preload: string, indlaes: (w: BrowserWindow, hash: string) => void): void {
  if (markoer) return
  const omraade = samletOmraade()
  markoer = new BrowserWindow({
    ...omraade,
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    // Uden dette stjæler vinduet fokus fra det Bjørn arbejder i, hver gang
    // Jarvis peger — og så ville laget være værre end ingen markør.
    focusable: false,
    show: false,
    title: 'Jarvis-markoer',
    // Et vindue større end én skærm er netop meningen her.
    enableLargerThanScreen: true,
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  })
  markoer.setAlwaysOnTop(true, 'floating')
  markoer.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  // Klik og scroll går IGENNEM til Bjørns egne vinduer under laget.
  markoer.setIgnoreMouseEvents(true)
  // En skærm til/fra eller en ny opløsning må ikke efterlade laget over det
  // gamle område — så ville ringen tegne ved siden af markøren.
  screen.on('display-added', opdaterMarkoerOmraade)
  screen.on('display-removed', opdaterMarkoerOmraade)
  screen.on('display-metrics-changed', opdaterMarkoerOmraade)
  indlaes(markoer, 'markoer')
  markoer.once('ready-to-show', () => markoer?.showInactive())
  markoer.on('closed', () => { markoer = null })
}

/** Flyt laget når skærmopsætningen ændrer sig (skærm til/fra, opløsning). */
export function opdaterMarkoerOmraade(): void {
  if (!markoer || markoer.isDestroyed()) return
  markoer.setBounds(samletOmraade())
}

export function lukMarkoer(): void {
  screen.removeListener('display-added', opdaterMarkoerOmraade)
  screen.removeListener('display-removed', opdaterMarkoerOmraade)
  screen.removeListener('display-metrics-changed', opdaterMarkoerOmraade)
  markoer?.destroy()
  markoer = null
}

export function markoerFindes(): boolean {
  return markoer !== null && !markoer.isDestroyed()
}

/**
 * Peg på (x, y) i SKÆRM-koordinater. Vi trækker vinduets egen position fra,
 * så renderer'en kun kender vinduets lokale rum og ikke skal vide hvor laget
 * ligger henne. Kaldes fra broen ved hvert musekald (se bridge.ts).
 */
export function pegMarkoer(x: number, y: number): void {
  if (!markoer || markoer.isDestroyed()) return
  const b = markoer.getBounds()
  markoer.webContents.send('markoer:peg', {
    x: Math.round(x - b.x),
    y: Math.round(y - b.y),
  })
}

/** Kaldt fra main ved opstart: hold laget over det aktuelle skrivebord. */
export function registrerMarkoerIpc(): void {
  ipcMain.handle('markoer:findes', () => markoerFindes())
}
