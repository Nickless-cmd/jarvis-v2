import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { SessionProvider } from './SessionContext'
import { useSessions } from '../hooks/useSessions'

vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([{ id: 's1', title: 'T', updated_at: 'x' }]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [] }),
  createSession: vi.fn().mockResolvedValue({ id: 's2', title: 'Ny', updated_at: 'x' }),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }
const wrapper = ({ children }: { children: ReactNode }) => (
  <SessionProvider config={cfg}>{children}</SessionProvider>
)

describe('SessionContext reconcile', () => {
  it('appendOptimistic shows user message immediately', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper })
    await act(async () => { result.current.select('s1') })
    act(() => {
      result.current.appendOptimistic({ id: 'u-1', role: 'user', content: [{ type: 'text', text: 'hej' }], created_at: 'now', parent_id: null })
    })
    expect(result.current.messages.some((m) => m.id === 'u-1')).toBe(true)
  })

  it('reconcile keeps stream blocks when server load is missing the message (no blank)', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper })
    await act(async () => { result.current.select('s1') })
    act(() => {
      result.current.reconcile({ id: 'a-temp', role: 'assistant', content: [{ type: 'text', text: 'svar' }], created_at: 'now', parent_id: null })
    })
    // server-load returnerer tom (race) — beskeden må IKKE forsvinde
    await act(async () => { await result.current.refresh() })
    const survived = result.current.messages.some(
      (m) => m.role === 'assistant' && m.content[0]?.type === 'text' && (m.content[0] as { text: string }).text === 'svar',
    )
    expect(survived).toBe(true)
  })

  it('loads sessions on mount', async () => {
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(result.current.sessions.length).toBe(1))
  })
})
