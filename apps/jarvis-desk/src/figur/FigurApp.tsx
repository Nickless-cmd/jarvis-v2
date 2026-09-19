import { useEffect, useRef, useState } from 'react'
import { AudioLines, ChevronDown, ChevronUp, SendHorizontal, SquarePen } from 'lucide-react'
import { apiFetch, type ApiConfig } from '../lib/api'
import type { Opmaerksomhed } from '../lib/opmaerksomhed'
import { FigurKrop } from './FigurKrop'
import { HANDLING_FOR, blikFraMus, boble, maalHoejde, type Handling } from './figurLogik'
import { sendHurtigt } from './hurtigChat'
import './figur.css'

interface FigurBro {
  config: { get: () => Promise<{ apiBaseUrl: string; authToken: string | null }> }
  figur: {
    traekStart: (mx: number, my: number) => Promise<void>
    traek: (mx: number, my: number) => Promise<void>
    traekSlut: () => Promise<void>
    hoejde: (h: number, contentHeight?: number, figureCenter?: number, side?: 'over' | 'under', currentCenter?: number) => Promise<void>
    snapshot?: () => Promise<{ cursor: { x: number; y: number }; bounds: { x: number; y: number }; side: 'over' | 'under' }>
    menu?: () => Promise<void>
    aabnSamtale: (sessionId: string | null) => Promise<void>
    stemme: () => Promise<void>
  }
}

const bro = () => (window as unknown as { jarvisDesk?: FigurBro }).jarvisDesk

/** Hvor ofte figuren spørger. Taleboblen viser hvad han laver LIGE NU, så
 *  den skal være hurtigere end sidepanelets linje (5 s). */
export const POLL_MS = 2500
/** Så længe skal vinduet have været for stort før det krymper. */
export const KRYMP_EFTER_MS = 6000
const TRAEK_TAERSKEL = 4

/**
 * Figuren i sit eget vindue (electron/figur.ts). Viser tilstands-hjernen som
 * krop + taleboble — også når hovedvinduet er lukket.
 *
 * - Klik: den hopper (Codex: «Klik for at hoppe»). Er boblen afvist, kommer
 *   den frem igen.
 * - Træk: den flyttes, og læner sig i retningen.
 * - Dobbeltklik: hovedvinduet.
 * - Boblen: klik åbner samtalen den taler om; × afviser den til der sker
 *   noget nyt.
 * - Tre ikoner under figuren (Codex' samme tre): ny chat herfra, stemme, og
 *   pak taleboblen væk / frem igen.
 */
export function FigurApp() {
  const [config, setConfig] = useState<ApiConfig | null>(null)
  const [o, setO] = useState<Opmaerksomhed | null>(null)
  const [handling, setHandling] = useState<Handling>('vinker') // første vågne øjeblik
  const [hilsen, setHilsen] = useState(true)
  const [afvist, setAfvist] = useState<string | null>(null)
  const [laener, setLaener] = useState<'venstre' | 'hoejre' | null>(null)
  const [blik, setBlik] = useState({ x: 0, y: 0 })
  const [side, setSide] = useState<'over' | 'under'>('over')
  const [grimasse, setGrimasse] = useState<'smil' | 'undren' | null>(null)
  const [pakket, setPakket] = useState(false)
  const [skriver, setSkriver] = useState(false)
  const [udkast, setUdkast] = useState('')
  const [sender, setSender] = useState(false)
  const [kvittering, setKvittering] = useState<string | null>(null)
  const [sendFejl, setSendFejl] = useState<string | null>(null)
  const rodRef = useRef<HTMLDivElement>(null)
  const grebRef = useRef<HTMLDivElement>(null)
  const traek = useRef<{ x: number; y: number; sidstX: number; flytter: boolean } | null>(null)
  const forrigeTilstand = useRef<string>('idle')
  const sidstMus = useRef<{ x: number; y: number; tid: number } | null>(null)
  const hvileBlik = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    document.documentElement.classList.add('figur-flade')
    void bro()?.config.get().then((c) => setConfig({ apiBaseUrl: c.apiBaseUrl, authToken: c.authToken }))
    const t = setTimeout(() => setHilsen(false), 4000)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!config?.authToken) return
    let aktiv = true
    const tick = () => {
      apiFetch<Opmaerksomhed>(config, '/cowork/opmaerksomhed', { retries: 0 })
        .then((d) => { if (aktiv) setO(d) })
        .catch(() => { /* behold sidste — ingen flimren ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { aktiv = false; clearInterval(id) }
  }, [config?.apiBaseUrl, config?.authToken])

  // En NY tilstand spiller sin handling (tre gange, se CSS) — samme tilstand
  // igen gør ingenting, ellers ville hver poll starte animationen forfra.
  useEffect(() => {
    const t = o?.tilstand ?? 'idle'
    if (t === forrigeTilstand.current) return
    forrigeTilstand.current = t
    setHandling(HANDLING_FOR[t])
  }, [o?.tilstand])

  // Cursorens skærmposition kommer fra Electron: DOM-events ser kun markøren
  // inde i det lille transparente figurvindue.
  useEffect(() => {
    const snapshot = bro()?.figur.snapshot
    if (!snapshot) return
    let aktiv = true
    const tick = async () => {
      try {
        const s = await snapshot()
        if (!aktiv) return
        setSide((prev) => prev === s.side ? prev : s.side)
        const old = sidstMus.current
        if (!old || Math.hypot(s.cursor.x - old.x, s.cursor.y - old.y) > 2) {
          sidstMus.current = { ...s.cursor, tid: Date.now() }
          hvileBlik.current = null
        }
        const rect = grebRef.current?.getBoundingClientRect()
        if (!rect) return
        const eyeCenter = { x: s.bounds.x + rect.left + rect.width / 2, y: s.bounds.y + rect.top + rect.height * 0.42 }
        const next = hvileBlik.current ?? blikFraMus(s.cursor, eyeCenter)
        setBlik((prev) => Math.hypot(prev.x - next.x, prev.y - next.y) < 0.05 ? prev : next)
      } catch { /* figuren kan være ved at lukke */ }
    }
    void tick()
    const id = setInterval(() => { void tick() }, 140)
    return () => { aktiv = false; clearInterval(id) }
  }, [])

  // Små spontane udtryk kun i hvile, og kun når systemet tillader animation.
  useEffect(() => {
    if (o?.tilstand && o.tilstand !== 'idle') { setGrimasse(null); return }
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    let pause: ReturnType<typeof setTimeout>
    let nulstil: ReturnType<typeof setTimeout>
    const naeste = () => {
      if (sidstMus.current && Date.now() - sidstMus.current.tid > 6000) {
        hvileBlik.current = { x: (Math.random() - 0.5) * 2.5, y: (Math.random() - 0.5) * 1.8 }
        setGrimasse(Math.random() < 0.7 ? 'smil' : 'undren')
        nulstil = setTimeout(() => { hvileBlik.current = null; setGrimasse(null) }, 1100)
      }
      pause = setTimeout(naeste, 7500 + Math.random() * 6500)
    }
    pause = setTimeout(naeste, 7500 + Math.random() * 6500)
    return () => { clearTimeout(pause); clearTimeout(nulstil); hvileBlik.current = null }
  }, [o?.tilstand])

  // Vinduet skal være så lille som indholdet (Linux kan ikke lade klik gå
  // igennem gennemsigtige områder) — men i FASTE trin (figurLogik.maalHoejde),
  // og det krymper først når det har været mindre et stykke tid. Ellers
  // skiftede det størrelse ved hver ny linje i boblen og glimtede.
  const [maalt, setMaalt] = useState(0)
  useEffect(() => {
    const el = rodRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => setMaalt(el.getBoundingClientRect().height))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const meldt = useRef(0)
  const meldtLayout = useRef('')
  const krymp = useRef<ReturnType<typeof setTimeout> | null>(null)

  const b = boble(o, afvist)
  const vis = pakket ? null : (
    (sendFejl ? { noegle: 'sendfejl', etiket: 'Kunne ikke sende', titel: '', tekst: sendFejl, sessionId: null, tilstand: 'failed' as const } : null)
    ?? b
    ?? (kvittering ? { noegle: 'sendt', etiket: 'Sendt', titel: kvittering, tekst: 'Jeg går i gang.', sessionId: null, tilstand: 'running' as const } : null)
    ?? (hilsen ? { noegle: 'hilsen', etiket: 'Her er jeg', titel: '', tekst: 'Jeg siger til, når noget kræver dig.', sessionId: null, tilstand: 'idle' as const } : null))

  const maal = maalHoejde(maalt, vis !== null, skriver)
  useEffect(() => {
    if (!maal) return
    if (krymp.current) { clearTimeout(krymp.current); krymp.current = null }
    const meld = (h: number) => {
      const root = rodRef.current?.getBoundingClientRect()
      const figure = grebRef.current?.getBoundingClientRect()
      if (!root || !figure) return
      const center = figure.top - root.top + figure.height / 2
      const currentCenter = figure.top + figure.height / 2
      const key = `${h}|${side}|${Math.round(root.height)}|${Math.round(center)}`
      if (key === meldtLayout.current) return
      meldtLayout.current = key
      meldt.current = h
      void bro()?.figur.hoejde(h, root.height, center, side, currentCenter)
    }
    if (maal >= meldt.current) {
      meld(maal)
      return
    }
    // Mindre: vent — kommer boblen tilbage lige om lidt, skal vinduet ikke
    // have skrumpet og vokset imens.
    krymp.current = setTimeout(() => meld(maal), KRYMP_EFTER_MS)
  }, [maal, side, maalt])
  useEffect(() => () => { if (krymp.current) clearTimeout(krymp.current) }, [])

  const send = async () => {
    if (!config || !udkast.trim() || sender) return
    setSender(true)
    setSendFejl(null)
    try {
      await sendHurtigt(config, udkast)
      setKvittering(udkast.trim().slice(0, 60))
      setUdkast(''); setSkriver(false); setPakket(false)
      setTimeout(() => setKvittering(null), 6000)
    } catch (e) {
      // Udkastet bliver stående, så intet går tabt — fejlen står i boblen.
      setSendFejl(e instanceof Error ? e.message : 'Kunne ikke sende')
    } finally {
      setSender(false)
    }
  }

  const ned = (e: React.PointerEvent) => {
    if (e.button !== 0) return
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
    traek.current = { x: e.screenX, y: e.screenY, sidstX: e.screenX, flytter: false }
  }
  const flyt = (e: React.PointerEvent) => {
    const t = traek.current
    if (!t) return
    if (!t.flytter && Math.hypot(e.screenX - t.x, e.screenY - t.y) < TRAEK_TAERSKEL) return
    if (!t.flytter) { t.flytter = true; void bro()?.figur.traekStart(t.x, t.y) }
    if (e.screenX !== t.sidstX) setLaener(e.screenX > t.sidstX ? 'hoejre' : 'venstre')
    t.sidstX = e.screenX
    void bro()?.figur.traek(e.screenX, e.screenY)
  }
  const op = () => {
    const t = traek.current
    traek.current = null
    setLaener(null)
    if (!t) return
    if (t.flytter) { void bro()?.figur.traekSlut(); return }
    setHandling('hopper')
    setAfvist(null)
  }
  /** Browser-preview uden Electron kan stadig reagere lokalt på markøren. */
  const kig = (e: React.PointerEvent<HTMLDivElement>) => {
    if (bro()?.figur.snapshot) return
    if (traek.current?.flytter) return
    const r = e.currentTarget.getBoundingClientRect()
    setBlik(blikFraMus({ x: e.clientX, y: e.clientY }, { x: r.left + r.width / 2, y: r.top + r.height * 0.42 }))
  }

  return (
    <div
      className={`figur-rod${side === 'under' ? ' boble-under' : ''}`}
      ref={rodRef}
      data-tilstand={o?.tilstand ?? 'idle'}
      onPointerMove={kig}
      onPointerLeave={() => { if (!bro()?.figur.snapshot) setBlik({ x: 0, y: 0 }) }}
      onContextMenu={(e) => { e.preventDefault(); void bro()?.figur.menu?.() }}
    >
      {vis ? (
        <div className={`figur-boble b-${vis.tilstand}`} role="status" data-testid="figur-boble">
          <button type="button" className="figur-boble-indhold" onClick={() => void bro()?.figur.aabnSamtale(vis.sessionId)}>
            <span className="figur-boble-etiket">{vis.etiket}</span>
            {vis.titel ? <span className="figur-boble-titel">{vis.titel}</span> : null}
            {vis.tekst ? <span className="figur-boble-tekst">{vis.tekst}</span> : null}
          </button>
          <button
            type="button"
            className="figur-boble-luk"
            aria-label="Skjul boblen"
            onClick={() => { if (sendFejl) setSendFejl(null); else if (b) setAfvist(b.noegle); else setHilsen(false) }}
          >×</button>
        </div>
      ) : null}
      <div
        className="figur-greb"
        ref={grebRef}
        data-testid="figur"
        title="Klik for at hoppe · træk for at flytte · dobbeltklik åbner Jarvis"
        onPointerDown={ned}
        onPointerMove={flyt}
        onPointerUp={op}
        onPointerCancel={op}
        onDoubleClick={() => void bro()?.figur.aabnSamtale(null)}
      >
        <div onAnimationEnd={(e) => { if (e.target === e.currentTarget.firstElementChild && handling !== 'hvile') setHandling('hvile') }}>
          <FigurKrop handling={handling} ring={o?.tilstand === 'running' ? 'hurtig' : 'rolig'} laener={laener} blik={blik} grimasse={grimasse} />
        </div>
      </div>
      {/* Codex' tre ikoner under figuren. Vist når der er noget at vise —
          eller når man holder musen over — så en figur i hvile står ren. */}
      <div className={`figur-ikoner${vis || skriver || (o && o.tilstand !== 'idle') ? ' synlige' : ''}`}>
        <button type="button" aria-label="Start ny chat" title="Start ny chat" className={skriver ? 'aktiv' : ''}
                onClick={() => setSkriver((v) => !v)}>
          <SquarePen size={15} strokeWidth={1.8} />
        </button>
        <button type="button" aria-label="Tal med Jarvis" title="Tal med Jarvis" onClick={() => void bro()?.figur.stemme()}>
          <AudioLines size={15} strokeWidth={1.8} />
        </button>
        <button type="button" aria-label={pakket ? 'Vis taleboblen' : 'Pak taleboblen væk'} title={pakket ? 'Vis taleboblen' : 'Pak taleboblen væk'}
                onClick={() => setPakket((p) => !p)}>
          {pakket ? <ChevronUp size={15} strokeWidth={1.8} /> : <ChevronDown size={15} strokeWidth={1.8} />}
        </button>
      </div>
      {skriver ? (
        <form className="figur-hurtig" onSubmit={(e) => { e.preventDefault(); void send() }}>
          <input
            autoFocus
            aria-label="Start ny chat"
            placeholder="Start ny chat"
            value={udkast}
            disabled={sender}
            onChange={(e) => setUdkast(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') { setSkriver(false); setUdkast('') } }}
          />
          <button type="submit" aria-label="Send" disabled={!udkast.trim() || sender}>
            <SendHorizontal size={14} strokeWidth={2} />
          </button>
        </form>
      ) : null}
    </div>
  )
}
