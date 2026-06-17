import EventSource from 'react-native-sse'

import type { ApiConfig } from './types'
import type { StreamEvent } from './sseProtocol'

export interface StreamRequest {
  config: ApiConfig
  sessionId: string
  message: string
  approvalMode?: 'ask' | 'trust'
  thinkingMode?: 'think' | 'fast'
  mode?: 'chat' | 'cowork' | 'code'
  model?: string
  providerChoice?: string
}

export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void
  onRunId?: (runId: string) => void
  onInterrupted?: () => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

export interface StreamControl {
  abort: () => void
  getRunId: () => string | null
}

const eventNames = [
  'message_start',
  'content_block_start',
  'content_block_delta',
  'content_block_stop',
  'message_delta',
  'message_stop',
  'ping',
  'system_event'
] as const

type StreamEventName = (typeof eventNames)[number]
type SsePayloadEvent = { data?: string | null; message?: string | null }

export function startStream(request: StreamRequest, handlers: StreamHandlers): StreamControl {
  let activeRunId: string | null = null
  const url = new URL('/chat/stream/v2', request.config.apiBaseUrl).toString()
  const source = new EventSource<StreamEventName>(url, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${request.config.authToken}`
    },
    body: JSON.stringify({
      message: request.message,
      session_id: request.sessionId,
      approval_mode: request.approvalMode ?? 'ask',
      thinking_mode: request.thinkingMode ?? 'think',
      mode: request.mode ?? 'chat',
      model: request.model ?? '',
      provider_choice: request.providerChoice ?? ''
    })
  })

  for (const name of eventNames) {
    source.addEventListener(name, (event) => {
      const payload = event as SsePayloadEvent
      if (!payload.data) return
      const parsed = JSON.parse(String(payload.data)) as StreamEvent
      if (parsed.type === 'message_start' && parsed.message.id) {
        activeRunId = parsed.message.id
        handlers.onRunId?.(parsed.message.id)
      }
      if (
        parsed.type === 'system_event' &&
        parsed.kind === 'run' &&
        typeof parsed.payload.run_id === 'string'
      ) {
        activeRunId = parsed.payload.run_id
        handlers.onRunId?.(parsed.payload.run_id)
      }
      handlers.onEvent(parsed)
      if (parsed.type === 'message_stop') {
        handlers.onComplete?.()
        source.close()
      }
    })
  }

  source.addEventListener('error', (event) => {
    const message = 'message' in event ? event.message : 'Stream interrupted'
    handlers.onInterrupted?.()
    handlers.onError?.(new Error(String(message ?? 'Stream interrupted')))
    source.close()
  })

  return {
    abort: () => source.close(),
    getRunId: () => activeRunId
  }
}
