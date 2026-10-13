import { apiFetch, type ApiConfig } from './api'

export type RoutineStatus = 'draft' | 'active' | 'paused' | 'stopped' | 'archived' | 'deleted'
export type RoutineAccessScope = 'user_private' | 'system_owner'
export type RoutineTriggerKind = 'manual' | 'schedule' | 'interval' | 'event' | 'system'
export type RoutineCapabilityScope = 'chat' | 'code' | 'system'

export interface Routine {
  routine_id: string
  owner_user_id: string
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

export const listRoutineEvents = (config: ApiConfig, runId: string) =>
  apiFetch<RoutineEvent[]>(config, `/api/routines/runs/${encodeURIComponent(runId)}/events`)

export const cancelRoutineRun = (config: ApiConfig, runId: string) =>
  apiFetch<RoutineRun>(config, `/api/routines/runs/${encodeURIComponent(runId)}/cancel`, { method: 'POST' })
