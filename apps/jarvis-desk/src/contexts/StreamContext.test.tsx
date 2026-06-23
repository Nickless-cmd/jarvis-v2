import { describe, it, expect, vi } from 'vitest'
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

vi.mock('../lib/streamClient', () => ({
  startStream: (_req: unknown, handlers: FakeHandlers) => {
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
