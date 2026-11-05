import { apiFetch, type ApiConfig } from './api'

/**
 * Git-panelets klient: kald mod `/chat/git-panel/*` plus de RENE funktioner
 * panelet tegner ud fra.
 *
 * Branch-liste, branch-skift og «opret worktree» ligger allerede i
 * `gitWorkspace.ts` og bliver ikke gentaget her.
 */

export type Maal = { kind: 'container' | 'workstation'; root: string }

export interface GitFil {
  path: string
  old_path: string
  /** Index-kolonnen fra `git status --porcelain` (M, A, D, R, ? …). */
  index: string
  /** Working-tree-kolonnen. */
  worktree: string
  untracked: boolean
  staged: boolean
  unstaged: boolean
  conflict: boolean
}

export interface GitStatusPanel {
  ok: boolean
  branch: string
  upstream: string
  ahead: number
  behind: number
  detached: boolean
  dirty: number
  staged_count: number
  unstaged_count: number
  files: GitFil[]
  error?: string
}

export interface GitCommitPost {
  sha: string; short: string; author: string; date: string; subject: string
}

export interface GitWorktree {
  path: string; head: string; branch: string
  detached: boolean; bare: boolean; locked: boolean; main: boolean; current: boolean
}

export type DiffMode = 'unstaged' | 'staged' | 'head'

const q = (m: Maal, ekstra: Record<string, string> = {}) => {
  const p = new URLSearchParams({ kind: m.kind, root: m.root, ...ekstra })
  return p.toString()
}

const BASE = '/chat/git-panel'

export async function hentGitStatus(config: ApiConfig, m: Maal): Promise<GitStatusPanel> {
  const r = await apiFetch<Partial<GitStatusPanel>>(config, `${BASE}/status?${q(m)}`)
  return {
    ok: !!r?.ok,
    branch: String(r?.branch ?? ''),
    upstream: String(r?.upstream ?? ''),
    ahead: Number(r?.ahead ?? 0),
    behind: Number(r?.behind ?? 0),
    detached: !!r?.detached,
    dirty: Number(r?.dirty ?? 0),
    staged_count: Number(r?.staged_count ?? 0),
    unstaged_count: Number(r?.unstaged_count ?? 0),
    files: Array.isArray(r?.files) ? (r.files as GitFil[]) : [],
    error: r?.error ? String(r.error) : undefined,
  }
}

export async function hentGitDiff(
  config: ApiConfig, m: Maal, path: string, mode: DiffMode,
): Promise<{ ok: boolean; diff: string; truncated: boolean; binary: boolean; error?: string }> {
  const r = await apiFetch<Record<string, unknown>>(
    config, `${BASE}/diff?${q(m, { path, mode })}`,
  )
  return {
    ok: !!r?.ok, diff: String(r?.diff ?? ''), truncated: !!r?.truncated,
    binary: !!r?.binary, error: r?.error ? String(r.error) : undefined,
  }
}

type Udfald = { ok: boolean; error?: string }
const udfald = (r: Record<string, unknown>): Udfald => ({
  ok: !!r?.ok, error: r?.error ? String(r.error) : undefined,
})

export async function stageFiler(
  config: ApiConfig, m: Maal, paths: string[], alle = false,
): Promise<Udfald> {
  return udfald(await apiFetch(config, `${BASE}/stage`, {
    method: 'POST', body: { ...m, paths, all: alle },
  }))
}

export async function unstageFiler(
  config: ApiConfig, m: Maal, paths: string[], alle = false,
): Promise<Udfald> {
  return udfald(await apiFetch(config, `${BASE}/unstage`, {
    method: 'POST', body: { ...m, paths, all: alle },
  }))
}

export async function commitStaged(
  config: ApiConfig, m: Maal, message: string,
): Promise<Udfald & { sha?: string }> {
  const r = await apiFetch<Record<string, unknown>>(config, `${BASE}/commit`, {
    method: 'POST', body: { ...m, message },
  })
  return { ...udfald(r), sha: r?.sha ? String(r.sha) : undefined }
}

export async function pushBranch(config: ApiConfig, m: Maal): Promise<Udfald & { upstream?: string }> {
  const r = await apiFetch<Record<string, unknown>>(config, `${BASE}/push`, {
    method: 'POST', body: { ...m },
    // Et push kan tage tid; og et POST gentages aldrig af apiFetch.
    timeoutMs: 60_000,
  })
  return { ...udfald(r), upstream: r?.upstream ? String(r.upstream) : undefined }
}

export async function hentGitLog(
  config: ApiConfig, m: Maal, limit = 30,
): Promise<{ ok: boolean; commits: GitCommitPost[]; error?: string }> {
  const r = await apiFetch<Record<string, unknown>>(
    config, `${BASE}/log?${q(m, { limit: String(limit) })}`,
  )
  return {
    ok: !!r?.ok,
    commits: Array.isArray(r?.commits) ? (r.commits as GitCommitPost[]) : [],
    error: r?.error ? String(r.error) : undefined,
  }
}

export async function hentGitWorktrees(
  config: ApiConfig, m: Maal,
): Promise<{ ok: boolean; worktrees: GitWorktree[]; error?: string }> {
  const r = await apiFetch<Record<string, unknown>>(config, `${BASE}/worktrees?${q(m)}`)
  return {
    ok: !!r?.ok,
    worktrees: Array.isArray(r?.worktrees) ? (r.worktrees as GitWorktree[]) : [],
    error: r?.error ? String(r.error) : undefined,
  }
}

// ── Rene funktioner ─────────────────────────────────────────────────────────

export interface FilGrupper {
  konflikt: GitFil[]
  staged: GitFil[]
  /** Ændrede, kendte filer der ikke er staged (eller er ændret igen efter staging). */
  aendret: GitFil[]
  nye: GitFil[]
}

/** Sortér filer i panelets sektioner. En fil kan stå to steder: staged OG ændret
 *  igen bagefter (`MM`) — så skal begge sider kunne ses og handles på. */
export function grupperFiler(filer: GitFil[]): FilGrupper {
  const g: FilGrupper = { konflikt: [], staged: [], aendret: [], nye: [] }
  for (const f of filer) {
    if (f.conflict) { g.konflikt.push(f); continue }
    if (f.untracked) { g.nye.push(f); continue }
    if (f.staged) g.staged.push(f)
    if (f.unstaged) g.aendret.push(f)
  }
  return g
}

const KODE_TEKST: Record<string, string> = {
  M: 'Ændret', A: 'Tilføjet', D: 'Slettet', R: 'Omdøbt', C: 'Kopieret', T: 'Type ændret',
}

/** Dansk etiket for en fil i en given sektion. */
export function statusEtiket(f: GitFil, sektion: 'staged' | 'aendret' | 'nye' | 'konflikt'): string {
  if (sektion === 'konflikt') return 'Konflikt'
  if (sektion === 'nye') return 'Ny'
  const kode = sektion === 'staged' ? f.index : f.worktree
  return KODE_TEKST[kode] ?? 'Ændret'
}

/** Hvilken diff-mode hører til en sektion. Ukendte filer diffes mod ingenting. */
export function diffModeForSektion(sektion: 'staged' | 'aendret' | 'nye' | 'konflikt'): DiffMode {
  return sektion === 'staged' ? 'staged' : sektion === 'konflikt' ? 'head' : 'unstaged'
}

export type DiffLinjeType = 'meta' | 'hunk' | 'tilfoejet' | 'fjernet' | 'kontekst'
export interface DiffLinje { type: DiffLinjeType; tekst: string }

/** Unified diff → typede linjer + tællere. Alt FØR første `@@` er meta, så en
 *  fil hvis indhold starter med `+++` ikke forveksles med filhovedet. */
export function parseDiff(tekst: string): { linjer: DiffLinje[]; tilfoejet: number; fjernet: number } {
  const linjer: DiffLinje[] = []
  let tilfoejet = 0
  let fjernet = 0
  let ihunk = false
  const rå = (tekst ?? '').split('\n')
  if (rå.length && rå[rå.length - 1] === '') rå.pop()
  for (const l of rå) {
    if (l.startsWith('diff --git ')) { ihunk = false; linjer.push({ type: 'meta', tekst: l }); continue }
    if (l.startsWith('@@')) { ihunk = true; linjer.push({ type: 'hunk', tekst: l }); continue }
    if (!ihunk) { linjer.push({ type: 'meta', tekst: l }); continue }
    if (l.startsWith('\\')) { linjer.push({ type: 'meta', tekst: l }); continue }
    if (l.startsWith('+')) { tilfoejet++; linjer.push({ type: 'tilfoejet', tekst: l }); continue }
    if (l.startsWith('-')) { fjernet++; linjer.push({ type: 'fjernet', tekst: l }); continue }
    linjer.push({ type: 'kontekst', tekst: l })
  }
  return { linjer, tilfoejet, fjernet }
}

/** Må der committes nu — og hvis ikke, hvorfor (på dansk). */
export function commitKlar(
  status: Pick<GitStatusPanel, 'staged_count' | 'files'> | null, besked: string,
): { klar: boolean; grund: string } {
  if (!status) return { klar: false, grund: 'Status er ikke hentet endnu' }
  if (status.files.some((f) => f.conflict)) return { klar: false, grund: 'Løs konflikterne først' }
  if (status.staged_count === 0) return { klar: false, grund: 'Stage mindst én fil først' }
  if (!besked.trim()) return { klar: false, grund: 'Skriv en commit-besked' }
  return { klar: true, grund: '' }
}

/** Kort tekst om forholdet til upstream. */
export function trackingTekst(
  s: Pick<GitStatusPanel, 'upstream' | 'ahead' | 'behind' | 'detached'>,
): string {
  if (s.detached) return 'Afkoblet HEAD'
  if (!s.upstream) return 'Ingen upstream — push opretter den'
  const dele: string[] = []
  if (s.ahead) dele.push(`${s.ahead} foran`)
  if (s.behind) dele.push(`${s.behind} bagud`)
  return dele.length ? `${dele.join(', ')} ${s.upstream}` : `Ajour med ${s.upstream}`
}

/** Er der noget at pushe? Uden upstream tæller en ikke-afkoblet branch som «ja». */
export function kanPushe(
  s: Pick<GitStatusPanel, 'upstream' | 'ahead' | 'detached' | 'branch'>,
): boolean {
  if (s.detached || !s.branch) return false
  return !s.upstream || s.ahead > 0
}

/** Seneste del af en sti til visning; hele stien bliver i `title`. */
export function filNavn(path: string): { navn: string; mappe: string } {
  const i = path.lastIndexOf('/')
  return i < 0 ? { navn: path, mappe: '' } : { navn: path.slice(i + 1), mappe: path.slice(0, i) }
}
