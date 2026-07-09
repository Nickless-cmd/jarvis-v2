import type { ContentBlock } from './sseProtocol'

/** Folder kanoniske tool_result-blokke ind på deres tool_use (via tool_use_id) og
 *  fjerner tool_result-blokkene, så resultatet er den render-ContentBlock[] som
 *  MessageView allerede forstår. tool_result uden match droppes stille. */
export function foldToolResults(blocks: Array<Record<string, unknown>>): ContentBlock[] {
  const out: ContentBlock[] = []
  const idxById = new Map<string, number>()
  for (const b of blocks || []) {
    if (b.type === 'tool_use') {
      idxById.set(String(b.id), out.length)
      out.push({ type: 'tool_use', id: String(b.id), name: String(b.name ?? ''), input: (b.input as Record<string, unknown>) ?? {}, status: 'running' })
    } else if (b.type === 'tool_result') {
      const at = idxById.get(String(b.tool_use_id))
      if (at === undefined) continue
      const tu = out[at] as Extract<ContentBlock, { type: 'tool_use' }>
      const status = b.status === 'error' || b.is_error ? 'error' : 'done'
      out[at] = { ...tu, status, result: String(b.content ?? '') }
    } else if (b.type === 'text') {
      out.push({ type: 'text', text: String(b.text ?? '') })
    } else if (b.type === 'thinking') {
      out.push({ type: 'thinking', thinking: String(b.thinking ?? '') })
    } else if (b.type === 'progress') {
      // Fladt progress-element (spec 2026-07-09) — bevares urørt så forløbs-
      // sporet kan rendres. parent_tool_use_id er null i v1.
      const st = b.status === 'error' ? 'error' : b.status === 'running' ? 'running' : 'done'
      out.push({
        type: 'progress',
        tool_use_id: String(b.tool_use_id ?? ''),
        parent_tool_use_id: b.parent_tool_use_id != null ? String(b.parent_tool_use_id) : null,
        message: String(b.message ?? ''),
        status: st,
      })
    }
  }
  return out
}
