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
  attachmentIds?: string[]
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
  const headers: Record<string, string> = {
    Accept: 'text/event-stream',
    'Content-Type': 'application/json'
  }
  if (request.config.authToken) {
    headers.Authorization = `Bearer ${request.config.authToken}`
  }
  const source = new EventSource<StreamEventName>(url, {
    method: 'POST',
    pollingInterval: 0,
    headers,
    body: JSON.stringify({
      message: request.message,
      session_id: request.sessionId,
      approval_mode: request.approvalMode ?? 'ask',
      thinking_mode: request.thinkingMode ?? 'think',
      mode: request.mode ?? 'chat',
      model: request.model ?? '',
      provider_choice: request.providerChoice ?? '',
      attachment_ids: request.attachmentIds ?? []
    })
  })

  for (const name of eventNames) {
    source.addEventListener(name, (event) => {
      const payload = event as SsePayloadEvent
      if (!payload.data) return
      let parsed: StreamEvent
      try {
        parsed = JSON.parse(String(payload.data)) as StreamEvent
      } catch (error) {
        handlers.onInterrupted?.()
        handlers.onError?.(
          error instanceof Error ? error : new Error('Malformed stream payload')
        )
        source.close()
        return
      }
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

/**
 * Følg en sessions live-stream (delte sessioner). Åbner en GET-SSE mod
 * /chat/sessions/{id}/follow og fodrer de SAMME v2-frames ind i handlers —
 * så denne klient ser transcript + liveness live uanset HVEM (anden enhed,
 * eller Jarvis autonomt) der skriver i sessionen. Bygger på run_follow-
 * bufferen (broadcast A1/A3). Catch-up fra start + live-tail indtil done.
 */
export function followSession(
  config: ApiConfig,
  sessionId: string,
  handlers: StreamHandlers
): StreamControl {
  let activeRunId: string | null = null
  const url = new URL(
    `/chat/sessions/${encodeURIComponent(sessionId)}/follow`,
    config.apiBaseUrl
  ).toString()
  const headers: Record<string, string> = { Accept: 'text/event-stream' }
  if (config.authToken) headers.Authorization = `Bearer ${config.authToken}`

  const source = new EventSource<StreamEventName>(url, {
    method: 'GET',
    pollingInterval: 0,
    headers
  })

  for (const name of eventNames) {
    source.addEventListener(name, (event) => {
      const payload = event as SsePayloadEvent
      if (!payload.data) return
      let parsed: StreamEvent
      try {
        parsed = JSON.parse(String(payload.data)) as StreamEvent
      } catch {
        return // tolerér enkelt-frame-parsefejl i en passiv follow
      }
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

  // En follow der lukker (run færdigt / intet aktivt run) er normalt — ikke en fejl.
  source.addEventListener('error', () => {
    handlers.onComplete?.()
    source.close()
  })

  return {
    abort: () => source.close(),
    getRunId: () => activeRunId
  }
}
