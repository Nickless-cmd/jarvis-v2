import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { SessionProvider, mergeServer } from './SessionContext'
import { useSessions } from '../hooks/useSessions'

const userMsg = (id: string, text: string) => ({ id, role: 'user' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })
const asstMsg = (id: string, text: string) => ({ id, role: 'assistant' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })

describe('mergeServer afdublering', () => {
  it('dropper optimistisk bruger-besked når serveren har indhentet svaret (ingen dublet før+efter)', () => {
    const local = [{ ...userMsg('u-123', 'hej'), clientStatus: 'optimistic_user' as const }]
    // Serveren har persisteret BÅDE bruger-beskeden (andet id!) OG svaret
    const server = [userMsg('srv-u', 'hej'), asstMsg('srv-a', 'svar')]
    const merged = mergeServer(local, server)
    expect(merged.filter((m) => m.role === 'user').length).toBe(1) // kun serverens kopi
  })

  it('afdublerer på indhold mens svaret stadig streamer (server har bruger-besked, intet svar endnu)', () => {
    const local = [{ ...userMsg('u-9', 'spørgsmål'), clientStatus: 'optimistic_user' as const }]
    const server = [userMsg('srv-u', 'spørgsmål')]
    const merged = mergeServer(local, server)
    expect(merged.filter((m) => m.role === 'user').length).toBe(1)
  })

  it('beholder optimistisk besked som bro når serveren slet ikke har den endnu', () => {
    const local = [{ ...userMsg('u-7', 'ny'), clientStatus: 'optimistic_user' as const }]
    const merged = mergeServer(local, [])
    expect(merged.some((m) => m.id === 'u-7')).toBe(true) // må ikke blank-forsvinde
  })
})

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
