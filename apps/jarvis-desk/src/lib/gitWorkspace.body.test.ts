import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiFetch = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { opretWorktree, skiftBranch } from './gitWorkspace'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

// apiFetch stringifier body selv. En allerede-stringificeret body blev til en
// JSON-streng inde i JSON, og ruternes pydantic-modeller svarede 422 (19/9-2026).
describe('git-kald sender OBJEKTER til apiFetch', () => {
  beforeEach(() => apiFetch.mockReset().mockResolvedValue({ ok: true, path: '.worktrees/x', current: 'x' }))

  it('opretWorktree', async () => {
    await opretWorktree(cfg, { kind: 'workstation', root: '/r', name: 'x' })
    const body = apiFetch.mock.calls[0]?.[2]?.body
    expect(typeof body).toBe('object')
    expect(body).toEqual({ kind: 'workstation', root: '/r', name: 'x' })
  })

  it('skiftBranch', async () => {
    await skiftBranch(cfg, { kind: 'workstation', root: '/r', name: 'main' })
    const body = apiFetch.mock.calls[0]?.[2]?.body
    expect(typeof body).toBe('object')
    expect(body).toEqual({ create: false, kind: 'workstation', root: '/r', name: 'main' })
  })
})
