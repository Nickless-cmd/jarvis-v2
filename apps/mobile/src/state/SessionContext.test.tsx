import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { SessionProvider, useSessions } from './SessionContext'

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
