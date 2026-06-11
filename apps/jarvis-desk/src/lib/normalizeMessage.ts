import type { ContentBlock } from './sseProtocol'

/** Normalisér en server-besked (markdown-string) til ContentBlock[].
 *  Loadede beskeder kommer som string; streamede kommer som native blocks.
 *  Begge rendres af samme pipeline. */
export function stringToBlocks(content: string): ContentBlock[] {
  if (!content) return []
  return [{ type: 'text', text: content }]
}
