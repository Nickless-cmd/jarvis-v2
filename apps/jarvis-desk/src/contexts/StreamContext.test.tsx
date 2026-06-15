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
  StreamError: class extends Error {},
}))
const cancelRunMock = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/api', () => ({ cancelRun: (...a: unknown[]) => cancelRunMock(...a) }))

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
})
