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
 * skrivebordet under det. Renderer'en melder størrelse og figurens midtpunkt;
 * vinduet flyttes omkring det punkt, når taleboblen vokser eller skifter side.
 */
import { app, BrowserWindow, ipcMain, Menu, screen } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import { bobleSide, vindueTop, type BobleSide } from './figurPlacering'

const BREDDE = 300
const MIN_HOEJDE = 150
const MARGEN = 24

interface FigurTilstand {
  vist: boolean; x?: number; y?: number
  /** Nye positioner gemmer figurens midte; ældre positioner gemte vinduets bund. */
  anker?: 'figur'
  hoejde?: number
  offsetY?: number
}

let figur: BrowserWindow | null = null
let tilstand: FigurTilstand = { vist: true }
let hoejde = MIN_HOEJDE
let indholdHoejde = MIN_HOEJDE
let figurMidte = 72
let side: BobleSide = 'over'

const fil = () => path.join(app.getPath('userData'), 'figur.json')

function laes(): FigurTilstand {
  try {
    const d = JSON.parse(fs.readFileSync(fil(), 'utf8')) as Partial<FigurTilstand>
    return { vist: d.vist !== false, x: d.x, y: d.y, anker: d.anker, hoejde: d.hoejde, offsetY: d.offsetY }
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

/** Gemt anker: figurens midte (nyere) eller vinduets bund (ældre data). */
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
  const y = tilstand.anker === 'figur'
    ? (tilstand.offsetY == null ? vindueTop(f.y, hoejde, indholdHoejde, figurMidte, side) : Math.round(f.y - tilstand.offsetY))
    : Math.round(f.y - hoejde)
  figur.setBounds({ x: Math.round(f.x - BREDDE / 2), y, width: BREDDE, height: hoejde })
}

export function opretFigur(preload: string, indlaes: (w: BrowserWindow, hash: string) => void): void {
  if (figur) return
  tilstand = laes()
  if (!tilstand.vist) return
  hoejde = tilstand.hoejde ?? MIN_HOEJDE
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
  ipcMain.handle('figur:hoejde', (_e, h: number, contentH?: number, center?: number, nextSide?: BobleSide, currentCenter?: number) => {
    const ny = Math.max(MIN_HOEJDE, Math.min(560, Math.round(h)))
    if (typeof contentH !== 'number' || typeof center !== 'number' || !nextSide || typeof currentCenter !== 'number' || !figur) {
      if (ny !== hoejde) { hoejde = ny; placer() }
      return
    }
    if (tilstand.anker !== 'figur') {
      const bounds = figur.getBounds()
      tilstand = { ...tilstand, x: bounds.x + BREDDE / 2, y: bounds.y + currentCenter, anker: 'figur' }
    }
    hoejde = ny
    indholdHoejde = Math.max(1, Math.round(contentH))
    figurMidte = center
    side = nextSide
    const anchorY = tilstand.y!
    tilstand = { ...tilstand, hoejde: ny, offsetY: anchorY - vindueTop(anchorY, ny, indholdHoejde, figurMidte, side) }
    placer()
    gem()
  })
  ipcMain.handle('figur:snapshot', () => {
    const f = fodpunkt()
    const display = screen.getDisplayNearestPoint({ x: Math.round(f.x), y: Math.round(f.y) })
    return {
      cursor: screen.getCursorScreenPoint(),
      bounds: figur?.getBounds() ?? { x: 0, y: 0 },
      side: bobleSide(f.y, display.workArea),
    }
  })
  ipcMain.handle('figur:menu', (event) => {
    const target = BrowserWindow.fromWebContents(event.sender) ?? figur
    if (!target) return
    Menu.buildFromTemplate([{
      label: 'Skjul figur',
      click: () => {
        saetFigurVist(false, opts.preload, opts.indlaes)
        opts.onVistAendret?.(false)
      },
    }]).popup({ window: target })
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
