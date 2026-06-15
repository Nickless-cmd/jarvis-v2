import { apiFetch, type ApiConfig } from './api'

export interface QueueItem {
  id: string
  kind: 'initiative' | 'capability' | 'tool_intent' | 'file_edit' | 'proposal'
  title: string
  detail: string
  source: string
  diff?: string
}
export interface CoworkPlan { id: string; title: string; status: string; steps_done: number; steps_total: number }
export interface CoworkChannel { name: string; online: boolean; unread: number }
export interface CoworkTodo { id: string; content: string; status: string; expires_at?: string }

export async function getCoworkQueue(config: ApiConfig): Promise<QueueItem[]> {
  const d = await apiFetch<{ items: QueueItem[] }>(config, '/cowork/queue')
  return d.items ?? []
}
export async function getCoworkPlans(config: ApiConfig): Promise<CoworkPlan[]> {
  const d = await apiFetch<{ plans: CoworkPlan[] }>(config, '/cowork/plans')
  return d.plans ?? []
}
export async function getCoworkTodos(config: ApiConfig): Promise<CoworkTodo[]> {
  const d = await apiFetch<{ todos: CoworkTodo[] }>(config, '/cowork/todos')
  return d.todos ?? []
}
export async function getCoworkChannels(config: ApiConfig): Promise<CoworkChannel[]> {
  const d = await apiFetch<{ channels: CoworkChannel[] }>(config, '/cowork/channels')
  return d.channels ?? []
}
export async function resolveQueueItem(config: ApiConfig, id: string, decision: 'approve' | 'reject'): Promise<void> {
  await apiFetch(config, `/cowork/queue/${encodeURIComponent(id)}/${decision}`, { method: 'POST' })
}

// ── Cross-user share-guard (§4.4) ──────────────────────────────────────────
export interface ShareDecision {
  id: string
  session_id: string
  current_user_id: string
  mentioned_users: string[]
  text_preview: string
  status: string
  created_at: string
}

export async function getShareGuard(config: ApiConfig): Promise<ShareDecision[]> {
  const d = await apiFetch<{ pending: ShareDecision[] }>(config, '/cowork/share-guard')
  return d.pending ?? []
}

export async function resolveShareGuard(config: ApiConfig, id: string, shared: boolean): Promise<void> {
  await apiFetch(config, `/cowork/share-guard/${encodeURIComponent(id)}/resolve?shared=${shared}`, { method: 'POST' })
}

// ── UI-panel-kald (§8.2) ───────────────────────────────────────────────────
export interface UiPanelRequest {
  id: string
  panel: 'preview' | 'right' | 'files' | 'file_tree'
  action?: 'open' | 'close'
  session_id: string
  detail: string
  status: string
  created_at: string
}

export async function getUiPanelPending(config: ApiConfig): Promise<UiPanelRequest[]> {
  const d = await apiFetch<{ pending: UiPanelRequest[] }>(config, '/cowork/ui-panel/pending')
  return d.pending ?? []
}

export async function ackUiPanel(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/cowork/ui-panel/${encodeURIComponent(id)}/ack`, { method: 'POST' })
}

// §19.5: agent dispatch i cowork command center. buildAgentDispatchView mapper
// resultatet fra backend (agent_dispatch.dispatch_code_mode_task) til visnings-rækker.
export type AgentStatus = 'planned' | 'running' | 'done' | 'error'

export interface AgentDispatchEntry {
  role: string
  goal: string
  parallel: boolean
  status: AgentStatus
  agentId?: string
}

export interface AgentDispatchView {
  mode: 'inline' | 'dispatch'
  decision: string
  entries: AgentDispatchEntry[]
  summary: { total: number; running: number; done: number; planned: number; error: number }
}

export function buildAgentDispatchView(result: Record<string, unknown> | null | undefined): AgentDispatchView {
  const mode = (result?.mode === 'dispatch' ? 'dispatch' : 'inline') as AgentDispatchView['mode']
  const decision = String((result?.decision as { reason?: string } | undefined)?.reason ?? '')
  const plan = Array.isArray(result?.plan) ? (result!.plan as Record<string, unknown>[]) : []
  const spawned = Array.isArray(result?.spawned) ? (result!.spawned as Record<string, unknown>[]) : []

  const entries: AgentDispatchEntry[] = plan.map((p, i) => {
    const sp = spawned[i] as { agent_id?: string; error?: string } | undefined
    let status: AgentStatus = 'planned'
    if (sp?.error) status = 'error'
    else if (sp?.agent_id) status = 'running'
    return {
      role: String(p.role ?? ''),
      goal: String(p.goal ?? ''),
      parallel: Boolean(p.parallel),
      status,
      agentId: sp?.agent_id,
    }
  })

  const summary = {
    total: entries.length,
    running: entries.filter((e) => e.status === 'running').length,
    done: entries.filter((e) => e.status === 'done').length,
    planned: entries.filter((e) => e.status === 'planned').length,
    error: entries.filter((e) => e.status === 'error').length,
  }
  return { mode, decision, entries, summary }
}

// Aktive dispatch-agenter fra /cowork/agents (agent_registry-rækker).
export interface ActiveAgent {
  agent_id: string
  role: string
  goal: string
  status: string
  parent: string
  tokens_burned: number
}

export async function getCoworkAgents(config: ApiConfig): Promise<ActiveAgent[]> {
  const d = await apiFetch<{ agents: ActiveAgent[] }>(config, '/cowork/agents')
  return d.agents ?? []
}

function _mapAgentStatus(raw: string): AgentStatus {
  const s = (raw || '').toLowerCase()
  if (s === 'active' || s === 'starting' || s === 'running') return 'running'
  if (s === 'queued' || s === 'pending') return 'planned'
  if (s === 'completed' || s === 'done') return 'done'
  if (s === 'failed' || s === 'error' || s === 'cancelled' || s === 'expired') return 'error'
  return 'running'
}

export function activeAgentsToView(agents: ActiveAgent[]): AgentDispatchView {
  const entries: AgentDispatchEntry[] = (agents ?? []).map((a) => ({
    role: a.role,
    goal: a.goal,
    parallel: a.parent === 'jarvis' || !a.parent,
    status: _mapAgentStatus(a.status),
    agentId: a.agent_id,
  }))
  return {
    mode: entries.length > 0 ? 'dispatch' : 'inline',
    decision: `${entries.length} aktive`,
    entries,
    summary: {
      total: entries.length,
      running: entries.filter((e) => e.status === 'running').length,
      done: entries.filter((e) => e.status === 'done').length,
      planned: entries.filter((e) => e.status === 'planned').length,
      error: entries.filter((e) => e.status === 'error').length,
    },
  }
}

export interface AccountProfile {
  user_id: string
  email: string
  email_verified: boolean
  language: string
  role: 'owner' | 'member' | 'guest'
  tier: string
}

export async function getAccountMe(config: ApiConfig): Promise<AccountProfile> {
  return apiFetch<AccountProfile>(config, '/account/me')
}

export async function createCoworkTodo(config: ApiConfig, content: string): Promise<void> {
  await apiFetch(config, '/cowork/todos', { method: 'POST', body: { content } })
}

export async function setCoworkTodoStatus(config: ApiConfig, id: string, status: string): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}/status`, { method: 'POST', body: { status } })
}

export async function deleteCoworkTodo(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}`, { method: 'DELETE' })
}

export async function setCoworkTodoExpiry(config: ApiConfig, id: string, expiresAt: string | null): Promise<void> {
  await apiFetch(config, `/cowork/todos/${id}/expiry`, { method: 'POST', body: { expires_at: expiresAt } })
}

export interface QuotaItem {
  kind: 'chat' | 'code' | 'cowork' | 'agent'
  used: number
  limit: number | null
  remaining: number | null
  warn: boolean
}
export interface QuotaOverview { tier: string; items: QuotaItem[] }

export async function getAccountQuota(config: ApiConfig): Promise<QuotaOverview> {
  return apiFetch<QuotaOverview>(config, '/account/quota')
}

export async function setAccountLanguage(config: ApiConfig, language: string): Promise<void> {
  await apiFetch(config, '/account/language', { method: 'PATCH', body: { language } })
}

export interface WorkspaceOverview {
  path_name: string
  files: number
  disk_bytes: number
  encrypted: boolean
  trusted: boolean
}

export async function getAccountWorkspace(config: ApiConfig): Promise<WorkspaceOverview> {
  return apiFetch<WorkspaceOverview>(config, '/account/workspace')
}

export interface MemoryOverview {
  memory_md: string
  user_md: string
  recent_sensory: { id: string; content: string; modality?: string }[]
  brain_count: number
}

export async function getAccountMemory(config: ApiConfig): Promise<MemoryOverview> {
  return apiFetch<MemoryOverview>(config, '/account/memory')
}

export async function searchAccountMemory(config: ApiConfig, q: string): Promise<{ id: string; content: string }[]> {
  const d = await apiFetch<{ results: { id: string; content: string }[] }>(config, `/account/memory/search?q=${encodeURIComponent(q)}`)
  return d.results ?? []
}

export interface PermissionMode { mode: string; all: boolean; tools: string[] }
export interface PermissionsOverview { role: string; modes: PermissionMode[]; computer_use_enabled: boolean }

export async function getAccountPermissions(config: ApiConfig): Promise<PermissionsOverview> {
  return apiFetch<PermissionsOverview>(config, '/account/permissions')
}

export async function setComputerUse(config: ApiConfig, enabled: boolean): Promise<void> {
  await apiFetch(config, '/account/computer-use', { method: 'PATCH', body: { enabled } })
}

export interface JarvisLane { lane: string; provider: string | null; model: string | null; active: boolean; credentials_ready: boolean }
export interface JarvisOverview { lanes: JarvisLane[]; visible_options: { provider: string | null; model: string | null }[] }

export async function getJarvisOverview(config: ApiConfig): Promise<JarvisOverview> {
  return apiFetch<JarvisOverview>(config, '/account/jarvis')
}

export async function setVisibleModel(config: ApiConfig, provider: string, model: string): Promise<void> {
  await apiFetch(config, '/account/jarvis/visible-model', { method: 'POST', body: { provider, model } })
}

export interface ConnectedApp { plugin_id: string; name: string; status: string; detail: string }
export async function getAccountApps(config: ApiConfig): Promise<ConnectedApp[]> {
  const d = await apiFetch<{ apps: ConnectedApp[] }>(config, '/account/apps')
  return d.apps ?? []
}

export interface McpServer { id: string; name: string; url: string }
export async function getAccountMcp(config: ApiConfig): Promise<McpServer[]> {
  const d = await apiFetch<{ servers: McpServer[] }>(config, '/account/mcp')
  return d.servers ?? []
}
export async function addMcpServer(config: ApiConfig, name: string, url: string): Promise<void> {
  await apiFetch(config, '/account/mcp', { method: 'POST', body: { name, url } })
}
export async function removeMcpServer(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/account/mcp/${id}`, { method: 'DELETE' })
}
