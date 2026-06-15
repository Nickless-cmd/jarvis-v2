import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({ apiFetch: (...a: unknown[]) => fetchMock(...a) }))

import { getAccountQuota } from './coworkApi'

describe('getAccountQuota', () => {
  beforeEach(() => fetchMock.mockReset())

  it('henter /account/quota', async () => {
    fetchMock.mockResolvedValue({ tier: 'plus', items: [{ kind: 'chat', used: 5, limit: null, remaining: null, warn: false }] })
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const ov = await getAccountQuota(cfg)
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/account/quota')
    expect(ov.tier).toBe('plus')
    expect(ov.items[0]!.kind).toBe('chat')
  })
})
