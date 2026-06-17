import {
  ApiError,
  approveTool,
  createSession,
  denyTool,
  getSession,
  googleLinkStart,
  googleLoginResult,
  googleLoginStart,
  health,
  listSessions,
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
