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

// Vandmaerket taeller KUN log-rammer (16/9-2026). Se naesteVandmaerke.
describe('genoptagelses-vandmaerket', () => {
  const START = 'event: message_start\ndata: {"type":"message_start","message":{"id":"r1","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n'
  const PING = 'event: ping\ndata: {"type":"ping"}\n\n'
  const DELTA = 'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"x"}}\n\n'
  const GAP = 'event: system_event\ndata: {"type":"system_event","kind":"relay_gap","resume_idx":800,"detail":"beskaaret"}\n\n'

  async function genoptagelsesUrl(foerste: string[]): Promise<string> {
    const kald: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      kald.push(String(url))
      return kald.length === 1
        ? sseResponse(foerste)
        : sseResponse(['event: message_stop\ndata: {"type":"message_stop"}\n\n'])
    }))
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => resolve(), onError: () => resolve(), onInterrupted: () => resolve() },
      )
    })
    return kald[1] ?? ''
  }

  it('pings taeller ikke — genoptagelsen beder om det rigtige indeks', async () => {
    const url = await genoptagelsesUrl([START, PING, PING, DELTA, PING])
    expect(url).toContain('from_idx=2')
  })

  it('gap-markoeren saetter vandmaerket til serverens position', async () => {
    const url = await genoptagelsesUrl([START, GAP, DELTA])
    expect(url).toContain('from_idx=801')
  })
})

/**
 * 5xx MED en forklaring — serverens ægte besked skal frem (8/10-2026).
 *
 * Baggrunden, målt: 503-blokaden på /chat/stream bar beskeden «Medlemschat er
 * midlertidigt sat på pause…». Klienten klassificerede den som `server` +
 * retryable — og på en frisk POST findes intet run_id at genoptage på, så den
 * faldt igennem til onInterrupted. UI'et viste «Forbindelse afbrudt».
 * Brugeren fik altså en løgn om forbindelsen for en besked der lå lige for.
 */
describe('5xx med forklaring → refused, ikke «Forbindelse afbrudt»', () => {
  function fejlSvar(status: number, krop: string, type = 'application/json'): Response {
    return new Response(krop, { status, headers: { 'content-type': type } })
  }

  /** Kører én POST mod et givet fejlsvar og fanger HVILKEN udgang der valgtes. */
  async function kør(svar: Response): Promise<{ udfald: unknown; afbrudt: boolean }> {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(svar))
    let afbrudt = false
    const udfald = await new Promise<unknown>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        {
          onEvent: () => {},
          onError: (e) => resolve(e),
          onInterrupted: () => { afbrudt = true; resolve('INTERRUPTED') },
          onComplete: () => resolve('COMPLETE'),
        },
      )
    })
    return { udfald, afbrudt }
  }

  it('503 med detail → onError med serverens ord, og ALDRIG onInterrupted', async () => {
    const { udfald, afbrudt } = await kør(fejlSvar(503, JSON.stringify({
      detail: 'Medlemschat er midlertidigt sat på pause, mens vi retter en privatlivsfejl.',
    })))
    expect(afbrudt).toBe(false)
    const e = udfald as { category: string; message: string; retryable: boolean; statusCode: number | null }
    expect(e.category).toBe('refused')
    expect(e.message).toBe('Medlemschat er midlertidigt sat på pause, mens vi retter en privatlivsfejl.')
    expect(e.retryable).toBe(false)
    expect(e.statusCode).toBe(503)
  })

  it('beskeden er den brugeren ser — userMessage giver serverens ord uændret', async () => {
    const { udfald } = await kør(fejlSvar(503, JSON.stringify({ detail: 'Køen er lukket for i dag.' })))
    expect((udfald as { userMessage: () => string }).userMessage()).toBe('Køen er lukket for i dag.')
  })

  it('503 UDEN detail (proxy-HTML) → den gamle vej er intakt', async () => {
    // Ingen struktur at læse → vi påstår ikke at kende årsagen. Uændret adfærd.
    const { udfald, afbrudt } = await kør(fejlSvar(503, '<html>Bad Gateway</html>', 'text/html'))
    expect(afbrudt).toBe(true)
    expect(udfald).toBe('INTERRUPTED')
  })

  it('500 med detail → refused også — reglen er 5xx, ikke kun 503', async () => {
    const { udfald } = await kør(fejlSvar(500, JSON.stringify({ detail: 'Databasen er låst.' })))
    expect((udfald as { category: string }).category).toBe('refused')
  })

  it('403 med token-ord er stadig auth — 403-reglen blev ikke slået i stykker', async () => {
    const { udfald } = await kør(fejlSvar(403, JSON.stringify({ detail: 'token udløbet' })))
    expect((udfald as { category: string }).category).toBe('auth')
  })
})
