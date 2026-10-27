import type { Artifact } from './artifacts'
import type { AgentReference, SourceEvidence, ToolEvidence } from './environmentEvidence'

export type InspectorTarget =
  | { type: 'artifact'; artifact: Artifact }
  | { type: 'agent'; agent: AgentReference; canMessage: boolean }
  | { type: 'source'; source: SourceEvidence; tool?: ToolEvidence }
  | { type: 'tool'; tool: ToolEvidence }
  | { type: 'file'; file: FilReference }
  | { type: 'dok'; dok: DokReference }

/** Svaret fra en af de tre Google-læsere, som en flade man kan læse.
 *
 * Baggrund (Bjørn 27/10-2026): «tag de 3 osse» — efter at fil-preview'et var
 * bygget stod `docs_read`, `sheets_read` og `slides_read` stadig tilbage med
 * rå JSON i tool-kortet. Et regneark kan man ikke se formen på som JSON.
 *
 * Referencen bærer den RÅ streng, ikke et parset objekt: værktøjssvar er
 * tekst hele vejen gennem samtalen, og tolkningen skal bo ét sted
 * (`lib/dokFlade.ts`), ikke deles mellem ToolCard og panelet.
 */
export interface DokReference {
  /** `docs_read` · `sheets_read` · `slides_read` — afgør hvordan der tolkes. */
  vaerktoej: string
  /** Det FULDE svar. Det afkortede i samtalen kan være klippet midt i JSON. */
  resultat: string
}

/** En fil Bjørn kan SE i panelet — ikke kun hente.
 *
 * Baggrund (Bjørn 27/10-2026): «mangler vi visningsflader i desk for de
 * fleste af disse ting?» En PDF eller et regneark var indtil da et
 * download-kort: man kunne hente den, ikke kigge på den. Panelet kendte
 * fire mål — agent, kilde, værktøj, artefakt — og ingen fil.
 */
export interface FilReference {
  navn: string
  /** `/files/{navn}` (udgivet) eller `/attachments/...` (upload). */
  url?: string
  attachment_id?: string
  mime_type?: string
  size_bytes?: number
}
