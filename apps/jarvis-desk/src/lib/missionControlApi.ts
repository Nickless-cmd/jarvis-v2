/** Mission Control datalag — fetchers mod Centralen (/central/*).
 *  Desk-MC beholdes, men henter nu fra Centralen i stedet for /mc/*. Interfacene er
 *  uændrede: /central-svarene mappes ind i de eksisterende former så de forbrugende
 *  komponenter (RunsTable/AgentRoster/CostPanel/EventStream) er urørte.
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
  const r = await apiFetch<{ runs?: McRun[]; count?: number; failed_count?: number }>(
    config,
    `/central/runs?limit=${limit}`,
  )
  const recent = r.runs ?? []
  return {
    active_run: null,
    last_outcome: null,
    recent_runs: recent,
    summary: {
      active: false,
      recent_count: r.count ?? recent.length,
      failed_count: r.failed_count ?? 0,
    },
  }
}

export interface McRunStep { kind: string; at?: string; summary?: string; tool?: string }
export interface McRunDetail { run: McRun | null; found: boolean; steps: McRunStep[] }

export async function getMcRunDetail(config: ApiConfig, runId: string): Promise<McRunDetail> {
  const r = await apiFetch<{ run?: McRun | null; found?: boolean }>(
    config,
    `/central/runs/${encodeURIComponent(runId)}`,
  )
  // /central leverer ingen steps — hold komponenterne robuste med tom liste.
  return { run: r.run ?? null, found: r.found ?? false, steps: [] }
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
  const r = await apiFetch<{ agents?: McAgent[]; count?: number }>(
    config,
    `/central/agents?limit=${limit}`,
  )
  const agents = r.agents ?? []
  // /central leverer ingen summary — beregn den defensivt fra agents-arrayet.
  const active_count = agents.filter((a) => a.status === 'active').length
  const completed_count = agents.filter((a) => a.status === 'completed').length
  const failed_count = agents.filter(
    (a) => a.status === 'failed' || a.status === 'cancelled',
  ).length
  const token_burn_total = agents.reduce((sum, a) => sum + (a.tokens_burned ?? 0), 0)
  return {
    agents,
    summary: {
      agent_count: r.count ?? agents.length,
      active_count,
      completed_count,
      failed_count,
      token_burn_total,
    },
  }
}

export interface McScheduledTask {
  task_id: string
  focus?: string
  run_at?: string
  status?: string
  source?: string
}

export async function getMcScheduledTasks(config: ApiConfig, limit = 20): Promise<McScheduledTask[]> {
  const r = await apiFetch<{ tasks?: McScheduledTask[] }>(
    config,
    `/central/queues/scheduled?limit=${limit}`,
  )
  return r.tasks ?? []
}

/** Faktisk form fra ledger.daily_cost_summary: én række pr. dag PR. lane. */
export interface McDailyCost {
  day?: string
  lane?: string
  calls?: number
  total_tokens?: number
  total_cost?: number
}

export async function getMcCostsDaily(config: ApiConfig, _days = 30): Promise<McDailyCost[]> {
  const r = await apiFetch<{ days?: McDailyCost[] }>(config, `/central/costs-daily`)
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
  const r = await apiFetch<{ items?: McEvent[] }>(config, `/central/events${q}`)
  return r.items ?? []
}

export interface McOverview {
  ok?: boolean
  events?: number
  total_cost_usd?: number
  visible_execution?: unknown
}

export async function getMcOverviewSafe(config: ApiConfig): Promise<McOverview> {
  // /central/overview findes ikke — byg et blødt overblik fra costs-daily.
  // Kaldet er wrappet i catch hos forbrugeren; hold det minimalt og robust.
  const r = await apiFetch<{ today_cost?: number }>(config, '/central/costs-daily')
  return {
    ok: true,
    events: 0,
    total_cost_usd: r.today_cost ?? 0,
    visible_execution: undefined,
  }
}
