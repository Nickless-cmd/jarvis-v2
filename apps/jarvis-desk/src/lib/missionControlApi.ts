/** Mission Control datalag — fetchers mod de eksisterende /mc/*-endpoints (+ de 3 nye).
 *  Eget modul (ikke i api.ts) så det store api.ts ikke vokser. Løse defensive typer:
 *  backend-formerne er kendt, men UI'et skal aldrig vælte på et manglende felt. */
import { apiFetch, type ApiConfig } from './api'

export interface McRun {
  run_id: string
  lane?: string
  provider?: string
  model?: string
  status?: string
  started_at?: string
  finished_at?: string
  text_preview?: string
  error?: string | null
  capability_id?: string | null
}

export interface McRunsResponse {
  active_run?: { run_id?: string; status?: string } | null
  last_outcome?: unknown
  recent_runs: McRun[]
  summary?: { active: boolean; recent_count: number; failed_count: number }
}

export async function getMcRuns(config: ApiConfig, limit = 20): Promise<McRunsResponse> {
  const r = await apiFetch<McRunsResponse>(config, `/mc/runs?limit=${limit}`)
  return { ...r, recent_runs: r.recent_runs ?? [] }
}

export interface McRunStep { kind: string; at?: string; summary?: string; tool?: string }
export interface McRunDetail { run: McRun | null; found: boolean; steps: McRunStep[] }

export async function getMcRunDetail(config: ApiConfig, runId: string): Promise<McRunDetail> {
  const r = await apiFetch<McRunDetail>(config, `/mc/runs/${encodeURIComponent(runId)}`)
  return { ...r, run: r.run ?? null, found: r.found ?? false, steps: r.steps ?? [] }
}

export interface McAgent {
  agent_id: string
  name?: string
  role?: string
  kind?: string
  status?: string
  goal?: string
  tokens_burned?: number
  message_count?: number
  run_count?: number
  tool_call_count?: number
  last_activity?: string | null
}

export interface McAgentsResponse {
  agents: McAgent[]
  summary?: {
    agent_count?: number
    active_count?: number
    completed_count?: number
    failed_count?: number
    token_burn_total?: number
  }
}

export async function getMcAgents(config: ApiConfig, limit = 100): Promise<McAgentsResponse> {
  const r = await apiFetch<McAgentsResponse>(config, `/mc/agents?limit=${limit}`)
  return { ...r, agents: r.agents ?? [] }
}

export interface McScheduledTask {
  task_id: string
  focus?: string
  run_at?: string
  status?: string
  source?: string
}

export async function getMcScheduledTasks(config: ApiConfig, limit = 20): Promise<McScheduledTask[]> {
  const r = await apiFetch<{ items?: McScheduledTask[] }>(config, `/mc/scheduled-tasks?limit=${limit}`)
  return r.items ?? []
}

/** Faktisk form fra ledger.daily_cost_summary: én række pr. dag PR. lane. */
export interface McDailyCost {
  day?: string
  lane?: string
  calls?: number
  total_tokens?: number
  total_cost?: number
}

export async function getMcCostsDaily(config: ApiConfig, days = 30): Promise<McDailyCost[]> {
  const r = await apiFetch<{ days?: McDailyCost[] }>(config, `/mc/costs/daily?days=${days}`)
  return r.days ?? []
}

export interface McEvent {
  id?: number
  kind?: string
  family?: string
  payload?: Record<string, unknown>
  created_at?: string
}

export async function getMcEvents(config: ApiConfig, limit = 50, family?: string): Promise<McEvent[]> {
  const q = family ? `?limit=${limit}&family=${encodeURIComponent(family)}` : `?limit=${limit}`
  const r = await apiFetch<{ items?: McEvent[] }>(config, `/mc/events${q}`)
  return r.items ?? []
}

export interface McOverview {
  ok?: boolean
  events?: number
  total_cost_usd?: number
  visible_execution?: unknown
}

export async function getMcOverviewSafe(config: ApiConfig): Promise<McOverview> {
  return apiFetch<McOverview>(config, '/mc/overview')
}
