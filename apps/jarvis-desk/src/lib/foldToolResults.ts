import type { ContentBlock } from './sseProtocol'

/** Folder kanoniske tool_result-blokke ind på deres tool_use (via tool_use_id) og
 *  fjerner tool_result-blokkene, så resultatet er den render-ContentBlock[] som
 *  MessageView allerede forstår.
 *
 *  Et tool_result UDEN match droppes ikke længere (18/9-2026). Det blev det
 *  stille, og så var der ingen måde at se at noget i beskeden ikke hang
 *  sammen. Nu bliver det sin egen blok, markeret `anomali: 'uden-kald'`, og
 *  står alene i tråden. */
export function foldToolResults(blocks: Array<Record<string, unknown>>): ContentBlock[] {
  const out: ContentBlock[] = []
  const idxById = new Map<string, number>()
  for (const b of blocks || []) {
    if (b.type === 'tool_use') {
      idxById.set(String(b.id), out.length)
      out.push({ type: 'tool_use', id: String(b.id), name: String(b.name ?? ''), input: (b.input as Record<string, unknown>) ?? {}, status: 'running' })
    } else if (b.type === 'tool_result') {
      const at = idxById.get(String(b.tool_use_id))
      if (at === undefined) {
        out.push({
          type: 'tool_use',
          id: String(b.tool_use_id || `uden-kald-${out.length}`),
          name: String(b.name || 'ukendt værktøj'),
          input: {},
          status: b.status === 'error' || b.is_error ? 'error' : 'done',
          result: String(b.content ?? ''),
          anomali: 'uden-kald',
        })
        continue
      }
      const tu = out[at] as Extract<ContentBlock, { type: 'tool_use' }>
      const status = b.status === 'error' || b.is_error ? 'error' : 'done'
      // Serveren sender kun begyndelsen af et langt resultat (20/9-2026);
      // markeringen skal med, ellers tror kortet at det har det hele.
      out[at] = {
        ...tu, status, result: String(b.content ?? ''),
        ...(b.truncated ? { resultAfkortet: true, resultTegnIAlt: Number(b.total_chars) || undefined } : {}),
      }
    } else if (b.type === 'tool_use_summary' && typeof b.summary === 'string' && b.summary.trim()) {
      // Rundens sætning (19/9-2026). Før blev den kun streamet og var væk
      // efter en genindlæsning; nu gemmer serveren den, og den må ikke falde
      // ud her som en ukendt type.
      out.push({
        type: 'tool_use_summary',
        summary: b.summary,
        preceding_tool_use_ids: Array.isArray(b.preceding_tool_use_ids)
          ? (b.preceding_tool_use_ids as unknown[]).map(String) : [],
      })
    } else if (b.type === 'text') {
      out.push({ type: 'text', text: String(b.text ?? '') })
    } else if (b.type === 'thinking') {
      // Gemte tanke-blokke hedder `text`, ikke `thinking` (visible_turn_blocks).
      // Kun `thinking` blev læst, så en tanke var ALTID tom efter reload.
      out.push({
        type: 'thinking',
        thinking: String(b.thinking ?? b.text ?? ''),
        ...(typeof b.seconds === 'number' ? { seconds: b.seconds } : {}),
      })
    } else if (b.type === 'skill_surface' && Array.isArray(b.matches)) {
      // Skills runtimen lagde i prompten (gemt først i turen).
      const matches = (b.matches as unknown[]).flatMap((m) => {
        const mm = m as { name?: unknown; score?: unknown; primary?: unknown }
        return typeof mm?.name === 'string' && typeof mm.score === 'number'
          ? [{ name: mm.name, score: mm.score, primary: !!mm.primary }]
          : []
      })
      if (matches.length) out.push({ type: 'skill_surface', matches, primary: !!b.primary || matches.some((m) => m.primary) })
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
