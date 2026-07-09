import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { SessionProvider, mergeServer } from './SessionContext'
import { useSessions } from '../hooks/useSessions'

const userMsg = (id: string, text: string) => ({ id, role: 'user' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })
const asstMsg = (id: string, text: string) => ({ id, role: 'assistant' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })
const toolMsg = (id: string) => ({ id, role: 'tool' as const, content: [{ type: 'text' as const, text: 'tool-resultat' }], created_at: 'now', parent_id: null })

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

  it('BEVARER streamet svar mens en tool-runde stadig kører (transcript slutter på tool)', () => {
    // Regression (Bjørn 2026-06-23 "svar lander → forsvinder"): midt i et multi-
    // runde tool-tur står serverens transcript [user, assistant(mellem), tool, tool]
    // mens det ENDELIGE svar streamer i broen. Før droppede serverCaught_up (sidste
    // IKKE-tool = assistant(mellem)) broen → svaret forsvandt. Nu: slutter på en
    // tool → turen kører → broen SKAL overleve.
    const local = [{ ...asstMsg('a-final', 'det endelige svar'), clientStatus: 'server_missing_keep_stream' as const }]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a-mid', 'lad mig tjekke'), toolMsg('srv-t1'), toolMsg('srv-t2')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(true) // broen overlever
  })

  it('dropper broen når turen ER færdig (transcript slutter på den persisterede assistant)', () => {
    const local = [{ ...asstMsg('a-final', 'svar'), clientStatus: 'server_missing_keep_stream' as const }]
    const server = [userMsg('srv-u', 'spm'), toolMsg('srv-t1'), asstMsg('srv-a', 'svar')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(false) // serverens rensede version overtager
    expect(merged.filter((m) => m.role === 'assistant').length).toBe(1)
  })

  it('BEVARER tool-kortene når broen droppes (serveren gemmer KUN tekst) — Bjørn 9. jul', () => {
    // Roden til "tool result forsvinder når svaret lander": serveren persisterer kun tekst
    // (content → stringToBlocks), aldrig tool_use/tool_result. Når broen (m. de streamede tool-
    // blokke) droppes til serverens tekst-kopi, forsvandt tool-kortene. Nu flettes de ind.
    const bridge = {
      id: 'a-final', role: 'assistant' as const, created_at: 'now', parent_id: null,
      clientStatus: 'server_missing_keep_stream' as const,
      content: [
        { type: 'tool_use', id: 'tu-1', name: 'bash', input: {}, status: 'done', result: 'ok' },
        { type: 'text', text: 'svaret' },
      ] as unknown as { type: 'text'; text: string }[],
    }
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'svaret')] // server = KUN tekst
    const merged = mergeServer([bridge], server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(false)   // broen droppet
    const srv = merged.find((m) => m.id === 'srv-a')!
    const types = (srv.content as Array<{ type: string }>).map((b) => b.type)
    expect(types).toContain('tool_use')  // tool-kortet overlevede i serverens besked
    expect(types).toContain('text')
    expect(types.indexOf('tool_use')).toBeLessThan(types.indexOf('text')) // tool FØR svar
  })

  it('tool-kortene overlever GENTAGNE merges (code mode poller refresh) — Bjørn 9. jul', () => {
    // Roden til at code mode STADIG tabte dem: CodeView poller sessions.refresh gentagne gange.
    // 1. merge injicerede tool-blokke i serverens besked; men 2. merge genopbyggede result fra
    // det friske (tekst-only) server-fetch → wipe. Nu re-injiceres via localToolsByNorm på HVER merge.
    const bridge = {
      id: 'a-final', role: 'assistant' as const, created_at: 'now', parent_id: null,
      clientStatus: 'server_missing_keep_stream' as const,
      content: [
        { type: 'tool_use', id: 'tu-1', name: 'bash', input: {}, status: 'done', result: 'ok' },
        { type: 'text', text: 'svaret' },
      ] as unknown as { type: 'text'; text: string }[],
    }
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'svaret')] // KUN tekst
    const first = mergeServer([bridge], server)
    // 2. merge: lokal = første merges resultat (m. injicerede tools); friskt server-fetch = tekst-only
    const second = mergeServer(first, server)
    const srv = second.find((m) => m.id === 'srv-a')!
    const types = (srv.content as Array<{ type: string }>).map((b) => b.type)
    expect(types).toContain('tool_use') // overlever ANDEN merge (var buggen i code mode)
    // ingen dublering: præcis én tool_use
    expect(types.filter((t) => t === 'tool_use').length).toBe(1)
  })

  // REGRESSION (Bjørn 2026-06-29, "3 svar lander samtidig"): bro-kopi + serverens
  // persisterede kopi af SAMME run skal kollapse til ÉT svar — også når serverens
  // transcript transient slutter på en tool (næste runde startede) så serverCaughtUp
  // er false. Tidligere holdt vi broen ved siden af serverens kopi → dublet.
  it('RUN-DEDUP: bro + serverens persisterede kopi af samme run kollapser til ÉT (selv med tool-hale)', () => {
    const local = [{ ...asstMsg('a-run1', 'her er svaret'), clientStatus: 'server_missing_keep_stream' as const }]
    // Serveren HAR persisteret det samme svar, men en ny runde startede → tool-hale.
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'her er svaret'), toolMsg('srv-t1'), toolMsg('srv-t2')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-run1')).toBe(false) // broen droppet — samme svar er persisteret
    // Kun ÉN kopi af svaret (serverens), ingen dublet.
    expect(merged.filter((m) => m.role === 'assistant' && (m.content[0] as { text: string }).text === 'her er svaret').length).toBe(1)
  })

  // En tool-tur-afsluttende transcript (slutter på tool) hvor broens svar IKKE
  // matcher noget persisteret (det er det ENDELIGE svar, server har kun mellem-
  // rundens tekst) må stadig BEVARE broen — ingen falsk drop.
  it('RUN-DEDUP: distinkt endeligt svar bevares når serveren kun har mellem-rundens tekst', () => {
    const local = [{ ...asstMsg('a-final', 'det endelige svar'), clientStatus: 'server_missing_keep_stream' as const }]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-mid', 'lad mig tjekke'), toolMsg('srv-t1')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(true) // distinkt svar → broen bevares
  })

  // Whitespace-variation mellem bro (rå stream) og server (normaliseret) må stadig
  // genkendes som samme svar → drop broen.
  it('RUN-DEDUP: normaliserer whitespace så rå bro matcher serverens rensede kopi', () => {
    const local = [{ ...asstMsg('a-ws', 'linje  et\n\nlinje to'), clientStatus: 'server_missing_keep_stream' as const }]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'linje et linje to'), toolMsg('srv-t1')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-ws')).toBe(false) // whitespace-normaliseret match → droppet
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
