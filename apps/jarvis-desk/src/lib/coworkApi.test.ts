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
