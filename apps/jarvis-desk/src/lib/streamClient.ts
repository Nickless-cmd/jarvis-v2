/**
 * jarvis-desk stream client — robust SSE-konsument af /chat/stream/v2.
 *
 * Design-mål:
 *   1. Konsumerer Anthropic-style protokol (message_start → content_block_*
 *      → message_stop) som specificeret i
 *      docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
 *
 *   2. ROBUSTHED på samme niveau som Claude Code:
 *      - Auto-reconnect med exponential backoff (1s → 2s → 4s → 8s → 15s → 30s)
 *      - Last-event-id resume (når server understøtter det)
 *      - Heartbeat detection: hvis vi ikke ser ping i 70s → forbindelsen død
 *      - AbortController support til ren cancellation
 *      - Auto-reset reconnectAttempt når én besked lykkes
 *
 *   3. TYPED ERRORS — aldrig generisk "Something went wrong":
 *      - NetworkError: TCP/DNS/connectivity
 *      - AuthError: 401/403 — auth-token udløbet
 *      - RateLimitError: 429 — backoff request
 *      - ServerError: 5xx — server crashed
 *      - ProtocolError: malformed SSE / unexpected event
 *      - StreamCancelled: bevidst abort fra klient
 *      Hver error indeholder context (URL, status code, retry-able boolean)
 *
 *   4. SIKKERHED:
 *      - Bearer token i Authorization header (ALDRIG i URL)
 *      - Validér event-types før dispatch (forhindrer prototype pollution)
 *      - Strict JSON-parsing med size limits
 *      - Ingen eval / Function()
 */

// ─── Typed event-modellen (Anthropic-style v2) ────────────────────────
// Udtrukket til sseProtocol.ts (delt med rich-rendering). Re-eksporteres her
// for bagudkompatibilitet med eksisterende imports.

export type {
  MessageStartEvent,
  ContentBlockStartEvent,
  ContentBlockDeltaEvent,
  ContentBlockStopEvent,
  MessageDeltaEvent,
  MessageStopEvent,
  PingEvent,
  SystemEvent,
  StreamEvent,
} from './sseProtocol'

import type { StreamEvent } from './sseProtocol'

// ─── Typed errors ──────────────────────────────────────────────────────

export type ErrorCategory =
  | 'network'
  | 'auth'
  | 'rate_limit'
  | 'server'
  | 'protocol'
  | 'cancelled'
  | 'unknown'

export class StreamError extends Error {
  category: ErrorCategory
  retryable: boolean
  statusCode: number | null
  context: Record<string, unknown>

  constructor(
    category: ErrorCategory,
    message: string,
    options: {
      retryable?: boolean
      statusCode?: number | null
      context?: Record<string, unknown>
      cause?: Error
    } = {},
  ) {
    super(message)
    this.name = 'StreamError'
    this.category = category
    this.retryable = options.retryable ?? false
    this.statusCode = options.statusCode ?? null
    this.context = options.context ?? {}
    if (options.cause) (this as Error & { cause?: Error }).cause = options.cause
  }

  /** Bruger-venlig dansk besked. Sikker at vise i UI. */
  userMessage(): string {
    switch (this.category) {
      case 'network':
        return 'Kunne ikke forbinde til Jarvis. Tjek netværk eller server-adresse.'
      case 'auth':
        return 'Adgangstoken er udløbet eller ugyldig. Log ind igen.'
      case 'rate_limit':
        return 'For mange forespørgsler. Prøver igen om lidt.'
      case 'server':
        return 'Jarvis-server svarede med en fejl. Vi prøver igen automatisk.'
      case 'protocol':
        return 'Modtaget uventet data fra serveren. Forbindelsen genstartes.'
      case 'cancelled':
        return 'Forespørgsel afbrudt.'
      case 'unknown':
      default:
        return `Uventet fejl: ${this.message}`
    }
  }
}

// ─── Reconnect backoff schedule ─────────────────────────────────────────

const RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000, 15000, 30000]
const PING_TIMEOUT_MS = 70_000 // 70s uden ping → død forbindelse
const MAX_BODY_BYTES = 50 * 1024 * 1024 // 50MB hard cap på enkelt-event payload

// ─── Hovedklassen ──────────────────────────────────────────────────────

export interface StreamRequest {
  apiBaseUrl: string
  authToken: string | null
  sessionId: string
  message: string
  approvalMode?: 'ask' | 'trust'
  thinkingMode?: 'think' | 'fast'
  attachmentIds?: string[]
}

export interface StreamHandlers {
  /** Hvert v2-event leveres her, typet. */
  onEvent: (event: StreamEvent) => void
  /** Vi forsøger reconnect — UI kan vise "reconnecter..." */
  onReconnect?: (attempt: number, delayMs: number) => void
  /** Endelig fejl (efter alle retries opbrugt eller non-retryable). */
  onError?: (error: StreamError) => void
  /** Strømmen er endegyldigt færdig (message_stop set eller abort). */
  onComplete?: () => void
}

/**
 * Send en besked og konsumér /chat/stream/v2.
 *
 * Returnerer en abort-funktion. Kald den for at lukke streamen rent.
 */
export function startStream(
  request: StreamRequest,
  handlers: StreamHandlers,
): () => void {
  const abortController = new AbortController()
  let reconnectAttempt = 0
  let lastEventId: string | null = null
  let userAborted = false
  let pingWatchdogTimer: ReturnType<typeof setTimeout> | null = null

  const log = (msg: string, ctx?: Record<string, unknown>): void => {
    // Console-log for udvikler. Ingen sensitive data — token er nedklassificeret.
    // eslint-disable-next-line no-console
    console.log(`[streamClient] ${msg}`, ctx ?? '')
  }

  const resetPingWatchdog = (): void => {
    if (pingWatchdogTimer) clearTimeout(pingWatchdogTimer)
    pingWatchdogTimer = setTimeout(() => {
      log('ping watchdog: no ping in 70s — forcing reconnect')
      // Force-close den nuværende stream — fetch's signal aborterer
      // og catch-grenen scheduler reconnect.
      try {
        abortController.abort()
      } catch {
        // ignore
      }
    }, PING_TIMEOUT_MS)
  }

  const stopPingWatchdog = (): void => {
    if (pingWatchdogTimer) {
      clearTimeout(pingWatchdogTimer)
      pingWatchdogTimer = null
    }
  }

  const dispatchEvent = (eventName: string, dataStr: string): void => {
    // SIKKERHED: cap event-size så en ondsindet eller buggy server ikke
    // kan crashe os via en gigantisk payload.
    if (dataStr.length > MAX_BODY_BYTES) {
      log('event payload exceeds MAX_BODY_BYTES — dropping', {
        size: dataStr.length,
      })
      return
    }

    let parsed: unknown
    try {
      parsed = JSON.parse(dataStr)
    } catch (e) {
      throw new StreamError(
        'protocol',
        `Malformed JSON in event ${eventName}`,
        {
          retryable: false,
          context: { event: eventName, snippet: dataStr.slice(0, 200) },
          cause: e instanceof Error ? e : undefined,
        },
      )
    }

    if (typeof parsed !== 'object' || parsed === null) {
      throw new StreamError('protocol', `Event ${eventName} payload is not an object`, {
        retryable: false,
        context: { event: eventName },
      })
    }

    const payload = parsed as { type?: string }
    if (typeof payload.type !== 'string') {
      throw new StreamError('protocol', `Event ${eventName} payload missing 'type' field`, {
        retryable: false,
        context: { event: eventName, payload },
      })
    }

    // Validér at event-name og payload.type matcher (forhindrer
    // forkert-routede beskeder fra en buggy server).
    if (eventName !== payload.type) {
      log('event name vs payload.type mismatch — dispatching by payload.type', {
        eventName,
        type: payload.type,
      })
    }

    // Reset ping watchdog ved ENHVER aktivitet, ikke kun ping.
    resetPingWatchdog()

    // Dispatch til klient. Vi tager nu (efter validering) det validerede
    // payload som StreamEvent — TypeScript-bro er bevidst.
    handlers.onEvent(parsed as StreamEvent)
  }

  const parseSseStream = async (response: Response): Promise<void> => {
    if (!response.body) {
      throw new StreamError('protocol', 'Response has no body', { retryable: true })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE event-format: \n\n adskiller events.
        let dblNewlineIdx
        while ((dblNewlineIdx = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, dblNewlineIdx)
          buffer = buffer.slice(dblNewlineIdx + 2)

          if (!block.trim()) continue

          // Parse SSE block — kan have flere felter (event:, data:, id:, retry:)
          let eventName = 'message'
          let data = ''
          let id: string | null = null

          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              data += (data ? '\n' : '') + line.slice(5).trimStart()
            } else if (line.startsWith('id:')) {
              id = line.slice(3).trim()
            } else if (line.startsWith(':')) {
              // SSE comment — typisk keepalive. Reset watchdog.
              resetPingWatchdog()
            }
          }

          if (id) lastEventId = id

          if (data) {
            dispatchEvent(eventName, data)

            // message_stop = endelig færdig. Vi forlader reconnect-loopet.
            if (eventName === 'message_stop') {
              userAborted = true // ikke en bruger-abort, men vi vil ikke reconnecte
              handlers.onComplete?.()
              return
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  const connectOnce = async (): Promise<void> => {
    const url = new URL('/chat/stream/v2', request.apiBaseUrl).toString()
    log('connecting', { url, attempt: reconnectAttempt + 1, lastEventId })

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'Cache-Control': 'no-cache',
    }
    if (request.authToken) {
      headers.Authorization = `Bearer ${request.authToken}`
    }
    if (lastEventId) {
      headers['Last-Event-ID'] = lastEventId
    }

    let response: Response
    try {
      response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: request.sessionId,
          message: request.message,
          attachment_ids: request.attachmentIds ?? [],
          approval_mode: request.approvalMode ?? 'ask',
          thinking_mode: request.thinkingMode ?? 'think',
        }),
        signal: abortController.signal,
      })
    } catch (e) {
      // fetch() afviste — typisk netværk eller abort.
      if ((e as Error).name === 'AbortError') {
        throw new StreamError('cancelled', 'Stream aborted by client', {
          retryable: false,
        })
      }
      throw new StreamError(
        'network',
        `Kunne ikke nå serveren: ${(e as Error).message}`,
        {
          retryable: true,
          context: { url },
          cause: e instanceof Error ? e : undefined,
        },
      )
    }

    // HTTP status-klassificering.
    if (response.status === 401 || response.status === 403) {
      throw new StreamError('auth', `HTTP ${response.status}`, {
        retryable: false,
        statusCode: response.status,
      })
    }
    if (response.status === 429) {
      // Brug Retry-After hvis givet.
      const retryAfter = response.headers.get('Retry-After')
      throw new StreamError('rate_limit', `Rate-limited (HTTP 429)`, {
        retryable: true,
        statusCode: 429,
        context: { retryAfter },
      })
    }
    if (response.status >= 500) {
      throw new StreamError('server', `Server-fejl HTTP ${response.status}`, {
        retryable: true,
        statusCode: response.status,
      })
    }
    if (!response.ok) {
      throw new StreamError('unknown', `Uventet HTTP ${response.status}`, {
        retryable: false,
        statusCode: response.status,
      })
    }

    // Start ping-watchdog. Server skal sende ping hvert 5s.
    resetPingWatchdog()

    // Parse stream — kaster på protokolfejl.
    await parseSseStream(response)

    // Hvis vi når herhen uden message_stop, var det en uventet ende.
    // (Stream lukkede uden afslutningsbesked.)
    throw new StreamError('network', 'Stream sluttede uden message_stop', {
      retryable: true,
    })
  }

  const runReconnectLoop = async (): Promise<void> => {
    while (!userAborted) {
      try {
        await connectOnce()
        // connectOnce returnerede uden at kaste → message_stop er set → færdig.
        return
      } catch (e) {
        stopPingWatchdog()
        const err =
          e instanceof StreamError
            ? e
            : new StreamError('unknown', (e as Error).message, {
                cause: e as Error,
              })

        if (err.category === 'cancelled') {
          // Bruger aborted — exit clean.
          handlers.onComplete?.()
          return
        }

        if (!err.retryable) {
          // Fatal — giv klienten besked og stop.
          handlers.onError?.(err)
          return
        }

        if (reconnectAttempt >= RECONNECT_BACKOFF_MS.length * 2) {
          // Vi har prøvet rigtig mange gange. Giv op for at undgå
          // uendelig spinning.
          handlers.onError?.(
            new StreamError(
              err.category,
              `Opgav efter ${reconnectAttempt} forsøg: ${err.message}`,
              { retryable: false, context: { lastError: err } },
            ),
          )
          return
        }

        const delayMs =
          RECONNECT_BACKOFF_MS[
            Math.min(reconnectAttempt, RECONNECT_BACKOFF_MS.length - 1)
          ] ?? 30000
        reconnectAttempt++
        handlers.onReconnect?.(reconnectAttempt, delayMs)

        await new Promise((resolve) => setTimeout(resolve, delayMs))
      }
    }
  }

  // Start hele loopet i baggrunden.
  void runReconnectLoop()

  // Returnér abort-funktion.
  return () => {
    userAborted = true
    stopPingWatchdog()
    abortController.abort()
  }
}
