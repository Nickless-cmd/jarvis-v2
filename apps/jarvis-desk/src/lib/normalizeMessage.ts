import type { ContentBlock } from './sseProtocol'
import { foldToolResults } from './foldToolResults'

/** Normalisér en server-besked (markdown-string) til ContentBlock[].
 *  Loadede beskeder kommer som string; streamede kommer som native blocks.
 *  Begge rendres af samme pipeline. */
export function stringToBlocks(content: string): ContentBlock[] {
  if (!content) return []
  return [{ type: 'text', text: content }]
}

/** Vælg render-blokke for en server-besked: kanonisk content_json (foldet) hvis
 *  til stede, ellers legacy tekst → én tekst-blok. */
export function messageToBlocks(m: { content: string; content_json?: unknown }): ContentBlock[] {
  if (Array.isArray(m.content_json) && m.content_json.length > 0) {
    return foldToolResults(m.content_json as Array<Record<string, unknown>>)
  }
  return stringToBlocks(m.content)
}
