import type { StreamEvent, ContentBlock } from './sseProtocol'

export type StreamStatus =
  | 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  blocks: ContentBlock[]
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, blocks: [], usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 } }
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
      return {
        ...state,
        status: 'working',
        activeRunId: event.message.id,
        blocks: [],
        usage: { ...state.usage, input: event.message.usage.input_tokens },
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
      return { ...state, blocks }
    }

    case 'content_block_stop':
      return state

    case 'system_event': {
      // run-event bærer det rigtige run_id (message_start har det tomt).
      if (event.kind === 'run') {
        const rp = event.payload as { run_id?: string }
        return rp.run_id ? { ...state, activeRunId: rp.run_id } : state
      }
      if (event.kind !== 'working_step') return state // ukendt kind → ignorér gracefully
      const p = event.payload as { tool_id?: string; status?: string; result?: string }
      if (!p.tool_id) return state
      const idx = state.blocks.findIndex((b) => b.type === 'tool_use' && b.id === p.tool_id)
      if (idx < 0) return state
      const blocks = state.blocks.slice()
      const b = blocks[idx]
      if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: (p.status as 'running' | 'done' | 'error') ?? b.status, result: p.result ?? b.result }
      return { ...state, blocks }
    }

    case 'message_delta':
      return {
        ...state,
        usage: {
          ...state.usage,
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
