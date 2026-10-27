import { FileText, LayoutList, Table2 } from 'lucide-react'
import { dokFraResultat, type DokFlade } from '../../lib/dokFlade'
import type { DokReference } from '../../lib/inspectorTargets'

/**
 * De tre Google-læseres svar som en flade man kan LÆSE — ikke rå JSON.
 *
 * ## Hvorfor den findes
 *
 * 27/10-2026 byggede jeg `drive_download` og et fil-preview, og skrev selv i
 * svaret til Bjørn at `sheets_read`, `docs_read` og `slides_read` stadig kun
 * returnerede tekst. Han svarede «tag de 3 osse». Det er denne fil.
 *
 * Forskellen er ikke kosmetisk: et regneark der kommer tilbage som
 * `{"values": [["Navn","Alder"],["Bo","41"]]}` kan man ikke se formen på.
 * Som tabel kan man.
 *
 * ## Hvorfor den parser i stedet for at få et objekt
 *
 * Værktøjssvaret er en streng hele vejen gennem samtalen — også når det er
 * JSON. Panelet får derfor den RÅ streng og tolker den selv, så der kun er ét
 * sted der kender formen (`lib/dokFlade.ts`). Alternativet var at parse i
 * ToolCard og sende et objekt videre, men så ville to steder dele meningen om
 * hvad et gyldigt svar er.
 */
export function DokPreview({ dok }: { dok: DokReference }) {
  const flade = dokFraResultat(dok.vaerktoej, dok.resultat)

  if (!flade) {
    // Ærligt udfald: vi ved at værktøjet HAR en flade (ellers var knappen ikke
    // vist), men svaret kunne ikke tolkes. Det kan ske hvis svaret blev
    // klippet, eller hvis Google svarede i en form vi ikke kender. En tom rude
    // ville se ud som en fejl i dokumentet i stedet for i tolkningen.
    return (
      <div className="artifact-body artifact-empty">
        Svaret fra {dok.vaerktoej} kunne ikke læses som et dokument.
      </div>
    )
  }

  if (flade.kind === 'docs') return <DokumentFlade flade={flade} />
  if (flade.kind === 'sheets') return <RegnearkFlade flade={flade} />
  return <PraesentationFlade flade={flade} />
}

function DokumentFlade({ flade }: { flade: Extract<DokFlade, { kind: 'docs' }> }) {
  return (
    <div className="artifact-body dok-flade">
      <div className="dok-hoved">
        <FileText size={14} />
        <span className="dok-titel">{flade.titel || 'Dokument'}</span>
      </div>
      {/* `white-space: pre-wrap` i CSS: et Docs-dokument har afsnit, og dem
          skal man kunne se. Teksten er ren tekst fra Googles API — den skal
          IKKE parses som markdown, så den vises i et <pre> og ikke i
          MarkdownRenderer. */}
      <pre className="dok-tekst">{flade.tekst}</pre>
    </div>
  )
}

function RegnearkFlade({ flade }: { flade: Extract<DokFlade, { kind: 'sheets' }> }) {
  // Første række vises som overskrift. Det er en LÆSEKONVENTION, ikke en
  // påstand om at arket har en header — Google Sheets har ikke begrebet. Den
  // gør en tabel med navne og tal læsbar, og koster intet hvis rækken ikke er
  // en header.
  const [hoved, ...resten] = flade.raekker
  return (
    <div className="artifact-body dok-flade">
      <div className="dok-hoved">
        <Table2 size={14} />
        <span className="dok-titel">{flade.interval || 'Regneark'}</span>
        <span className="dok-meta">{flade.raekker.length} rækker</span>
      </div>
      <div className="dok-tabel-ramme">
        <table className="dok-tabel">
          <thead>
            <tr>
              {(hoved ?? []).map((c, i) => (
                <th key={i}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {resten.map((r, ri) => (
              <tr key={ri}>
                {r.map((c, ci) => (
                  <td key={ci}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PraesentationFlade({ flade }: { flade: Extract<DokFlade, { kind: 'slides' }> }) {
  return (
    <div className="artifact-body dok-flade">
      <div className="dok-hoved">
        <LayoutList size={14} />
        <span className="dok-titel">{flade.titel || 'Præsentation'}</span>
        <span className="dok-meta">{flade.antal} slides</span>
      </div>
      {flade.slides.map((s) => (
        <div className="dok-slide" key={s.nr}>
          <div className="dok-slide-nr">{s.nr}</div>
          <div className="dok-slide-tekst">{s.tekst || <em>uden tekst</em>}</div>
        </div>
      ))}
    </div>
  )
}
