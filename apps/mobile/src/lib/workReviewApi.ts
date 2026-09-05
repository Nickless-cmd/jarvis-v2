import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export interface WorkReview {
  id: string
  kind: 'dispatch'
  title: string
  status: string
  branch: string
  updatedAt: string
  summary: string
  filesChanged: number
  additions: number
  deletions: number
}

export interface DispatchDiff {
  taskId: string
  status: string
  worktreeAlive: boolean
  diff: string
  diffSummary: string
}

function firstNumber(pattern: RegExp, text: string): number {
  const m = pattern.exec(text)
  return m ? Number(m[1]) || 0 : 0
}

export function summarizeDiff(text: string): {
  filesChanged: number
  additions: number
  deletions: number
  summary: string
} {
  const lines = String(text || '').split('\n').map((l) => l.trim()).filter(Boolean)
  const summary = [...lines].reverse().find((l) => /files? changed|insertions?\(\+\)|deletions?\(-\)/.test(l)) ?? ''
  return {
    filesChanged: firstNumber(/(\d+)\s+files?\s+changed/, summary),
    additions: firstNumber(/(\d+)\s+insertions?\(\+\)/, summary),
    deletions: firstNumber(/(\d+)\s+deletions?\(-\)/, summary),
    summary
  }
}

function normaliseDispatch(raw: Record<string, unknown>): WorkReview | null {
  const id = typeof raw.task_id === 'string' ? raw.task_id : ''
  if (!id) return null
  const prompt = typeof raw.prompt === 'string' ? raw.prompt.trim() : ''
  const stats = summarizeDiff(typeof raw.diff_summary === 'string' ? raw.diff_summary : '')
  return {
    id,
    kind: 'dispatch',
    title: prompt || id,
    status: typeof raw.status === 'string' ? raw.status : 'unknown',
    branch: typeof raw.branch === 'string' ? raw.branch : '',
    updatedAt:
      (typeof raw.ended_at === 'string' && raw.ended_at) ||
      (typeof raw.started_at === 'string' ? raw.started_at : ''),
    summary: stats.summary,
    filesChanged: stats.filesChanged,
    additions: stats.additions,
    deletions: stats.deletions
  }
}

export async function fetchWorkReviews(config: ApiConfig, limit = 30): Promise<WorkReview[]> {
  const raw = await apiFetch<{ dispatches?: unknown[] }>(config, `/api/dispatches?limit=${limit}`)
  return (raw.dispatches ?? [])
    .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
    .map(normaliseDispatch)
    .filter((x): x is WorkReview => x !== null)
}

export async function fetchDispatchDiff(config: ApiConfig, taskId: string): Promise<DispatchDiff> {
  const raw = await apiFetch<{
    task_id?: string
    status?: string
    worktree_alive?: boolean
    diff?: string
    diff_summary?: string
  }>(config, `/api/dispatches/${encodeURIComponent(taskId)}/diff`)
  return {
    taskId: raw.task_id ?? taskId,
    status: raw.status ?? 'unknown',
    worktreeAlive: raw.worktree_alive === true,
    diff: raw.diff ?? '',
    diffSummary: raw.diff_summary ?? ''
  }
}
