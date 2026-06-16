import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiFetch = vi.fn()
vi.mock('./api', () => ({
  apiFetch: (...a: unknown[]) => apiFetch(...a),
}))

import { getConnectors, setEnabled, deleteConnector, startConnect } from './connectorsApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('connectorsApi', () => {
  beforeEach(() => apiFetch.mockReset())

  it('getConnectors henter /api/connectors og returnerer listen', async () => {
    apiFetch.mockResolvedValue({ connectors: [{ id: 'github', connected: false }] })
    const list = await getConnectors(cfg)
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/api/connectors')
    expect(list[0]?.id).toBe('github')
  })

  it('setEnabled POSTer enabled-flag', async () => {
    apiFetch.mockResolvedValue({ ok: true })
    await setEnabled(cfg, 'github', false)
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/api/connectors/github/enabled', { method: 'POST', body: { enabled: false } })
  })

  it('deleteConnector DELETEr connector', async () => {
    apiFetch.mockResolvedValue({ ok: true })
    await deleteConnector(cfg, 'github')
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/api/connectors/github', { method: 'DELETE' })
  })

  it('startConnect henter authorize_url', async () => {
    apiFetch.mockResolvedValue({ authorize_url: 'https://github.com/login/oauth/authorize?x' })
    const url = await startConnect(cfg, 'github')
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/api/oauth/github/start')
    expect(url).toContain('github.com/login/oauth')
  })
})
