import type { ContentBlock } from './sseProtocol'

/** Render-lokal blok-type: en sammenfoldet run af read/søge-tool-kald.
 *  IKKE en del af sseProtocol.ContentBlock (wire/persist) — den findes kun i
 *  view-laget og persisteres/sendes aldrig. */
export interface ToolGroupBlock {
  type: 'tool_group'
  kind: 'round'
  count: number
  tools: Array<Extract<ContentBlock, { type: 'tool_use' }>>
}

/** Union som render-laget dispatcher over: alle wire-blokke + den view-lokale
 *  tool_group. */
export type RenderBlock = ContentBlock | ToolGroupBlock

/**
 * Gruppér ALLE sammenhængende tool-kald til ÉN runde — 1:1 med mobilen.
 *
 * Før foldede vi kun ≥3 read/søge-kald og lod resten stå enkeltvis. Mobilen
 * grupperer HELE runden uanset værktøj: fortælling → én linje → fortælling.
 * En tekst- eller thinking-blok afslutter runden.
 *
 * Fejlede kald brydes stadig ud og står alene. En fejl må aldrig forsvinde
 * ind i «Kørte 5 værktøjer» — den er netop det man leder efter.
 */
function erSamlbar(b: RenderBlock): b is Extract<ContentBlock, { type: 'tool_use' }> {
  return b.type === 'tool_use' && b.status !== 'error' && b.name !== 'pause_and_ask'
}

export function groupToolRounds(blocks: RenderBlock[]): RenderBlock[] {
  const ud: RenderBlock[] = []
  let buffer: Array<Extract<ContentBlock, { type: 'tool_use' }>> = []
  const flush = () => {
    if (buffer.length === 0) return
    ud.push({ type: 'tool_group', kind: 'round', count: buffer.length, tools: buffer })
    buffer = []
  }
  for (const b of blocks) {
    if (erSamlbar(b)) buffer.push(b)
    else { flush(); ud.push(b) }
  }
  flush()
  return ud
}
