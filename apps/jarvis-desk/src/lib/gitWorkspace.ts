import { apiFetch, type ApiConfig } from './api'

/**
 * Git- og workspace-valg for code-mode (Bjørn 18/9-2026).
 *
 * Ruterne er nye: API'et kunne kun svare på «hvilken branch er jeg på» og «er
 * DENNE mappe betroet». En vælger skal kende kandidaterne, og det kunne den
 * ikke spørge om.
 */

export interface BranchListe {
  ok: boolean
  current: string
  local: string[]
  remote: string[]
  /** Serverens egen begrundelse når listen ikke kunne hentes. */
  error?: string
}

export interface BetroetMappe {
  kind: string
  root: string
  trusted_at: string
}

const q = (kind: string, root: string) =>
  `kind=${encodeURIComponent(kind)}&root=${encodeURIComponent(root)}`

export async function hentBranches(
  config: ApiConfig, kind: string, root: string,
): Promise<BranchListe> {
  const r = await apiFetch<Record<string, unknown>>(config, `/chat/git/branches?${q(kind, root)}`)
  return {
    ok: !!r?.ok,
    current: String(r?.current ?? ''),
    local: Array.isArray(r?.local) ? (r.local as unknown[]).map(String) : [],
    remote: Array.isArray(r?.remote) ? (r.remote as unknown[]).map(String) : [],
    error: r?.error ? String(r.error) : undefined,
  }
}

export async function skiftBranch(
  config: ApiConfig,
  body: { kind: string; root: string; name: string; create?: boolean },
): Promise<{ ok: boolean; current?: string; error?: string }> {
  const r = await apiFetch<Record<string, unknown>>(config, '/chat/git/checkout', {
    method: 'POST', body: JSON.stringify({ create: false, ...body }),
  })
  return { ok: !!r?.ok, current: r?.current ? String(r.current) : undefined,
           error: r?.error ? String(r.error) : undefined }
}

export async function opretWorktree(
  config: ApiConfig,
  body: { kind: string; root: string; name: string; path?: string },
): Promise<{ ok: boolean; path?: string; error?: string }> {
  const r = await apiFetch<Record<string, unknown>>(config, '/chat/git/worktree', {
    method: 'POST', body: JSON.stringify(body),
  })
  return { ok: !!r?.ok, path: r?.path ? String(r.path) : undefined,
           error: r?.error ? String(r.error) : undefined }
}

export async function hentBetroedeMapper(
  config: ApiConfig, kind = '',
): Promise<BetroetMappe[]> {
  const sti = kind ? `/chat/workspace-trust/list?kind=${encodeURIComponent(kind)}` : '/chat/workspace-trust/list'
  const r = await apiFetch<Record<string, unknown>>(config, sti)
  const f = (Array.isArray(r?.folders) ? r.folders : []) as Record<string, unknown>[]
  return f.map((x) => ({
    kind: String(x.kind ?? ''), root: String(x.root ?? ''),
    trusted_at: String(x.trusted_at ?? ''),
  }))
}
