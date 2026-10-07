/** Agentkontraktens Desk-projektion (agent-contract-v1 G) — datalag.
 *
 *  ÉN DB-projektion læses af tre flader: AgentInspector, Baggrundsjob-panelet og
 *  notifikationsfeedet. Ruterne (`/agents/contract/...`) er tynde adaptere over
 *  `core.services.agent_contract_projection`; ejeren er den indloggede bruger,
 *  aldrig et felt herfra — der findes derfor hverken ejer- eller sessionsfelt i
 *  nogen anmodning nedenfor.
 *
 *  FELTNAVNENE er pinnet i begge ender: backend-testen `test_agent_contract_view`
 *  fastlåser nøglerne i svaret, og `agentContractApi.test.ts` læser en fixture
 *  genereret fra den rigtige rute og tester at typerne herunder dækker præcis dem.
 *  Status afledes ALDRIG af tekst — `bucket` kommer færdig fra serveren.
 */
import { apiFetch, type ApiConfig } from './api'
import { StreamError } from './streamClient'

export type Bucket =
  | 'idle' | 'queued' | 'active' | 'settling' | 'retry_pending'
  | 'waiting_for_client' | 'waiting_for_approval' | 'waiting_for_budget' | 'outcome_unknown'
  | 'done' | 'failed' | 'timed_out' | 'cancelled' | 'unknown'

export interface ContractError { phase: string; code: string; reason: string }
export interface ContractRoute { route_source: string; provider: string; model: string }
export interface Heartbeat { at: string; state: 'ok' | 'expired' }

export interface ContractAgentRow {
  agent_id: string
  parent_agent_id: string
  role: string
  goal: string
  council_id: string
  children: number
  lifecycle_status: string
  target: string
  assignment_id: string
  assignment_status: string
  origin_session_id: string
  run_id: string
  run_status: string
  attempts: number
  bucket: Bucket
  attention: boolean
  reason: string
  error: ContractError | null
  started_at: string
  finished_at: string
  duration_s: number | null
  updated_at: string
  heartbeat: Heartbeat | null
  tokens: number
  /** null = ingen kørsel har meldt forbrug — «ingen data» er ikke «gratis». */
  cost_usd: number | null
  route: ContractRoute | null
  last_message: { direction: string; kind: string; at: string; text: string } | null
  summary: string
  pending_approvals: number
  /** agent_result_outbox.delivery_status — modellens claim, ikke brugerens kvittering. */
  model_claim: string
  read: boolean
  acknowledged: boolean
}

export interface ContractCounts {
  active: number; queued: number; waiting: number; blocked: number; attention: number; open: number
}

export interface ContractGroup {
  council_id: string
  members: { agent_id: string; role: string; bucket: Bucket }[]
  synthesis: { agent_id: string; bucket: Bucket } | null
  counts: ContractCounts
}

export interface ContractCapability { enabled: boolean; reason: string; contract_version: string }

export interface ContractOverview {
  status: 'ok'
  capability: ContractCapability
  agents: ContractAgentRow[]
  counts: ContractCounts
  groups: ContractGroup[]
  contract_version: string
}

export interface ContractAssignment {
  assignment_id: string; status: string; goal: string; expected_result: string; target: string
  deadline_at: string; operation: string; created_by: string; created_at: string; updated_at: string
  terminal_at: string
  budget: Record<string, unknown>
  outcome: { status: string; error_code: string; error_phase: string; summary: string; artifact_ref: string; artifact_error: string }
  routes: { attempt: number; route_source: string; provider: string; model: string; created_at: string }[]
}

export interface ContractRun {
  run_id: string; assignment_id: string; attempt_no: number; status: string; provider: string; model: string
  started_at: string; finished_at: string; input_tokens: number; output_tokens: number; cost_usd: number
  failure_reason: string; error_phase: string; error_code: string
}

export interface ContractMessage {
  message_id: string; direction: string; role: string; kind: string; content: string; created_at: string
}

export interface ContractToolCall {
  tool_call_id: string; run_id: string; tool_name: string; status: string; started_at: string; finished_at: string
}

export interface ContractApproval {
  approval_id: string; kind: string; status: string; agent_id: string; assignment_id: string; run_id: string
  parent_run_id: string; origin_session_id: string; target: string; tool_name: string; safe_view: string
  args_digest: string; risk_class: string; requested_by: string; created_at: string; expires_at: string
  decided_at: string; decided_by: string; decision_note: string
}

export interface ContractArtifact {
  assignment_id: string; run_id: string; name: string; size: number; status: string; attempt_no: number | null
}

export interface ContractDetail {
  status: 'ok'
  agent: ContractAgentRow
  assignments: ContractAssignment[]
  runs: ContractRun[]
  messages: ContractMessage[]
  tool_calls: ContractToolCall[]
  approvals: ContractApproval[]
  artifacts: ContractArtifact[]
  children: string[]
  capability: ContractCapability
  contract_version: string
}

export interface ContractReceipt {
  kind: 'message' | 'followup' | 'stop' | 'close'
  /** Serveren har taget imod anmodningen. */
  accepted: boolean
  /** ALTID false: bekræftelsen er den efterfølgende projektion (assignment `cancelled`, agent `closed`, …). */
  confirmed: boolean
  code: string
  state: string
  /** Kun for beskeder: levering til en igangværende tur er aldrig bevist ved accept. */
  delivered: boolean | null
}

export interface ActionResult {
  status: string
  agent_id?: string
  assignment_id?: string
  message_id?: string
  audit_id?: string
  receipt: ContractReceipt
  [key: string]: unknown
}

export interface FeedCard {
  ref_kind: 'agent' | 'approval'
  ref_id: string
  section: 'venter' | 'svar' | 'aktiv'
  bucket: Bucket | 'approval'
  agent_id: string
  assignment_id: string
  origin_session_id: string
  title: string
  reason: string
  summary: string
  error: ContractError | null
  updated_at: string
  created_at: string
  approval?: { approval_id: string; digest: string; risk_class: string; expires_at: string; tool_name: string; status: string }
  state: { read: boolean; acknowledged: boolean; model_claim: string; assignment_status: string }
  can_acknowledge: boolean
}

export interface ContractFeed {
  status: 'ok'
  cards: FeedCard[]
  counts: { venter: number; svar: number; aktiv: number; unread: number }
  contract_version: string
}

export interface ArtifactContent {
  status: string; ref: string; partial?: boolean; size?: number; offset?: number
  content?: string; truncated?: boolean; expired_at?: string
}

const BASE = '/agents/contract'
const enc = encodeURIComponent

export async function getKontraktOverblik(config: ApiConfig, scope: 'panel' | 'all' = 'panel'): Promise<ContractOverview> {
  return apiFetch(config, `${BASE}/overview?scope=${scope}`)
}

/** `null` = agenten er ikke en kontrakt-agent for denne bruger (404). Det er IKKE en fejl: en gammel
 *  scout-agent har ingen kontrakt, og inspectoren falder så tilbage til sin gamle visning. */
export async function getKontraktAgent(config: ApiConfig, agentId: string): Promise<ContractDetail | null> {
  try {
    // retries:0 — inspectoren poller selv, og et GET-forsøg der hænger må ikke holde den gamle visning tilbage
    return await apiFetch<ContractDetail>(config, `${BASE}/agents/${enc(agentId)}`, { retries: 0 })
  } catch (reason) {
    if (reason instanceof StreamError && reason.statusCode === 404) return null
    throw reason
  }
}

/** En handling serveren afviser med 403 betyder næsten altid «kontrakten er slukket» — ikke «log ind». Uden
 *  denne oversættelse står der bare «HTTP 403», og brugeren gætter. */
async function handling<T>(kald: Promise<T>): Promise<T> {
  try {
    return await kald
  } catch (reason) {
    if (reason instanceof StreamError && reason.statusCode === 403) {
      throw new Error('Afvist af serveren: agent-kontrakten er slukket, eller du har ikke ret til handlingen.')
    }
    if (reason instanceof StreamError && reason.statusCode === 404) {
      throw new Error('Agenten findes ikke for dig.')
    }
    throw reason
  }
}

export async function getKontraktFeed(config: ApiConfig): Promise<ContractFeed> {
  return apiFetch(config, `${BASE}/feed`)
}

export async function laesArtefakt(
  config: ApiConfig, agentId: string, runId: string, name: string, offset = 0,
): Promise<ArtifactContent> {
  return apiFetch(config, `${BASE}/agents/${enc(agentId)}/artifacts/${enc(runId)}/${enc(name)}?offset=${offset}`)
}

export async function kontraktBesked(config: ApiConfig, agentId: string, content: string): Promise<ActionResult> {
  return handling(apiFetch(config, `${BASE}/agents/${enc(agentId)}/message`, { method: 'POST', body: { content } }))
}

export async function kontraktOpfoelgning(
  config: ApiConfig, agentId: string, goal: string, idempotencyKey: string,
): Promise<ActionResult> {
  return handling(apiFetch(config, `${BASE}/agents/${enc(agentId)}/followup`,
    { method: 'POST', body: { goal, idempotency_key: idempotencyKey } }))
}

export async function kontraktStop(config: ApiConfig, agentId: string): Promise<ActionResult> {
  return handling(apiFetch(config, `${BASE}/agents/${enc(agentId)}/stop`, { method: 'POST', body: {} }))
}

export async function kontraktLuk(config: ApiConfig, agentId: string): Promise<ActionResult> {
  return handling(apiFetch(config, `${BASE}/agents/${enc(agentId)}/close`, { method: 'POST', body: {} }))
}

export async function markerKontraktLaest(config: ApiConfig, refKind: string, refId: string): Promise<{ read: boolean }> {
  return apiFetch(config, `${BASE}/feed/${enc(refKind)}/${enc(refId)}/read`, { method: 'POST', body: {} })
}

export async function kvitterKontrakt(config: ApiConfig, assignmentId: string): Promise<{ acknowledged: boolean }> {
  return apiFetch(config, `${BASE}/assignments/${enc(assignmentId)}/acknowledge`, { method: 'POST', body: {} })
}

/** Approval-afgørelsen går over den EKSISTERENDE rute (`/agents/approvals`): kun et menneske, og en
 *  godkendelse kræver totrinskoden hvis brugeren har sat en op. Digest'en binder afgørelsen til
 *  netop dette kald — er argumenterne ændret, afvises den og en ny approval kræves. */
export async function afgoerAgentApproval(
  config: ApiConfig, approvalId: string, decision: 'approve' | 'deny', digest: string, kode = '',
): Promise<{ status: string; approval: { status: string } }> {
  try {
    return await apiFetch(config, `/agents/approvals/${enc(approvalId)}/decision`,
      { method: 'POST', body: { decision, digest, kode } })
  } catch (reason) {
    const code = reason instanceof StreamError ? reason.statusCode : null
    if (code === 403) throw new Error('Afvist: forkert eller manglende totrinskode, eller du må ikke afgøre den.')
    if (code === 410) throw new Error('Godkendelsen er udløbet.')
    if (code === 409) throw new Error('Godkendelsen er allerede afgjort.')
    if (code === 404) throw new Error('Godkendelsen passer ikke længere (ændret handling) eller findes ikke.')
    throw reason
  }
}

// ── Visning ──────────────────────────────────────────────────────────────

const LABEL: Record<string, string> = {
  idle: 'Ledig', queued: 'I kø', active: 'Kører', settling: 'Afslutter', retry_pending: 'Nyt forsøg afventer',
  waiting_for_client: 'Venter på klient', waiting_for_approval: 'Venter på godkendelse',
  waiting_for_budget: 'Venter på budget', outcome_unknown: 'Udfald ukendt', done: 'Færdig',
  failed: 'Fejlet', timed_out: 'Tidsfrist udløbet', cancelled: 'Afbrudt', unknown: 'Ukendt tilstand',
  approval: 'Godkendelse',
}

export function bucketLabel(bucket: string): string {
  return LABEL[bucket] ?? bucket
}

/** Kører eller er på vej — det der tæller som «aktivt». Opmærksomhed er et ANDET tal. */
export const AKTIVE_BUCKETS: readonly string[] = ['active', 'settling', 'retry_pending']

export function erKontraktAktiv(bucket: string): boolean {
  return AKTIVE_BUCKETS.includes(bucket)
}

/** Et åbent run (ikke terminalt) — kan stoppes. */
export function erKontraktAaben(row: Pick<ContractAgentRow, 'assignment_status'>): boolean {
  return ['queued', 'active', 'waiting'].includes(row.assignment_status)
}

export function kontraktVarighed(sekunder: number | null | undefined): string {
  if (sekunder === null || sekunder === undefined) return ''
  const s = Math.max(0, Math.floor(sekunder))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (t) return `${t}t ${m}m`
  if (m) return `${m}m ${s % 60}s`
  return `${s}s`
}

/** Kvitteringen i klartekst. Accept er ikke levering og ikke stop — det står der. */
export function kvitteringTekst(r: ContractReceipt): string {
  if (!r.accepted) return 'Serveren afviste anmodningen.'
  switch (r.kind) {
    case 'message': return 'Beskeden er accepteret og gemt til agentens næste tur. Levering er ikke bekræftet.'
    case 'stop': return 'Stop er anmodet. Agenten er ikke bekræftet stoppet endnu.'
    case 'close': return 'Lukning er accepteret. Agenten afslutter sit igangværende arbejde først.'
    default: return 'Opfølgningen er accepteret som en ny opgave. Resultatet er ikke bekræftet.'
  }
}
