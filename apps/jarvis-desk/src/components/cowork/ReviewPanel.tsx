import { useEffect, useState } from 'react'
import { GitCompare, AlertTriangle, ChevronRight } from 'lucide-react'
import { getReviewAendringer, type ReviewAendringer } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'

/** Review: hvad blev der ændret, og hvad bør man kigge efter?
 *
 *  Risikoflagene er repoets EGNE regler fra CLAUDE.md — filstørrelser og
 *  manglende testkørsel — ikke en vurdering appen finder på. Et flag uden
 *  en regel bag sig får folk til at ignorere flagene.
 */
export function ReviewPanel({ config, testKoert = false }: { config?: ApiConfig; testKoert?: boolean }) {
  const [d, setD] = useState<ReviewAendringer | null>(null)
  const [fejl, setFejl] = useState('')
  const [visDiff, setVisDiff] = useState(false)

  useEffect(() => {
    if (!config) return
    let levende = true
    getReviewAendringer(config, testKoert)
      .then((r) => { if (levende) setD(r) })
      .catch(() => { if (levende) setFejl('Kunne ikke hente ændringerne.') })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, testKoert])

  if (fejl) return <p className="rv-tom">{fejl}</p>
  if (!d) return null
  if (d.files.length === 0) {
    return <p className="rv-tom">Intet ændret i arbejdstræet{d.branch ? ` på ${d.branch}` : ''}.</p>
  }

  return (
    <section className="rv">
      <h3 className="rv-head">
        <GitCompare size={14} />
        <span>{d.files.length} filer på {d.branch}</span>
        <span className="rv-stat">
          <span className="git-add">+{d.added}</span> <span className="git-del">−{d.removed}</span>
        </span>
      </h3>

      {d.risks.length > 0 && (
        <ul className="rv-risici">
          {d.risks.map((r, i) => (
            <li key={i} className="rv-risiko">
              <AlertTriangle size={12} />
              <span className="rv-regel">{r.path ? `${r.path} — ` : ''}{r.regel}</span>
              <span className="rv-note">{r.note}</span>
            </li>
          ))}
        </ul>
      )}

      <ul className="rv-filer">
        {d.files.map((f) => (
          <li key={f.path} className="rv-fil">
            <span className="rv-sti" title={f.path}>{f.path}</span>
            {f.binary
              ? <span className="rv-bin">binær</span>
              : <span className="rv-tal">
                  <span className="git-add">+{f.added}</span> <span className="git-del">−{f.removed}</span>
                </span>}
          </li>
        ))}
      </ul>

      {d.diff && (
        <>
          <button type="button" className="rv-diffknap" onClick={() => setVisDiff((v) => !v)} aria-expanded={visDiff}>
            <ChevronRight size={12} className={visDiff ? 'rv-pil aaben' : 'rv-pil'} />
            {visDiff ? 'Skjul diff' : 'Vis diff'}
          </button>
          {visDiff && (
            <>
              <pre className="rv-diff">{d.diff}</pre>
              {d.diff_truncated && <p className="rv-tom">Diff'en er afkortet — åbn den i editoren for resten.</p>}
            </>
          )}
        </>
      )}
    </section>
  )
}
