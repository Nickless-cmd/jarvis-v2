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
            created_at: 'now'
          })
        }
      >
        appendAssistant
      </Text>
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
