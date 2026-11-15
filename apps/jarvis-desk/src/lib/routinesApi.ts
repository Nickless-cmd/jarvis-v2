import { apiFetch, type ApiConfig } from './api'

export type RoutineStatus = 'draft' | 'active' | 'paused' | 'stopped' | 'archived' | 'deleted'
export type RoutineAccessScope = 'user_private' | 'system_owner'
export type RoutineTriggerKind = 'manual' | 'schedule' | 'interval' | 'event' | 'system'
export type RoutineCapabilityScope = 'chat' | 'code' | 'system'

export interface Routine {
  routine_id: string
  owner_user_id: string
  canonical_owner_user_id?: string
  access_scope: RoutineAccessScope
  name: string
  instruction: string
  capability_scope: RoutineCapabilityScope
  trigger_kind: RoutineTriggerKind
  trigger_config: Record<string, unknown>
  permission_policy: Record<string, unknown>
  delivery_policy: Record<string, unknown>
  inbox_policy: Record<string, unknown>
  retention_policy: Record<string, unknown>
  failure_policy: Record<string, unknown>
  jarvis_restart_allowed: boolean
  status: RoutineStatus
  version: number
  created_at: string
  updated_at: string
  stopped_at?: string | null
  archived_at?: string | null
}

export interface RoutineRun {
  run_id: string
  routine_id: string
  owner_user_id?: string
  access_scope?: RoutineAccessScope
  routine_version?: number
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelling' | 'cancelled' | 'skipped'
  created_at: string
  /** Det samlede svar, dekrypteret af serveren. Findes kun på GET /runs/{id}. */
  result?: string | null
  diagnostic_code?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export interface RoutineEvent {
  event_id: string
  run_id?: string
  seq?: number
  kind: string
  payload?: Record<string, unknown>
  terminal?: number | boolean
  created_at: string
  [key: string]: unknown
}

export interface RoutineDraft {
  name: string
  instruction: string
  capability_scope: RoutineCapabilityScope
  trigger_kind: RoutineTriggerKind
  trigger_config?: Record<string, unknown>
  permission_policy?: Record<string, unknown>
  delivery_policy?: Record<string, unknown>
  inbox_policy?: Record<string, unknown>
  retention_policy?: Record<string, unknown>
  failure_policy?: Record<string, unknown>
  access_scope?: RoutineAccessScope
  jarvis_restart_allowed?: boolean
}

export type RoutinePatch = Partial<RoutineDraft>
export type RoutineAction = 'pause' | 'resume' | 'stop' | 'restart' | 'archive' | 'restore'

export const listRoutines = (config: ApiConfig) =>
  apiFetch<Routine[]>(config, '/api/routines')

export const createRoutine = (config: ApiConfig, draft: RoutineDraft) =>
  apiFetch<Routine>(config, '/api/routines', { method: 'POST', body: draft })

export const updateRoutine = (config: ApiConfig, routineId: string, expectedVersion: number, patch: RoutinePatch) =>
  apiFetch<Routine>(config, `/api/routines/${encodeURIComponent(routineId)}`, {
    method: 'PATCH', body: { expected_version: expectedVersion, ...patch },
  })

export const deleteRoutine = (config: ApiConfig, routineId: string) =>
  apiFetch<{ deleted: boolean }>(config, `/api/routines/${encodeURIComponent(routineId)}`, { method: 'DELETE' })

export const routineAction = (config: ApiConfig, routineId: string, action: RoutineAction) =>
  apiFetch<Routine>(config, `/api/routines/${encodeURIComponent(routineId)}/actions/${action}`, { method: 'POST' })

export const runRoutine = (config: ApiConfig, routineId: string) =>
  apiFetch<RoutineRun>(config, `/api/routines/${encodeURIComponent(routineId)}/runs`, { method: 'POST', body: {} })

export const listRoutineRuns = (config: ApiConfig, routineId: string) =>
  apiFetch<RoutineRun[]>(config, `/api/routines/${encodeURIComponent(routineId)}/runs`)

/**
 * Ét run MED resultatet. `listRoutineRuns` læser `list_runs` i db-laget, som
 * ikke dekrypterer — så listen bærer aldrig `result`. Kun dette kald giver
 * det svar rutinen faktisk leverede.
 */
export const getRoutineRun = (config: ApiConfig, runId: string) =>
  apiFetch<RoutineRun>(config, `/api/routines/runs/${encodeURIComponent(runId)}`)

export const listRoutineEvents = (config: ApiConfig, runId: string) =>
  apiFetch<RoutineEvent[]>(config, `/api/routines/runs/${encodeURIComponent(runId)}/events`)

export const cancelRoutineRun = (config: ApiConfig, runId: string) =>
  apiFetch<RoutineRun>(config, `/api/routines/runs/${encodeURIComponent(runId)}/cancel`, { method: 'POST' })

/** En system-rutines arbejde ligger i autonome sessioner, ikke i `routine_runs`.
 *  «System · heartbeat» har nul kørsler men 672 beskeder i `auto-heartbeat-…`.
 *  Uden dette opslag står dens Kørsler-fane tom (målt 15/11-2026). */
export const listOriginSessions = (config: ApiConfig, routineId: string) =>
  apiFetch<{ session_id: string; title: string; updated_at: string }[]>(
    config,
    `/api/routines/${encodeURIComponent(routineId)}/origin-sessions`,
  )

/** Rutinens samtale — hvor man SER hvad den gjorde, og kan svare den.
 *
 *  Personlige rutiner får deres egen session (`routine-{id}`); system-rutiner
 *  peger på den nyeste autonome session, fordi det er dér deres arbejde faktisk
 *  ligger (målt 15/11-2026: nul `routine_runs` for dream/heartbeat/wakeup). */
export const getRoutineChatSession = (config: ApiConfig, routineId: string) =>
  apiFetch<{ session_id: string; title: string; kind: 'routine' | 'origin' }>(
    config, `/api/routines/${encodeURIComponent(routineId)}/chat-session`,
  )

/** Send en besked i rutinens samtale.
 *
 *  Går gennem samme stream-endpoint som chat-fladen, så svaret er et rigtigt
 *  visible-run i netop denne session — men uden at røre `SessionContext`, hvis
 *  `select()` ville kapre den samtale man sad i. SSE'en læses ikke: vi venter
 *  til strømmen lukker og henter så sessionen igen. */
export async function sendRoutineMessage(
  config: ApiConfig, sessionId: string, message: string,
): Promise<void> {
  const res = await fetch(`${config.apiBaseUrl}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
    },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) throw new Error(`Kunne ikke sende beskeden (HTTP ${res.status})`)
  // Læs strømmen til ende: først da er svaret persisteret på serveren.
  await res.text()
}
