/** Agent pool — datalag for owner-fladen.
 *
 *  To slags kald, og forskellen betyder noget for hastigheden:
 *
 *    /mc/agent-pool        LET liste, ét opslag, filtrerbar og sideinddelt
 *    /mc/agents/{id}       TUNG detalje: kørsler, beskeder, planer, politik
 *
 *  Detaljen hentes først når man åbner en agent. Den gamle flade hentede alt
 *  for alle på én gang — 306 agenter blev til over tolvhundrede forespørgsler.
 */
import { apiFetch, type ApiConfig } from './api'

export interface PoolAgent {
  agent_id: string
  parent_agent_id?: string | null
  council_id?: string | null
  kind?: string
  role?: string
  goal?: string
  status?: string
  provider?: string
  model?: string
  persistent?: boolean | number
  tokens_burned?: number
  failure_count?: number
  last_error?: string | null
  created_at?: string
  completed_at?: string | null
  koersler: number
  beskeder: number
  pris_usd: number
  tokens: number
  seneste_udfald?: string | null
  seneste_resume?: string | null
  seneste_slut?: string | null
  varighed_s: number
  er_aktiv: boolean
}

export interface PoolListe {
  agenter: PoolAgent[]
  vist?: number
  /** Det ÆGTE antal i filteret — holdt adskilt fra `limit`. */
  i_alt?: number
  offset?: number
  limit?: number
}

export interface PoolOpsummering {
  agenter_i_alt?: number
  pr_status?: Record<string, number>
  aktive_nu?: number
  pr_rolle?: { rolle: string; antal: number }[]
  vindue?: {
    koersler: number; fejlede: number
    /** `null` = ingen kørsler. «Ingen data» er ikke «nul procent». */
    fejlrate: number | null
    pris_usd: number; tokens: number
  }
  raad?: Record<string, number>
  graenser?: { samtidige?: number; dybde?: number }
}

export interface AgentKoersel {
  run_id?: string
  agent_id?: string
  role?: string
  goal?: string
  status?: string
  execution_mode?: string
  provider?: string
  model?: string
  input_summary?: string
  output_summary?: string
  failure_reason?: string | null
  started_at?: string
  finished_at?: string | null
  input_tokens?: number
  output_tokens?: number
  cost_usd?: number
  varighed_s?: number
}

export interface AgentBesked {
  message_id?: string
  direction?: string
  role?: string
  content?: string
  kind?: string
  created_at?: string
}

export interface AgentDetail {
  agent_id: string
  role?: string
  kind?: string
  goal?: string
  status?: string
  model?: string
  tokens_burned?: number
  tokens?: number
  last_error?: string | null
  created_at?: string
  completed_at?: string | null
  runs: AgentKoersel[]
  messages: AgentBesked[]
  allowed_tools?: string[]
  progress_label?: string
  message_count?: number
  tool_call_count?: number
  [key: string]: unknown
}

export function getPoolListe(
  config: ApiConfig,
  { status = '', rolle = '', soeg = '', limit = 50, offset = 0 } = {},
): Promise<PoolListe> {
  const q = new URLSearchParams({
    status, rolle, soeg, limit: String(limit), offset: String(offset),
  })
  return apiFetch<PoolListe>(config, `/mc/agent-pool?${q.toString()}`)
}

export function getPoolOpsummering(config: ApiConfig, timer = 24): Promise<PoolOpsummering> {
  return apiFetch<PoolOpsummering>(config, `/mc/agent-pool/summary?timer=${timer}`)
}

export function getPoolArbejde(config: ApiConfig, limit = 30): Promise<{ koersler: AgentKoersel[] }> {
  return apiFetch(config, `/mc/agent-pool/work?limit=${limit}`)
}

export function getAgentDetalje(config: ApiConfig, agentId: string): Promise<AgentDetail> {
  return apiFetch(config, `/mc/agents/${encodeURIComponent(agentId)}`)
}

export function getAgentKoersler(config: ApiConfig, agentId: string): Promise<{ runs: AgentKoersel[] }> {
  return apiFetch(config, `/mc/agents/${encodeURIComponent(agentId)}/runs`)
}

export function getAgentBeskeder(config: ApiConfig, agentId: string): Promise<{ messages: AgentBesked[] }> {
  return apiFetch(config, `/mc/agents/${encodeURIComponent(agentId)}/messages`)
}

/** Handlingerne findes allerede i backenden og er ikke ens:
 *  `cancel` stopper agenten, `expire` lukker den som udløbet, og `suspend`
 *  sætter KUN databasestatus — den stopper ikke en tråd der allerede kører.
 *  Teksten på knapperne siger det, så en pause ikke læses som et stop. */
export function agentHandling(
  config: ApiConfig, agentId: string,
  handling: 'cancel' | 'suspend' | 'resume' | 'expire',
): Promise<{ status?: string }> {
  return apiFetch(config, `/mc/runtime/agents/${encodeURIComponent(agentId)}/${handling}`,
    { method: 'POST' })
}

export function sendTilAgent(
  config: ApiConfig, agentId: string, besked: string,
): Promise<{ status?: string }> {
  return apiFetch(config, `/mc/runtime/agents/${encodeURIComponent(agentId)}/message`,
    { method: 'POST', body: { content: besked } })
}
