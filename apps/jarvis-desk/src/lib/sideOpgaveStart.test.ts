import { describe, it, expect, vi, beforeEach } from 'vitest'

const createSession = vi.fn()
const opretWorktree = vi.fn()
const sendLoesrevet = vi.fn()
vi.mock('./api', () => ({ createSession: (...a: unknown[]) => createSession(...a) }))
vi.mock('./gitWorkspace', () => ({ opretWorktree: (...a: unknown[]) => opretWorktree(...a) }))
vi.mock('./sendLoesrevet', () => ({ sendLoesrevet: (...a: unknown[]) => sendLoesrevet(...a) }))

import { startSideOpgave, worktreeNavn, worktreeTilOpgave } from './sideOpgaveStart'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const t = { side_task_id: 'a', title: 'Fix two failing visible-run tests', prompt: 'Find ud af hvorfor', tldr: '', status: 'pending' as const, session_id: 's', created_at: '' }

describe('sideOpgaveStart', () => {
  beforeEach(() => { createSession.mockReset().mockResolvedValue({ id: 's-ny' }); opretWorktree.mockReset(); sendLoesrevet.mockReset().mockResolvedValue(undefined) })

  it('ny samtale med titlen, prompten som foerste besked, paa samme flade og i samme arbejdsomraade', async () => {
    expect(await startSideOpgave(cfg, t, { kind: 'code', workspaceKind: 'workstation', workspaceRoot: '/r' })).toBe('s-ny')
    expect(createSession).toHaveBeenCalledWith(cfg, t.title, 'code')
    expect(sendLoesrevet).toHaveBeenCalledWith(cfg, { sessionId: 's-ny', message: 'Find ud af hvorfor', mode: 'code', workspaceKind: 'workstation', workspaceRoot: '/r' })
  })

  it('worktree-navnet er git-venligt', () => {
    expect(worktreeNavn('Fix two failing visible-run tests')).toBe('side-fix-two-failing-visible-run-tests')
    expect(worktreeNavn('Ryd op i Ærøs gamle ÅBNE filer!')).toBe('side-ryd-op-i-aeroes-gamle-aabne-filer')
    expect(worktreeNavn('!!!')).toBe('side-opgave')
  })

  it('worktree-stien goeres hel — serveren svarer relativt', async () => {
    opretWorktree.mockResolvedValue({ ok: true, path: '.worktrees/side-x' })
    expect(await worktreeTilOpgave(cfg, '/repo/', t)).toBe('/repo/.worktrees/side-x')
    expect(opretWorktree).toHaveBeenCalledWith(cfg, { kind: 'workstation', root: '/repo/', name: 'side-fix-two-failing-visible-run-tests' })
    opretWorktree.mockResolvedValue({ ok: false, error: 'branch findes' })
    await expect(worktreeTilOpgave(cfg, '/repo', t)).rejects.toThrow('branch findes')
  })
})
