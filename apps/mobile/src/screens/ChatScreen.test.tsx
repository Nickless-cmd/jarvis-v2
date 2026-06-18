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
const mockApprove = jest.fn()
const mockDeny = jest.fn()

type MockStream = {
  state: {
    status: 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'
    blocks: []
  }
  approval: null | {
    approvalId: string
    tool: string
    message: string
    detail?: string
  }
  approve: typeof mockApprove
  deny: typeof mockDeny
  send: typeof mockSend
  stop: typeof mockStop
}

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

let mockStream: MockStream = {
  state: {
    status: 'error',
    blocks: []
  },
  approval: null,
  approve: mockApprove,
  deny: mockDeny,
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

jest.mock('react-native-safe-area-context', () => ({
  useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 })
}))

jest.mock('../components/SidePanel', () => ({
  SidePanel: () => null
}))

jest.mock('../lib/apiClient', () => ({
  whoami: jest.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  getModelOptions: jest.fn().mockResolvedValue([])
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
    approval: null,
    approve: mockApprove,
    deny: mockDeny,
    send: mockSend,
    stop: mockStop
  }
})

it('shows retry after a failed stream and resends the last user message', async () => {
  const screen = await render(<ChatScreen />)

  await waitFor(() => expect(screen.getByText('Retry')).toBeTruthy())
  await fireEvent.press(screen.getByText('Retry'))

  expect(mockCreate).not.toHaveBeenCalled()
  // 4. arg (model-opts) ignoreres her — testen handler om retry-routing.
  expect(mockSend.mock.calls[0].slice(0, 3)).toEqual([config, 'session-1', 'Hej Jarvis'])
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

it('renders approval requests and forwards explicit decisions', async () => {
  mockStream = {
    ...mockStream,
    state: {
      status: 'working',
      blocks: []
    },
    approval: {
      approvalId: 'approval-1',
      tool: 'shell',
      message: 'Tillad kommando?'
    }
  }

  const screen = await render(<ChatScreen />)

  await waitFor(() => expect(screen.getByText('Tillad kommando?')).toBeTruthy())
  await fireEvent.press(screen.getByText('Tillad'))
  await fireEvent.press(screen.getByText('Afvis'))

  expect(mockApprove).toHaveBeenCalledWith(config)
  expect(mockDeny).toHaveBeenCalledWith(config)
})
