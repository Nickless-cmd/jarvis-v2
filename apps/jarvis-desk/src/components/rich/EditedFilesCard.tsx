import { ChevronRight, Code2 } from 'lucide-react'
import { kortSti, type RedigeretFil } from '../../lib/redigeredeFiler'

/**
 * «Redigerede N filer» under Jarvis' besked — formen er Claude Codes egen.
 *
 * Bjørn 16/9-2026: «lav forløb under hans besked i chatview om til det på
 * billedet og kun vist hvis han har redigeret en fil eller flere … når man
 * klikker på dem åbner de i den changes panel du lige har lavet og viser diff».
 *
 * TALLENE ER IKKE ALTID DER, OG DET ER MED VILJE. `+166 −0` kommer fra
 * arbejdstræets diff mod HEAD — samme kilde som Ændringer-ruden. Tool-svarene
 * bærer `bytes_written` og `line_count`, men ikke hvad der blev tilføjet og
 * fjernet i forhold til det der stod før; de tal findes ingen steder pr.
 * redigering. Er filen allerede committet, står der derfor INTET tal frem for
 * et forkert et.
 */
export interface FilTal { added: number; removed: number }

export function EditedFilesCard({
  filer,
  tal,
  onAabn,
}: {
  filer: RedigeretFil[]
  /** sti → +/− fra arbejdstræet. Mangler en sti, vises intet tal for den. */
  tal?: Record<string, FilTal>
  /** Klik på en fil: åbn Ændringer-ruden med netop den fil foldet ud. */
  onAabn: (sti: string) => void
}) {
  if (filer.length === 0) return null
  const n = filer.length

  return (
    <div className="edited-files">
      <div className="edited-files-head">
        <span className="edited-files-titel">
          Redigerede {n} {n === 1 ? 'fil' : 'filer'}
        </span>
        <button type="button" className="edited-files-vis"
                onClick={() => onAabn(filer[0]!.path)}>
          Vis ændringer
        </button>
      </div>
      <ul className="edited-files-liste">
        {filer.map((f) => {
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
    </div>
  )
}
