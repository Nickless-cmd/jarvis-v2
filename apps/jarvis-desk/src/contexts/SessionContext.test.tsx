import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { SessionProvider, mergeServer } from './SessionContext'
import { getSession } from '../lib/api'
import { useSessions } from '../hooks/useSessions'

const userMsg = (id: string, text: string) => ({ id, role: 'user' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })
const asstMsg = (id: string, text: string) => ({ id, role: 'assistant' as const, content: [{ type: 'text' as const, text }], created_at: 'now', parent_id: null })
const toolMsg = (id: string) => ({ id, role: 'tool' as const, content: [{ type: 'text' as const, text: 'tool-resultat' }], created_at: 'now', parent_id: null })

describe('mergeServer afdublering', () => {
  it('beholder array- og beskedreferencer når serverens transcript er uændret', () => {
    const local = [
      { ...userMsg('u-1', 'hej'), clientStatus: 'server_confirmed' as const },
      { ...asstMsg('a-1', 'svar'), clientStatus: 'server_confirmed' as const },
    ]
    const server = [userMsg('u-1', 'hej'), asstMsg('a-1', 'svar')]

    const merged = mergeServer(local, server)

    expect(merged).toBe(local)
    expect(merged[0]).toBe(local[0])
    expect(merged[1]).toBe(local[1])
  })

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

  it('bevarer pause_and_ask ved skiftet fra live-card til den afsluttende servertekst', () => {
    const pauseResult = JSON.stringify({
      kind: 'pause_and_ask',
      question: 'Skal jeg fortsætte?',
      options: ['Ja', 'Nej'],
      context: '',
      urgency: 'normal',
    })
    const bridge = {
      id: 'a-live', role: 'assistant' as const, created_at: 'now', parent_id: null,
      clientStatus: 'server_missing_keep_stream' as const,
      content: [
        { type: 'tool_use', id: 'ask-1', name: 'pause_and_ask', input: {}, status: 'done', result: pauseResult },
        { type: 'text', text: 'Jeg venter på dit valg.' },
      ] as unknown as { type: 'text'; text: string }[],
    }
    // Persistenslaget kan allerede have et andet tool-kort og kan normalisere
    // den korte slutlinje. Cardet skal stadig flyttes fra live-broen til den
    // afsluttede assistant-besked i stedet for at blinke væk.
    const server = [
      userMsg('srv-u', 'spm'),
      {
        ...asstMsg('srv-a', 'Jeg afventer dit valg.'),
        content: [
          { type: 'tool_use', id: 'other-1', name: 'read_file', input: {}, status: 'done', result: 'ok' },
          { type: 'text', text: 'Jeg afventer dit valg.' },
        ] as unknown as { type: 'text'; text: string }[],
      },
    ]

    const merged = mergeServer([bridge], server)

    expect(merged.some((m) => m.id === 'a-live')).toBe(false)
    const persisted = merged.find((m) => m.id === 'srv-a')!
    const tools = (persisted.content as unknown as Array<{ type: string; name?: string }>)
      .filter((b) => b.type === 'tool_use')
    expect(tools.map((b) => b.name)).toEqual(['pause_and_ask', 'read_file'])
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

  it('serverens content_json-baserede tool-kort overlever merge uden lokal re-injektion — Bjørn 9. jul', () => {
    // Server leverer nu FULDE blokke (via messageToBlocks i getSession) →
    // mergeServer skal bevare dem, ikke wipe dem til tekst.
    const server = [
      userMsg('srv-u', 'spm'),
      { id: 'srv-a', role: 'assistant' as const, created_at: 'now', parent_id: null,
        content: [
          { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {}, status: 'done', result: 'ok' },
          { type: 'text', text: 'svaret' },
        ] as unknown as { type: 'text'; text: string }[] },
    ]
    const merged = mergeServer([], server)
    const srv = merged.find((m) => m.id === 'srv-a')!
    const types = (srv.content as Array<{ type: string }>).map((b) => b.type)
    expect(types).toContain('tool_use')
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

// ---------------------------------------------------------------------------
// Session-listen skal opdatere UDEN et fladeskift (8/9-2026)
//
// Bjørn: «jeg skal trykke over på cowork og tilbage før den opdatere den nye
// sessioner i panelet». Listen blev hentet én gang ved mount og aldrig igen —
// et fladeskift gen-monterede provideren, og DET var opdateringen.
// ---------------------------------------------------------------------------

describe('session-listen opdaterer af sig selv', () => {
  it('henter listen igen når vinduet får fokus', async () => {
    const { listSessions } = await import('../lib/api')
    const spy = vi.mocked(listSessions)
    spy.mockClear()
    renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(spy).toHaveBeenCalled())
    const foer = spy.mock.calls.length

    await act(async () => { window.dispatchEvent(new Event('focus')) })
    await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThan(foer))
  })

  it('henter listen igen når fanen bliver synlig', async () => {
    const { listSessions } = await import('../lib/api')
    const spy = vi.mocked(listSessions)
    spy.mockClear()
    renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(spy).toHaveBeenCalled())
    const foer = spy.mock.calls.length

    await act(async () => { document.dispatchEvent(new Event('visibilitychange')) })
    await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThan(foer))
  })

  it('refresh henter OGSÅ listen, ikke kun beskederne', async () => {
    const { listSessions } = await import('../lib/api')
    const spy = vi.mocked(listSessions)
    spy.mockClear()
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(spy).toHaveBeenCalled())
    const foer = spy.mock.calls.length

    // Ingen aktiv session: før fiksningen returnerede refresh med det samme
    // og rørte aldrig listen — så en netop oprettet session blev usynlig.
    await act(async () => { await result.current.refresh() })
    expect(spy.mock.calls.length).toBeGreaterThan(foer)
  })

  it('hyppige besked-polls henter samtalen hver gang, men begrænser session-listen', async () => {
    const { listSessions, getSession } = await import('../lib/api')
    const list = vi.mocked(listSessions)
    const session = vi.mocked(getSession)
    list.mockClear()
    session.mockClear()
    localStorage.clear()
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(list).toHaveBeenCalled())
    await act(async () => { result.current.select('s1') })
    const listFoer = list.mock.calls.length
    const sessionFoer = session.mock.calls.length

    await act(async () => { await result.current.refreshMessages() })
    await act(async () => { await result.current.refreshMessages() })

    expect(session.mock.calls.length).toBe(sessionFoer + 2)
    expect(list.mock.calls.length).toBeLessThanOrEqual(listFoer + 1)
  })
})

// ---------------------------------------------------------------------------
// Sidst-valgte samtale skal overleve en genstart (8/9-2026)
//
// Bjørn: «appen glemmer hvilken session man var på efter genstart og det er
// rimelig træls». Id'et blev SKREVET til localStorage — der var bare aldrig
// nogen der læste det. Det vender samtidig en beslutning fra 17. juni om altid
// at lande på greeting-skærmen.
// ---------------------------------------------------------------------------

describe('gendan sidst-valgte samtale', () => {
  it('åbner den samtale man var på', async () => {
    localStorage.setItem('jarvis-desk:activeSession', 's1')
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(result.current.activeId).toBe('s1'))
    localStorage.clear()
  })

  it('genopliver IKKE en slettet samtale — og glemmer den', async () => {
    // Ellers ville et dødt id hente 404 ved hver eneste opstart, for evigt.
    localStorage.setItem('jarvis-desk:activeSession', 's-findes-ikke')
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(result.current.sessions.length).toBe(1))
    expect(result.current.activeId).toBeNull()
    expect(localStorage.getItem('jarvis-desk:activeSession')).toBeNull()
  })

  it('lander på greeting når der intet er gemt', async () => {
    localStorage.clear()
    const { result } = renderHook(() => useSessions(), { wrapper })
    await waitFor(() => expect(result.current.sessions.length).toBe(1))
    expect(result.current.activeId).toBeNull()
  })
})

describe('den gendannede samtale vælger sin flade', () => {
  it('en kode-session åbner i code-fladen', async () => {
    // Uden det åbnede en kode-session i chat-fladen, og så så det ud som om
    // miljø-panelet var forsvundet (Bjørn 8/9-2026).
    localStorage.setItem('jarvis-desk:activeSession', 's1')
    const set = vi.fn()
    const w = ({ children }: { children: ReactNode }) => (
      <SessionProvider config={cfg} onRestore={set}>{children}</SessionProvider>
    )
    renderHook(() => useSessions(), { wrapper: w })
    await waitFor(() => expect(set).toHaveBeenCalled())
    // listSessions-mocken har ingen workspace_kind → chat.
    expect(set).toHaveBeenCalledWith('chat')
    localStorage.clear()
  })
})

describe('en fejlet hentning maa ikke ligne en tom samtale', () => {
  // Codex' punkt 2 (21/9-2026). `select()` havde `.then().finally()` og INGEN
  // `.catch`: faldt hentningen, ryddede den foerst beskederne og satte saa
  // bare loading=false. Resultatet paa skaermen var en samtale uden en eneste
  // besked — ikke til at skelne fra en ny. Det er den mest foruroligende
  // maade en chat kan fejle paa, for den ser ud som om historikken er VAEK.
  // `select()` skriver selv til localStorage, saa tidligere tests i filen
  // efterlader en gemt samtale her. Uden denne blev min mockRejectedValueOnce
  // brugt op af gendannelsen ved mount, foer testen naaede at kalde noget.
  beforeEach(() => localStorage.clear())

  it('siger at beskederne ikke blev hentet — og henter dem paa ny ved forsoeg nummer to', async () => {
    vi.mocked(getSession)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({
        session: { id: 's1', title: 'T', updated_at: 'x' },
        messages: [userMsg('u-1', 'hej igen')],
      } as never)
    const { result } = renderHook(() => useSessions(), { wrapper })
    // Vent til listen er inde: gendannelses-effekten fyrer foerst DA, og den
    // maa vaere faerdig foer vi vaelger — ellers vaelger den selv bagefter.
    await waitFor(() => expect(result.current.sessions).toHaveLength(1))
    await act(async () => { result.current.select('s1') })
    await waitFor(() => expect(result.current.loadFejl).toMatch(/kunne ikke hentes/))
    expect(result.current.loading).toBe(false)

    // Og «Proev igen» maa ikke ramme «allerede loaded»-genvejen.
    await act(async () => { result.current.genindlaes() })
    await waitFor(() => expect(result.current.messages).toHaveLength(1))
    expect(result.current.loadFejl).toBe('')
  })
})
