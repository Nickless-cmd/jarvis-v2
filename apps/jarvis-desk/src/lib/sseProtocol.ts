/**
 * Anthropic-style v2 SSE event-typer for /chat/stream/v2.
 *
 * Udtrukket fra streamClient.ts så både stream-konsumenten OG rich-rendering
 * kan dele typerne uden cirkulær import. streamClient re-eksporterer dem for
 * bagudkompatibilitet.
 */

// ─── Wire-form events (1:1 fra serverens v2-protokol) ────────────────────

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
    | { type: 'tool_result'; tool_use_id: string; status: string; content: string; is_error?: boolean }
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

export type StreamEvent =
  | MessageStartEvent
  | ContentBlockStartEvent
  | ContentBlockDeltaEvent
  | ContentBlockStopEvent
  | MessageDeltaEvent
  | MessageStopEvent
  | PingEvent
  | SystemEvent

// ─── Rendret form (ikke wire-form). Bruges af reducer + rich-rendering. ───

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
  | {
      // Fladt persisteret progress-element (spec 2026-07-09 §5). Bærer den
      // narration live-working_step viste ("Analyserede billede…") så forløbet
      // overlever reload. parent_tool_use_id er altid null i v1 (fladt).
      type: 'progress'
      tool_use_id: string
      parent_tool_use_id: string | null
      message: string
      status: 'running' | 'done' | 'error'
    }

/** Lightweight type-guard: et objekt med en string `type` er et StreamEvent. */
export function isStreamEvent(value: unknown): value is StreamEvent {
  if (typeof value !== 'object' || value === null) return false
  const t = (value as { type?: unknown }).type
  return typeof t === 'string'
}

/** Groft estimat af output-tokens fra streamede blokke (≈ tegn/4). Bruges til
 *  en LIVE token-tæller i liveness-linjen — de rigtige output_tokens kommer
 *  først i message_delta ved svar-slut. */
export function approxOutputTokens(blocks: ContentBlock[]): number {
  const chars = blocks.reduce(
    (n, b) => n + (b.type === 'text' ? b.text.length : b.type === 'thinking' ? b.thinking.length : 0),
    0,
  )
  return Math.round(chars / 4)
}
