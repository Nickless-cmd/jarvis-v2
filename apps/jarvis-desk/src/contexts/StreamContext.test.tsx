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
})
