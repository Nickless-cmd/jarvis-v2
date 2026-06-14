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
export interface CoworkTodo { id: string; content: string; status: string }

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
