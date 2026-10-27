import type { Artifact } from './artifacts'
import type { AgentReference, SourceEvidence, ToolEvidence } from './environmentEvidence'

export type InspectorTarget =
  | { type: 'artifact'; artifact: Artifact }
  | { type: 'agent'; agent: AgentReference; canMessage: boolean }
  | { type: 'source'; source: SourceEvidence; tool?: ToolEvidence }
  | { type: 'tool'; tool: ToolEvidence }
  | { type: 'file'; file: FilReference }

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
