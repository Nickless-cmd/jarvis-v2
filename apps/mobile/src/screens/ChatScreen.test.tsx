import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { ChatScreen } from './ChatScreen'

const config = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

const mockRefresh = jest.fn().mockResolvedValue(undefined)
const mockCreate = jest.fn()
const mockSend = jest.fn()
const mockStop = jest.fn()

let mockSessions = {
  activeId: 'session-1',
  messages: [
    {
      id: 'user-1',
      role: 'user' as const,
      content: 'Hej Jarvis',
      created_at: '2026-06-17T00:00:00.000Z'
    }
  ],
  refresh: mockRefresh,
  create: mockCreate
}

let mockStream = {
  state: {
    status: 'error',
    blocks: []
  },
  send: mockSend,
  stop: mockStop
}

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config })
}))

jest.mock('../state/SessionContext', () => ({
  useSessions: () => mockSessions
}))

jest.mock('../state/StreamContext', () => ({
  useStream: () => mockStream
}))

jest.mock('../components/Composer', () => ({
  Composer: () => {
    const ReactLib = jest.requireActual('react')
    const { Text } = jest.requireActual('react-native')
    return ReactLib.createElement(Text, null, 'Composer')
  }
}))

jest.mock('../components/MessageList', () => ({
  MessageList: () => {
    const ReactLib = jest.requireActual('react')
    const { Text } = jest.requireActual('react-native')
    return ReactLib.createElement(Text, null, 'Messages')
  }
}))

beforeEach(() => {
  jest.clearAllMocks()
  mockSessions = {
    activeId: 'session-1',
    messages: [
      {
        id: 'user-1',
        role: 'user',
        content: 'Hej Jarvis',
        created_at: '2026-06-17T00:00:00.000Z'
      }
    ],
    refresh: mockRefresh,
    create: mockCreate
  }
  mockStream = {
    state: {
      status: 'error',
      blocks: []
    },
    send: mockSend,
    stop: mockStop
  }
})

it('shows retry after a failed stream and resends the last user message', async () => {
  const screen = await render(<ChatScreen />)

  await waitFor(() => expect(screen.getByText('Retry')).toBeTruthy())
  fireEvent.press(screen.getByText('Retry'))

  expect(mockCreate).not.toHaveBeenCalled()
  expect(mockSend).toHaveBeenCalledWith(config, 'session-1', 'Hej Jarvis')
})

it('hides retry while the stream is working', async () => {
  mockStream = {
    ...mockStream,
    state: {
      status: 'working',
      blocks: []
    }
  }

  const screen = await render(<ChatScreen />)

  expect(screen.queryByText('Retry')).toBeNull()
})
