/**
 * Mission-control-typer — Arbejde-rummet (V2 fase 1).
 *
 * Typerne er skrevet mod serverens FAKTISKE svar (målt live 2026-09-02), ikke
 * mod spec-teksten. Det er bevidst: en spec beskriver hvad der var meningen,
 * en måling beskriver hvad appen faktisk får.
 */

/** En kørsel som mission-control kender den (`/mc/runs`). */
export interface McRun {
  run_id: string
  lane: string
  provider: string | null
  model: string | null
  status: string
  started_at: string
  finished_at: string | null
  text_preview: string | null
}

export interface McRunsResponse {
  active_run: McRun | null
  last_outcome: McRun | null
  recent_runs: McRun[]
  summary: { active: boolean; recent_count: number; failed_count: number }
}

/**
 * Runtime har TO godkendelsessystemer, og de deler kun en fælles konvolut.
 * `approval_system` er diskriminanten — brug den, aldrig feltnavne-gætteri.
 */
export type ApprovalSystem = 'capability' | 'tool-intent'

/** Status som serveren beregner den. `stale`/`expired` er IKKE handlingsbare. */
export type ApprovalStatus = 'pending' | 'approved' | 'executed' | 'stale' | 'expired' | string

interface ApprovalEnvelope {
  request_id: string
  approval_system: ApprovalSystem
  status: ApprovalStatus
  /** Serverens dom: kan der stadig handles på den? */
  active: boolean
  /** Vinduet er løbet fra den (tool-intent) eller forslaget er forældet (capability). */
  stale: boolean
  requested_at: string
  initiated_by: string | null
  scheduled_for_user_id: string | null
}

export interface CapabilityApproval extends ApprovalEnvelope {
  approval_system: 'capability'
  capability_id: string
  capability_name: string
  capability_kind: string
  execution_mode: string
  approval_policy: string
  run_id: string | null
  proposal_target_path: string | null
  proposal_content: string | null
  proposal_content_summary: string | null
  proposal_reason: string | null
  approved_at: string | null
  executed: number | boolean
  executed_at: string | null
}

export interface ToolIntentApproval extends ApprovalEnvelope {
  approval_system: 'tool-intent'
  approval_id: string
  intent_key: string
  intent_type: string
  intent_target: string | null
  approval_scope: string
  approval_state: string
  approval_reason: string | null
  /** Kun tool-intent har et vindue der lukker (15 min). */
  expires_at: string | null
  execution_state: string | null
}

export type Approval = CapabilityApproval | ToolIntentApproval

export interface McApprovalsResponse {
  requests: Approval[]
  summary: { pending_count: number; approved_count: number; request_count: number }
}

export function isCapability(a: Approval): a is CapabilityApproval {
  return a.approval_system === 'capability'
}

export function isToolIntent(a: Approval): a is ToolIntentApproval {
  return a.approval_system === 'tool-intent'
}

/**
 * Kan brugeren handle på kortet?
 *
 * Serveren svarer 409 på en udløbet tool-intent — det er præcis den døde-kort-
 * oplevelse Arbejde-rummet skal fjerne, så vi filtrerer FØR knappen vises,
 * ikke bagefter i en fejlbesked.
 */
export function isActionable(a: Approval): boolean {
  return a.active === true && a.stale !== true
}

/** Én tekstlinje der beskriver hvad der bedes om — uanset system. */
export function approvalTitle(a: Approval): string {
  if (isCapability(a)) return a.capability_name || a.capability_id || 'Ukendt handling'
  return a.intent_type || 'Ukendt hensigt'
}

/** Den forklarende anledningstekst (R8-mønsteret). */
export function approvalReason(a: Approval): string {
  const raw = isCapability(a) ? a.proposal_reason : a.approval_reason
  return (raw ?? '').trim()
}

/** Selve det konkrete — kommandoen, stien eller målet. */
export function approvalDetail(a: Approval): string {
  if (isCapability(a)) {
    const s = (a.proposal_content_summary ?? '').trim()
    if (s) return s
    const c = (a.proposal_content ?? '').trim()
    if (c) return c
    return (a.proposal_target_path ?? '').trim()
  }
  return (a.intent_target ?? '').trim()
}

/** Etiketten over detaljen — «Kommandoudførelse» hos OpenAI. */
export function approvalTag(a: Approval): string {
  return isCapability(a) ? a.execution_mode : a.approval_scope
}
