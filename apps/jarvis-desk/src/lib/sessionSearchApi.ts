import { apiFetch, type ApiConfig } from './api'

export interface SessionHit {
  session_id: string
  title: string
  snippet: string
  updated_at?: string
}

/** Søg sessioner på titel + besked-indhold (self-scoped på serveren). */
export async function searchSessions(config: ApiConfig, q: string, limit = 30): Promise<SessionHit[]> {
  const query = encodeURIComponent(q)
  const d = await apiFetch<{ items: SessionHit[] }>(config, `/api/chat/sessions/search?q=${query}&limit=${limit}`)
  return d.items ?? []
}
