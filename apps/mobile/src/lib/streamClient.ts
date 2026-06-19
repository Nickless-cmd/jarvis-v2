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
  onReconnecting?: (attempt: number) => void
  onInterrupted?: () => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

function errorDetail(event: unknown): string {
  const e = event as {
    type?: string
    message?: string
    xhrStatus?: number
    xhrState?: number
    error?: { message?: string }
  }
  const parts: string[] = []
  if (e.type) parts.push(e.type)
  if (typeof e.xhrStatus === 'number') parts.push(`http=${e.xhrStatus}`)
  if (typeof e.xhrState === 'number') parts.push(`state=${e.xhrState}`)
  if (e.message) parts.push(e.message)
  if (e.error?.message) parts.push(e.error.message)
  return parts.length ? parts.join(' · ') : 'ukendt'
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

const MAX_RECONNECTS = 5

export function startStream(request: StreamRequest, handlers: StreamHandlers): StreamControl {
  let activeRunId: string | null = null
  let offset = 0 // antal modtagne frames — server-frame-index til reconnect
  let gotStop = false
  let attempt = 0 // fortløbende reconnects UDEN fremgang
  let closed = false
  let current: EventSource<StreamEventName> | null = null

  const authHeaders = (json: boolean): Record<string, string> => {
    const h: Record<string, string> = { Accept: 'text/event-stream' }
    if (json) h['Content-Type'] = 'application/json'
    if (request.config.authToken) h.Authorization = `Bearer ${request.config.authToken}`
    return h
  }

  const attach = (source: EventSource<StreamEventName>) => {
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
          closed = true
          source.close()
          return
        }
        offset += 1 // hver modtaget frame = ét skridt i server-loggen
        attempt = 0 // fremgang → nulstil reconnect-tæller (tillader mange reconnects på lange runs)
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
          gotStop = true
          handlers.onComplete?.()
          closed = true
          source.close()
        }
      })
    }

    source.addEventListener('error', (event) => {
      if (gotStop || closed) return
      try {
        source.close()
      } catch {
        /* ignore */
      }
      // Server-autoritativt run: forbindelsen kan dø (Android kapper socket'en
      // ved baggrund), men runnet kører videre server-side. Gen-abonnér fra
      // sidste offset i stedet for at fejle. Kun hvis vi kender run_id.
      if (activeRunId && attempt < MAX_RECONNECTS) {
        attempt += 1
        handlers.onReconnecting?.(attempt)
        const delay = 500 * 2 ** (attempt - 1)
        setTimeout(() => {
          if (closed) return
          const url = new URL(
            `/chat/runs/${encodeURIComponent(activeRunId as string)}/subscribe?from_idx=${offset}`,
            request.config.apiBaseUrl
          ).toString()
          current = new EventSource<StreamEventName>(url, {
            method: 'GET',
            pollingInterval: 0,
            headers: authHeaders(false)
          })
          attach(current)
        }, delay)
        return
      }
      // Ingen run_id endnu, eller reconnects opbrugt uden fremgang → ægte fejl.
      handlers.onInterrupted?.()
      handlers.onError?.(new Error(errorDetail(event)))
    })
  }

  const startUrl = new URL('/chat/stream/v2', request.config.apiBaseUrl).toString()
  current = new EventSource<StreamEventName>(startUrl, {
    method: 'POST',
    pollingInterval: 0,
    headers: authHeaders(true),
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
  attach(current)

  return {
    abort: () => {
      closed = true
      current?.close()
    },
    getRunId: () => activeRunId
  }
}

/**
 * Følg en sessions live-stream (delte sessioner). Åbner en GET-SSE mod
 * /chat/sessions/{id}/live og fodrer de SAMME v2-frames ind i handlers — så
 * denne klient ser transcript + liveness live uanset HVEM (anden enhed, eller
 * Jarvis autonomt) der skriver i sessionen. Læser run_event_log (server-
 * authoritative, flag ON). 204 hvis intet aktivt run → onComplete med det samme.
 */
export function followSession(
  config: ApiConfig,
  sessionId: string,
  handlers: StreamHandlers
): StreamControl {
  let activeRunId: string | null = null
  const url = new URL(
    `/chat/sessions/${encodeURIComponent(sessionId)}/live`,
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
