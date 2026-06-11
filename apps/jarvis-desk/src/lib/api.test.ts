import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cancelRun, getSession, createSession } from './api'

const cfg = { apiBaseUrl: 'http://test', authToken: 't' }

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('cancelRun', () => {
  it('POSTs to /chat/runs/{id}/cancel and resolves on 200', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'cancelled' }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(cancelRun(cfg, 'visible-9')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/chat/runs/visible-9/cancel'), expect.objectContaining({ method: 'POST' }))
  })
  it('treats 404 (unknown run) as already-cancelled (no throw)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))
    await expect(cancelRun(cfg, 'gone')).resolves.toBeUndefined()
  })
  it('swallows network error (aborts locally anyway)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
    await expect(cancelRun(cfg, 'r')).resolves.toBeUndefined()
  })
})

describe('createSession unwraps { session: {...} }', () => {
  it('returns the inner session with a real id (ikke undefined)', async () => {
    const payload = { session: { id: 'chat-abc', title: 'Ny samtale', updated_at: 'x', message_count: 0 } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'content-type': 'application/json' } })))
    const sess = await createSession(cfg, 'Ny samtale')
    expect(sess.id).toBe('chat-abc')
    expect(sess.title).toBe('Ny samtale')
  })
})

describe('getSession normalizes string content to blocks', () => {
  it('wraps assistant string content in a text block', async () => {
    const payload = { session: { id: 's', title: 't', updated_at: 'x', messages: [{ id: 'm1', role: 'assistant', content: '**hi**', created_at: 'x' }] } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'content-type': 'application/json' } })))
    const { messages } = await getSession(cfg, 's')
    expect(messages[0]?.content).toEqual([{ type: 'text', text: '**hi**' }])
  })
})
