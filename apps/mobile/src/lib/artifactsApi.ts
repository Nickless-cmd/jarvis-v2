import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export interface ArtifactItem {
  id: string
  kind: 'patch'
  title: string
  detail: string
  createdAt: string
}

export async function fetchArtifacts(config: ApiConfig): Promise<ArtifactItem[]> {
  try {
    const raw = await apiFetch<{ dispatches?: unknown[] }>(config, '/api/dispatches?limit=30')
    return (raw.dispatches ?? [])
      .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
      .filter((x) => typeof x.task_id === 'string' && typeof x.diff_summary === 'string' && x.diff_summary.trim())
      .map((x) => ({
        id: `dispatch:${x.task_id as string}`,
        kind: 'patch' as const,
        title: String(x.prompt || x.task_id || 'Patch').trim(),
        detail: String(x.diff_summary || '').trim(),
        createdAt: String(x.ended_at || x.started_at || '')
      }))
  } catch {
    return []
  }
}
