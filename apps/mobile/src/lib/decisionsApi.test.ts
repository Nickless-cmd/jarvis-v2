import { actOnDecision, fetchDecisions, type Decision } from './decisionsApi'

const config = { apiBaseUrl: 'https://x.test', authToken: 't' } as never

function mockFetch(body: unknown, status = 200) {
  const fn = jest.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body)
  })
  global.fetch = fn as never
  return fn
}

/** Formen er taget fra det levende endpoint 2026-09-05, ikke gættet. */
const LIVE = {
  section: 'decisions',
  count: 3,
  queue: { pending: 0, expired_unanswered: 31, answered: 0 },
  items: [
    {
      kind: 'life_project',
      id: 'life-2df08aeedb',
      text: 'Build a steadier inner architecture',
      why: 'I want a longer thread of coherence through my own work.',
      priority: 'low',
      created_at: '',
      actions: ['abandon']
    }
  ]
}

describe('fetchDecisions', () => {
  it('læser den levende form', async () => {
    mockFetch(LIVE)
    const res = await fetchDecisions(config)
    expect(res.expiredUnanswered).toBe(31)
    expect(res.items).toHaveLength(1)
    expect(res.items[0]!.kind).toBe('life_project')
    expect(res.items[0]!.actions).toEqual(['abandon'])
  })

  it('rammer mind-hubben med query, ikke sti-segment (sti-formen er 404)', async () => {
    const fn = mockFetch(LIVE)
    await fetchDecisions(config)
    expect(String(fn.mock.calls[0][0])).toContain('/central/mind?section=decisions')
  })

  it('smider halve poster væk frem for at vise et kort der ikke kan handles', async () => {
    mockFetch({
      items: [
        { kind: 'initiative', id: '', text: 'uden id' },
        { kind: 'initiative', id: 'i1', text: '' },
        { kind: 'noget-nyt', id: 'x', text: 'ukendt slags' },
        { kind: 'initiative', id: 'i2', text: 'ægte', actions: ['approve', 'reject'] }
      ]
    })
    const res = await fetchDecisions(config)
    expect(res.items.map((d) => d.id)).toEqual(['i2'])
  })

  it('frafiltrerer handlinger uden en rute', async () => {
    mockFetch({
      items: [{ kind: 'life_project', id: 'l1', text: 't', actions: ['approve', 'abandon'] }]
    })
    const res = await fetchDecisions(config)
    expect(res.items[0]!.actions).toEqual(['abandon'])
  })

  it('tåler et svar uden items og uden queue', async () => {
    mockFetch({ section: 'decisions' })
    const res = await fetchDecisions(config)
    expect(res.items).toEqual([])
    expect(res.expiredUnanswered).toBe(0)
  })
})

describe('actOnDecision', () => {
  const init: Decision = {
    kind: 'initiative',
    id: 'i 1',
    text: 't',
    why: '',
    priority: '',
    created_at: '',
    actions: ['approve', 'reject']
  }

  it('rammer den rigtige rute og url-koder id', async () => {
    const fn = mockFetch({ ok: true })
    const res = await actOnDecision(config, init, 'approve')
    expect(String(fn.mock.calls[0][0])).toContain('/mc/initiatives/i%201/approve')
    expect(fn.mock.calls[0][1].method).toBe('POST')
    expect(res.ok).toBe(true)
  })

  it('vælger reject-ruten', async () => {
    const fn = mockFetch({ ok: true })
    await actOnDecision(config, init, 'reject')
    expect(String(fn.mock.calls[0][0])).toContain('/reject')
  })

  it('vælger life-projects-ruten for abandon', async () => {
    const fn = mockFetch({ ok: true })
    await actOnDecision(config, { ...init, kind: 'life_project', id: 'l1' }, 'abandon')
    expect(String(fn.mock.calls[0][0])).toContain('/mc/life-projects/l1/abandon')
  })

  it('tror ikke på HTTP 200 alene — ok:false er et nej', async () => {
    mockFetch({ ok: false, error: 'initiative not found' })
    const res = await actOnDecision(config, init, 'approve')
    expect(res.ok).toBe(false)
    expect(res.error).toBe('initiative not found')
  })

  it('nægter en handling der ikke findes for slagsen, uden at kalde ud', async () => {
    const fn = mockFetch({ ok: true })
    const res = await actOnDecision(config, init, 'abandon')
    expect(res.ok).toBe(false)
    expect(fn).not.toHaveBeenCalled()
  })
})
