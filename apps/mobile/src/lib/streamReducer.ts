import type { ContentBlock, StreamEvent } from './sseProtocol'

export type StreamStatus = 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  model: string
  provider: string
  lane: string
  blocks: ContentBlock[]
  workingStep: string | null
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return {
    status: 'idle',
    activeRunId: null,
    model: '',
    provider: '',
    lane: '',
    blocks: [],
    workingStep: null,
    usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 }
  }
}

function estimateOutputTokens(blocks: ContentBlock[]): number {
  let chars = 0
  for (const b of blocks) {
    if (b?.type === 'text') chars += b.text.length
    if (b?.type === 'thinking') chars += b.thinking.length
    if (b?.type === 'tool_use' && b.partialJson) chars += b.partialJson.length
  }
  return Math.round(chars / 4)
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      return {
        ...state,
        status: 'working',
        activeRunId: event.message.id,
        model: event.message.model,
        provider: event.message.provider,
        lane: event.message.lane,
        blocks: [],
        workingStep: null,
        usage: { ...state.usage, input: event.message.usage.input_tokens, output: 0 }
      }

    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text }
      if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking }
      if (cb.type === 'tool_use') {
        blocks[event.index] = {
          type: 'tool_use',
          id: cb.id,
          name: cb.name,
          input: cb.input,
          partialJson: '',
          status: 'running'
        }
      }
      return { ...state, blocks }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') {
        blocks[event.index] = { ...existing, text: existing.text + d.text }
      }
      if (d.type === 'thinking_delta' && existing.type === 'thinking') {
        blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      }
      if (d.type === 'input_json_delta' && existing.type === 'tool_use') {
        blocks[event.index] = {
          ...existing,
          partialJson: (existing.partialJson ?? '') + d.partial_json
        }
      }
      return { ...state, blocks, usage: { ...state.usage, output: estimateOutputTokens(blocks) } }
    }

    case 'system_event':
      if (event.kind === 'run') {
        const runId = typeof event.payload.run_id === 'string' ? event.payload.run_id : ''
        return runId ? { ...state, activeRunId: runId } : state
      }
      if (event.kind === 'working_step') {
        const detail =
          typeof event.payload.detail === 'string' ? event.payload.detail : state.workingStep
        return { ...state, workingStep: detail }
      }
      return state

    case 'message_delta':
      return {
        ...state,
        usage: {
          input: event.usage.input_tokens || state.usage.input,
          output: event.usage.output_tokens,
          cacheHit: event.usage.cache_hit_tokens,
          cacheMiss: event.usage.cache_miss_tokens
        }
      }

    case 'message_stop':
      return { ...state, status: 'done' }

    default:
      return state
  }
}
