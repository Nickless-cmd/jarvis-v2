import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('coworkApi', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('getCoworkQueue henter items fra /cowork/queue', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ items: [{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }] }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)
    const { getCoworkQueue } = await import('./coworkApi')
    const out = await getCoworkQueue({ apiBaseUrl: 'http://t', authToken: 't' })
    expect(out).toEqual([{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }])
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/cowork/queue'), expect.anything())
  })
})

import { buildAgentDispatchView } from './coworkApi'

describe('buildAgentDispatchView', () => {
  it('mapper plan+spawned til rækker med status', () => {
    const v = buildAgentDispatchView({
      mode: 'dispatch',
      decision: { reason: '3 signaler' },
      plan: [
        { role: 'researcher', goal: 'g1', parallel: true },
        { role: 'planner', goal: 'g2', parallel: false },
      ],
      spawned: [{ agent_id: 'a1' }, { error: 'x' }],
    })
    expect(v.mode).toBe('dispatch')
    expect(v.entries[0]?.status).toBe('running')
    expect(v.entries[1]?.status).toBe('error')
    expect(v.summary).toEqual({ total: 2, running: 1, done: 0, planned: 0, error: 1 })
  })

  it('inline uden plan', () => {
    const v = buildAgentDispatchView({ mode: 'inline', decision: { reason: 'simpel' } })
    expect(v.mode).toBe('inline')
    expect(v.entries).toEqual([])
  })
})

import { activeAgentsToView } from './coworkApi'

describe('activeAgentsToView', () => {
  it('mapper aktive agent-registry-rækker til view', () => {
    const v = activeAgentsToView([
      { agent_id: 'a1', role: 'researcher', goal: 'find', status: 'active', parent: 'jarvis', tokens_burned: 10 },
      { agent_id: 'a2', role: 'executor', goal: 'impl', status: 'queued', parent: 'a1', tokens_burned: 0 },
    ])
    expect(v.mode).toBe('dispatch')
    expect(v.entries[0]?.status).toBe('running')
    expect(v.entries[1]?.status).toBe('planned')
    expect(v.summary.total).toBe(2)
  })
  it('tom liste → inline', () => {
    expect(activeAgentsToView([]).mode).toBe('inline')
  })
})
