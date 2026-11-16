import type { ChatMessage } from './api'

/** Bærer rækken den godkendelse der venter LIGE NU?
 *
 *  31/10-2026. DEL 3 flyttede godkendelses-kortet ind i transcriptet som en
 *  `approval_request`-række. Rækken er ikke garanteret til stede: den hentes af
 *  `refreshMessages` (op til 1,5 s forsinkelse), og godkendelser der ikke går
 *  gennem `_publicer_approval_requested` bliver slet ikke persisteret.
 *
 *  16/11-2026 — HVAD FUNKTIONEN IKKE LÆNGERE ER. Den var engang gaten der
 *  afgjorde hvilken af to flader der skulle vise godkendelsen. Den gate er
 *  væk: kortet over composeren vises ALTID naar der venter en godkendelse, og
 *  rækken er ren historik uden knapper (Bjørn: «hver gang der kommer en skal
 *  jeg scrolle til toppen af din tur for at godkende!»).
 *
 *  Tilbage er ét ærligt brug: `medVentendeGodkendelse` må ikke flette en
 *  dublet-række ind når den rigtige række allerede findes. Det er dét, og ikke
 *  mere, denne funktion afgør nu.
 *
 *  Match på `approval_id`, aldrig på tekst: to godkendelser kan have samme
 *  kommando, og et tekst-match ville pege på den forkerte række.
 */
export function findesGodkendelseIRækken(
  raekker: ReadonlyArray<{ role: string; content_json?: unknown }>,
  approvalId: string | null | undefined,
): boolean {
  if (!approvalId) return false
  return raekker.some((m) => {
    if (m.role !== 'approval_request') return false
    const liste = Array.isArray(m.content_json) ? m.content_json : []
    const blok = liste[0] as { approval_id?: unknown } | undefined
    return String(blok?.approval_id ?? '') === approvalId
  })
}

/** Den hentede, ventende godkendelse — kun de felter projektionen behøver. */
export interface VentendeKort {
  approvalId: string
  tool: string
  action: string
  sessionId?: string
}

/** Flet den HENTEDE ventende godkendelse ind i beskedlisten som en
 *  `approval_request`-række (16/11-2026).
 *
 *  MÅLT: kortet manglede ikke, men stod i `.composer-notices` — «oven på
 *  turen» — så længe den persisterede række ikke fandt vej. Persisteringen er
 *  bevidst fail-open (`approval_runtime` kan returnere None), og
 *  `refreshMessages` halter op til 1,5 s efter en genstart. `StreamContext`
 *  poller `/chat/approvals/pending` og HAR altså svaret; det blev bare aldrig
 *  til en række.
 *
 *  Rækken lægges SIDST: en afventende godkendelse hører til den tur der kører
 *  nu, og `fletGodkendelser` lader en række uden efterfølgende assistent blive
 *  stående som selvstændig — samme sted som en persisteret række ville stå.
 *  Kør denne FØR `fletGodkendelser`.
 *
 *  Dublet-regel: findes der allerede en række med samme `approval_id`
 *  (persisteret, uanset status) gør vi INTET — den rigtige række vinder.
 *  Hører kortet til en anden session end den åbne, røres listen heller ikke;
 *  så bærer det flydende kort det som før. Afgøres godkendelsen, bliver
 *  `pending` null og rækken er væk igen. */
export function medVentendeGodkendelse<T extends ChatMessage>(
  beskeder: readonly T[],
  ventende: VentendeKort | null | undefined,
  sessionId: string | null | undefined,
): readonly T[] {
  if (!ventende?.approvalId) return beskeder
  if (ventende.sessionId && sessionId && ventende.sessionId !== sessionId) return beskeder
  if (findesGodkendelseIRækken(beskeder, ventende.approvalId)) return beskeder
  const raekke = {
    id: `pending-approval-${ventende.approvalId}`,
    role: 'approval_request',
    content: [],
    content_json: [{
      approval_id: ventende.approvalId,
      tool: ventende.tool,
      action: ventende.action,
      status: 'pending',
    }],
    created_at: new Date().toISOString(),
  } as unknown as T
  return [...beskeder, raekke]
}

/** Hvor mange tomme svar i træk der skal til før et holdt kort regnes for afgjort. */
export const TOMME_SVAR_FOER_RYD = 2

export type AfstemHandling = 'behold' | 'skift' | 'ryd'

/** Afstem det kort klienten HOLDER mod hvad serveren siger venter.
 *
 *  12/11-2026. Opsamlingen holdt op med at spørge så snart klienten havde et
 *  kort, og kortet ryddes ellers kun af message_stop, nyt send, eget klik eller
 *  udløb (3600 s). Blev det afgjort et andet sted — notifikations-feedet,
 *  telefonen — blev det stående og blokerede opsamlingen af alle de næste.
 *  Målt: 19 godkendelser på 12 minutter, alle afgjort i feedet.
 *
 *  `tool`-opsamlingen kender kun tool-kort, så et AGENT-kort lader vi være: en
 *  tom tool-liste siger intet om det.
 *
 *  Et tomt svar er tvetydigt (`hentVentendeGodkendelseOveralt` svarer også
 *  `null` på en netværksfejl), så ét tomt svar rydder ikke — der skal to i
 *  træk. Rydder vi forkert, finder næste poll kortet igen.
 */
export function afstemVentendeGodkendelse(
  holdt: { approvalId: string; kind?: 'tool' | 'agent' } | null,
  fundet: { approvalId: string } | null,
  tommeISnor: number,
): { handling: AfstemHandling; tommeISnor: number } {
  if (!holdt) return { handling: fundet ? 'skift' : 'behold', tommeISnor: 0 }
  if (holdt.kind === 'agent') return { handling: 'behold', tommeISnor: 0 }
  if (fundet) {
    return fundet.approvalId === holdt.approvalId
      ? { handling: 'behold', tommeISnor: 0 }
      : { handling: 'skift', tommeISnor: 0 }
  }
  const n = tommeISnor + 1
  return n >= TOMME_SVAR_FOER_RYD
    ? { handling: 'ryd', tommeISnor: 0 }
    : { handling: 'behold', tommeISnor: n }
}
