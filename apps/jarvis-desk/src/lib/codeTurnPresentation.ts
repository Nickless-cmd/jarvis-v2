import type { ContentBlock } from './sseProtocol'

export const CODE_FOLD_MS = 379

/** Keep later work behind the text the reader has not reached yet. The
 * pacer still advances on its own clock; this only projects its cursor. */
export function codeVisibleBlocks(source: ContentBlock[], paced: ContentBlock[]): ContentBlock[] {
  const end = paced.findIndex((block, index) => block.type === 'text'
    && source[index]?.type === 'text' && block.text.length < source[index].text.length)
  return end < 0 ? paced : paced.slice(0, end + 1)
}

export function codeAnswerStarted(blocks: readonly ContentBlock[]): boolean {
  const explicitProtocol = blocks.some((b) => b.type === 'text' && b.code_answer_protocol === 1)
  return blocks.some((block) => block.type === 'text' && block.text.trim().length > 0
    && (block.code_answer_start || (!explicitProtocol && block.phase === 'final_answer')))
}

export function codeHasLateWork(blocks: readonly ContentBlock[]): boolean {
  const explicitProtocol = blocks.some((b) => b.type === 'text' && b.code_answer_protocol === 1)
  let answer = false
  for (const block of blocks) {
    if (block.type === 'text' && (block.code_answer_start || (!explicitProtocol && block.phase === 'final_answer'))) answer = true
    else if (answer && block.type === 'tool_use') return true
  }
  return false
}
