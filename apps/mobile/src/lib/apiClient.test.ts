import {
  ApiError,
  apiFetch,
  approveTool,
  createSession,
  denyTool,
  getSession,
  googleLinkStart,
  googleLoginResult,
  googleLoginStart,
  health,
  listSessions,
  cancelRunById,
  getActiveRunSnapshot,
  steerRun,
  whoami
} from './apiClient'
import type { ApiConfig } from './types'

const config: ApiConfig = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

beforeEach(() => {
  global.fetch = jest.fn()
})

it('reads active run snapshots for resumable mobile UI', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      sessions: [{ session_id: 's1', run_id: 'r1', status: 'working' }]
    })
  })

  await expect(getActiveRunSnapshot(config)).resolves.toEqual([
    { sessionId: 's1', runId: 'r1', status: 'working' }
  ])
})

it('adds bearer token and reads whoami', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      user_id: 'u1',
      user_display_name: 'Bjørn',
      role: 'owner'
    })
  })

  await expect(whoami(config)).resolves.toEqual({
    user_id: 'u1',
    display_name: 'Bjørn',
    role: 'owner'
  })
  expect(global.fetch).toHaveBeenCalledWith(
    expect.stringContaining('/api/whoami'),
    expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer token'
      })
    })
  )
})

it('unwraps session list variants', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      items: [{ id: 's1', title: 'T', updated_at: 'now' }]
    })
  })

  await expect(listSessions(config)).resolves.toHaveLength(1)
})

it('unwraps created session', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      session: { id: 's2', title: 'Ny', updated_at: 'now' }
    })
  })

  await expect(createSession(config)).resolves.toMatchObject({ id: 's2' })
})

it('reads a session with messages', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      session: {
        id: 's2',
        title: 'Ny',
        updated_at: 'now',
        messages: [{ id: 'm1', role: 'user', content: 'Hej', created_at: 'now' }]
      }
    })
  })

  await expect(getSession(config, 's2')).resolves.toEqual({
    session: {
      id: 's2',
      title: 'Ny',
      updated_at: 'now',
      messages: [{ id: 'm1', role: 'user', content: 'Hej', created_at: 'now' }]
    },
    messages: [{ id: 'm1', role: 'user', content: 'Hej', created_at: 'now' }]
  })
})

it('classifies auth errors', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: false,
    status: 401,
    json: async () => ({})
  })

  await expect(whoami(config)).rejects.toMatchObject(new ApiError('auth', 'HTTP 401', 401))
})

it('posts explicit approval decisions', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({})
  })

  await approveTool(config, 'approval 1')
  await denyTool(config, 'approval 2')

  expect(global.fetch).toHaveBeenNthCalledWith(
    1,
    expect.stringContaining('/chat/approvals/approval%201/approve'),
    expect.objectContaining({ method: 'POST' })
  )
  expect(global.fetch).toHaveBeenNthCalledWith(
    2,
    expect.stringContaining('/chat/approvals/approval%202/deny'),
    expect.objectContaining({ method: 'POST' })
  )
})

it('styrer og afbryder aktive runs via run-id endpoints', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ ok: true })
  })

  await steerRun(config, 'run/1', 'brug den lille løsning')
  await cancelRunById(config, 'run/1')

  expect(global.fetch).toHaveBeenNthCalledWith(
    1,
    expect.stringContaining('/chat/runs/run%2F1/steer'),
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ content: 'brug den lille løsning' })
    })
  )
  expect(global.fetch).toHaveBeenNthCalledWith(
    2,
    expect.stringContaining('/chat/runs/run%2F1/cancel'),
    expect.objectContaining({ method: 'POST' })
  )
})

it('checks API health without bearer auth', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200
  })

  await expect(health('https://api.srvlab.dk/')).resolves.toBe(true)
  expect(global.fetch).toHaveBeenCalledWith(
    'https://api.srvlab.dk/health',
    expect.objectContaining({
      headers: { Accept: 'application/json' }
    })
  )
})

it('starts Google login without bearer auth and polls the result', async () => {
  ;(global.fetch as jest.Mock)
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth', nonce: 'n1' })
    })
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok', token: 'jarvis-token', role: 'member', user_id: 'u1' })
    })

  await expect(googleLoginStart('https://api.srvlab.dk/', 'jarvis-mobile')).resolves.toEqual({
    authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth',
    nonce: 'n1'
  })
  await expect(googleLoginResult('https://api.srvlab.dk/', 'n1')).resolves.toEqual({
    status: 'ok',
    token: 'jarvis-token',
    role: 'member',
    user_id: 'u1'
  })

  expect(global.fetch).toHaveBeenNthCalledWith(
    1,
    'https://api.srvlab.dk/api/auth/google/start?app_id=jarvis-mobile'
  )
  expect(global.fetch).toHaveBeenNthCalledWith(
    2,
    'https://api.srvlab.dk/api/auth/google/result?nonce=n1'
  )
})

it('starts Google account linking with bearer auth', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ authorize_url: 'https://accounts.google.com/link', nonce: 'link-nonce' })
  })

  await expect(googleLinkStart(config)).resolves.toEqual({
    authorize_url: 'https://accounts.google.com/link',
    nonce: 'link-nonce'
  })
  expect(global.fetch).toHaveBeenCalledWith(
    expect.stringContaining('/api/auth/google/link/start'),
    expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer token'
      })
    })
  )
})

describe('serverens forklaring når et kald fejler', () => {
  const cfg = { apiBaseUrl: 'https://x.test', authToken: 't' } as never

  function svar(status: number, body: unknown) {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false, status,
      json: async () => body,
    }) as never
  }

  it('bruger detail frem for statuskoden', async () => {
    // Set live: en godkendelse afvist som «stale» viste sig som «HTTP 409».
    svar(409, { detail: 'Capability approval request is stale and must be recreated' })
    await expect(apiFetch(cfg, '/x')).rejects.toThrow(/stale and must be recreated/)
  })

  it('falder tilbage til koden når kroppen ikke er JSON', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false, status: 409,
      json: async () => { throw new Error('ikke json') },
    }) as never
    await expect(apiFetch(cfg, '/x')).rejects.toThrow(/HTTP 409/)
  })

  it('tager første besked i en validerings-liste', async () => {
    svar(422, { detail: [{ msg: 'field required' }] })
    await expect(apiFetch(cfg, '/x')).rejects.toThrow(/field required/)
  })

  it('tom detail giver stadig en brugbar besked', async () => {
    svar(409, { detail: '   ' })
    await expect(apiFetch(cfg, '/x')).rejects.toThrow(/HTTP 409/)
  })
})
