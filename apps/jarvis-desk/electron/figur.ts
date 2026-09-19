/**
 * Jarvis-figuren — et eget, rammeløst vindue på skrivebordet.
 *
 * Bygget efter Codex' kæledyr (Jarvis' kortlægning codex-pet.md, efterprøvet
 * 19/9-2026 med xwininfo på det kørende vindue): gennemsigtigt, uden ramme,
 * altid øverst, på alle arbejdsområder, ikke i opgavelinjen — og det lever
 * videre når hovedvinduet lukkes, fordi × kun SKJULER hovedvinduet (tray).
 *
 * Det overlever IKKE at processen afsluttes, og det gør Codex' heller ikke:
 * målt delte figuren og hovedvinduet PID 449396, og i X11 dør et vindue med
 * sin klient. «Afslut» i tray-menuen lukker begge.
 *
 * Standardplacering er Codex' `pet-overlay`: nederst til højre, 24 px fra
 * kanten. Flyttes den, huskes pladsen (figur.json i userData).
 *
 * Vinduet er så lille som indholdet: på Linux kan Electron ikke lade tryk gå
 * igennem gennemsigtige områder og samtidig se musen (`forward` findes kun på
 * macOS/Windows), så et stort gennemsigtigt vindue ville stjæle klik fra
 * skrivebordet under det. Renderer'en melder sin størrelse, og vinduet vokser
 * OPAD fra figurens fødder, så figuren står stille når taleboblen kommer.
 */
import { app, BrowserWindow, ipcMain, screen } from 'electron'
import fs from 'node:fs'
import path from 'node:path'

const BREDDE = 300
const MIN_HOEJDE = 150
const MARGEN = 24

interface FigurTilstand { vist: boolean; x?: number; y?: number }

let figur: BrowserWindow | null = null
let tilstand: FigurTilstand = { vist: true }
let hoejde = MIN_HOEJDE

const fil = () => path.join(app.getPath('userData'), 'figur.json')

function laes(): FigurTilstand {
  try {
    const d = JSON.parse(fs.readFileSync(fil(), 'utf8')) as Partial<FigurTilstand>
    return { vist: d.vist !== false, x: d.x, y: d.y }
  } catch {
    return { vist: true }
  }
}

function gem(): void {
  try {
    fs.mkdirSync(path.dirname(fil()), { recursive: true })
    fs.writeFileSync(fil(), JSON.stringify(tilstand))
  } catch { /* ikke kritisk — pladsen er en bekvemmelighed */ }
}

/** Fødderne: nederste midtpunkt. Figuren står der, uanset vinduets højde. */
function fodpunkt(): { x: number; y: number } {
  const wa = screen.getPrimaryDisplay().workArea
  const standard = { x: wa.x + wa.width - MARGEN - BREDDE / 2, y: wa.y + wa.height - MARGEN }
  if (tilstand.x === undefined || tilstand.y === undefined) return standard
  // Er skærmen den stod på koblet fra, falder den tilbage — ellers stod
  // figuren uden for alt synligt.
  const synlig = screen.getAllDisplays().some((d) => {
    const a = d.workArea
    return tilstand.x! >= a.x && tilstand.x! <= a.x + a.width && tilstand.y! >= a.y && tilstand.y! <= a.y + a.height + 4
  })
  return synlig ? { x: tilstand.x, y: tilstand.y } : standard
}

function placer(): void {
  if (!figur) return
  const f = fodpunkt()
  figur.setBounds({ x: Math.round(f.x - BREDDE / 2), y: Math.round(f.y - hoejde), width: BREDDE, height: hoejde })
}

export function opretFigur(preload: string, indlaes: (w: BrowserWindow, hash: string) => void): void {
  if (figur) return
  tilstand = laes()
  if (!tilstand.vist) return
  figur = new BrowserWindow({
    width: BREDDE,
    height: hoejde,
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,
    resizable: false,
    movable: true,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    show: false,
    title: 'Jarvis',
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  })
  figur.setAlwaysOnTop(true, 'floating')
  figur.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  placer()
  indlaes(figur, 'figur')
  figur.once('ready-to-show', () => figur?.showInactive())
  figur.on('closed', () => { figur = null })
}

export function lukFigur(): void {
  figur?.destroy()
  figur = null
}

/** Den gemte indstilling — til tray-menuens flueben, før vinduet findes. */
export function laesFigurVist(): boolean {
  return laes().vist
}

export function figurVist(): boolean {
  return figur !== null
}

export function saetFigurVist(vist: boolean, preload: string, indlaes: (w: BrowserWindow, hash: string) => void): void {
  tilstand = { ...laes(), vist }
  gem()
  if (vist) opretFigur(preload, indlaes)
  else lukFigur()
}

/** IPC for figur-vinduet. `aabnSamtale` viser hovedvinduet på samtalen. */
export function registrerFigurIpc(opts: {
  preload: string
  indlaes: (w: BrowserWindow, hash: string) => void
  aabnSamtale: (sessionId: string | null) => void
  /** Stemme-ikonet: hovedvinduet frem og samtale-mode i gang. */
  stemme: () => void
  onVistAendret?: (vist: boolean) => void
}): void {
  // Træk: renderer'en sender skærm-koordinater for musen; vi flytter
  // fodpunktet med samme forskydning. Codex gør det samme selv
  // (`nativeWindowDragStart`) i stedet for et -webkit-app-region-felt, som
  // ellers ville æde klikket der får figuren til at hoppe.
  let start: { mx: number; my: number; fx: number; fy: number } | null = null
  ipcMain.handle('figur:traekStart', (_e, mx: number, my: number) => {
    const f = fodpunkt()
    start = { mx, my, fx: f.x, fy: f.y }
  })
  ipcMain.handle('figur:traek', (_e, mx: number, my: number) => {
    if (!start) return
    tilstand = { ...tilstand, x: start.fx + (mx - start.mx), y: start.fy + (my - start.my) }
    placer()
  })
  ipcMain.handle('figur:traekSlut', () => {
    start = null
    gem()
  })
  ipcMain.handle('figur:hoejde', (_e, h: number) => {
    const ny = Math.max(MIN_HOEJDE, Math.min(560, Math.round(h)))
    if (ny === hoejde) return
    hoejde = ny
    placer()
  })
  ipcMain.handle('figur:aabnSamtale', (_e, sessionId: string | null) => opts.aabnSamtale(sessionId))
  ipcMain.handle('figur:stemme', () => opts.stemme())
  ipcMain.handle('figur:vist', () => figurVist())
  ipcMain.handle('figur:saetVist', (_e, vist: boolean) => {
    saetFigurVist(vist, opts.preload, opts.indlaes)
    opts.onVistAendret?.(vist)
    return figurVist()
  })
}
