import { describe, it, expect, vi, beforeEach } from 'vitest'

const fetchMock = vi.fn()
vi.mock('./api', () => ({
  apiFetch: (...args: unknown[]) => fetchMock(...args),
}))

import { getAccountMe } from './coworkApi'

describe('getAccountMe', () => {
  beforeEach(() => fetchMock.mockReset())

  it('henter /account/me og returnerer profilen', async () => {
    fetchMock.mockResolvedValue({
      user_id: 'u1', email: 'a@x.dk', email_verified: true,
      language: 'da', role: 'owner', tier: 'owner',
    })
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const prof = await getAccountMe(cfg)
    expect(fetchMock).toHaveBeenCalledWith(cfg, '/account/me')
    expect(prof.email).toBe('a@x.dk')
    expect(prof.role).toBe('owner')
  })
})
