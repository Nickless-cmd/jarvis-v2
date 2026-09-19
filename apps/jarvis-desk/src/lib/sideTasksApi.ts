import { apiFetch, type ApiConfig } from './api'

/**
 * Jarvis' flaggede sideopgaver (server: core.services.side_tasks, ruterne
 * /cowork/side-tasks). Serveren er eneste sandhed — desk holder ingen kopi
 * af status, den spørger bare igen.
 */
export interface SideTask {
  side_task_id: string
  title: string
  prompt: string
  tldr: string
  status: 'pending' | 'activated'
  session_id: string
  created_at: string
}

export type SideTaskAfslutning = 'activated' | 'completed' | 'dismissed'

export async function getSideTasks(config: ApiConfig): Promise<SideTask[]> {
  const d = await apiFetch<{ side_tasks?: SideTask[] }>(config, '/cowork/side-tasks', { retries: 0 })
  return d.side_tasks ?? []
}

export async function setSideTaskStatus(config: ApiConfig, id: string, status: SideTaskAfslutning): Promise<void> {
  const r = await apiFetch<{ status?: string; error?: string }>(
    config, `/cowork/side-tasks/${encodeURIComponent(id)}/status`, { method: 'POST', body: { status } },
  )
  // Serveren svarer 200 med {status:'error'} for en ukendt eller allerede
  // afsluttet opgave. Det er en fejl for brugeren, ikke en succes.
  if (r?.status === 'error') throw new Error(r.error || 'Kunne ikke opdatere sideopgaven')
}
