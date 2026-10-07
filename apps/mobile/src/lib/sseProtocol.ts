export interface MessageStartEvent {
  type: 'message_start'
  message: {
    id: string
    model: string
    provider: string
    lane: string
    session_id: string | null
    usage: { input_tokens: number; output_tokens: number }
  }
}

export interface ContentBlockStartEvent {
  type: 'content_block_start'
  index: number
  content_block:
    | { type: 'text'; text: string }
    | { type: 'thinking'; thinking: string }
    | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
    // Billede UNDER kørslen (27/9-2026). Samme konvolut som tool_result —
    // ingen ny event-type. Bærer `src` når den kan, ellers `attachment_id`.
    | {
        type: 'image'
        src?: string
        alt?: string
        attachment_id?: string
        url?: string
        filename?: string
        mime_type?: string
        kilde?: string
        tool_use_id?: string
      }
    // UDGIVET fil eller video UNDER kørslen (7/10-2026). Samme konvolut og
    // samme reference-felter som `image` — kun typen er forskellig.
    //
    // Uden disse to varianter her kunne reduceren ikke engang sammenligne på
    // typen, og en widget (`text/html` → `file`) faldt til jorden i den
    // levende strøm. Den dukkede først op når tråden blev genindlæst.
    | {
        type: 'file'
        src?: string
        alt?: string
        attachment_id?: string
        url?: string
        filename?: string
        mime_type?: string
        size_bytes?: number
        kilde?: string
        tool_use_id?: string
      }
    | {
        type: 'video'
        src?: string
        alt?: string
        attachment_id?: string
        url?: string
        filename?: string
        mime_type?: string
        size_bytes?: number
        kilde?: string
        tool_use_id?: string
      }
    // Den bærer et tool_use_id og foldes ind på sin matchende tool_use-blok
    // (status/result) i reduceren — den fylder ALDRIG sit eget index (undgår hul).
    | {
        type: 'tool_result'
        tool_use_id: string
        status?: string
        content?: string
        is_error?: boolean
      }
}

export interface ContentBlockDeltaEvent {
  type: 'content_block_delta'
  index: number
  delta:
    | { type: 'text_delta'; text: string }
    | { type: 'thinking_delta'; thinking: string }
    | { type: 'input_json_delta'; partial_json: string }
}

export interface ContentBlockStopEvent {
  type: 'content_block_stop'
  index: number
}

export interface MessageDeltaEvent {
  type: 'message_delta'
  delta: { stop_reason: string }
  usage: {
    input_tokens: number
    output_tokens: number
    cache_hit_tokens: number
    cache_miss_tokens: number
  }
}

export interface MessageStopEvent {
  type: 'message_stop'
}

export interface PingEvent {
  type: 'ping'
}

export interface SystemEvent {
  type: 'system_event'
  kind: string
  payload: Record<string, unknown>
}

// §4.1 round-niveau-retry — serveren emitter disse som EGNE top-level events
// (ikke system_event-kinds). `retry` er ren signalering ("Reconnecting n/m");
// `round_restart_discard_partial` instruerer klienten i at droppe den ikke-
// finaliserede on-screen partial for denne rundes run (advisory — serverens
// persisterede svar er allerede trunkeret).
export interface RetryEvent {
  type: 'retry'
  run_id: string
  round: number
  attempt: number
  max_attempts: number
  failure_kind?: string
  message?: string
}

/**
 * Én kort etiket for en afsluttet værktøjs-runde — «Rettede fejl i login».
 *
 * Skrevet af en lille LOKAL model på serveren, og leveret ved NÆSTE rundes
 * start: etiketten regnes i en tråd, og en generator kan kun yield'e fra sit
 * eget flow. Det er samme grund som får Claude Code til at levere sin næste
 * TUR — vores løkke har bare flere runder pr. tur.
 *
 * `tool_use_ids` er ikke pynt. Etiketten hæfter sig på DE kald den opsummerer,
 * ikke på en plads i strømmen: en sen etiket, eller en tråd der genopbygges i
 * en anden rækkefølge, ville ellers sætte sig over de forkerte.
 */
export interface ToolRoundLabelEvent {
  type: 'tool_round_label'
  run_id: string
  round: number
  etiket: string
  tool_use_ids: string[]
  /** Tænke-resuméet — kun når samtalen står i visningen «thinking». */
  tanke_resume?: string
}

export interface RoundRestartDiscardPartialEvent {
  type: 'round_restart_discard_partial'
  run_id: string
  round: number
}

export type StreamEvent =
  | ToolRoundLabelEvent
  | MessageStartEvent
  | ContentBlockStartEvent
  | ContentBlockDeltaEvent
  | ContentBlockStopEvent
  | MessageDeltaEvent
  | MessageStopEvent
  | PingEvent
  | SystemEvent
  | RetryEvent
  | RoundRestartDiscardPartialEvent

export type ContentBlock =
  | { type: 'text'; text: string }
  | {
      type: 'thinking'
      thinking: string
      /** Hvornaar den foerste tanke-delta faldt. */
      startet?: number
      /** Hvornaar den seneste faldt. Forskellen ER taenketiden. */
      sidst?: number
    }
  | {
      type: 'tool_use'
      id: string
      name: string
      input: Record<string, unknown>
      partialJson?: string
      status?: 'running' | 'done' | 'error'
      result?: string
      /**
       * Sat af KLIENTEN når serveren annoncerer kaldet (`working_step`), før
       * den rigtige blok findes. Bærer starttidspunktet, så rækken kan vise
       * hvor længe det har kørt — og markerer at blokken skal vige for den
       * rigtige når den kommer.
       */
      foreloebig?: {
        startet: number
        skridt: number
        /** Serverens egen menneske-læsbare etiket, fx «bash: npm test». */
        etiket: string
      }
    }
  // Billede. `src` var PÅKRÆVET indtil 27/9-2026, og derfor kunne blokken slet
  // ikke udtrykke et billede der kun har en reference. LIVE bærer den `src`
  // (data-URL) og tegnes straks; er billedet for stort til en data-URL, kommer
  // den med `attachment_id` alene og hentes over `/attachments/image/{id}`.
  // `MessageAttachments.tegnBillede` har kunnet begge dele hele tiden — den
  // tager `b.src` hvis den er der, ellers `blokUrl(b, apiBaseUrl)`.
  | {
      type: 'image'
      src?: string
      alt?: string
      attachment_id?: string
      url?: string
      filename?: string
      mime_type?: string
      kilde?: string
      tool_use_id?: string
    }
  // UDGIVET fil eller video (7/10-2026). Samme reference-felter som `image`.
  //
  // Uden dem her kunne reduceren ikke tildele blokken til tilstanden: en
  // widget er `text/html` → `file`, og den faldt til jorden i den levende
  // strøm. Den dukkede først op når tråden blev genindlæst fra serveren.
  | {
      type: 'file'
      src?: string
      alt?: string
      attachment_id?: string
      url?: string
      filename?: string
      mime_type?: string
      size_bytes?: number
      kilde?: string
      tool_use_id?: string
    }
  | {
      type: 'video'
      src?: string
      alt?: string
      attachment_id?: string
      url?: string
      filename?: string
      mime_type?: string
      size_bytes?: number
      kilde?: string
      tool_use_id?: string
    }
