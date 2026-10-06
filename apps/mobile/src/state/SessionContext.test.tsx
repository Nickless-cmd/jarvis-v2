import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { SessionProvider, mergeServer, useSessions } from './SessionContext'
import type { ChatMessage } from '../lib/types'

const mockListSessions = jest.fn()
const mockCreateSession = jest.fn()
const mockGetSession = jest.fn()

jest.mock('../lib/apiClient', () => ({
  listSessions: (config: unknown) => mockListSessions(config),
  createSession: (config: unknown) => mockCreateSession(config),
  getSession: (config: unknown, sessionId: string) => mockGetSession(config, sessionId)
}))

const config = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

function Probe() {
  const { sessions, activeId, messages, loading, refresh, select, create, appendLocalMessage, replaceMessages } =
    useSessions()

  return (
    <>
      <Text>{loading ? 'loading' : 'ready'}</Text>
      <Text>{sessions.map((session) => session.id).join(',') || 'none'}</Text>
      <Text>{activeId ?? 'inactive'}</Text>
      <Text>{messages.map((message) => message.id).join(',') || 'empty'}</Text>
      <Text onPress={() => void refresh(config)}>refresh</Text>
      <Text onPress={() => void select(config, 's2')}>select</Text>
      <Text
        onPress={async () => {
          await create(config)
        }}
      >
        create
      </Text>
      <Text
        onPress={() =>
          appendLocalMessage({
            id: 'local',
            role: 'user',
            content: 'Hej',
            created_at: 'now'
          })
        }
      >
        append
      </Text>
      <Text
        onPress={() =>
          appendLocalMessage({
            id: 'local-assistant-run1-1',
            role: 'assistant',
            content: 'Streamet svar',
            content_json: [{ type: 'text', text: 'Før arbejdet' }, { type: 'text', text: 'Endeligt svar' }],
            created_at: 'now'
          })
        }
      >
        appendAssistant
      </Text>
      <Text onPress={() => appendLocalMessage({
        id: 'local-assistant-replay', role: 'assistant', content: 'Andet snapshot', created_at: 'now',
      })}>appendOtherAssistant</Text>
      <Text
        onPress={() =>
          replaceMessages([
            {
              id: 'replaced',
              role: 'assistant',
              content: 'Svar',
              created_at: 'now'
            }
          ])
        }
      >
        replace
      </Text>
    </>
  )
}

beforeEach(() => {
  mockListSessions.mockReset()
  mockCreateSession.mockReset()
  mockGetSession.mockReset()
})

it('refreshes, selects, creates, and updates local messages', async () => {
  mockListSessions.mockResolvedValue([{ id: 's1', title: 'One', updated_at: 'now' }])
  mockGetSession.mockResolvedValue({
    session: { id: 's2', title: 'Two', updated_at: 'now' },
    messages: [{ id: 'm1', role: 'assistant', content: 'Hej', created_at: 'now' }]
  })
  mockCreateSession.mockResolvedValue({ id: 's3', title: 'Three', updated_at: 'now' })

  const screen = await render(
    <SessionProvider>
      <Probe />
    </SessionProvider>
  )

  expect(screen.getByText('ready')).toBeTruthy()
  expect(screen.getByText('none')).toBeTruthy()
  expect(screen.getByText('inactive')).toBeTruthy()
  expect(screen.getByText('empty')).toBeTruthy()

  await act(async () => {
    await screen.getByText('refresh').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('s1')).toBeTruthy())

  await act(async () => {
    await screen.getByText('select').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('s2')).toBeTruthy())
  await waitFor(() => expect(screen.getByText('m1')).toBeTruthy())

  await act(async () => {
    await screen.getByText('create').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('s3,s1')).toBeTruthy())
  await waitFor(() => expect(screen.getByText('empty')).toBeTruthy())

  await act(async () => {
    await screen.getByText('append').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('local')).toBeTruthy())

  await act(async () => {
    await screen.getByText('replace').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('replaced')).toBeTruthy())
})

it('clears sessions, active id, and messages after provider remount', async () => {
  mockCreateSession.mockResolvedValue({ id: 's3', title: 'Three', updated_at: 'now' })

  const screen = await render(
    <SessionProvider>
      <Probe />
    </SessionProvider>
  )

  await act(async () => {
    await screen.getByText('create').props.onPress()
  })

  await waitFor(() => expect(screen.getAllByText('s3')).toHaveLength(2))
  await waitFor(() => expect(screen.getByText('empty')).toBeTruthy())

  await act(async () => {
    await screen.getByText('append').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('local')).toBeTruthy())

  await act(async () => {
    screen.unmount()
  })

  const remounted = await render(
    <SessionProvider>
      <Probe />
    </SessionProvider>
  )

  await waitFor(() => expect(remounted.getByText('none')).toBeTruthy())
  expect(remounted.getByText('inactive')).toBeTruthy()
  expect(remounted.getByText('empty')).toBeTruthy()
})

it('tilføjer ikke et replay-snapshot efter serverens endelige svar allerede er hentet', async () => {
  const serverMessages = [
    { id: 'u1', role: 'user', content: 'Godkend prop', created_at: 'now' },
    { id: 'a1', role: 'assistant', content: 'Status. Endeligt svar',
      content_json: [{ type: 'text', text: 'Status' }, { type: 'text', text: 'Endeligt svar' }], created_at: 'now' },
  ]
  mockGetSession.mockResolvedValue({
    session: { id: 's2', title: 'Two', updated_at: 'now' }, messages: serverMessages,
  })
  const screen = await render(<SessionProvider><Probe /></SessionProvider>)
  await act(async () => { await screen.getByText('select').props.onPress() })
  await act(async () => { screen.getByText('appendAssistant').props.onPress() })
  expect(screen.getByText('u1,a1')).toBeTruthy()
})

it('304 fletter lokale snapshots igen selv om serverens array er uændret', async () => {
  const serverMessages = [
    { id: 'u1', role: 'user', content: 'Godkend prop', created_at: 'now' },
    { id: 'a1', role: 'assistant', content: 'Endeligt svar', created_at: 'now' },
  ]
  mockGetSession.mockResolvedValue({
    session: { id: 's2', title: 'Two', updated_at: 'now' }, messages: serverMessages,
    uaendret: true,
  })
  const screen = await render(<SessionProvider><Probe /></SessionProvider>)
  await act(async () => { await screen.getByText('select').props.onPress() })
  await act(async () => { screen.getByText('appendOtherAssistant').props.onPress() })
  expect(screen.getByText('u1,a1,local-assistant-replay')).toBeTruthy()
  await act(async () => { await screen.getByText('select').props.onPress() })
  expect(screen.getByText('u1,a1')).toBeTruthy()
})

// G1 (spec §10): porteret fra desk's bevist-virkende mergeServer-bro. Disse
// tests spejler desk's SessionContext.test.tsx-suite (mobil-content er en streng).
const userMsg = (id: string, text: string): ChatMessage => ({
  id,
  role: 'user',
  content: text,
  created_at: 'now'
})
const asstMsg = (id: string, text: string): ChatMessage => ({
  id,
  role: 'assistant',
  content: text,
  created_at: 'now'
})
const toolMsg = (id: string): ChatMessage => ({
  id,
  role: 'tool',
  content: 'tool-resultat',
  created_at: 'now'
})

describe('mergeServer afdublering', () => {
  it('dropper optimistisk bruger-besked når serveren har indhentet svaret', () => {
    const local = [{ ...userMsg('u-123', 'hej'), clientStatus: 'optimistic_user' as const }]
    const server = [userMsg('srv-u', 'hej'), asstMsg('srv-a', 'svar')]
    const merged = mergeServer(local, server)
    expect(merged.filter((m) => m.role === 'user').length).toBe(1)
  })

  it('afdublerer på indhold mens svaret stadig streamer (server har bruger-besked, intet svar)', () => {
    const local = [{ ...userMsg('u-9', 'spørgsmål'), clientStatus: 'optimistic_user' as const }]
    const server = [userMsg('srv-u', 'spørgsmål')]
    const merged = mergeServer(local, server)
    expect(merged.filter((m) => m.role === 'user').length).toBe(1)
  })

  it('beholder optimistisk besked som bro når serveren slet ikke har den endnu', () => {
    const local = [{ ...userMsg('u-7', 'ny'), clientStatus: 'optimistic_user' as const }]
    const merged = mergeServer(local, [])
    expect(merged.some((m) => m.id === 'u-7')).toBe(true)
  })

  it('BEVARER streamet svar mens en tool-runde stadig kører (transcript slutter på tool)', () => {
    const local = [
      { ...asstMsg('a-final', 'det endelige svar'), clientStatus: 'server_missing_keep_stream' as const }
    ]
    const server = [
      userMsg('srv-u', 'spm'),
      asstMsg('srv-a-mid', 'lad mig tjekke'),
      toolMsg('srv-t1'),
      toolMsg('srv-t2')
    ]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(true)
  })

  it('dropper broen når turen ER færdig (transcript slutter på den persisterede assistant)', () => {
    const local = [
      { ...asstMsg('a-final', 'svar'), clientStatus: 'server_missing_keep_stream' as const }
    ]
    const server = [userMsg('srv-u', 'spm'), toolMsg('srv-t1'), asstMsg('srv-a', 'svar')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(false)
    expect(merged.filter((m) => m.role === 'assistant').length).toBe(1)
  })

  // REGRESSION (Bjørn 2026-06-29, "3 svar lander samtidig"; porteret fra desk):
  // bro + serverens persisterede kopi af SAMME run kollapser til ÉT — også med tool-hale.
  it('RUN-DEDUP: bro + serverens persisterede kopi af samme run kollapser til ÉT (selv med tool-hale)', () => {
    const local = [
      { ...asstMsg('a-run1', 'her er svaret'), clientStatus: 'server_missing_keep_stream' as const }
    ]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'her er svaret'), toolMsg('srv-t1'), toolMsg('srv-t2')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-run1')).toBe(false)
    expect(merged.filter((m) => m.role === 'assistant' && m.content === 'her er svaret').length).toBe(1)
  })

  it('RUN-DEDUP: distinkt endeligt svar bevares når serveren kun har mellem-rundens tekst', () => {
    const local = [
      { ...asstMsg('a-final', 'det endelige svar'), clientStatus: 'server_missing_keep_stream' as const }
    ]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-mid', 'lad mig tjekke'), toolMsg('srv-t1')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-final')).toBe(true)
  })

  it('RUN-DEDUP: normaliserer whitespace så rå bro matcher serverens rensede kopi', () => {
    const local = [
      { ...asstMsg('a-ws', 'linje  et\n\nlinje to'), clientStatus: 'server_missing_keep_stream' as const }
    ]
    const server = [userMsg('srv-u', 'spm'), asstMsg('srv-a', 'linje et linje to'), toolMsg('srv-t1')]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'a-ws')).toBe(false)
  })

  // MÅLT 6/10-2026 (Bjørn: «mobil klienten viser 2 beskeder i chatview når du
  // svarer»). Broen bærer HELE turen — `blocksToAssistantText` joiner alle
  // text-blokke fra den levende stream. Serveren persisterer derimod alle
  // text-blokke UNDTAGEN den første (målt på message-48f9616a og
  // message-e46058df: content == join(blok 1..slut)). Derfor er de to tekster
  // ALDRIG ens, `serverAsstTexts.has(assistantNorm(lm))` fejler, og da
  // transcriptet slutter på en tool-række (81.750 tool-rækker i DB'en;
  // nyeste session slutter på `tool`) er serverCaughtUp=false → broen blev
  // holdt VED SIDEN AF serverens kopi → slutteksten stod to gange.
  it('DUBLET: broens sluttekst findes i serverens tekst selv når teksterne ikke er ens', () => {
    const foerste = 'Jeg går til sagen: de to forslag skal godkendes og verificeres.'
    const anden = 'De to forslag i køen er mine egne: bruger-scope i db_fts.py og db_runtime_misc.py.'
    const slut = 'Begge ting er fikset, pushet og bevist.'
    const local = [{
      id: 'local-assistant-run1',
      role: 'assistant' as const,
      // Broens content = HELE turen (alle blokke, inkl. den første).
      content: `${foerste} ${anden} ${slut}`,
      content_json: [
        { type: 'text', text: foerste },
        { type: 'text', text: anden },
        { type: 'text', text: slut }
      ],
      created_at: 'now',
      clientStatus: 'server_missing_keep_stream' as const
    }]
    // Serveren har persisteret ALT undtagen den første blok — og slutter på tool.
    const server = [
      userMsg('srv-u', 'spm'),
      asstMsg('srv-a', `${anden} ${slut}`),
      toolMsg('srv-t1')
    ]
    const merged = mergeServer(local, server)
    expect(merged.filter((m) => m.role === 'assistant').length).toBe(1)
    expect(merged.some((m) => m.id === 'local-assistant-run1')).toBe(false)
  })

  it('DUBLET-VÆRN: distinkt sluttekst bevares når serveren kun har mellemteksten', () => {
    // Samme form som ovenfor, men serveren mangler det ENDELIGE svar. Broen
    // SKAL bevares — ellers forsvinder svaret (Bjørn 23/6-regressionen).
    const mellem = 'Lad mig tjekke koden først.'
    const slut = 'Det endelige svar står her, og det er ikke persisteret endnu.'
    const local = [{
      id: 'local-assistant-run2',
      role: 'assistant' as const,
      content: `${mellem} ${slut}`,
      content_json: [
        { type: 'text', text: mellem },
        { type: 'text', text: slut }
      ],
      created_at: 'now',
      clientStatus: 'server_missing_keep_stream' as const
    }]
    const server = [
      userMsg('srv-u', 'spm'),
      asstMsg('srv-a', mellem),
      toolMsg('srv-t1')
    ]
    const merged = mergeServer(local, server)
    expect(merged.some((m) => m.id === 'local-assistant-run2')).toBe(true)
  })
})

it('select() bevarer local-assistant-snapshot når serveren endnu ikke har indhentet (G1)', async () => {
  // Regression for G1: en resync/poll-select midt i svar-halen wholesale-
  // replacede før beskeder → svaret forsvandt. Nu flettes: snapshottet bevares
  // indtil serverens transcript slutter på den persisterede assistant.
  mockGetSession.mockResolvedValue({
    session: { id: 's2', title: 'Two', updated_at: 'now' },
    // Server har endnu KUN bruger-beskeden + en tool-runde (intet endeligt svar)
    messages: [
      { id: 'srv-u', role: 'user', content: 'spm', created_at: 'now' },
      { id: 'srv-t', role: 'tool', content: 'tool', created_at: 'now' }
    ]
  })

  const screen = await render(
    <SessionProvider>
      <Probe />
    </SessionProvider>
  )

  // Simulér et lokalt-streamet assistant-snapshot (persistAssistantSnapshot).
  await act(async () => {
    screen.getByText('appendAssistant').props.onPress()
  })
  await waitFor(() => expect(screen.getByText(/local-assistant/)).toBeTruthy())

  // En resync-select lander mens serveren endnu ikke har persisteret svaret.
  await act(async () => {
    await screen.getByText('select').props.onPress()
  })

  // Snapshottet må IKKE være wiped — broen overlever (serveren har ikke indhentet).
  await waitFor(() => expect(screen.getByText(/local-assistant/)).toBeTruthy())
})

/** 19/9-2026: ved 304 flettes serverlisten ikke igen — men KUN hvis det er den
 *  liste vi sidst flettede. Er den lokale liste skiftet (ny samtale), og vender
 *  man tilbage til en uændret session, skal beskederne komme igen. */
it('et 304 efter en ny samtale bringer den gamle samtales beskeder tilbage', async () => {
  const beskeder = [{ id: 'g1', role: 'user', content: 'gammel', created_at: 'now' }]
  const session = { id: 's2', title: 'T', updated_at: 'now', messages: beskeder }
  mockGetSession.mockResolvedValueOnce({ session, messages: beskeder, uaendret: false })
  mockCreateSession.mockResolvedValueOnce({ id: 'ny', title: 'Ny', updated_at: 'now' })
  mockGetSession.mockResolvedValueOnce({ session, messages: beskeder, uaendret: true })

  const screen = await render(<SessionProvider><Probe /></SessionProvider>)
  await act(async () => { await screen.getByText('select').props.onPress() })
  await waitFor(() => expect(screen.getByText('g1')).toBeTruthy())

  await act(async () => { await screen.getByText('create').props.onPress() })
  await waitFor(() => expect(screen.getByText('empty')).toBeTruthy())

  await act(async () => { await screen.getByText('select').props.onPress() })
  await waitFor(() => expect(screen.getByText('g1')).toBeTruthy())
})

// ── RUN-ID SOM PRÆCIS NØGLE (Bjørn 6/10-2026) ──────────────────────────────
//
// De tre tekst-regler er heuristikker paa en prosa serveren selv skriver om, og
// hver ny false-positive har krævet en ny regel. Serveren sender nu `run_id`
// med, og det kan ikke brækkes af en omskrivning.
describe('mergeServer: run-id slaar tekst-heuristikkerne', () => {
  // PRODUKTIONENS FORMAT, ikke et opdigtet. `StreamContext` bygger
  // `local-assistant-<runId>-<timestamp>` — desk bygger `a-<runId>`. Foerste
  // udgave af rettelsen var en kopi af desks `startsWith('a-')` og var derfor
  // DOED KODE paa mobilen; en test der pinnede mit eget format havde bekraeftet
  // den.
  const bro = (runId: string, tekst: string) => ({
    id: `local-assistant-${runId}-1791312000000`,
    role: 'assistant' as const,
    content: tekst,
    created_at: 'now',
    clientStatus: 'server_missing_keep_stream' as const,
  })

  it('dropper broen naar run-id matcher, OGSAA naar teksten er forskellig', () => {
    const server = [
      { ...asstMsg('srv-a', 'kort'), run_id: 'visible-bd1727a4' },
      toolMsg('srv-t'),
    ]
    const merged = mergeServer(
      [bro('visible-bd1727a4', 'et helt andet og meget laengere svar end serverens')],
      server)
    expect(merged.filter((m) => m.role === 'assistant').length).toBe(1)
    expect(merged.find((m) => m.id.startsWith('local-assistant-'))).toBeUndefined()
  })

  it('run-id med bindestreger i sig parses korrekt', () => {
    const server = [
      { ...asstMsg('srv-a', 'kort'), run_id: 'visible-bd1727a4-631641feb6dd' },
      toolMsg('srv-t'),
    ]
    const merged = mergeServer(
      [bro('visible-bd1727a4-631641feb6dd', 'noget helt andet og langt nok til at undgaa delvis match')],
      server)
    expect(merged.find((m) => m.id.startsWith('local-assistant-'))).toBeUndefined()
  })

  it('BEHOLDER broen naar serveren ikke sender run_id', () => {
    const server = [asstMsg('srv-a', 'kort'), toolMsg('srv-t')]
    const merged = mergeServer(
      [bro('visible-bd1727a4', 'et helt andet og meget laengere svar end serverens')],
      server)
    expect(merged.find((m) => m.id.startsWith('local-assistant-'))).toBeDefined()
  })

  it('BEHOLDER broen naar run_id ligger paa et ANDET run', () => {
    const server = [
      { ...asstMsg('srv-a', 'kort'), run_id: 'visible-et-andet-run' },
      toolMsg('srv-t'),
    ]
    const merged = mergeServer(
      [bro('visible-bd1727a4', 'et helt andet og meget laengere svar end serverens')],
      server)
    expect(merged.find((m) => m.id.startsWith('local-assistant-'))).toBeDefined()
  })
})
