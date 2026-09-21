import { useCallback, useEffect, useRef, useState } from 'react'
import { Globe, X, RotateCw } from 'lucide-react'
import { ListeTilstand } from '../feedback/ListeTilstand'

interface Fane { id: number; url: string; titel: string; aktiv: boolean }

interface Bro {
  saetRect: (r: { x: number; y: number; width: number; height: number }) => Promise<boolean>
  saetSynlig: (v: boolean) => Promise<boolean>
  faner: () => Promise<Fane[]>
  vaelg: (id: number) => Promise<boolean>
  luk: (id: number) => Promise<boolean>
  aabn: (url: string) => Promise<Fane>
  naviger: (url: string) => Promise<boolean>
}

const bro = (): Bro | undefined =>
  (window as unknown as { jarvisDesk?: { browser?: Bro } }).jarvisDesk?.browser

/**
 * Jarvis' browser — panelet omkring hans egen webvisning.
 *
 * ## Hvad komponenten ER og ikke er (Bjørn 21/9-2026)
 *
 * Den tegner IKKE siden. Siden er en `WebContentsView` som Electron
 * komponerer oven på vinduet; her står kun fanerækken og en PLADSHOLDER der
 * fortæller main hvor visningen skal ligge.
 *
 * Det er ikke en omvej. En webvisning kan ikke ligge inde i React-træet —
 * den er et søskende-lag i vinduet. Derfor må nogen måle hullet, og det skal
 * være den der ejer layoutet. Gjorde main sit eget regnestykke, ville de to
 * skride fra hinanden i samme øjeblik panelbredden ændrede sig.
 *
 * Bjørn kan klikke direkte i visningen mens Jarvis arbejder i den — det er
 * hele grunden til at det er Electrons egen visning og ikke et skærmbillede
 * af en fremmed Chrome.
 */
export function JarvisBrowserPanel({ aaben }: { aaben: boolean }) {
  const [faner, setFaner] = useState<Fane[]>([])
  // Codex' punkt 2 (21/9-2026): en fejl må ikke se ud som en tom kasse. Den
  // her rude var selv én af de fjorten der intet sagde — skrevet samme aften.
  const [fejl, setFejl] = useState('')
  const [henter, setHenter] = useState(true)
  const holder = useRef<HTMLDivElement | null>(null)

  const meldRect = useCallback(() => {
    const el = holder.current
    const b = bro()
    if (!el || !b) return
    const r = el.getBoundingClientRect()
    void b.saetRect({ x: r.left, y: r.top, width: r.width, height: r.height })
  }, [])

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

  useEffect(() => {
    const b = bro()
    if (!b) return
    void b.saetSynlig(aaben)
    if (aaben) meldRect()
  }, [aaben, meldRect])

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
  }, [])

  useEffect(() => {
    if (!aaben) return
    hentFaner()
    const id = window.setInterval(hentFaner, 2000)
    return () => window.clearInterval(id)
  }, [aaben, hentFaner])

  if (!aaben) return null
  if (!bro()) {
    return (
      <div className="jbrowser jbrowser-tom">
        Jarvis&apos; browser kraever desk-appen — den findes ikke i en almindelig fane.
      </div>
    )
  }

  return (
    <div className="jbrowser">
      <div className="jbrowser-faner" role="tablist" aria-label="Jarvis faner">
        <ListeTilstand
          henter={henter}
          fejl={fejl}
          antal={faner.length}
          tomTekst=""
          onIgen={fejl ? hentFaner : null}
        >
          <></>
        </ListeTilstand>
        {!fejl && !henter && faner.length === 0 && (
          <button
            type="button"
            className="jbrowser-ny"
            onClick={() => { void bro()!.aabn('about:blank').then(hentFaner) }}
          >
            <Globe size={13} /> Aabn en fane
          </button>
        )}
        {!fejl && faner.map((f) => (
          <div key={f.id} className={`jbrowser-fane${f.aktiv ? ' aktiv' : ''}`} role="tab"
               aria-selected={f.aktiv}>
            <button type="button" className="jbrowser-fane-titel"
                    title={f.url}
                    onClick={() => { void bro()!.vaelg(f.id).then(hentFaner) }}>
              <Globe size={12} />
              <span>{f.titel || f.url || 'ny fane'}</span>
            </button>
            <button type="button" className="jbrowser-fane-luk" aria-label="Luk fane"
                    onClick={() => { void bro()!.luk(f.id).then(hentFaner) }}>
              <X size={11} />
            </button>
          </div>
        ))}
        <button type="button" className="jbrowser-genindlaes" aria-label="Opdater listen"
                onClick={hentFaner}>
          <RotateCw size={12} />
        </button>
      </div>
      {/* Hullet. Selve siden tegnes af Electron oven paa dette rektangel. */}
      <div className="jbrowser-hul" ref={holder} data-testid="jbrowser-hul" />
    </div>
  )
}
