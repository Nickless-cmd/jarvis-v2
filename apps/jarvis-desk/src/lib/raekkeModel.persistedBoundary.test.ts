import { describe, it, expect } from 'vitest'
import { messageToBlocks } from './normalizeMessage'
import { opdel } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'
const blocks: ContentBlock[] = [
  { type: 'tool_use', id: 'a', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Første syntese', phase: 'commentary' },
  { type: 'text', text: 'SLUTBESKEDEN', phase: 'final_answer' },
  { type: 'tool_use', id: 'b', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Sen syntese A', phase: 'commentary' },
  { type: 'tool_use', id: 'c', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Sen syntese B', phase: 'commentary' },
]
const tekst = (b: ContentBlock[]) => b.flatMap(x => x.type === 'text' ? [x.text] : [])
describe('code mode: samme tur live og gemt', () => {
  it('bevarer alle afsnit i et direkte svar uden værktøjer', () => {
    const plain: ContentBlock[] = [
      { type: 'text', text: 'First paragraph', phase: 'commentary' },
      { type: 'text', text: 'Last paragraph', phase: 'final_answer' },
    ]
    expect(tekst(opdel(plain).svar)).toEqual(['First paragraph', 'Last paragraph'])
  })
  it('live: slutbesked og begge sene synteser er i svarsporet', () => {
    expect(tekst(opdel(blocks, false, true).svar)).toEqual(['SLUTBESKEDEN', 'Sen syntese A', 'Sen syntese B'])
  })
  it('gemt: svarsporet skal bevare den samme tekst uden et flygtigt live-flag', () => {
    expect(tekst(opdel(blocks, false, false).svar)).toEqual(['SLUTBESKEDEN', 'Sen syntese A', 'Sen syntese B'])
  })
  it('gemt: code-grænsen overlever at legacy-fasen kun markerer sidste syntese', () => {
    const saved = blocks.map((b) => b.type === 'text'
      ? { ...b, phase: b.text === 'Sen syntese B' ? 'final_answer' as const : 'commentary' as const,
          code_answer_start: b.text === 'SLUTBESKEDEN' }
      : b)
    expect(tekst(opdel(messageToBlocks({content: '', content_json: saved}), false, false).svar)).toEqual(['SLUTBESKEDEN', 'Sen syntese A', 'Sen syntese B'])
  })
})
