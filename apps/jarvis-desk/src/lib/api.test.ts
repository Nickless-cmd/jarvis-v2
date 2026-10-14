import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cancelRun, getSession, createSession, apiFetch, followRun } from './api'
import { StreamError } from './streamClient'
import { onUnauthorized } from './authEvents'

const cfg = { apiBaseUrl: 'http://test', authToken: 't' }

beforeEach(() => {
  vi.restoreAllMocks()
})

it('passiv desk følger det konkrete run med GET', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)
  followRun(cfg, 's1', vi.fn(), vi.fn(), 'run-2')
  await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
  expect(fetchMock).toHaveBeenCalledWith(
    'http://test/chat/runs/run-2/subscribe?from_idx=0',
    expect.objectContaining({ method: 'GET' })
  )
})

function sseResponse(events: unknown[]): Response {
  const body = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('followRun authoritative reconnect contract', () => {
  it.each([404, 410])('%s reconciles without inventing message_stop', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status })))
    const onEvent = vi.fn()
    const onDone = vi.fn()
    followRun(cfg, 's1', onEvent, onDone, 'finished-run')
    await vi.waitFor(() => expect(onDone).toHaveBeenCalledOnce())
    expect(onDone).toHaveBeenCalledWith('reconcile')
    expect(onEvent).not.toHaveBeenCalled()
  })

  it.each([401, 403])('%s is an error and never a terminal', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status })))
    const onEvent = vi.fn()
    const onDone = vi.fn()
    followRun(cfg, 's1', onEvent, onDone, 'run-auth')
    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('error'))
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('reconnects after 503 from the current cursor', async () => {
    vi.useFakeTimers()
    try {
      const fetchMock = vi.fn()
        .mockResolvedValueOnce(sseResponse([{ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'a' } }]))
        .mockResolvedValueOnce(new Response(null, { status: 503 }))
        .mockResolvedValueOnce(sseResponse([{ type: 'message_stop' }]))
      vi.stubGlobal('fetch', fetchMock)
      const onDone = vi.fn()
      const control = followRun(cfg, 's1', vi.fn(), onDone, 'run-retry')
      await vi.runAllTimersAsync()
      await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('terminal'))
      expect(fetchMock.mock.calls[1]?.[0]).toContain('from_idx=1')
      expect(fetchMock.mock.calls[2]?.[0]).toContain('from_idx=1')
      expect(control.getOffset()).toBe(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('pings do not advance and relay_gap replaces the cursor base', async () => {
    vi.useFakeTimers()
    try {
      const fetchMock = vi.fn()
        .mockResolvedValueOnce(sseResponse([
          { type: 'ping' },
          { type: 'system_event', kind: 'relay_gap', resume_idx: 7, payload: {} },
        ]))
        .mockResolvedValueOnce(sseResponse([{ type: 'message_stop' }]))
      vi.stubGlobal('fetch', fetchMock)
      const done = vi.fn()
      const control = followRun(cfg, 's1', vi.fn(), done, 'run-gap')
      await vi.runAllTimersAsync()
      await vi.waitFor(() => expect(done).toHaveBeenCalledWith('terminal'))
      expect(fetchMock.mock.calls[1]?.[0]).toContain('from_idx=7')
      expect(control.getOffset()).toBe(8)
    } finally {
      vi.useRealTimers()
    }
  })

  it('a real message_stop completes exactly once', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([{ type: 'message_stop' }])))
    const onEvent = vi.fn()
    const onDone = vi.fn()
    const control = followRun(cfg, 's1', onEvent, onDone, 'run-stop')
    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('terminal'))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenCalledWith({ type: 'message_stop' })
    expect(control.getRunId()).toBe('run-stop')
  })

  it('real frame progress resets the retry budget for long runs', async () => {
    vi.useFakeTimers()
    try {
      const fetchMock = vi.fn()
      for (let i = 0; i < 7; i += 1) {
        fetchMock.mockResolvedValueOnce(sseResponse([
          { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: String(i) } },
        ]))
      }
      fetchMock.mockResolvedValueOnce(sseResponse([{ type: 'message_stop' }]))
      vi.stubGlobal('fetch', fetchMock)
      const onDone = vi.fn()

      followRun(cfg, 's1', vi.fn(), onDone, 'run-long')
      await vi.runAllTimersAsync()
      await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('terminal'))

      expect(fetchMock).toHaveBeenCalledTimes(8)
      expect(onDone).not.toHaveBeenCalledWith('error')
    } finally {
      vi.useRealTimers()
    }
  })
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

// V6: «tom» maa ikke ligne «brudt». Serveren svarer nu 401 (ikke et tomt
// 200-svar) ved manglende/udloebet bruger-binding for baade GET /notifikationer
// og GET /notifikations-valg. apiFetch skal KASTE paa 401 — ikke returnere
// noget der ligner et gyldigt, tomt svar — saa kalderne (NotifikationsFeed,
// NotifikationsValg) rammer deres fejl-gren i stedet for "Ingen
// notifikationer — alt er klaret".
describe('V6: 401 paa notifikations-endpoints kaster, det stille-fejler ikke', () => {
  it('reports 401 to browser login but keeps 403 as an authorization error', async () => {
    let count = 0
    const stop = onUnauthorized(() => { count += 1 })
    try {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('', { status: 401 }))
        .mockResolvedValueOnce(new Response('', { status: 403 })))
      await expect(apiFetch(cfg, '/chat/sessions')).rejects.toBeInstanceOf(StreamError)
      expect(count).toBe(1)
      await expect(apiFetch(cfg, '/mc/runtime')).rejects.toBeInstanceOf(StreamError)
      expect(count).toBe(1)
    } finally { stop() }
  })

  it('GET /notifikationer paa 401 kaster en ikke-genforsoegsbar auth-fejl', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })))
    await expect(apiFetch(cfg, '/notifikationer')).rejects.toMatchObject({
      name: 'StreamError', category: 'auth', retryable: false,
    })
  })

  it('GET /notifikations-valg paa 401 kaster ligesaa', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 401 })))
    await expect(apiFetch(cfg, '/notifikations-valg')).rejects.toBeInstanceOf(StreamError)
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

  it('revaliderer med ETag og returnerer null ved et uændret transcript', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, {
      status: 304,
      headers: { etag: 'W/"v1"' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    const snapshot = await getSession(cfg, 's', { ifNoneMatch: 'W/"v1"' })

    expect(snapshot).toBeNull()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/s'),
      expect.objectContaining({
        cache: 'no-store',
        headers: expect.objectContaining({ 'If-None-Match': 'W/"v1"' }),
      }),
    )
  })

  it('giver ETag videre sammen med et ændret transcript', async () => {
    const payload = { session: { id: 's', title: 't', updated_at: 'x', messages: [] } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json', etag: 'W/"v2"' },
    })))

    const snapshot = await getSession(cfg, 's')

    expect(snapshot?.etag).toBe('W/"v2"')
  })
})

describe('getTree', () => {
  it('henter entries fra /chat/tree med kind+root', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ entries: [{ name: 'src', kind: 'dir' }] }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)
    const { getTree } = await import('./api')
    const out = await getTree(cfg, 'container', 'core', '')
    expect(out).toEqual([{ name: 'src', kind: 'dir' }])
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/chat/tree?kind=container'), expect.anything(),
    )
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Fase 10, kriterium 4: «connection retry never replays a unary mutation»
//
// Maalt 13/9-2026: `retries = 2` var METODE-AGNOSTISK. Loekken gentog paa
// timeout (10 s), netvaerksfejl og 5xx uden at se paa metoden, og disse arvede
// den uden vaern eller idempotens-noegle:
//
//   POST /chat/git/commit-all   POST /chat/git/create-pr
//   POST /chat/file             POST /central/command
//
// En git-operation over ti sekunder ville altsaa blive sendt igen.
// ─────────────────────────────────────────────────────────────────────────

describe('gentagelse maa aldrig gentage en HANDLING', () => {
  function taellende503() {
    const f = vi.fn().mockResolvedValue(new Response('nej', { status: 503 }))
    vi.stubGlobal('fetch', f)
    return f
  }

  it('POST sendes ÉN gang selv naar serveren svarer 503', async () => {
    const f = taellende503()
    await expect(
      apiFetch(cfg, '/chat/git/commit-all', { method: 'POST' }),
    ).rejects.toBeTruthy()
    expect(f).toHaveBeenCalledTimes(1)
  })

  it('DELETE og PUT gentages heller ikke', async () => {
    for (const method of ['DELETE', 'PUT'] as const) {
      const f = taellende503()
      await expect(apiFetch(cfg, '/x', { method })).rejects.toBeTruthy()
      expect(f).toHaveBeenCalledTimes(1)
      vi.unstubAllGlobals()
    }
  })

  it('GET gentages STADIG — en gentagen laesning koster tid, ikke en handling', async () => {
    const f = taellende503()
    await expect(apiFetch(cfg, '/chat/sessions')).rejects.toBeTruthy()
    expect(f).toHaveBeenCalledTimes(3)   // 1 forsoeg + 2 gentagelser
  })

  it('en kalder kan STADIG bede om gentagelse eksplicit', async () => {
    // Doeren staar aaben for et endpoint der beviseligt er idempotent — men
    // valget skal traeffes af den der VED det, ikke af en default.
    const f = taellende503()
    await expect(
      apiFetch(cfg, '/noget/idempotent', { method: 'POST', retries: 2 }),
    ).rejects.toBeTruthy()
    expect(f).toHaveBeenCalledTimes(3)
  })
})
