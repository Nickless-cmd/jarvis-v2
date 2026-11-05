import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/tokenRenewal'
import {
  openBrowserStream, tilSideKoord, museKnap,
  type BrowserStream, type StreamInput,
} from '../../lib/browserStream'
import { Globe, X, RotateCw, ArrowLeft, ArrowRight, Plus, Maximize2, Minimize2 } from 'lucide-react'
import { ListeTilstand } from '../feedback/ListeTilstand'

interface Fane {
  id: number
  url: string
  titel: string
  aktiv: boolean
  kanTilbage: boolean
  kanFrem: boolean
  henter: boolean
}

interface Bro {
  saetRect: (r: { x: number; y: number; width: number; height: number }) => Promise<boolean>
  saetSynlig: (v: boolean) => Promise<boolean>
  faner: () => Promise<Fane[]>
  vaelg: (id: number) => Promise<boolean>
  luk: (id: number) => Promise<boolean>
  aabn: (url: string) => Promise<Fane>
  naviger: (url: string) => Promise<boolean>
  tilbage: () => Promise<boolean>
  frem: () => Promise<boolean>
  genindlaes: () => Promise<boolean>
}

const elektronBro = (): Bro | undefined =>
  (window as unknown as { jarvisDesk?: { browser?: Bro } }).jarvisDesk?.browser

const TOM_FANE: Fane = { id: -1, url: '', titel: '', aktiv: true, kanTilbage: false, kanFrem: false, henter: true }

/** Kort navn til fanen. En fane uden titel skal vise sit værtsnavn, ikke en
 *  hel URL — «github.com» frem for «https://github.com/x/y?z=1#a». */
function faneNavn(f: Fane): string {
  if (f.titel) return f.titel
  try { return new URL(f.url).hostname || 'ny fane' } catch { return f.url || 'ny fane' }
}

/**
 * Jarvis' browser — panelet omkring hans egen webvisning.
 *
 * ## Hvad komponenten ER og ikke er (Bjørn 21/9-2026)
 *
 * Den tegner IKKE siden. Siden er en `WebContentsView` som Electron
 * komponerer oven på vinduet; her står kun browserens kant — faner, pile,
 * adresselinje — og en PLADSHOLDER der fortæller main hvor visningen skal
 * ligge.
 *
 * Det er ikke en omvej. En webvisning kan ikke ligge inde i React-træet —
 * den er et søskende-lag i vinduet. Derfor må nogen måle hullet, og det skal
 * være den der ejer layoutet. Gjorde main sit eget regnestykke, ville de to
 * skride fra hinanden i samme øjeblik panelbredden ændrede sig.
 *
 * Bjørn kan klikke direkte i visningen mens Jarvis arbejder i den — det er
 * hele grunden til at det er Electrons egen visning og ikke et skærmbillede
 * af en fremmed Chrome.
 *
 * ## Hvorfor der er en adresselinje
 *
 * Første udgave havde kun en fanerække. Broen KUNNE navigere hele tiden —
 * `naviger()` lå der ubrugt — men der var ingen vej til den fra fladen, så
 * ruden kunne åbne about:blank og derefter ingenting. En browser uden
 * adresselinje er et vindue uden håndtag.
 */
export function JarvisBrowserPanel({ aaben, fuld = false, onFuld, onClose, config }: {
  aaben: boolean
  /** API-adgang til WS-streamen. Bruges KUN når Electron-broen mangler (PWA). */
  config?: ApiConfig | null
  /** Fuld visning — samme ⤢ som ændringer og baggrundsjob. */
  fuld?: boolean
  onFuld?: (fuld: boolean) => void
  onClose?: () => void
}) {
  const [faner, setFaner] = useState<Fane[]>([])
  // Codex' punkt 2 (21/9-2026): en fejl må ikke se ud som en tom kasse. Den
  // her rude var selv én af de fjorten der intet sagde — skrevet samme aften.
  const [fejl, setFejl] = useState('')
  const [henter, setHenter] = useState(true)
  const [adresse, setAdresse] = useState('')
  const holder = useRef<HTMLDivElement | null>(null)
  const adressefelt = useRef<HTMLInputElement | null>(null)

  // ── PWA-fallback: uden Electron-broen tegnes siden fra en WS-frame-stream ──
  // Med broen er alt nedenfor inaktivt (webTilstand er false) og `bro()` er
  // præcis Electron-broen som før.
  // Primitiver, ikke objektet: kaldere bygger `config` på ny ved hver render, og
  // det ville lukke og genåbne streamen hele tiden.
  const apiBase = config?.apiBaseUrl
  const apiToken = config?.authToken ?? null
  const cfg = useMemo<ApiConfig | null>(
    () => (apiBase ? { apiBaseUrl: apiBase, authToken: apiToken } : null),
    [apiBase, apiToken],
  )
  const webTilstand = !elektronBro() && !!cfg
  const canvas = useRef<HTMLCanvasElement | null>(null)
  const strom = useRef<BrowserStream | null>(null)
  const webFaner = useRef<Fane[]>([])
  const sidsteRect = useRef<{ width: number; height: number } | null>(null)
  const rammeStr = useRef({ w: 1, h: 1 })
  const sidsteMus = useRef(0)

  const sendStorrelse = useCallback(() => {
    const r = sidsteRect.current
    if (r && r.width >= 100 && r.height >= 100) {
      strom.current?.send({ t: 'resize', w: Math.round(r.width), h: Math.round(r.height) })
    }
  }, [])

  const bro = useCallback((): Bro | undefined => {
    const e = elektronBro()
    if (e) return e
    if (!cfg) return undefined
    const send = (m: StreamInput) => strom.current?.send(m)
    const ok = async () => true
    const web: Bro = {
      saetRect: async (r) => { sidsteRect.current = r; sendStorrelse(); return true },
      saetSynlig: ok,
      faner: async () => webFaner.current,
      vaelg: async (id) => { send({ t: 'tab', action: 'switch', index: id }); return true },
      luk: async (id) => { send({ t: 'tab', action: 'close', index: id }); return true },
      aabn: async (url) => { send({ t: 'tab', action: 'new', url }); return TOM_FANE },
      naviger: async (url) => { send({ t: 'nav', action: 'goto', url }); return true },
      tilbage: async () => { send({ t: 'nav', action: 'back' }); return true },
      frem: async () => { send({ t: 'nav', action: 'forward' }); return true },
      genindlaes: async () => { send({ t: 'nav', action: 'reload' }); return true },
    }
    return web
  }, [cfg, sendStorrelse])

  useEffect(() => {
    if (!aaben || !webTilstand || !cfg) return
    const s = openBrowserStream(cfg, {
      onFrame: (blob) => {
        void createImageBitmap(blob).then((bmp) => {
          const c = canvas.current
          if (!c) { bmp.close(); return }
          if (c.width !== bmp.width || c.height !== bmp.height) { c.width = bmp.width; c.height = bmp.height }
          rammeStr.current = { w: bmp.width, h: bmp.height }
          c.getContext('2d')?.drawImage(bmp, 0, 0)
          bmp.close()
        }).catch(() => { /* ødelagt frame — næste kommer */ })
      },
      onTabs: (f) => { webFaner.current = f; setFaner(f); setFejl(''); setHenter(false) },
      onStatus: (st) => {
        if (st === 'open') { setFejl(''); sendStorrelse() }
        else if (st === 'error') setFejl('Forbindelsen til Jarvis’ browser fejlede.')
        else setHenter(false)
      },
    })
    strom.current = s
    return () => { s.close(); strom.current = null }
  }, [aaben, webTilstand, cfg, sendStorrelse])

  const musKoord = (e: { clientX: number; clientY: number }) => {
    const c = canvas.current
    if (!c) return { x: 0, y: 0 }
    return tilSideKoord(e.clientX, e.clientY, c.getBoundingClientRect(), rammeStr.current.w, rammeStr.current.h)
  }

  const aktiv = faner.find((f) => f.aktiv) ?? null

  const meldRect = useCallback(() => {
    const el = holder.current
    const b = bro()
    if (!el || !b) return
    const r = el.getBoundingClientRect()
    void b.saetRect({ x: r.left, y: r.top, width: r.width, height: r.height })
  }, [bro])

  // Rektanglet skal meldes ved ENHVER ændring, ikke kun ved åbning: et
  // vinduesresize, et sidepanel der folder ud, en skalering. ResizeObserver
  // ser dem alle; en window-resize-lytter ville kun se den ene.
  useEffect(() => {
    const el = holder.current
    if (!el) return
    const ro = new ResizeObserver(meldRect)
    ro.observe(el)
    window.addEventListener('resize', meldRect)
    meldRect()
    return () => { ro.disconnect(); window.removeEventListener('resize', meldRect) }
  }, [meldRect, aaben])

  // Oprydningen er IKKE pynt. Fladerne tegner ruden som `{browserOpen && …}`,
  // saa komponenten AFMONTERES naar man lukker den — og saa faar effekten
  // aldrig et `aaben === false` at reagere paa. Uden denne linje fik main
  // aldrig besked, og siden blev staaende oven paa vinduet mens panelet var
  // vaek (Bjørn 21/9-2026: «jeg kan ikk lukke browseren … så bliver den
  // stående»). Webvisningen er et soeskende-lag i vinduet; den forsvinder
  // ikke af at React holder op med at tegne noget.
  useEffect(() => {
    const b = bro()
    if (!b) return
    void b.saetSynlig(aaben)
    if (aaben) meldRect()
    return () => { void b.saetSynlig(false) }
  }, [aaben, meldRect, bro])

  const hentFaner = useCallback(() => {
    const b = bro()
    if (!b) return
    void b.faner()
      .then((f) => { setFaner(f); setFejl('') })
      .catch((e: unknown) => setFejl(
        e instanceof Error && e.message
          ? `Kunne ikke hente fanerne: ${e.message}`
          : 'Kunne ikke hente fanerne.'))
      .finally(() => setHenter(false))
  }, [bro])

  useEffect(() => {
    if (!aaben) return
    hentFaner()
    const id = window.setInterval(hentFaner, 2000)
    return () => window.clearInterval(id)
  }, [aaben, hentFaner])

  // Adressen følger den aktive fane — men ALDRIG mens man selv skriver i
  // feltet. Pollet henter hvert 2. sekund, og uden dette værn ville det
  // overskrive halvfærdig tastning to gange i minuttet.
  const aktivUrl = aktiv?.url ?? ''
  useEffect(() => {
    if (document.activeElement === adressefelt.current) return
    setAdresse(aktivUrl === 'about:blank' ? '' : aktivUrl)
  }, [aktivUrl, aktiv?.id])

  const gaaTil = useCallback(() => {
    const b = bro()
    const t = adresse.trim()
    if (!b || !t) return
    adressefelt.current?.blur()
    // Ingen fane endnu: så er «gå til» det samme som «åbn en fane».
    const p = aktiv ? b.naviger(t) : b.aabn(t)
    void Promise.resolve(p)
      .then(hentFaner)
      .catch(() => setFejl(`Kunne ikke åbne ${t}.`))
  }, [adresse, aktiv, hentFaner, bro])

  const handling = useCallback((fn: () => Promise<unknown>, hvad: string) => {
    void fn().then(hentFaner).catch(() => setFejl(`Kunne ikke ${hvad}.`))
  }, [hentFaner])

  if (!aaben) return null
  const b = bro()
  // Hovedet er FAELLES med de to andre ruder i skinnen — `jobs-head` og
  // `jobs-close`, ikke egne klasser. De tre staar side om side i samme stak;
  // en rude med sin egen kant og sine egne knapper ville se laant ud.
  const hoved = (
    <div className="jobs-head">
      <span>Jarvis&apos; browser</span>
      {onFuld && (
        <button type="button" className="jobs-close jobs-fuld" onClick={() => onFuld(!fuld)}
                aria-label={fuld ? 'Formindsk' : 'Fuld visning'}
                title={fuld ? 'Formindsk' : 'Fuld visning'}>
          {fuld ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        </button>
      )}
      {onClose && (
        <button type="button" className="jobs-close" onClick={onClose} aria-label="Luk">
          <X size={14} />
        </button>
      )}
    </div>
  )

  if (!b) {
    return (
      <aside className="jbrowser" aria-label="Jarvis' browser">
        {hoved}
        <p className="jbrowser-tom">
          Jarvis&apos; browser kraever desk-appen — den findes ikke i en almindelig fane.
        </p>
      </aside>
    )
  }

  return (
    <aside className="jbrowser" aria-label="Jarvis' browser">
      {hoved}
      <div className="jbrowser-faner" role="tablist" aria-label="Jarvis faner">
        <ListeTilstand
          henter={henter}
          fejl={Boolean(fejl)}
          navn="fanerne"
          antal={faner.length}
          tomTekst=""
          onIgen={fejl ? hentFaner : null}
        >
          <></>
        </ListeTilstand>
        {!fejl && faner.map((f) => (
          <div key={f.id} className={`jbrowser-fane${f.aktiv ? ' aktiv' : ''}`} role="tab"
               aria-selected={f.aktiv}>
            <button type="button" className="jbrowser-fane-titel"
                    title={f.url}
                    onClick={() => handling(() => b.vaelg(f.id), 'skifte fane')}>
              <Globe size={12} />
              <span>{faneNavn(f)}</span>
            </button>
            <button type="button" className="jbrowser-fane-luk" aria-label={`Luk ${faneNavn(f)}`}
                    onClick={() => handling(() => b.luk(f.id), 'lukke fanen')}>
              <X size={11} />
            </button>
          </div>
        ))}
        {!fejl && (
          <button type="button" className="jbrowser-ny" aria-label="Ny fane" title="Ny fane"
                  onClick={() => handling(() => b.aabn('about:blank'), 'åbne en fane')}>
            <Plus size={13} />
          </button>
        )}
      </div>

      <div className="jbrowser-nav">
        <button type="button" aria-label="Tilbage" title="Tilbage"
                disabled={!aktiv?.kanTilbage}
                onClick={() => handling(() => b.tilbage(), 'gå tilbage')}>
          <ArrowLeft size={14} />
        </button>
        <button type="button" aria-label="Frem" title="Frem"
                disabled={!aktiv?.kanFrem}
                onClick={() => handling(() => b.frem(), 'gå frem')}>
          <ArrowRight size={14} />
        </button>
        <button type="button"
                aria-label={aktiv?.henter ? 'Stop' : 'Genindlæs'}
                title={aktiv?.henter ? 'Stop' : 'Genindlæs'}
                disabled={!aktiv}
                onClick={() => handling(() => b.genindlaes(), 'genindlæse')}>
          {aktiv?.henter ? <X size={14} /> : <RotateCw size={14} />}
        </button>
        <input
          ref={adressefelt}
          className="jbrowser-adresse"
          type="text"
          value={adresse}
          aria-label="Adresse"
          placeholder="Skriv en adresse eller en søgning"
          spellCheck={false}
          onChange={(e) => setAdresse(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); gaaTil() }
            if (e.key === 'Escape') { setAdresse(aktivUrl === 'about:blank' ? '' : aktivUrl); adressefelt.current?.blur() }
          }}
          onFocus={(e) => e.target.select()}
        />
      </div>

      {fejl && <p className="jbrowser-fejl" role="alert">{fejl}</p>}

      {/* Hullet. Selve siden tegnes af Electron oven paa dette rektangel —
          derfor må der ikke ligge noget her naar en fane er aabne. */}
      <div className="jbrowser-hul" ref={holder} data-testid="jbrowser-hul">
        {webTilstand && (
          <canvas
            ref={canvas}
            data-testid="jbrowser-canvas"
            tabIndex={0}
            aria-label="Jarvis' browser"
            style={{ width: '100%', height: '100%', display: 'block', outline: 'none' }}
            onContextMenu={(e) => e.preventDefault()}
            onMouseMove={(e) => {
              const nu = performance.now()
              if (nu - sidsteMus.current < 30) return
              sidsteMus.current = nu
              strom.current?.send({ t: 'mouse', kind: 'move', ...musKoord(e) })
            }}
            onMouseDown={(e) => {
              e.currentTarget.focus()
              strom.current?.send({ t: 'mouse', kind: 'down', button: museKnap(e.button), ...musKoord(e) })
            }}
            onMouseUp={(e) => strom.current?.send({ t: 'mouse', kind: 'up', button: museKnap(e.button), ...musKoord(e) })}
            onWheel={(e) => strom.current?.send({ t: 'mouse', kind: 'wheel', dx: e.deltaX, dy: e.deltaY, ...musKoord(e) })}
            onKeyDown={(e) => {
              if (e.ctrlKey || e.metaKey) return // lad paste/kopi m.m. i fred
              e.preventDefault()
              strom.current?.send({ t: 'key', kind: 'down', key: e.key === ' ' ? 'Space' : e.key })
            }}
            onKeyUp={(e) => {
              if (e.ctrlKey || e.metaKey) return
              e.preventDefault()
              strom.current?.send({ t: 'key', kind: 'up', key: e.key === ' ' ? 'Space' : e.key })
            }}
            onPaste={(e) => {
              const text = e.clipboardData.getData('text')
              if (text) { e.preventDefault(); strom.current?.send({ t: 'text', text }) }
            }}
          />
        )}
        {faner.length === 0 && !henter && !fejl && (
          <p className="jbrowser-intet">Ingen faner endnu. Skriv en adresse ovenfor.</p>
        )}
      </div>
    </aside>
  )
}
