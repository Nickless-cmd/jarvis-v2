import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { StreamProvider, useStream } from './StreamContext'
import type { StreamHandlers } from '../lib/streamClient'
import type { StreamEvent } from '../lib/sseProtocol'

const mockAppendLocalMessage = jest.fn()
const mockStartStream = jest.fn()
const mockCancelRun = jest.fn()

jest.mock('./SessionContext', () => ({
  useSessions: () => ({
    appendLocalMessage: (message: unknown) => mockAppendLocalMessage(message)
  })
}))

jest.mock('../lib/streamClient', () => ({
  startStream: (...args: unknown[]) => mockStartStream(...args)
}))

jest.mock('../lib/apiClient', () => ({
  cancelRun: (...args: unknown[]) => mockCancelRun(...args)
}))

const config = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

function Probe() {
  const { state, send, stop } = useStream()

  return (
    <>
      <Text>{state.status}</Text>
      <Text>{state.activeRunId ?? 'no-run'}</Text>
      <Text onPress={() => send(config, 'session-1', 'Hej Jarvis')}>send</Text>
      <Text onPress={() => void stop(config)}>stop</Text>
    </>
  )
}

beforeEach(() => {
  jest.clearAllMocks()
  mockStartStream.mockReturnValue({
    abort: jest.fn(),
    getRunId: () => 'run-123'
  })
})

it('appends a local message and updates state from stream events', async () => {
  let handlers: StreamHandlers | undefined
  mockStartStream.mockImplementation((_request: unknown, nextHandlers: StreamHandlers) => {
    handlers = nextHandlers
    return {
      abort: jest.fn(),
      getRunId: () => 'run-123'
    }
  })

  const screen = await render(
    <StreamProvider>
      <Probe />
    </StreamProvider>
  )

  await act(async () => {
    screen.getByText('send').props.onPress()
  })

  expect(mockAppendLocalMessage).toHaveBeenCalledWith(
    expect.objectContaining({
      role: 'user',
      content: 'Hej Jarvis'
    })
  )
  expect(mockStartStream).toHaveBeenCalledWith(
    {
      config,
      sessionId: 'session-1',
      message: 'Hej Jarvis',
      mode: 'chat'
    },
    expect.any(Object)
  )

  await act(async () => {
    handlers?.onEvent({
      type: 'message_start',
      message: {
        id: 'run-123',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 'session-1',
        usage: { input_tokens: 2, output_tokens: 0 }
      }
    } satisfies StreamEvent)
  })

  await waitFor(() => expect(screen.getByText('working')).toBeTruthy())
  expect(screen.getByText('run-123')).toBeTruthy()
})

it('aborts and cancels the active run when stopped', async () => {
  const abort = jest.fn()
  mockStartStream.mockReturnValue({
    abort,
    getRunId: () => 'run-123'
  })

  const screen = await render(
    <StreamProvider>
      <Probe />
    </StreamProvider>
  )

  await waitFor(() => expect(screen.getByText('send')).toBeTruthy())

  await act(async () => {
    screen.getByText('send').props.onPress()
  })
  await act(async () => {
    await screen.getByText('stop').props.onPress()
  })

  expect(abort).toHaveBeenCalledTimes(1)
  expect(mockCancelRun).toHaveBeenCalledWith(config, 'run-123')
  expect(screen.getByText('interrupted')).toBeTruthy()
})

it('persists partial assistant output when a stream is interrupted', async () => {
  let handlers: StreamHandlers | undefined
  mockStartStream.mockImplementation((_request: unknown, nextHandlers: StreamHandlers) => {
    handlers = nextHandlers
    return {
      abort: jest.fn(),
      getRunId: () => 'run-123'
    }
  })

  const screen = await render(
    <StreamProvider>
      <Probe />
    </StreamProvider>
  )

  await act(async () => {
    screen.getByText('send').props.onPress()
  })
  await act(async () => {
    handlers?.onEvent({
      type: 'message_start',
      message: {
        id: 'run-123',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 'session-1',
        usage: { input_tokens: 2, output_tokens: 0 }
      }
    } satisfies StreamEvent)
    handlers?.onEvent({
      type: 'content_block_start',
      index: 0,
      content_block: { type: 'text', text: '' }
    } satisfies StreamEvent)
    handlers?.onEvent({
      type: 'content_block_delta',
      index: 0,
      delta: { type: 'text_delta', text: 'Delvist svar' }
    } satisfies StreamEvent)
    handlers?.onInterrupted?.()
  })

  expect(mockAppendLocalMessage).toHaveBeenCalledWith(
    expect.objectContaining({
      role: 'assistant',
      content: 'Delvist svar'
    })
  )
  expect(screen.getByText('interrupted')).toBeTruthy()
})

it('marks the stream interrupted even when server cancel fails', async () => {
  const abort = jest.fn()
  mockCancelRun.mockRejectedValueOnce(new Error('cancel failed'))
  mockStartStream.mockReturnValue({
    abort,
    getRunId: () => 'run-123'
  })

  const screen = await render(
    <StreamProvider>
      <Probe />
    </StreamProvider>
  )

  await act(async () => {
    screen.getByText('send').props.onPress()
  })
  await act(async () => {
    await screen.getByText('stop').props.onPress()
  })

  expect(abort).toHaveBeenCalledTimes(1)
  expect(mockCancelRun).toHaveBeenCalledWith(config, 'run-123')
  expect(screen.getByText('interrupted')).toBeTruthy()
})
