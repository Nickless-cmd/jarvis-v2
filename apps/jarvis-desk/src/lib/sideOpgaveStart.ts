import { createSession, type ApiConfig } from './api'
import { opretWorktree } from './gitWorkspace'
import { sendLoesrevet } from './sendLoesrevet'
import type { SideTask } from './sideTasksApi'

/**
 * Start en sideopgave i en NY samtale. Oprettes via API'et (ikke
 * SessionContext.create): create vælger samtalen som «indlæst og tom», og så
 * ville beskeden vi sender bagefter først vises efter en genindlæsning.
 * Rækkefølgen er derfor: opret → send løsrevet → kalderen genindlæser listen
 * og VÆLGER samtalen (som så hentes med beskeden, og desk følger runnet).
 */
export async function startSideOpgave(
  config: ApiConfig,
  t: SideTask,
  opts: { kind: 'chat' | 'code'; workspaceKind?: 'container' | 'workstation'; workspaceRoot?: string },
): Promise<string> {
  const s = await createSession(config, t.title, opts.kind)
  await sendLoesrevet(config, {
    sessionId: s.id, message: t.prompt, mode: opts.kind,
    workspaceKind: opts.workspaceKind, workspaceRoot: opts.workspaceRoot,
  })
  return s.id
}

/** Et git-venligt navn til worktree'en: «Fix two failing tests» → «side-fix-two-failing-tests». */
export function worktreeNavn(titel: string): string {
  const slug = titel
    .toLowerCase()
    .replace(/æ/g, 'ae').replace(/ø/g, 'oe').replace(/å/g, 'aa')
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    .slice(0, 40).replace(/-+$/g, '')
  return `side-${slug || 'opgave'}`
}

/** Opret en worktree til opgaven under `root` og returnér dens HELE sti. */
export async function worktreeTilOpgave(config: ApiConfig, root: string, t: SideTask): Promise<string> {
  const r = await opretWorktree(config, { kind: 'workstation', root, name: worktreeNavn(t.title) })
  if (!r.ok || !r.path) throw new Error(r.error || 'Kunne ikke oprette worktree')
  // Serveren svarer RELATIVT til repoet (samme regel som WorkspaceVaelger).
  return r.path.startsWith('/') ? r.path : `${root.replace(/\/$/, '')}/${r.path}`
}
