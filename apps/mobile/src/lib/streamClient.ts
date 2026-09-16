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
  researchMode?: boolean
  attachmentIds?: string[]
  /** Genoptag et run der allerede kører, i stedet for at sende en ny besked.
   *
   *  Appen river strømmen ned MED VILJE når den baggrunder (Android dræber
   *  SSE alligevel), men runnet kører videre server-side. Den indbyggede
   *  reconnect nedenfor dækker kun den UTILSIGTEDE død: `abort()` sætter
   *  `closed = true`, så den gren springes over. Uden denne vej var der
   *  ingen måde tilbage til et kørende run — man måtte lukke appen helt.
   */
  genoptag?: { runId: string; fromIdx: number }
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
  /** Hvor mange frames vi har modtaget. Skal gemmes FØR `abort()`, ellers
   *  forsvinder det med closuren — og så kan et run kun genoptages fra 0,
   *  hvilket ville afspille hele turen igen. */
  getOffset: () => number
}

/**
 * Genoptagelses-maerket efter en modtaget ramme.
 *
 * Kun rammer der LIGGER i serverens run-log taeller. Foer talte hver ramme,
 * ogsaa `ping` — men pings logges aldrig (run_event_log smider dem vaek som
 * keepalive), og baade den live stroem og subscribe sender deres egne hvert 5.
 * sekund i stilhed. Hver ping skubbede maerket ét skridt forbi serverens
 * indeks, saa en genoptagelse efter N pings SPRANG N AEGTE rammer over: en
 * `content_block_start` (hele tekstblokken vaek) eller `message_stop` (turen
 * haenger paa «arbejder»). Tavst — alt er der efter en genstart, fordi den
 * henter fra databasen (16/9-2026).
 *
 * Gap-markoeren er heller ikke en log-ramme. Den baerer i stedet serverens
 * position for rammerne efter den (`resume_idx`).
 */
export function naesteOffset(offset: number, ramme: { type?: string; kind?: string; payload?: unknown }): number {
  if (ramme.type === 'ping') return offset
  if (ramme.type === 'system_event' && ramme.kind === 'relay_gap') {
    const r = (ramme as { resume_idx?: unknown; payload?: { resume_idx?: unknown } })
    const idx = typeof r.resume_idx === 'number' ? r.resume_idx : r.payload?.resume_idx
    return typeof idx === 'number' && Number.isFinite(idx) ? idx : offset
  }
  return offset + 1
}

const eventNames = [
  'message_start',
  'content_block_start',
  'content_block_delta',
  'content_block_stop',
  'message_delta',
  'message_stop',
  'ping',
  'system_event',
  // §4.1 round-niveau-retry: serveren emitter disse som EGNE SSE-event-navne
  // (event: retry / event: round_restart_discard_partial). De skal registreres
  // her, ellers leverer react-native-sse dem aldrig til reduceren. Desk modtager
  // dem allerede (manuel SSE-reader). `retry` tolereres no-op; discard rydder den
  // live on-screen partial (advisory — serveren har allerede trunkeret det
  // persisterede svar, så en klient der ignorerer det forbliver korrekt).
  'retry',
  'round_restart_discard_partial',
  // Runde-etiketten. Uden navnet her leverer `react-native-sse` den ALDRIG —
  // samme fælde som `retry` og `round_restart_discard_partial` ovenfor, hvor
  // desk fik dem og mobilen ikke.
  'tool_round_label'
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
        // GENERATIONS-HEGN. Fase 10, kriterium 3: «fences late old-generation
        // callbacks».
        //
        // `attach()` kaldes igen ved hver genforbindelse, og den gamle
        // EventSource'ens lyttere fjernes ALDRIG — kun `close()` kaldes. En
        // sen frame fra en afloest kilde kunne derfor stadig koere hele
        // kroppen nedenfor.
        //
        // Den dyreste foelge var `offset`. Det er GENOPTAGELSES-MAERKET:
        // taeller to kilder den samme logiske frame hver sin gang, springer
        // naeste genforbindelse forbi indhold der aldrig blev vist. En tavs
        // mangel i samtalen, ikke en fejl nogen ser.
        //
        // Dertil: `attempt = 0` nulstiller backoff'en paa en doed forbindelse,
        // og `handlers.onEvent` skriver i reduceren.
        if (source !== current || closed) return

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
        offset = naesteOffset(offset, parsed)
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
      // Samme hegn. En afloest kilde der fejler bagefter ville ellers
      // planlaegge ENDNU en genforbindelse — to kilder paa samme run, som
      // begge taeller `offset` op.
      if (source !== current) return
      if (gotStop || closed) return
      try {
        source.close()
      } catch {
        /* ignore */
      }
      // Run-subscribe 404: runnet blev FÆRDIGT + ryddet server-side mens vi var
      // i baggrunden (Android kappede socket'en, svaret kom imens). Det er IKKE
      // en fejl — afslut graccelt som et normalt message_stop, så "arbejder"/
      // "genforbinder"-UI'en rydder. Klienten henter de færdige beskeder via
      // session-select (notif-tap / foreground-resync). Kun når vi kender run_id.
      const status = (event as { xhrStatus?: number }).xhrStatus
      if (activeRunId && status === 404) {
        gotStop = true
        closed = true
        handlers.onEvent({ type: 'message_stop' } as StreamEvent)
        handlers.onComplete?.()
        return
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

  if (request.genoptag) {
    // GENOPTAG: samme endpoint som den indbyggede reconnect bruger, så
    // rammerne, offset-tællingen, 404-håndteringen og backoff'en nedenfor
    // gælder uændret. Der sendes ingen besked — runnet kører allerede.
    activeRunId = request.genoptag.runId
    offset = Math.max(0, request.genoptag.fromIdx)
    const genUrl = new URL(
      `/chat/runs/${encodeURIComponent(activeRunId)}/subscribe?from_idx=${offset}`,
      request.config.apiBaseUrl
    ).toString()
    current = new EventSource<StreamEventName>(genUrl, {
      method: 'GET',
      pollingInterval: 0,
      headers: authHeaders(false)
    })
    attach(current)
    return {
      abort: () => { closed = true; current?.close() },
      getRunId: () => activeRunId,
      getOffset: () => offset
    }
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
      research_mode: request.researchMode ?? false,
      attachment_ids: request.attachmentIds ?? []
    })
  })
  attach(current)

  return {
    abort: () => {
      closed = true
      current?.close()
    },
    getRunId: () => activeRunId,
    getOffset: () => offset
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
    // followSession laeser en sessions live-stream, ikke et enkelt run, saa
    // der er intet offset at genoptage fra. 0 er aerligt: "jeg har ingen".
    getOffset: () => 0,
    abort: () => source.close(),
    getRunId: () => activeRunId
  }
}
