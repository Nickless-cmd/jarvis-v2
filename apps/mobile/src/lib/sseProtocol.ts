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

export interface RoundRestartDiscardPartialEvent {
  type: 'round_restart_discard_partial'
  run_id: string
  round: number
}

export type StreamEvent =
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
  | { type: 'thinking'; thinking: string }
  | {
      type: 'tool_use'
      id: string
      name: string
      input: Record<string, unknown>
      partialJson?: string
      status?: 'running' | 'done' | 'error'
      result?: string
    }
  | { type: 'image'; src: string; alt?: string }
