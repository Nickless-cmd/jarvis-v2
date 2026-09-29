import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { beregnDiffPlacering } from '../../lib/diffPopupPlacering'
import { ChevronDown, ChevronRight, Code2, FileDiff, RotateCcw } from 'lucide-react'
import { kortSti, type DiffPar, type RedigeretFil } from '../../lib/redigeredeFiler'
import { DiffView } from './DiffView'

/**
 * «Redigerede N filer» under Jarvis' besked — formen er Claude Codes egen.
 *
 * Bjørn 16/9-2026: «lav forløb under hans besked i chatview om til det på
 * billedet og kun vist hvis han har redigeret en fil eller flere … når man
 * klikker på dem åbner de i den changes panel du lige har lavet og viser diff».
 *
 * Tallene kommer fra serverens målte linjetal i redigeringsresultaterne.
 * Mangler de for bare ét kald til en fil, står den uden tal frem for et gæt.
 *
 * Hover-diffen kom 29/9-2026 (Bjørn: «hvis jeg holder musen over fil navnet i
 * feltet så kommer der en diff visning med scrool»). Den viser ændringen UDEN
 * at man først skal åbne Ændringer-ruden — et klik åbner stadig ruden, men nu
 * kan man se hvad der skete ved bare at pege på rækken.
 */
export interface FilTal { added: number; removed: number }

/** Højden popup'en højst må fylde — resten scroller. Samme tal i CSS'en. */
const DIFF_HOEJDE = 360

export function EditedFilesCard({
  filer,
  tal,
  diffs,
  onAabn,
  onFortryd,
}: {
  filer: RedigeretFil[]
  /** sti → målte +/− fra værktøjsresultater. Mangler en sti, vises intet tal. */
  tal?: Record<string, FilTal>
  /** sti → gammel/ny-par fra kaldets egne argumenter. Grundlaget for hover-diffen. */
  diffs?: Record<string, DiffPar[]>
  /** Klik på en fil: åbn Ændringer-ruden med netop den fil foldet ud. */
  onAabn: (sti: string) => void
  onFortryd?: () => Promise<{ status: string; files?: number; error?: string }>
}) {
  const [alle, setAlle] = useState(false)
  const [bekraeft, setBekraeft] = useState(false)
  const [venter, setVenter] = useState(false)
  const [fortrudt, setFortrudt] = useState(false)
  const [fejl, setFejl] = useState('')
  const [hover, setHover] = useState<
    { path: string; top: number; left: number; bredde: number; hoejde: number } | null>(null)
  const lukkeTimer = useRef<number | null>(null)

  // Popup'en staar uden for kortet i DOM'en (portal), fordi `.edited-files`
  // har `overflow: hidden` — uden portalen blev diffen klippet af kortets kant.
  const afbrydLuk = () => {
    if (lukkeTimer.current !== null) { window.clearTimeout(lukkeTimer.current); lukkeTimer.current = null }
  }
  // Lille nådesfrist: musen skal kunne flytte fra rækken og OVER i popup'en
  // (hvor man kan scrolle og trykke «Kun ændringer») uden at den lukker.
  const planlaegLuk = () => {
    afbrydLuk()
    lukkeTimer.current = window.setTimeout(() => setHover(null), 140)
  }
  useEffect(() => afbrydLuk, [])

  useEffect(() => {
    if (!hover) return
    const paaTast = (e: KeyboardEvent) => { if (e.key === 'Escape') setHover(null) }
    window.addEventListener('keydown', paaTast)
    return () => window.removeEventListener('keydown', paaTast)
  }, [hover])

  if (filer.length === 0) return null
  const n = filer.length
  const viste = alle ? filer : filer.slice(0, 3)
  const rest = n - viste.length
  const harAlleTal = filer.every((f) => tal?.[f.path] !== undefined)
  const sum = harAlleTal ? filer.reduce((s, f) => ({
    added: s.added + tal![f.path]!.added,
    removed: s.removed + tal![f.path]!.removed,
  }), { added: 0, removed: 0 }) : null

  const visDiff = (path: string, el: HTMLElement) => {
    if (!diffs?.[path]?.length) return
    afbrydLuk()
    // Rammen er CHAT-FLADEN, ikke vinduet. Foer blev pladsen maalt mod hele
    // vinduet, og en fil-raekke yderst til hoejre havde saa aldrig plads —
    // spejlingen lagde diffen hen over sidepanelet (Bjoern 29/9-2026).
    // `.main` er den flade raekken selv bor i; findes den ikke, falder vi
    // tilbage paa vinduet, og saa opfoerer den sig som foer.
    const flade = el.closest('.main')
    const ramme = flade
      ? flade.getBoundingClientRect()
      : { top: 0, bottom: window.innerHeight, left: 0, right: window.innerWidth }
    const p = beregnDiffPlacering({
      raekke: el.getBoundingClientRect(),
      ramme,
      vindue: { bredde: window.innerWidth, hoejde: window.innerHeight },
      hoejde: DIFF_HOEJDE,
    })
    setHover({ path, top: p.top, left: p.left, bredde: p.bredde, hoejde: p.hoejde })
  }

  const hoverPar = hover ? diffs?.[hover.path] : undefined

  return (
    <div className="edited-files">
      <div className="edited-files-head">
        <span className="edited-files-headikon" aria-hidden="true"><FileDiff size={16} /></span>
        <span className="edited-files-titel">
          Redigerede {n} {n === 1 ? 'fil' : 'filer'}
        </span>
        {sum && <span className="edited-files-sum">
          <span className="git-add">+{sum.added}</span> <span className="git-del">−{sum.removed}</span>
        </span>}
        {onFortryd && (fortrudt
          ? <span className="edited-files-kvittering">{n} {n === 1 ? 'fil fortrudt' : 'filer fortrudt'}</span>
          : <button type="button" className="edited-files-vis" disabled={venter}
              onClick={() => { setFejl(''); setBekraeft(true) }}>
              <RotateCcw size={12} /> Fortryd
            </button>)}
        <button type="button" className="edited-files-vis"
                onClick={() => onAabn(filer[0]!.path)}>
          Vis ændringer
        </button>
      </div>
      {bekraeft && !fortrudt && <div className="edited-files-bekraeft">
        <span>Fortryd denne beskeds {n} {n === 1 ? 'filændring' : 'filændringer'}? Nyere ændringer i filerne bliver beskyttet.</span>
        <button type="button" disabled={venter} onClick={() => setBekraeft(false)}>Annuller</button>
        <button type="button" disabled={venter} onClick={() => {
          setVenter(true)
          void onFortryd!().then((result) => {
            if (result.status === 'ok') { setFortrudt(true); setBekraeft(false) }
            else setFejl(result.error || 'Kunne ikke fortryde filerne.')
          }).catch((error: unknown) => {
            setFejl(error instanceof Error ? error.message : 'Kunne ikke fortryde filerne.')
          }).finally(() => setVenter(false))
        }}>Ja, fortryd {n} {n === 1 ? 'fil' : 'filer'}</button>
      </div>}
      {fejl && <p className="edited-files-fejl" role="alert">{fejl}</p>}
      <ul className="edited-files-liste">
        {viste.map((f) => {
          const t = tal?.[f.path]
          const harDiff = Boolean(diffs?.[f.path]?.length)
          return (
            <li key={f.path}>
              <button type="button" className="edited-files-rk" onClick={() => onAabn(f.path)}
                      /* Native tooltip kun når der IKKE er en diff-popup — ellers
                         ville to tooltips ligge oven i hinanden. */
                      title={harDiff ? undefined : f.path}
                      onMouseEnter={(e) => visDiff(f.path, e.currentTarget)}
                      onMouseLeave={planlaegLuk}
                      onFocus={(e) => visDiff(f.path, e.currentTarget)}
                      onBlur={planlaegLuk}>
                <Code2 size={12} className="edited-files-ikon" />
                <span className="edited-files-sti">{kortSti(f.path)}</span>
                {f.gange > 1 && (
                  /* To redigeringer af samme fil er ÉN række — men antallet
                     siges, ellers ser en fil der blev rettet tre gange ud som
                     én enkelt rettelse. */
                  <span className="edited-files-gange">{f.gange}×</span>
                )}
                {t && (
                  <span className="edited-files-tal">
                    <span className="git-add">+{t.added}</span>
                    <span className="git-del">−{t.removed}</span>
                  </span>
                )}
                <ChevronRight size={13} className="edited-files-chevron" />
              </button>
            </li>
          )
        })}
      </ul>
      {n > 3 && (
        <button type="button" className="edited-files-mere" onClick={() => setAlle((v) => !v)}>
          {alle ? 'Vis færre filer' : `Vis ${rest} ${rest === 1 ? 'fil' : 'filer'} mere`}
          <ChevronDown size={13} className={alle ? 'er-aaben' : ''} aria-hidden="true" />
        </button>
      )}

      {hover && hoverPar && createPortal(
        <div className="edited-files-diff" role="tooltip"
             aria-label={`Diff for ${hover.path}`}
             style={{ top: hover.top, left: hover.left, width: hover.bredde, maxHeight: hover.hoejde }}
             onMouseEnter={afbrydLuk} onMouseLeave={planlaegLuk}>
          <div className="edited-files-diff-head">
            <span className="edited-files-diff-sti" title={hover.path}>{hover.path}</span>
            {hoverPar.length > 1 && (
              <span className="edited-files-diff-antal">{hoverPar.length} ændringer</span>
            )}
          </div>
          {/* Kroppen scroller. Flere redigeringer af samme fil vises i
              rækkefølge, så man kan følge hvad der skete — ikke kun slutformen. */}
          <div className="edited-files-diff-krop">
            {hoverPar.map((p, i) => (
              <DiffView key={i} oldText={p.gammel} newText={p.ny}
                        filename={hoverPar.length > 1 ? `Ændring ${i + 1} af ${hoverPar.length}` : undefined} />
            ))}
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
