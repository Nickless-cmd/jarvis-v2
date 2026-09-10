import { describe, it, expect, vi } from 'vitest'
import { startStream } from './streamClient'

function sseResponse(chunks: string[]): Response {
  const body = new ReadableStream({
    start(controller) {
      const enc = new TextEncoder()
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('startStream R1-R3', () => {
  it('calls onRunId with message_start id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"visible-42","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    const runIds: string[] = []
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onRunId: (id) => runIds.push(id), onComplete: () => resolve() },
      )
    })
    expect(runIds).toEqual(['visible-42'])
  })

  it('message_stop → onComplete og IKKE onInterrupted (ingen falsk genoptag)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n',
      'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"ok"}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    let completed = false
    let interrupted = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => { completed = true; resolve() }, onInterrupted: () => { interrupted = true; resolve() } },
      )
    })
    expect(completed).toBe(true)
    expect(interrupted).toBe(false)
  })

  it('message_stop stopper ping-watchdog (ingen falsk hung efter svar)', async () => {
    vi.useFakeTimers()
    try {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
        'event: message_start\ndata: {"type":"message_start","message":{"id":"","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
        'event: message_stop\ndata: {"type":"message_stop"}\n\n',
      ])))
      let hung = false
      let completed = false
      const done = new Promise<void>((resolve) => {
        startStream(
          { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
          { onEvent: () => {}, onComplete: () => { completed = true; resolve() }, onHung: () => { hung = true } },
        )
      })
      await vi.runAllTimersAsync()
      await done
      vi.advanceTimersByTime(120_000) // 2 min efter svar — watchdog må IKKE fyre
      expect(completed).toBe(true)
      expect(hung).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  // FASE 10. Testen her haevdede foer at klienten GAV OP paa et brudt stream.
  // Den beskyttede konklusionen, ikke praemissen. Praemissen — «aldrig en
  // re-POST, for den ville duplikere brugerbeskeden og lave et nyt run» — er
  // stadig sand og staar nu direkte i asserts. Men re-POST er ikke den eneste
  // genforbindelse: serveren har en run-log, og `subscribe` er en REN
  // LAESNING fra et vandmaerke. Mobil-klienten har brugt den hele tiden.
  it('genoptager via GET subscribe i stedet for at give op — og re-POSTer ALDRIG', async () => {
    const kald: Array<{ url: string; method: string }> = []
    const fetchMock = vi.fn(async (url: string, init?: { method?: string }) => {
      kald.push({ url: String(url), method: String(init?.method ?? 'GET') })
      if (kald.length === 1) {
        // Foerste forbindelse: run_id kommer, saa brister stroemmen.
        return sseResponse([
          'event: message_start\ndata: {"type":"message_start","message":{"id":"r1","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
        ])
      }
      return sseResponse([
        'event: message_stop\ndata: {"type":"message_stop"}\n\n',
      ])
    })
    vi.stubGlobal('fetch', fetchMock)

    let genforbandt = 0
    let afbrudt = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        {
          onEvent: () => {},
          onReconnecting: () => { genforbandt += 1 },
          onInterrupted: () => { afbrudt = true; resolve() },
          onComplete: () => resolve(),
          onError: () => resolve(),
        },
      )
    })

    expect(genforbandt).toBeGreaterThan(0)
    expect(afbrudt).toBe(false)
    expect(kald.length).toBeGreaterThan(1)
    // PRAEMISSEN: praecis ÉN POST. Alt andet er laesninger.
    expect(kald.filter((k) => k.method === 'POST')).toHaveLength(1)
    const genoptagelse = kald[1]!
    expect(genoptagelse.method).toBe('GET')
    expect(genoptagelse.url).toContain('/chat/runs/r1/subscribe')
    expect(genoptagelse.url).toContain('from_idx=1')     // én frame set
  })

  it('giver op naar run_id er ukendt — der er intet at genoptage', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sseResponse([]))
    vi.stubGlobal('fetch', fetchMock)
    let afbrudt = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onInterrupted: () => { afbrudt = true; resolve() },
          onError: () => resolve() },
      )
    })
    expect(afbrudt).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)      // ingen re-POST
  })

  it('404 paa genoptagelse er FAERDIG, ikke fejl', async () => {
    // Runnet blev faerdigt og ryddet server-side mens vi var vaek. Svaret
    // ligger i sessionen; UI'et henter det ved naeste select.
    let n = 0
    vi.stubGlobal('fetch', vi.fn(async () => {
      n += 1
      if (n === 1) {
        return sseResponse([
          'event: message_start\ndata: {"type":"message_start","message":{"id":"r9","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
        ])
      }
      return { ok: false, status: 404, body: null } as unknown as Response
    }))
    let faerdig = false
    let fejl = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => { faerdig = true; resolve() },
          onInterrupted: () => resolve(),
          onError: () => { fejl = true; resolve() } },
      )
    })
    expect(faerdig).toBe(true)
    expect(fejl).toBe(false)
  })

  it('returns an abort handle with getRunId', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"visible-7","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    const handle = await new Promise<{ abort: () => void; getRunId: () => string | null }>((resolve) => {
      const h = startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => resolve(h) },
      )
    })
    expect(typeof handle.abort).toBe('function')
    expect(handle.getRunId()).toBe('visible-7')
  })
})
