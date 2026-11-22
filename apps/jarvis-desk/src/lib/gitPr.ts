import { apiFetch, createPullRequest, type ApiConfig } from './api'
import type { Maal } from './gitPanel'

/** PR-oprettelse bruger den eksisterende `POST /chat/git/create-pr` (via `createPullRequest`).
 *
 *  CI-status: backend-agenten bygger ruten parallelt. AFTALT STI (kan flyttes ét sted her):
 *  `GET /chat/git/ci-status?kind=&root=&branch=` → `{ok, state, checks:[{name, state, url?}], url?, error?}`
 *  med `state` ∈ pending | success | failure | none. Findes ruten ikke endnu, viser panelet fejlen
 *  åbent frem for at skjule den. */
export interface CiCheck { name: string; state: string; url?: string }
export interface CiStatus {
  ok: boolean
  state: 'pending' | 'success' | 'failure' | 'none' | 'ukendt'
  checks: CiCheck[]
  url?: string
  error?: string
}

const CI_STI = '/chat/git/ci-status'

export async function hentCiStatus(config: ApiConfig, m: Maal, branch: string): Promise<CiStatus> {
  const p = new URLSearchParams({ kind: m.kind, root: m.root, branch })
  const r = await apiFetch<Partial<CiStatus>>(config, `${CI_STI}?${p.toString()}`)
  const s = String(r.state ?? '')
  const state = (['pending', 'success', 'failure', 'none'] as const).find((x) => x === s) ?? 'ukendt'
  return { ok: r.ok !== false, state, checks: Array.isArray(r.checks) ? r.checks : [], url: r.url, error: r.error }
}

export const CI_NAVN: Record<CiStatus['state'], string> = {
  pending: 'CI kører', success: 'CI grøn', failure: 'CI fejlet', none: 'Ingen CI-kørsel', ukendt: 'CI-status ukendt',
}

/** Serveren melder fejl som `{status:'error', detail}` — `detail` løftes op i fejlen. */
export async function opretPr(
  config: ApiConfig, m: Maal, titel: string,
): Promise<{ ok: boolean; url: string; error?: string }> {
  const r = await createPullRequest(config, { kind: m.kind, root: m.root }, titel, '')
  const url = r.url ?? ''
  if (r.status === 'ok' || url !== '') return { ok: true, url }
  const detail = (r as { detail?: unknown }).detail
  return { ok: false, url: '', error: typeof detail === 'string' && detail ? detail : `PR blev ikke oprettet (${r.status})` }
}
