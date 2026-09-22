import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cancelRun, getSession, createSession, apiFetch } from './api'
import { StreamError } from './streamClient'

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

// V6: «tom» maa ikke ligne «brudt». Serveren svarer nu 401 (ikke et tomt
// 200-svar) ved manglende/udloebet bruger-binding for baade GET /notifikationer
// og GET /notifikations-valg. apiFetch skal KASTE paa 401 — ikke returnere
// noget der ligner et gyldigt, tomt svar — saa kalderne (NotifikationsFeed,
// NotifikationsValg) rammer deres fejl-gren i stedet for "Ingen
// notifikationer — alt er klaret".
describe('V6: 401 paa notifikations-endpoints kaster, det stille-fejler ikke', () => {
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
