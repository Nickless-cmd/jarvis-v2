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
  /** Historik-tilstand, så pilene kan være grå når de ikke fører nogen steder. */
  kanTilbage: boolean
  kanFrem: boolean
  /** Siden henter stadig — genindlæs-knappen bliver til en stop-knap. */
  henter: boolean
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
  void view.webContents.loadURL(tydUrl(url))
  anvendBounds()
  return { id, url, titel: '', aktiv: true, kanTilbage: false, kanFrem: false, henter: true }
}

/**
 * Gør det man taster i adresselinjen til noget der kan hentes.
 *
 * En adresselinje får sjældent en hel URL. «github.com» skal blive til
 * https, og «hvad er en webcontentsview» skal blive til en søgning — ellers
 * står man med en fejlside og tror browseren er i stykker.
 *
 * Søgningen går til DuckDuckGo, fordi den ikke bygger en profil på det der
 * tastes. Det ER en udgående forespørgsel: taster man noget der ikke ligner
 * et værtsnavn, forlader teksten maskinen — nøjagtig som i enhver anden
 * browsers adresselinje.
 */
export function tydUrl(raa: string): string {
  const t = String(raa).trim()
  if (!t) return 'about:blank'
  // Skema kraever «://». Uden den regel blev «localhost:5174» laest som
  // skemaet «localhost» med stien «5174», og udvikling herinde var umulig.
  // De faa skemaer UDEN skraastreger staar navngivet; alt andet, herunder
  // «javascript:», ender som en soegning frem for at blive kaldt.
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(t)) return t
  if (/^(about|mailto|data|blob|tel|file):/i.test(t)) return t
  const etOrd = !/\s/.test(t)
  const lignerVaert = etOrd && (/^[^/]+\.[a-z]{2,}(?::\d+)?(?:[/?#]|$)/i.test(t) || /^localhost(?::\d+)?(?:[/?#]|$)/i.test(t))
  if (lignerVaert) return `https://${t}`
  return `https://duckduckgo.com/?q=${encodeURIComponent(t)}`
}

export function naviger(url: string, id = aktivId): void {
  const f = faner.find((x) => x.id === id)
  if (!f) throw new Error(`ukendt fane ${id}`)
  void f.view.webContents.loadURL(tydUrl(url))
}

/** Electron 33 flyttede historikken til `navigationHistory`; de gamle
 *  `canGoBack()`/`goBack()` på webContents er på vej ud. Vi går efter den nye
 *  og falder tilbage, så panelet ikke brækker på nogen af dem. */
function historik(f: Fane) {
  const wc = f.view.webContents as unknown as {
    navigationHistory?: { canGoBack(): boolean; canGoForward(): boolean; goBack(): void; goForward(): void }
    canGoBack?: () => boolean
    canGoForward?: () => boolean
    goBack?: () => void
    goForward?: () => void
  }
  return {
    kanTilbage: wc.navigationHistory?.canGoBack() ?? wc.canGoBack?.() ?? false,
    kanFrem: wc.navigationHistory?.canGoForward() ?? wc.canGoForward?.() ?? false,
    tilbage: () => { if (wc.navigationHistory) wc.navigationHistory.goBack(); else wc.goBack?.() },
    frem: () => { if (wc.navigationHistory) wc.navigationHistory.goForward(); else wc.goForward?.() },
  }
}

export function tilbage(id = aktivId): void {
  const f = faner.find((x) => x.id === id)
  if (!f) return
  const h = historik(f)
  if (h.kanTilbage) h.tilbage()
}

export function frem(id = aktivId): void {
  const f = faner.find((x) => x.id === id)
  if (!f) return
  const h = historik(f)
  if (h.kanFrem) h.frem()
}

/** Genindlæs — eller afbryd, hvis siden stadig henter. Samme knap, som i en
 *  rigtig browser: der er ingen grund til to. */
export function genindlaes(id = aktivId): void {
  const f = faner.find((x) => x.id === id)
  if (!f) return
  if (f.view.webContents.isLoading()) f.view.webContents.stop()
  else f.view.webContents.reload()
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
  return faner.map((f) => {
    const h = historik(f)
    return {
      id: f.id,
      url: f.view.webContents.getURL(),
      titel: f.view.webContents.getTitle(),
      aktiv: f.id === aktivId,
      kanTilbage: h.kanTilbage,
      kanFrem: h.kanFrem,
      henter: f.view.webContents.isLoading(),
    }
  })
}

export function status(): { aktiv: number; antal: number; synlig: boolean } {
  return { aktiv: aktivId, antal: faner.length, synlig }
}
