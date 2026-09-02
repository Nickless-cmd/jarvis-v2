import type { ContentBlock } from './sseProtocol'

/** Fjern sparsomme huller / falsy elementer fra en blocks-array.
 *
 * Reduceren holder `state.blocks` INDEX-ALIGNED med serverens content-block-
 * indices (nødvendigt for content_block_delta-opslag). Når en tool_result-
 * content-blok foldes ind på sin tool_use (via tool_use_id), fyldes dens eget
 * index ALDRIG → en efterfølgende tekst-blok på et højere index efterlader et
 * `undefined`-hul i arrayet. `for..of`/spread/`.find`/`.map` over det rå array
 * rammer så `undefined` og crasher på `b.type` → sort skærm (samme bug som
 * desk, Bjørn 9. jul).
 *
 * Alle RENDER-/søge-konsumenter skal derfor gå gennem denne (aldrig råt
 * `state.blocks` til iteration der tilgår `.type`). */
export function denseBlocks(blocks: readonly (ContentBlock | undefined | null)[]): ContentBlock[] {
  return (blocks ?? []).filter(Boolean) as ContentBlock[]
}
