import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { StreamProvider, useStream } from './StreamContext'
import type { StreamHandlers } from '../lib/streamClient'
import type { StreamEvent } from '../lib/sseProtocol'

const mockAppendLocalMessage = jest.fn()
const mockStartStream = jest.fn()
const mockCancelRun = jest.fn()
const mockApproveTool = jest.fn()
const mockDenyTool = jest.fn()

jest.mock('./SessionContext', () => ({
  useSessions: () => ({
    appendLocalMessage: (message: unknown) => mockAppendLocalMessage(message)
  })
}))

jest.mock('../lib/streamClient', () => ({
  startStream: (...args: unknown[]) => mockStartStream(...args)
}))

jest.mock('../lib/apiClient', () => ({
  approveTool: (...args: unknown[]) => mockApproveTool(...args),
  cancelRun: (...args: unknown[]) => mockCancelRun(...args),
  denyTool: (...args: unknown[]) => mockDenyTool(...args)
}))

const config = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

function Probe() {
  const { approval, approve, deny, state, send, stop } = useStream()

  return (
    <>
      <Text>{state.status}</Text>
      <Text>{state.activeRunId ?? 'no-run'}</Text>
      <Text>{approval?.message ?? 'no-approval'}</Text>
      <Text onPress={() => send(config, 'session-1', 'Hej Jarvis')}>send</Text>
      <Text onPress={() => void stop(config)}>stop</Text>
      <Text onPress={() => void approve(config)}>approve</Text>
      <Text onPress={() => void deny(config)}>deny</Text>
    </>
  )
}

beforeEach(() => {
  jest.clearAllMocks()
  mockStartStream.mockReturnValue({
    abort: jest.fn(),
    getRunId: () => 'run-123'
  })
  mockApproveTool.mockResolvedValue(undefined)
  mockDenyTool.mockResolvedValue(undefined)
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

it('captures approval requests and posts explicit decisions', async () => {
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
      type: 'system_event',
      kind: 'approval_request',
      payload: {
        approval_id: 'approval-1',
        tool: 'shell',
        message: 'Tillad kommando?',
        detail: 'pwd'
      }
    } satisfies StreamEvent)
  })

  expect(screen.getByText('Tillad kommando?')).toBeTruthy()

  await act(async () => {
    await screen.getByText('approve').props.onPress()
  })

  expect(mockApproveTool).toHaveBeenCalledWith(config, 'approval-1')
  expect(screen.getByText('no-approval')).toBeTruthy()
})

function ErrorProbe() {
  const { streamError, clearError, send } = useStream()
  return (
    <>
      <Text>{streamError ? `err:${streamError.code}:${streamError.severity}` : 'no-err'}</Text>
      <Text>{streamError?.retryable ? 'retryable' : 'not-retryable'}</Text>
      <Text onPress={() => send(config, 'session-1', 'Hej')}>send</Text>
      <Text onPress={() => clearError()}>clear</Text>
    </>
  )
}

it('fanger backendens error-system_event som struktureret streamError; clearError rydder', async () => {
  let handlers: StreamHandlers | undefined
  mockStartStream.mockImplementation((_r: unknown, h: StreamHandlers) => {
    handlers = h
    return { abort: jest.fn(), getRunId: () => 'run-123' }
  })
  const screen = await render(
    <StreamProvider>
      <ErrorProbe />
    </StreamProvider>
  )
  await act(async () => { screen.getByText('send').props.onPress() })
  await act(async () => {
    handlers?.onEvent({
      type: 'system_event',
      kind: 'error',
      payload: { type: 'error', code: 'provider_rate_limited', severity: 'warning',
                 message: 'Rate-limited', fix_hint: 'Vent', retryable: true,
                 correlation_id: 'run-123' }
    } as StreamEvent)
  })
  await waitFor(() => expect(screen.getByText('err:provider_rate_limited:warning')).toBeTruthy())
  expect(screen.getByText('retryable')).toBeTruthy()
  // FIX: dismiss/clearError virker.
  await act(async () => { screen.getByText('clear').props.onPress() })
  await waitFor(() => expect(screen.getByText('no-err')).toBeTruthy())
})
