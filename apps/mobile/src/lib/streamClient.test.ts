const mockAddEventListener = jest.fn()
const mockClose = jest.fn()

jest.mock('react-native-sse', () => {
  return jest.fn().mockImplementation(() => ({
    addEventListener: mockAddEventListener,
    close: mockClose
  }))
})

import EventSource from 'react-native-sse'
import { startStream } from './streamClient'
import type { StreamEvent } from './sseProtocol'
import type { ApiConfig } from './types'

const config: ApiConfig = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

type Listener = (event: { data?: string | null; message?: string }) => void

const getListener = (name: string): Listener => {
  const call = mockAddEventListener.mock.calls.find(([eventName]) => eventName === name)
  if (!call) {
    throw new Error(`Missing listener for ${name}`)
  }
  return call[1] as Listener
}

beforeEach(() => {
  jest.clearAllMocks()
})

it('forwards parsed events and completes on message_stop', () => {
  const onEvent = jest.fn<void, [StreamEvent]>()
  const onComplete = jest.fn()
  const control = startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent, onComplete }
  )

  getListener('message_start')({
    data: JSON.stringify({
      type: 'message_start',
      message: {
        id: 'm1',
        model: 'deepseek',
        provider: 'ollama',
        lane: 'primary',
        session_id: 's1',
        usage: { input_tokens: 0, output_tokens: 0 }
      }
    })
  })
  getListener('message_stop')({
    data: JSON.stringify({ type: 'message_stop' })
  })

  expect(onEvent).toHaveBeenCalledTimes(2)
  expect(onComplete).toHaveBeenCalledTimes(1)
  expect(mockClose).toHaveBeenCalledTimes(1)
  expect(control.getRunId()).toBe('m1')
})

it('captures run id from system_event run payload', () => {
  const onRunId = jest.fn()
  const control = startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent: jest.fn(), onRunId }
  )

  getListener('system_event')({
    data: JSON.stringify({
      type: 'system_event',
      kind: 'run',
      payload: { run_id: 'visible-2' }
    })
  })

  expect(onRunId).toHaveBeenCalledWith('visible-2')
  expect(control.getRunId()).toBe('visible-2')
})

it('reports interruption through error handler', () => {
  const onInterrupted = jest.fn()
  const onError = jest.fn()
  startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej'
    },
    { onEvent: jest.fn(), onInterrupted, onError }
  )

  getListener('error')({ message: 'Stream interrupted' })

  expect(onInterrupted).toHaveBeenCalledTimes(1)
  expect(onError).toHaveBeenCalledWith(expect.any(Error))
  expect(mockClose).toHaveBeenCalledTimes(1)
})

it('sends the expected request payload and auth header', () => {
  startStream(
    {
      config,
      sessionId: 's1',
      message: 'Hej',
      approvalMode: 'trust',
      thinkingMode: 'fast',
      mode: 'code',
      model: 'deepseek-r1',
      providerChoice: 'ollama'
    },
    { onEvent: jest.fn() }
  )

  expect(EventSource).toHaveBeenCalledWith(
    'https://api.srvlab.dk/chat/stream/v2',
    expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        Authorization: 'Bearer token'
      }),
      body: JSON.stringify({
        message: 'Hej',
        session_id: 's1',
        approval_mode: 'trust',
        thinking_mode: 'fast',
        mode: 'code',
        model: 'deepseek-r1',
        provider_choice: 'ollama'
      })
    })
  )
})
