import { useState } from 'react'
import { ChevronDown, ChevronRight, Code2, FileDiff, RotateCcw } from 'lucide-react'
import { kortSti, type RedigeretFil } from '../../lib/redigeredeFiler'

/**
 * «Redigerede N filer» under Jarvis' besked — formen er Claude Codes egen.
 *
 * Bjørn 16/9-2026: «lav forløb under hans besked i chatview om til det på
 * billedet og kun vist hvis han har redigeret en fil eller flere … når man
 * klikker på dem åbner de i den changes panel du lige har lavet og viser diff».
 *
 * Tallene kommer fra serverens målte linjetal i redigeringsresultaterne.
 * Mangler de for bare ét kald til en fil, står den uden tal frem for et gæt.
 */
export interface FilTal { added: number; removed: number }

export function EditedFilesCard({
  filer,
  tal,
  onAabn,
  onFortryd,
}: {
  filer: RedigeretFil[]
  /** sti → målte +/− fra værktøjsresultater. Mangler en sti, vises intet tal. */
  tal?: Record<string, FilTal>
  /** Klik på en fil: åbn Ændringer-ruden med netop den fil foldet ud. */
  onAabn: (sti: string) => void
  onFortryd?: () => Promise<{ status: string; files?: number; error?: string }>
}) {
  const [alle, setAlle] = useState(false)
  const [bekraeft, setBekraeft] = useState(false)
  const [venter, setVenter] = useState(false)
  const [fortrudt, setFortrudt] = useState(false)
  const [fejl, setFejl] = useState('')
  if (filer.length === 0) return null
  const n = filer.length
  const viste = alle ? filer : filer.slice(0, 3)
  const rest = n - viste.length
  const harAlleTal = filer.every((f) => tal?.[f.path] !== undefined)
  const sum = harAlleTal ? filer.reduce((s, f) => ({
    added: s.added + tal![f.path]!.added,
    removed: s.removed + tal![f.path]!.removed,
  }), { added: 0, removed: 0 }) : null

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
          return (
            <li key={f.path}>
              <button type="button" className="edited-files-rk" onClick={() => onAabn(f.path)}
                      title={f.path}>
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
    </div>
  )
}
