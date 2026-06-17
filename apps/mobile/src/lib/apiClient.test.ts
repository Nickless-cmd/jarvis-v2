import {
  ApiError,
  approveTool,
  createSession,
  denyTool,
  getSession,
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
