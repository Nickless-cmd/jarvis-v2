/**
 * Jarvis' egen browser — en rigtig webvisning INDE i desk.
 *
 * ## Hvorfor den findes (Bjørn 21/9-2026)
 *
 * «browsers i desk appen som du også har i cc desktop… med eget panel som
 * baggrundsjobs… altså Jarvis' browser, lige som din.»
 *
 * Der fandtes to browser-stakke i forvejen, og ingen af dem kunne ses:
 * serveren kører Playwright på CT105, og desk havde `operator_browser_*` mod
 * en LØS Chrome via puppeteer-core. Sidstnævnte var oven i købet død —
 * `puppeteer-core` stod aldrig i `package.json`, præcis som nut.js.
 *
 * Ingen af dem kan vises i desk: Playwright og puppeteer styrer hver sin
 * fremmede proces. En `WebContentsView` er Electrons egen, den lever i
 * vinduet, og derfor kan Bjørn SE hvad Jarvis gør — og selv tage over med
 * musen midt i det. Det er hele pointen med «lige som din».
 *
 * ## Hvem bestemmer hvor den ligger
 *
 * Rendereren ejer layoutet og melder et rektangel; main sætter visningens
 * bounds efter det. Omvendt ville to lag kende samme mål, og de ville skride
 * fra hinanden ved første ændring af panelbredden.
 */
import { WebContentsView, BrowserWindow, shell } from 'electron'

export interface Faneblad {
  id: number
  url: string
  titel: string
  aktiv: boolean
}

interface Fane {
  id: number
  view: WebContentsView
}

const faner: Fane[] = []
let naesteId = 1
let aktivId = 0
let vaert: BrowserWindow | null = null
let rect = { x: 0, y: 0, width: 0, height: 0 }
let synlig = false

/** Tomt rektangel = skjult. Electron har ingen «hide» på en view, så den
 *  flyttes ud af syne ved at få nul størrelse. */
function anvendBounds(): void {
  const f = faner.find((x) => x.id === aktivId)
  if (!f) return
  f.view.setBounds(synlig ? rect : { x: 0, y: 0, width: 0, height: 0 })
}

function sikrVaert(win: BrowserWindow): void {
  vaert = win
}

export function saetVaert(win: BrowserWindow): void {
  sikrVaert(win)
}

/** Opret en fane. Første kald bliver den aktive. */
export function aabnFane(url: string): Faneblad {
  if (!vaert) throw new Error('browserpanelet har intet vindue endnu')
  const view = new WebContentsView({
    webPreferences: {
      // Jarvis' browser er en BRUGERFLADE, ikke en udvidelse af appen: ingen
      // node-integration, egen isolation. Falder en side fra hinanden, tager
      // den ikke desk med sig.
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  })
  const id = naesteId++
  vaert.contentView.addChildView(view)
  faner.push({ id, view })
  aktivId = id
  // Nye vinduer (target=_blank) bliver faner her frem for løse vinduer —
  // ellers åbner en side sig uden for det Bjørn kan se.
  view.webContents.setWindowOpenHandler(({ url: ny }) => {
    if (/^https?:/i.test(ny)) { void aabnFane(ny) }
    else { void shell.openExternal(ny) }
    return { action: 'deny' }
  })
  void view.webContents.loadURL(url)
  anvendBounds()
  return { id, url, titel: '', aktiv: true }
}

export function naviger(url: string, id = aktivId): void {
  const f = faner.find((x) => x.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  void f.view.webContents.loadURL(url)
}

export async function laes(id = aktivId, maxTegn = 24_000): Promise<string> {
  const f = faner.find((x) => x.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  const tekst = await f.view.webContents.executeJavaScript(
    'document.body ? document.body.innerText : ""', true,
  )
  return String(tekst ?? '').slice(0, maxTegn)
}

export async function billede(id = aktivId): Promise<string> {
  const f = faner.find((x) => x.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  const img = await f.view.webContents.capturePage()
  return img.toPNG().toString('base64')
}

/** Klik på rigtige skærmkoordinater inde i visningen. `sendInputEvent` er
 *  Electrons egen vej; den rammer siden som en ægte mus, så React-handlere
 *  og hover-tilstande opfører sig normalt. */
export function klik(x: number, y: number, id = aktivId): void {
  const f = faner.find((v) => v.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  const wc = f.view.webContents
  wc.sendInputEvent({ type: 'mouseDown', x, y, button: 'left', clickCount: 1 })
  wc.sendInputEvent({ type: 'mouseUp', x, y, button: 'left', clickCount: 1 })
}

export function skriv(tekst: string, id = aktivId): void {
  const f = faner.find((v) => v.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  for (const tegn of String(tekst)) {
    f.view.webContents.sendInputEvent({ type: 'char', keyCode: tegn })
  }
}

export function luk(id: number): void {
  const i = faner.findIndex((x) => x.id === id)
  if (i < 0) return
  const [f] = faner.splice(i, 1)
  vaert?.contentView.removeChildView(f.view)
  f.view.webContents.close()
  if (aktivId === id) {
    aktivId = faner.length ? faner[faner.length - 1].id : 0
    anvendBounds()
  }
}

export function vaelg(id: number): void {
  if (!faner.some((x) => x.id === id)) return
  // Kun den aktive har bounds; resten parkeres i nul, så de ikke tegner oven
  // i hinanden. Electron har ingen z-orden vi kan stole på her.
  aktivId = id
  for (const f of faner) {
    f.view.setBounds(f.id === id && synlig ? rect : { x: 0, y: 0, width: 0, height: 0 })
  }
}

export function saetRect(r: { x: number; y: number; width: number; height: number }): void {
  rect = { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) }
  anvendBounds()
}

export function saetSynlig(v: boolean): void {
  synlig = Boolean(v)
  anvendBounds()
}

export function fanebladeliste(): Faneblad[] {
  return faner.map((f) => ({
    id: f.id,
    url: f.view.webContents.getURL(),
    titel: f.view.webContents.getTitle(),
    aktiv: f.id === aktivId,
  }))
}

export function status(): { aktiv: number; antal: number; synlig: boolean } {
  return { aktiv: aktivId, antal: faner.length, synlig }
}
