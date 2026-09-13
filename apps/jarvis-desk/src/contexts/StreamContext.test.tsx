import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act } from '@testing-library/react'
import { StreamProvider } from './StreamContext'
import { useStream } from '../hooks/useStream'

interface FakeHandlers {
  onEvent: (e: unknown) => void
  onRunId: (id: string) => void
  onHung: () => void
  onInterrupted: () => void
  onError: (e: Error) => void
  onComplete: () => void
}
const handlersRef: { current: FakeHandlers | null } = { current: null }

// Standard-implementeringen kan overtages pr. test, saa en test kan samle ALLE
// generationer i stedet for kun den seneste.
const startStreamImpl: { current: ((r: unknown, h: FakeHandlers) => unknown) | null } = {
  current: null,
}
vi.mock('../lib/streamClient', () => ({
  startStream: (_req: unknown, handlers: FakeHandlers) => {
    if (startStreamImpl.current) return startStreamImpl.current(_req, handlers)
    handlersRef.current = handlers
    return { abort: vi.fn(), getRunId: () => 'visible-1' }
  },
  StreamError: class extends Error { category = 'unknown'; retryable = false },
}))
const cancelRunMock = vi.fn().mockResolvedValue(undefined)
const followRunMock = vi.fn((..._a: unknown[]) => ({ abort: vi.fn() }))
vi.mock('../lib/api', () => ({
  cancelRun: (...a: unknown[]) => cancelRunMock(...a),
  approveTool: vi.fn(),
  denyTool: vi.fn(),
  followRun: (...a: unknown[]) => followRunMock(...a),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }
const wrapper = ({ children }: { children: ReactNode }) => (
  <StreamProvider config={cfg}>{children}</StreamProvider>
)

describe('StreamContext', () => {
  it('send → working, message_stop → done', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => {
      handlersRef.current?.onRunId('visible-1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'visible-1', model: 'm', provider: 'p', lane: 'l', session_id: 's', usage: { input_tokens: 0, output_tokens: 0 } } })
    })
    expect(result.current.status).toBe('working')
    act(() => { handlersRef.current?.onEvent({ type: 'message_stop' }) })
    expect(result.current.status).toBe('done')
  })

  it('onHung → hung status', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => { handlersRef.current?.onHung() })
    expect(result.current.status).toBe('hung')
  })

  it('abort() calls cancelRun with active run_id then aborts', async () => {
    cancelRunMock.mockClear()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => { handlersRef.current?.onRunId('visible-1') })
    await act(async () => { await result.current.abort() })
    expect(cancelRunMock).toHaveBeenCalledWith(cfg, 'visible-1')
  })

  it('app_action_request → pendingAppAction; survives message_stop; armable auto-continue', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('ret bug i db.py', { sessionId: 's' }) })
    act(() => {
      handlersRef.current?.onEvent({
        type: 'system_event',
        kind: 'app_action_request',
        payload: { action: 'switch_to_code_mode', reason: 'kræver filer', original_message: 'ret bug i db.py' },
      })
    })
    expect(result.current.pendingAppAction).toEqual({
      action: 'switch_to_code_mode',
      reason: 'kræver filer',
      originalMessage: 'ret bug i db.py',
    })
    // Kortet skal OVERLEVE message_stop (Jarvis afslutter turen; kortet bliver stående).
    act(() => { handlersRef.current?.onEvent({ type: 'message_stop' }) })
    expect(result.current.pendingAppAction).not.toBeNull()

    // Auto-continue arm/consume.
    act(() => { result.current.armAutoContinue('ret bug i db.py') })
    expect(result.current.autoContinue).toBe('ret bug i db.py')
    let consumed: string | null = null
    act(() => { consumed = result.current.consumeAutoContinue() })
    expect(consumed).toBe('ret bug i db.py')
    expect(result.current.autoContinue).toBeNull()

    // clearAppAction rydder kortet.
    act(() => { result.current.clearAppAction() })
    expect(result.current.pendingAppAction).toBeNull()
  })

  it('error-system_event → status=error + struktureret streamError; clearError rydder', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    act(() => {
      handlersRef.current?.onEvent({
        type: 'system_event', kind: 'error',
        payload: { type: 'error', code: 'provider_rate_limited', severity: 'warning',
                   message: 'Rate-limited', fix_hint: 'Vent lidt', retryable: true,
                   correlation_id: 'visible-1' },
      })
    })
    expect(result.current.status).toBe('error')
    expect(result.current.streamError?.code).toBe('provider_rate_limited')
    expect(result.current.streamError?.severity).toBe('warning')
    expect(result.current.streamError?.retryable).toBe(true)
    // FIX: clearError virker (var no-op før).
    act(() => { result.current.clearError() })
    expect(result.current.streamError).toBeNull()
    expect(result.current.status).not.toBe('error')
  })

  it('netværksfejl → auto-reconnect (status=reconnecting + followRun kaldt), ikke terminal error', () => {
    followRunMock.mockClear()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    const netErr = Object.assign(new Error('net'), { category: 'network', retryable: true })
    act(() => { handlersRef.current?.onError(netErr as unknown as Error) })
    expect(result.current.status).toBe('reconnecting')
    expect(result.current.streamError).toBeNull() // ikke en terminal fejl
  })

  it('ikke-retryable fejl → terminal error med struktureret besked', () => {
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    const authErr = Object.assign(new Error('401'), { category: 'auth', retryable: false })
    act(() => { handlersRef.current?.onError(authErr as unknown as Error) })
    expect(result.current.status).toBe('error')
    expect(result.current.streamError?.code).toBe('auth')
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Fase 10, kriterium 3: «fences late old-generation callbacks»
//
// Maalt 13/9-2026: baade `controlRef.current = startStream(...)` og
// `reconnectCtrlRef.current = followRun(...)` blev overskrevet UDEN at den
// forrige blev afbrudt. To stroemme dispatchede ind i samme reducer.
// ─────────────────────────────────────────────────────────────────────────

describe('generations-hegn i StreamContext', () => {
  /** Saml ALLE handler-saet, ikke kun det seneste. */
  function alleGenerationer() {
    const gen: { handlers: FakeHandlers; abort: ReturnType<typeof vi.fn> }[] = []
    startStreamImpl.current = (_req: unknown, handlers: FakeHandlers) => {
      const abort = vi.fn()
      gen.push({ handlers, abort })
      return { abort, getRunId: () => `visible-${gen.length}` }
    }
    return gen
  }

  // Uden den her laekker overtagelsen til de FOELGENDE describe-blokke, og
  // `handlersRef` bliver aldrig fyldt dér. Min egen reattach-test maalte
  // ingenting paa grund af det.
  afterEach(() => { startStreamImpl.current = null })

  it('et nyt send AFBRYDER den forrige stroem', () => {
    const gen = alleGenerationer()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('en', { sessionId: 's' }) })
    act(() => { result.current.send('to', { sessionId: 's' }) })
    expect(gen.length).toBe(2)
    expect(gen[0]!.abort).toHaveBeenCalled()
  })

  it('en AFLOEST stroem skriver ikke i tilstanden', () => {
    const gen = alleGenerationer()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('en', { sessionId: 's' }) })
    act(() => { result.current.send('to', { sessionId: 's' }) })

    // Den GAMLE generation leverer en sen fejl-ramme.
    act(() => {
      gen[0]!.handlers.onEvent({
        type: 'system_event', kind: 'error',
        payload: { message: 'spoegelse fra en doed stroem' },
      })
    })
    expect(JSON.stringify(result.current.streamError ?? {}))
      .not.toContain('spoegelse')
  })

  it('den AKTUELLE stroem skriver stadig — hegnet maa ikke slukke den', () => {
    const gen = alleGenerationer()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('en', { sessionId: 's' }) })
    act(() => { result.current.send('to', { sessionId: 's' }) })
    act(() => {
      gen[1]!.handlers.onEvent({
        type: 'system_event', kind: 'error',
        payload: { message: 'aegte fejl' },
      })
    })
    expect(JSON.stringify(result.current.streamError ?? {})).toContain('aegte fejl')
  })
})

describe('generations-hegn paa reattach', () => {
  /** Saml alle `followRun`-kald med hver sin handler og abort-spion. */
  function alleFollows() {
    const gen: { paaEvent: (e: unknown) => void; abort: ReturnType<typeof vi.fn> }[] = []
    followRunMock.mockImplementation(
      (..._a: unknown[]) => {
        const abort = vi.fn()
        gen.push({ paaEvent: _a[2] as (e: unknown) => void, abort })
        return { abort }
      },
    )
    return gen
  }

  // `reattach` planlaegger sit arbejde med `setTimeout(arm, delay)`. Uden
  // falske timere sker der INTET, og testen maaler ingenting — hvilket var
  // praecis hvad foerste udgave gjorde.
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers(); followRunMock.mockReset() })

  /** Fremkald en netvaerksfejl, som er det der udloeser `reattach`. */
  function brudPaaNettet() {
    const fejl = Object.assign(new Error('brud'), {
      category: 'network', retryable: true,
    })
    act(() => { (handlersRef.current as unknown as {
      onError: (e: Error) => void }).onError(fejl as Error) })
    act(() => { vi.advanceTimersByTime(10_000) })
  }

  it('et nyt reattach AFBRYDER det forrige', () => {
    const gen = alleFollows()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    brudPaaNettet()
    brudPaaNettet()
    expect(gen.length).toBeGreaterThanOrEqual(2)
    expect(gen[0]!.abort).toHaveBeenCalled()
  })

  it('et AFLOEST reattach skriver ikke i tilstanden', () => {
    const gen = alleFollows()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    brudPaaNettet()
    brudPaaNettet()

    act(() => {
      gen[0]!.paaEvent({
        type: 'system_event', kind: 'error',
        payload: { message: 'spoegelse fra et doedt reattach' },
      })
    })
    expect(JSON.stringify(result.current.streamError ?? {}))
      .not.toContain('spoegelse')
  })

  it('det AKTUELLE reattach skriver stadig', () => {
    const gen = alleFollows()
    const { result } = renderHook(() => useStream(), { wrapper })
    act(() => { result.current.send('hej', { sessionId: 's' }) })
    brudPaaNettet()
    brudPaaNettet()

    act(() => {
      gen[gen.length - 1]!.paaEvent({
        type: 'system_event', kind: 'error',
        payload: { message: 'aegte reattach-fejl' },
      })
    })
    expect(JSON.stringify(result.current.streamError ?? {}))
      .toContain('aegte reattach-fejl')
  })
})
