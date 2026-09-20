const mockAddEventListener = jest.fn()
const mockClose = jest.fn()

jest.mock('react-native-sse', () => {
  return jest.fn().mockImplementation(() => ({
    addEventListener: mockAddEventListener,
    close: mockClose
  }))
})

import EventSource from 'react-native-sse'
import { startStream } from './streamClient'
import type { StreamEvent } from './sseProtocol'
import type { ApiConfig } from './types'

const config: ApiConfig = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

type Listener = (event: { data?: string | null; message?: string }) => void

const getListener = (name: string): Listener => {
  const call = mockAddEventListener.mock.calls.find(([eventName]) => eventName === name)
  if (!call) {
    throw new Error(`Missing listener for ${name}`)
  }
  return call[1] as Listener
}

beforeEach(() => {
  jest.clearAllMocks()
})

it('forwards parsed events and completes on message_stop', () => {
  const onEvent = jest.fn<void, [StreamEvent]>()
  const onComplete = jest.fn()
  const control = startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent, onComplete }
  )

  getListener('message_start')({
    data: JSON.stringify({
      type: 'message_start',
      message: {
        id: 'm1',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 's1',
        usage: { input_tokens: 0, output_tokens: 0 }
      }
    })
  })
  getListener('message_stop')({
    data: JSON.stringify({ type: 'message_stop' })
  })

  expect(onEvent).toHaveBeenCalledTimes(2)
  expect(onComplete).toHaveBeenCalledTimes(1)
  expect(mockClose).toHaveBeenCalledTimes(1)
  expect(control.getRunId()).toBe('m1')
})

it('captures run id from system_event run payload', () => {
  const onRunId = jest.fn()
  const control = startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent: jest.fn(), onRunId }
  )

  getListener('system_event')({
    data: JSON.stringify({
      type: 'system_event',
      kind: 'run',
      payload: { run_id: 'visible-2' }
    })
  })

  expect(onRunId).toHaveBeenCalledWith('visible-2')
  expect(control.getRunId()).toBe('visible-2')
})

it('reports interruption through error handler', () => {
  const onInterrupted = jest.fn()
  const onError = jest.fn()
  startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent: jest.fn(), onInterrupted, onError }
  )

  getListener('error')({ message: 'Stream interrupted' })

  expect(onInterrupted).toHaveBeenCalledTimes(1)
  expect(onError).toHaveBeenCalledWith(expect.any(Error))
  expect(mockClose).toHaveBeenCalledTimes(1)
})

it('closes and reports malformed json payloads', () => {
  const onEvent = jest.fn<void, [StreamEvent]>()
  const onInterrupted = jest.fn()
  const onError = jest.fn()
  startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent, onInterrupted, onError }
  )

  expect(() => {
    getListener('message_start')({ data: '{not-json' })
  }).not.toThrow()

  expect(onEvent).not.toHaveBeenCalled()
  expect(onInterrupted).toHaveBeenCalledTimes(1)
  expect(onError).toHaveBeenCalledWith(expect.any(Error))
  expect(mockClose).toHaveBeenCalledTimes(1)
})

it('sends the expected request payload and auth header', () => {
  startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej',
      approvalMode: 'trust',
      thinkingMode: 'fast',
      mode: 'code',
      model: 'deepseek-r1',
      providerChoice: 'ollama',
      researchMode: true
    },
    { onEvent: jest.fn() }
  )

  expect(EventSource).toHaveBeenCalledWith(
    'https://api.srvlab.dk/chat/stream/v2',
    expect.objectContaining({
      method: 'POST',
      pollingInterval: 0,
      headers: expect.objectContaining({
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        Authorization: 'Bearer token'
      }),
      body: JSON.stringify({
        message: 'Hej',
        session_id: 's1',
        approval_mode: 'trust',
        // Fladen følger med i kroppen (streamClient.ts:284). Assertionen blev
        // skrevet før feltet kom til, og stod derfor og fejlede på HEAD —
        // uskyldigt for eftertiden, men rødt for enhver der kørte suiten.
        surface: 'mobil',
        thinking_mode: 'fast',
        mode: 'code',
        model: 'deepseek-r1',
        provider_choice: 'ollama',
        research_mode: true,
        attachment_ids: []
      })
    })
  )
})

it('reconnects from offset via subscribe when the socket drops mid-run', () => {
  jest.useFakeTimers()
  const onReconnecting = jest.fn()
  startStream(
    { config, sessionId: 's1', message: 'Hej' },
    { onEvent: jest.fn(), onReconnecting }
  )

  // modtag message_start (offset=1, run_id kendt) + en delta (offset=2)
  getListener('message_start')({
    data: JSON.stringify({
      type: 'message_start',
      message: {
        id: 'visible-x',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 's1',
        usage: { input_tokens: 0, output_tokens: 0 }
      }
    })
  })
  getListener('content_block_delta')({
    data: JSON.stringify({
      type: 'content_block_delta',
      index: 0,
      delta: { type: 'text_delta', text: 'hi' }
    })
  })

  // socket dør (Android-baggrund) → skal planlægge reconnect, ikke fejle
  getListener('error')({ message: 'software caused connection abort' } as never)
  expect(onReconnecting).toHaveBeenCalledWith(1)

  jest.runOnlyPendingTimers()

  expect(EventSource).toHaveBeenCalledWith(
    'https://api.srvlab.dk/chat/runs/visible-x/subscribe?from_idx=2',
    expect.objectContaining({ method: 'GET' })
  )
  jest.useRealTimers()
})

it('treats a 404 on reconnect as benign completion (run finished while away)', () => {
  const onEvent = jest.fn()
  const onError = jest.fn()
  const onReconnecting = jest.fn()
  const onComplete = jest.fn()
  startStream(
    { config, sessionId: 's1', message: 'Hej' },
    { onEvent, onError, onReconnecting, onComplete }
  )

  // run startede (run_id kendt) — vi backgrounder herefter
  getListener('message_start')({
    data: JSON.stringify({
      type: 'message_start',
      message: {
        id: 'visible-x',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 's1',
        usage: { input_tokens: 0, output_tokens: 0 }
      }
    })
  })

  // socket gen-abonnerer, men runnet er allerede færdigt + ryddet → 404
  getListener('error')({ xhrStatus: 404, message: 'run not found' } as never)

  // IKKE en fejl, IKKE en reconnect-loop — afslut graccelt som 'done'
  expect(onError).not.toHaveBeenCalled()
  expect(onReconnecting).not.toHaveBeenCalled()
  expect(onComplete).toHaveBeenCalled()
  expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'message_stop' }))
})

it('omits the authorization header when auth token is empty', () => {
  startStream(
    {
      config: { ...config, authToken: '' },
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent: jest.fn() }
  )

  expect(EventSource).toHaveBeenCalledWith(
    'https://api.srvlab.dk/chat/stream/v2',
    expect.objectContaining({
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json'
      }
    })
  )
})

// ─────────────────────────────────────────────────────────────────────────
// Fase 10, kriterium 3: «fences late old-generation callbacks»
//
// `attach()` kaldes igen ved hver genforbindelse, og den gamle EventSource'ens
// lyttere fjernes ALDRIG — kun `close()`. En sen frame fra en afloest kilde
// kunne derfor stadig taelle `offset` op, nulstille backoff'en og skrive i
// reduceren.
//
// `offset` er GENOPTAGELSES-MAERKET. Taelles den samme logiske frame to gange,
// springer naeste genforbindelse forbi indhold der aldrig blev vist — en tavs
// mangel i samtalen, ikke en fejl nogen ser.
// ─────────────────────────────────────────────────────────────────────────

describe('generations-hegn paa stroemmen', () => {
  /** Hver `new EventSource` faar sine EGNE lyttere, saa generationer kan skilles. */
  function medGenerationer() {
    const gen: { lyt: Record<string, Listener[]>; lukket: boolean }[] = []
    ;(EventSource as unknown as jest.Mock).mockImplementation(() => {
      const g = { lyt: {} as Record<string, Listener[]>, lukket: false }
      gen.push(g)
      return {
        addEventListener: (navn: string, fn: Listener) => {
          (g.lyt[navn] ||= []).push(fn)
        },
        close: () => { g.lukket = true }
      }
    })
    return {
      gen,
      fyr: (i: number, navn: string, event: unknown) => {
        for (const fn of gen[i]?.lyt[navn] ?? []) fn(event as never)
      }
    }
  }

  afterEach(() => {
    jest.useRealTimers()
    ;(EventSource as unknown as jest.Mock).mockImplementation(() => ({
      addEventListener: mockAddEventListener,
      close: mockClose
    }))
  })

  it('en AFLOEST kilde taeller ikke offset op', () => {
    jest.useFakeTimers()
    const { gen, fyr } = medGenerationer()
    const events: StreamEvent[] = []
    const ctrl = startStream(
      { config, message: 'hej' } as never,
      { onEvent: (e: StreamEvent) => { events.push(e) } } as never
    )

    // Generation 0 leverer to frames og laerer sit run_id.
    fyr(0, 'message_start', { data: JSON.stringify({
      type: 'message_start', message: { id: 'visible-1' } }) })
    fyr(0, 'content_block_delta', { data: JSON.stringify({
      type: 'content_block_delta', delta: { text: 'a' } }) })
    expect(ctrl.getOffset()).toBe(2)

    // Forbindelsen dør; klienten planlaegger en genforbindelse.
    fyr(0, 'error', { type: 'error', message: 'brud' })
    jest.advanceTimersByTime(5_000)
    expect(gen.length).toBe(2)

    const foer = ctrl.getOffset()
    // Den GAMLE kilde leverer en sen frame.
    fyr(0, 'content_block_delta', { data: JSON.stringify({
      type: 'content_block_delta', delta: { text: 'spoegelse' } }) })

    expect(ctrl.getOffset()).toBe(foer)
    expect(events.some((e) => JSON.stringify(e).includes('spoegelse'))).toBe(false)
    ctrl.abort()
  })

  it('den AKTUELLE kilde taeller stadig — hegnet maa ikke slukke stroemmen', () => {
    jest.useFakeTimers()
    const { gen, fyr } = medGenerationer()
    const events: StreamEvent[] = []
    const ctrl = startStream(
      { config, message: 'hej' } as never,
      { onEvent: (e: StreamEvent) => { events.push(e) } } as never
    )
    fyr(0, 'message_start', { data: JSON.stringify({
      type: 'message_start', message: { id: 'visible-1' } }) })
    fyr(0, 'error', { type: 'error', message: 'brud' })
    jest.advanceTimersByTime(5_000)
    expect(gen.length).toBe(2)

    const foer = ctrl.getOffset()
    fyr(1, 'content_block_delta', { data: JSON.stringify({
      type: 'content_block_delta', delta: { text: 'aegte' } }) })

    expect(ctrl.getOffset()).toBe(foer + 1)
    expect(events.some((e) => JSON.stringify(e).includes('aegte'))).toBe(true)
    ctrl.abort()
  })

  it('en AFLOEST kilde planlaegger ikke ENDNU en genforbindelse', () => {
    jest.useFakeTimers()
    const { gen, fyr } = medGenerationer()
    const ctrl = startStream(
      { config, message: 'hej' } as never,
      { onEvent: () => {} } as never
    )
    fyr(0, 'message_start', { data: JSON.stringify({
      type: 'message_start', message: { id: 'visible-1' } }) })
    fyr(0, 'error', { type: 'error', message: 'brud' })
    jest.advanceTimersByTime(5_000)
    expect(gen.length).toBe(2)

    // Den gamle fejler igen bagefter — to kilder paa samme run ville begge
    // taelle offset op.
    fyr(0, 'error', { type: 'error', message: 'sent brud' })
    jest.advanceTimersByTime(30_000)
    expect(gen.length).toBe(2)
    ctrl.abort()
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Genoptagelses-maerket taeller KUN log-rammer (16/9-2026).
//
// Pings logges aldrig i run_event_log, men baade den live stroem og subscribe
// sender dem hvert 5. sekund i stilhed. Talte de med, sprang en genoptagelse
// efter N pings N aegte rammer over — tavst.
describe('genoptagelses-maerket', () => {
  const start = () => ({
    data: JSON.stringify({
      type: 'message_start',
      message: { id: 'visible-x', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } }
    })
  })
  const delta = () => ({
    data: JSON.stringify({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'x' } })
  })
  const ping = () => ({ data: JSON.stringify({ type: 'ping' }) })

  it('pings taeller ikke med', () => {
    const ctrl = startStream({ config, sessionId: 's1', message: 'Hej' }, { onEvent: jest.fn() })
    getListener('message_start')(start())
    getListener('ping')(ping())
    getListener('ping')(ping())
    getListener('content_block_delta')(delta())
    getListener('ping')(ping())
    expect(ctrl.getOffset()).toBe(2)
  })

  it('gap-markoeren saetter maerket til serverens position', () => {
    const ctrl = startStream({ config, sessionId: 's1', message: 'Hej' }, { onEvent: jest.fn() })
    getListener('message_start')(start())
    getListener('system_event')({
      data: JSON.stringify({ type: 'system_event', kind: 'relay_gap', resume_idx: 800, detail: 'beskaaret' })
    })
    getListener('content_block_delta')(delta())
    expect(ctrl.getOffset()).toBe(801)
  })

  it('gap-markoer uden position (gammel server) taeller ikke som en ramme', () => {
    const ctrl = startStream({ config, sessionId: 's1', message: 'Hej' }, { onEvent: jest.fn() })
    getListener('message_start')(start())
    getListener('system_event')({ data: JSON.stringify({ type: 'system_event', kind: 'relay_gap' }) })
    expect(ctrl.getOffset()).toBe(1)
  })

  it('genforbindelse efter pings beder om det RIGTIGE indeks', () => {
    jest.useFakeTimers()
    startStream({ config, sessionId: 's1', message: 'Hej' }, { onEvent: jest.fn(), onReconnecting: jest.fn() })
    getListener('message_start')(start())
    for (let i = 0; i < 5; i++) getListener('ping')(ping())
    getListener('content_block_delta')(delta())
    getListener('error')({ message: 'software caused connection abort' } as never)
    jest.runOnlyPendingTimers()
    expect(EventSource).toHaveBeenLastCalledWith(
      'https://api.srvlab.dk/chat/runs/visible-x/subscribe?from_idx=2',
      expect.objectContaining({ method: 'GET' })
    )
    jest.useRealTimers()
  })
})
