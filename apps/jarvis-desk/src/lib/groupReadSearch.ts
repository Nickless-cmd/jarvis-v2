import type { ContentBlock } from './sseProtocol'

/** Render-lokal blok-type: en sammenfoldet run af read/søge-tool-kald.
 *  IKKE en del af sseProtocol.ContentBlock (wire/persist) — den findes kun i
 *  view-laget og persisteres/sendes aldrig. */
export interface ToolGroupBlock {
  type: 'tool_group'
  kind: 'read_search'
  count: number
  tools: Array<Extract<ContentBlock, { type: 'tool_use' }>>
}

/** Union som render-laget dispatcher over: alle wire-blokke + den view-lokale
 *  tool_group. */
export type RenderBlock = ContentBlock | ToolGroupBlock

/** Foldbare read/søge-tools — kategorisering UDELUKKENDE via tool-navn (ingen
 *  per-argument-inspektion). Konservativ default: ukendt navn → IKKE foldbart. */
const READ_SEARCH_TOOLS = new Set<string>([
  'read_file',
  'Read',
  'operator_read_file',
  'list_dir',
  'operator_list_dir',
  'find_files',
  'glob',
  'operator_glob',
  'grep',
  'operator_grep',
  'search',
  'search_sessions',
  'search_memory',
  'search_jarvis_brain',
  'web_search',
])

/** Er dette et foldbart, ikke-fejlet read/søge-tool_use? Fejl brydes altid ud
 *  (må aldrig skjules i "N gange"-samlingen). Ukendte navne → ikke foldbare. */
function isFoldable(b: RenderBlock): b is Extract<ContentBlock, { type: 'tool_use' }> {
  if (b.type !== 'tool_use') return false
  if (b.status === 'error') return false
  const name = b.name || ''
  if (READ_SEARCH_TOOLS.has(name)) return true
  // Enhver variant med "search" i navnet regnes som søgning (read-only).
  return name.toLowerCase().includes('search')
}

/** Erstat maksimale runs af ≥3 sammenhængende foldbare read/søge-tool_use-blokke
 *  med én tool_group-blok. Alt andet (tekst, thinking, muterende/fejlede/enkelte
 *  tools) bevares uændret og enkeltvis. Rent deterministisk. */
export function groupReadSearch(blocks: RenderBlock[]): RenderBlock[] {
  const out: RenderBlock[] = []
  let i = 0
  const n = blocks.length
  while (i < n) {
    const b = blocks[i]
    if (isFoldable(b)) {
      // Saml maksimal run af sammenhængende foldbare blokke.
      let j = i
      while (j < n && isFoldable(blocks[j])) j++
      const run = blocks.slice(i, j) as Array<Extract<ContentBlock, { type: 'tool_use' }>>
      if (run.length >= 3) {
        out.push({ type: 'tool_group', kind: 'read_search', count: run.length, tools: run })
      } else {
        // <3 → vis enkeltvis (skjul aldrig en enkelt handling).
        for (const r of run) out.push(r)
      }
      i = j
    } else {
      out.push(b)
      i++
    }
  }
  return out
}
