import { useCallback, useEffect, useRef, useState } from 'react'
import { X, ChevronRight, ChevronDown, FileDiff, Maximize2, Minimize2 } from 'lucide-react'
import { getReviewAendringer, type ReviewAendringer, type ReviewFil } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/**
 * Ændringer i arbejdstræet — diff'en, mens turen kører.
 *
 * Bjørn 16/9-2026: «jeg mangler et changes icon der åbner dette panel … det
 * bruger jeg også rigtigt meget, der kan jeg følge med i ændringer under
 * runnet … og den er så tom enten efter run eller hvis træet ikk er rent».
 *
 * TOM ER IKKE ÉN TILSTAND, MEN TRE, og de betyder helt forskellige ting:
 *
 *   «Ingen ændringer»      træet er rent — alt er committet
 *   «Kan ikke læse træet»  git svarede ikke; vi VED ikke om der er ændringer
 *   «Henter…»              vi har ikke spurgt færdig endnu
 *
 * Et panel der viser «ingen ændringer» i alle tre tilfælde ville lyve i to af
 * dem. Det er samme fejl som jobs-ruden havde med den døde bro.
 *
 * BEGGE OPRINDELIGE BEGRÆNSNINGER ER LUKKET 16/9-2026:
 *  - utrackede filer tæller med (`ny: true`), så en helt ny fil ikke er
 *    usynlig — `git diff HEAD` ser kun sporede filer
 *  - `kilde='maskine'` læser hans EGET træ over broen
 *
 * Headeren siger stadig hvilket træ der tales om. «Ingen ændringer» i
 * serverens repo er ikke det samme som «Jarvis har ikke lavet noget».
 */
export function ChangesPanel({
  config,
  onClose,
  /** Er der kørt test i denne tur? Klienten ved det; serveren kan ikke se det. */
  testKoert = false,
  /** Stiger når en tur slutter — så diff'en hentes igen uden at vente på pollen. */
  refreshKey = 0,
  onCount,
  /** Hvilket træ. 'maskine' kræver `rod` — stien til arbejdstræet hos ham. */
  kilde = 'server',
  rod = '',
  /** Fil der skal foldes ud, sat UDEFRA: klik på en fil i «Redigerede N filer»
   *  under Jarvis' besked åbner ruden med netop den fil åben. */
  fokusFil = '',
  fuld = false,
  onFuld,
}: {
  config?: ApiConfig
  onClose: () => void
  testKoert?: boolean
  refreshKey?: number
  onCount?: (antal: number) => void
  kilde?: 'server' | 'maskine'
  rod?: string
  fokusFil?: string
  fuld?: boolean
  onFuld?: (fuld: boolean) => void
}) {
  const [data, setData] = useState<ReviewAendringer | null>(null)
  const [fejl, setFejl] = useState('')
  const [aabne, setAabne] = useState<Set<string>>(new Set())
  const undervejs = useRef(false)

  const hent = useCallback(() => {
    if (!config || undervejs.current) return
    undervejs.current = true
    getReviewAendringer(config, testKoert, kilde, rod)
      .then((d) => { setData(d); setFejl('') })
      .catch(() => setFejl('kunne ikke læse arbejdstræet'))
      .finally(() => { undervejs.current = false })
  }, [config, testKoert, kilde, rod])

  useEffect(() => {
    hent()
    // 4 sekunder: hurtigt nok til at følge med UNDER en tur, langsomt nok til
    // at `git diff HEAD` på et stort repo ikke bliver en belastning i sig selv.
    const id = setInterval(() => { if (!document.hidden) hent() }, 4000)
    return () => clearInterval(id)
  }, [hent, refreshKey])

  // Én fil udefra folder sig ud — uden at lukke det man selv havde aabnet.
  useEffect(() => {
    if (fokusFil) setAabne((f) => new Set(f).add(fokusFil))
  }, [fokusFil])

  const filer = data?.files ?? []
  useEffect(() => { onCount?.(filer.length) }, [filer.length, onCount])

  const skift = (sti: string) => setAabne((f) => {
    const n = new Set(f)
    if (n.has(sti)) n.delete(sti); else n.add(sti)
    return n
  })

  /** Diff-hunks for ÉN fil ud af den samlede diff-tekst. */
  const hunksFor = (sti: string): string => {
    const tekst = data?.diff ?? ''
    if (!tekst) return ''
    const start = tekst.indexOf(`diff --git a/${sti}`)
    if (start < 0) return ''
    const naeste = tekst.indexOf('\ndiff --git ', start + 1)
    return tekst.slice(start, naeste < 0 ? undefined : naeste)
  }

  const linjeKlasse = (l: string) =>
    l.startsWith('+++') || l.startsWith('---') ? 'diff-fil'
      : l.startsWith('@@') ? 'diff-hunk'
        : l.startsWith('+') ? 'diff-tilf'
          : l.startsWith('-') ? 'diff-fjern' : ''

  return (
    <aside className="changes-panel" aria-label="Ændringer">
      <div className="changes-head">
        <span className="changes-gren">{data?.branch || '—'}</span>
        <span className="changes-pil" aria-hidden="true">→</span>
        {/* HVILKET træ. Uden det kan «ingen ændringer» forveksles med «alt hvad
            Jarvis har lavet» — de to træer er ikke det samme. */}
        <span className="changes-maal">{kilde === 'maskine' ? 'din maskine' : 'arbejdstræ'}</span>
        {onFuld && (
          <button type="button" className="jobs-close" onClick={() => onFuld(!fuld)}
                  aria-label={fuld ? 'Formindsk' : 'Fuld visning'}
                  title={fuld ? 'Formindsk' : 'Fuld visning'}>
            {fuld ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        )}
        <button type="button" className="jobs-close" onClick={onClose} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      {data?.fejl ? (
        /* Serveren NAAEDE ud, men kunne ikke laese hans trae — typisk fordi
           broen er nede. Vi ved altsaa ikke om der er aendringer. */
        <div className="changes-tom is-fejl">{data.fejl}</div>
      ) : fejl ? (
        /* IKKE «ingen ændringer». Vi kunne ikke læse træet, og de to udsagn
           er stik modsatte. */
        <div className="changes-tom is-fejl">{fejl}</div>
      ) : !data ? (
        <div className="changes-tom">Henter…</div>
      ) : filer.length === 0 ? (
        <div className="changes-tom">Ingen ændringer</div>
      ) : (
        <>
          <div className="changes-opsummering">
            {filer.length} {filer.length === 1 ? 'fil' : 'filer'}
            <span className="git-add">+{data.added}</span>
            <span className="git-del">−{data.removed}</span>
            {data.diff_truncated && (
              /* Diff'en er klippet af serveren. Uden dette ville de sidste
                 filer se ud som om de ingen ændringer havde. */
              <span className="changes-klippet" title="Diff'en er for stor og er klippet">klippet</span>
            )}
          </div>
          <ul className="changes-liste">
            {filer.map((f: ReviewFil) => {
              const aaben = aabne.has(f.path)
              const hunks = aaben ? hunksFor(f.path) : ''
              return (
                <li key={f.path} className="changes-fil">
                  <button type="button" className="changes-fil-rk" onClick={() => skift(f.path)}
                          aria-expanded={aaben}>
                    {aaben ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <FileDiff size={12} />
                    <span className="changes-sti" title={f.path}>{f.path}</span>
                    {f.ny && <span className="changes-ny">ny</span>}
                    {f.binary ? (
                      <span className="changes-binaer">binær</span>
                    ) : f.ny && f.added === 0 ? (
                      /* Over broen henter vi ikke filens indhold, saa
                         linjeantallet er UKENDT. «+0» ville vaere et gaet. */
                      <span className="changes-binaer">—</span>
                    ) : (
                      <>
                        <span className="git-add">+{f.added}</span>
                        <span className="git-del">−{f.removed}</span>
                      </>
                    )}
                  </button>
                  {aaben && (
                    hunks ? (
                      <pre className="changes-diff">
                        {hunks.split('\n').map((l, i) => (
                          <span key={i} className={linjeKlasse(l)}>{l}{'\n'}</span>
                        ))}
                      </pre>
                    ) : (
                      /* Filen står i listen, men dens hunks er ikke i teksten —
                         typisk fordi diff'en blev klippet. At vise en tom
                         kasse ville ligne «ingen ændringer i denne fil». */
                      <div className="changes-tom is-lille">
                        {data.diff_truncated ? 'Diff\'en er klippet — denne fil nåede ikke med.'
                          : 'Ingen tekst-diff for denne fil.'}
                      </div>
                    )
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </aside>
  )
}
