import type { StreamEvent, ContentBlock } from './sseProtocol'

export type StreamStatus =
  | 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  blocks: ContentBlock[]
  workingStep: string | null // nyeste live progress-tekst (fx "Kalder analyze_image")
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, blocks: [], workingStep: null, usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 } }
}

/** Estimer output-tokens fra akkumuleret tekst/tænkning i blocks. Bruges
 * mens streaming kører, fordi Anthropic kun sender det faktiske tal i
 * `message_delta` (typisk én gang til sidst). Heuristik: ~4 chars/token. */
function estimateOutputTokens(blocks: ContentBlock[]): number {
  let chars = 0
  for (const b of blocks) {
    if (!b) continue
    if (b.type === 'text') chars += b.text.length
    else if (b.type === 'thinking') chars += b.thinking.length
    else if (b.type === 'tool_use' && b.partialJson) chars += b.partialJson.length
  }
  return Math.round(chars / 4)
}

/**
 * Ren reducer: (state, v2event) → state. Ingen netværk, ingen side-effekter.
 * Akkumulerer content-blocks pr. index og styrer status-overgange.
 * Status hung/interrupted/error sættes UDENFOR reduceren (fra streamClient-
 * handlers i StreamContext), ikke fra events.
 */
export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      // Nyt run → output-tokens nulstilles. Live-estimat bygges op via
      // content_block_delta indtil message_delta lander med det rigtige tal.
      return {
        ...state,
        status: 'working',
        activeRunId: event.message.id,
        blocks: [],
        workingStep: null,
        usage: {
          ...state.usage,
          input: event.message.usage.input_tokens,
          output: 0,
        },
      }

    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text ?? '' }
      else if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking ?? '' }
      else if (cb.type === 'tool_use') blocks[event.index] = { type: 'tool_use', id: cb.id, name: cb.name, input: cb.input ?? {}, partialJson: '', status: 'running' }
      return { ...state, blocks }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state // delta uden forudgående start → ignorér (edge-case)
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') blocks[event.index] = { ...existing, text: existing.text + d.text }
      else if (d.type === 'thinking_delta' && existing.type === 'thinking') blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      else if (d.type === 'input_json_delta' && existing.type === 'tool_use') blocks[event.index] = { ...existing, partialJson: (existing.partialJson ?? '') + d.partial_json }
      // Live-estimer output-tokens fra ny content. Erstattes af det rigtige
      // tal når message_delta lander til sidst.
      return { ...state, blocks, usage: { ...state.usage, output: estimateOutputTokens(blocks) } }
    }

    case 'content_block_stop':
      return state

    case 'system_event': {
      // run-event bærer det rigtige run_id (message_start har det tomt).
      if (event.kind === 'run') {
        const rp = event.payload as { run_id?: string }
        return rp.run_id ? { ...state, activeRunId: rp.run_id } : state
      }
      // Phase 2: tool_result formidler en tool_use-blocks udfald (status)
      // bundet til tool_use_id.
      if (event.kind === 'tool_result') {
        const tr = event.payload as { tool_use_id?: string; status?: string }
        if (!tr.tool_use_id) return state
        const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === tr.tool_use_id)
        if (idx < 0) return state
        const mapped =
          tr.status === 'ok' || tr.status === 'executed' || tr.status === 'completed'
            ? 'done'
            : tr.status === 'error' || tr.status === 'failed'
              ? 'error'
              : undefined
        const blocks = state.blocks.slice()
        const b = blocks[idx]
        if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: mapped ?? b.status }
        return { ...state, blocks }
      }
      if (event.kind !== 'working_step') return state // ukendt kind → ignorér gracefully
      const p = event.payload as { tool_id?: string; status?: string; result?: string; detail?: string; action?: string }
      // Surface seneste progress-tekst (også steps uden tool_id, fx "thinking").
      const step = p.detail ?? p.action ?? state.workingStep
      if (!p.tool_id) return { ...state, workingStep: step }
      const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === p.tool_id)
      if (idx < 0) return { ...state, workingStep: step }
      const blocks = state.blocks.slice()
      const b = blocks[idx]
      if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: (p.status as 'running' | 'done' | 'error') ?? b.status, result: p.result ?? b.result }
      return { ...state, blocks, workingStep: step }
    }

    case 'message_delta':
      return {
        ...state,
        usage: {
          ...state.usage,
          // input kommer i message_delta (v2 message_start bærer ikke usage) —
          // bruges af context-ringen (#9). Behold tidligere ved 0.
          input: event.usage.input_tokens || state.usage.input,
          output: event.usage.output_tokens,
          cacheHit: event.usage.cache_hit_tokens ?? state.usage.cacheHit,
          cacheMiss: event.usage.cache_miss_tokens ?? state.usage.cacheMiss,
        },
      }

    case 'message_stop':
      return { ...state, status: 'done' }

    case 'ping':
      return state

    default:
      return state
  }
}
