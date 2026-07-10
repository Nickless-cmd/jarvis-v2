import type { ContentBlock } from './sseProtocol'

/** Fjern sparsomme huller / falsy elementer fra en blocks-array.
 *
 * Reduceren holder `state.blocks` INDEX-ALIGNED med serverens content-block-
 * indices (nødvendigt for content_block_delta-opslag). Når en tool_result-
 * content-blok foldes ind på sin tool_use (via tool_use_id), fyldes dens eget
 * index ALDRIG → en efterfølgende tekst-blok på et højere index efterlader et
 * `undefined`-hul i arrayet. `[...blocks]`/`for..of`/`.find` densificerer hullet
 * til `undefined` og crasher på `b.type` → sort skærm (Bjørn 9. jul).
 *
 * Alle RENDER-/søge-konsumenter skal derfor gå gennem denne (aldrig råt
 * `state.blocks` til iteration der tilgår `.type`). */
export function denseBlocks(blocks: readonly (ContentBlock | undefined | null)[]): ContentBlock[] {
  return (blocks ?? []).filter(Boolean) as ContentBlock[]
}

/** Sidste tekst-blok (null-safe mod sparsomme huller). */
export function lastTextBlock(
  blocks: readonly (ContentBlock | undefined | null)[],
): { type: 'text'; text: string } | undefined {
  const dense = denseBlocks(blocks)
  for (let i = dense.length - 1; i >= 0; i--) {
    const b = dense[i]
    if (b && b.type === 'text') return b
  }
  return undefined
}
