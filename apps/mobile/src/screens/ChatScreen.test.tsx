import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { ChatScreen } from './ChatScreen'
import type { StreamErrorInfo } from '../state/StreamContext'

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
  streamError: null | StreamErrorInfo
  clearError: () => void
  approve: typeof mockApprove
  deny: typeof mockDeny
  send: typeof mockSend
  stop: typeof mockStop
  follow: () => void
  stopFollow: () => void
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
  streamError: null,
  clearError: jest.fn(),
  approve: mockApprove,
  deny: mockDeny,
  send: mockSend,
  stop: mockStop,
  follow: jest.fn(),
  stopFollow: jest.fn()
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
  Composer: (props: {
    onSend: (text: string) => void
    permission?: string
    onPressPermission?: () => void
  }) => {
    const ReactLib = jest.requireActual('react')
    const { Text } = jest.requireActual('react-native')
    return ReactLib.createElement(
      ReactLib.Fragment,
      null,
      ReactLib.createElement(Text, null, `Composer permission ${props.permission ?? 'none'}`),
      // Mocken skal foelge den AEGTE kontrakt: ingen handler = ingen knap.
      // Uden det kan en test ikke se forskel paa «skjult» og «vist», og saa
      // maaler den kun sig selv.
      props.onPressPermission
        ? ReactLib.createElement(Text, { onPress: props.onPressPermission }, 'Open permissions')
        : null,
      ReactLib.createElement(Text, { onPress: () => props.onSend('ret remote delen') }, 'Send mocked composer')
    )
  }
}))

jest.mock('../components/PermissionPicker', () => ({
  PermissionPicker: (props: {
    open: boolean
    onSelect: (mode: 'ask' | 'trust') => void
  }) => {
    const ReactLib = jest.requireActual('react')
    const { Text } = jest.requireActual('react-native')
    return props.open
      ? ReactLib.createElement(Text, { onPress: () => props.onSelect('trust') }, 'Choose full access')
      : null
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

jest.mock('../lib/useConnectivity', () => ({
  useConnectivity: () => 'connected'
}))

// HVIDLISTE, ikke en delvis mock: alt der ikke staar her er `undefined` naar
// skaermen kalder det. En ny eksport i apiClient braekker derfor denne fil
// uden at have noget med den at goere - det er praecis hvad der skete da
// kontekst-ringen kom til.
jest.mock('../lib/apiClient', () => ({
  whoami: jest.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  getModelOptions: jest.fn().mockResolvedValue([]),
  getContextUsage: jest.fn().mockResolvedValue(null),
  compactNow: jest.fn().mockResolvedValue({ started: true }),
  getGitStatus: jest.fn().mockResolvedValue(null)
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
    streamError: null,
    clearError: jest.fn(),
    approve: mockApprove,
    deny: mockDeny,
    send: mockSend,
    stop: mockStop,
    follow: jest.fn(),
    stopFollow: jest.fn()
  }
})

it('shows retry after a failed stream and resends the last user message', async () => {
  const screen = await render(<ChatScreen />)

  await waitFor(() => expect(screen.getByText('Prøv igen')).toBeTruthy())
  await fireEvent.press(screen.getByText('Prøv igen'))

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

  expect(screen.queryByText('Prøv igen')).toBeNull()
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

it('tilladelses-knappen findes IKKE i chat-fladen', async () => {
  // Tilladelser handler om hvad Jarvis maa goere ved filer og skal. I en
  // samtale er skjoldet et ikon man aldrig roerer, paa den plads hvor de faa
  // knapper man BRUGER skal staa.
  const screen = await render(<ChatScreen />)
  await waitFor(() => expect(screen.getByText('Send mocked composer')).toBeTruthy())
  expect(screen.queryByText('Open permissions')).toBeNull()
})

it('sender permission-valget og bruger samtalens værktøjs-mode', async () => {
  mockStream = {
    ...mockStream,
    state: {
      status: 'idle',
      blocks: []
    }
  }

  // I CODE-fladen: det er dér knappen bor nu.
  const screen = await render(<ChatScreen kodeTilstand />)

  await waitFor(() => expect(screen.getByText('Composer permission ask')).toBeTruthy())
  fireEvent.press(screen.getByText('Open permissions'))
  fireEvent.press(await screen.findByText('Choose full access'))
  await waitFor(() => expect(screen.getByText('Composer permission trust')).toBeTruthy())
  fireEvent.press(screen.getByText('Send mocked composer'))

  expect(mockSend).toHaveBeenCalledWith(
    config,
    'session-1',
    'ret remote delen',
    expect.objectContaining({ mode: 'chat', approvalMode: 'trust' })
  )
})

it('UDEN en tidligere session vises greeting-siden, ikke en tom traad', async () => {
  // Bjoern bad om «greeting side lige som i desk» naar der ingen session er.
  // Den virkede allerede, men INGEN test roerte den - saa det var en paastand
  // uden belaeg.
  mockSessions = { ...mockSessions, activeId: '', messages: [] }
  const screen = await render(<ChatScreen />)
  await waitFor(() => expect(screen.getByTestId('greeting-hero')).toBeTruthy())
})

it('MED beskeder er greeting VAEK', async () => {
  // Den maa ikke ligge og skygge for traaden.
  const screen = await render(<ChatScreen />)
  await waitFor(() => expect(screen.queryByTestId('greeting-hero')).toBeNull())
})
