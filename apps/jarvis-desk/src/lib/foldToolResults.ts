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
    } else if (b.type === 'image') {
      // PERSISTERET billede: en REFERENCE, ikke en src. Går urørt videre, så
      // `AttachmentBlock` kan hente det med token ved visning. Før faldt
      // typen ud af denne kæde, og et billede der levede i beskeden forsvandt
      // fra tråden efter reload.
      out.push({
        type: 'image',
        src: b.src != null ? String(b.src) : undefined,
        alt: b.alt != null ? String(b.alt) : undefined,
        attachment_id: b.attachment_id != null ? String(b.attachment_id) : undefined,
        url: b.url != null ? String(b.url) : undefined,
        filename: b.filename != null ? String(b.filename) : undefined,
        mime_type: b.mime_type != null ? String(b.mime_type) : undefined,
      })
    } else if (b.type === 'file') {
      // UDGIVET fil eller vedhæftning. Uden denne gren droppede normaliseringen
      // den, og filen Jarvis lagde ud nåede aldrig skærmen (målt 15/9-2026).
      out.push({
        type: 'file',
        filename: String(b.filename ?? 'fil'),
        url: b.url != null ? String(b.url) : undefined,
        attachment_id: b.attachment_id != null ? String(b.attachment_id) : undefined,
        mime_type: b.mime_type != null ? String(b.mime_type) : undefined,
        size_bytes: typeof b.size_bytes === 'number' ? b.size_bytes : undefined,
        kilde: b.kilde != null ? String(b.kilde) : undefined,
      })
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
