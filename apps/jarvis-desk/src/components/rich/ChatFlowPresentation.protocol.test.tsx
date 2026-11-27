import { act, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'
import { CODE_FOLD_MS } from '../../lib/codeTurnPresentation'

let shown: ContentBlock[] | undefined
vi.mock('../../lib/useChatPacedBlocks', () => ({ useChatPacedBlocks: (blocks: ContentBlock[]) => shown ?? blocks }))
afterEach(() => { shown = undefined; vi.useRealTimers() })
const tool = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'read_file', input: { path: `${id}.txt` }, status: 'done' })
const text = (value: string, start = false): ContentBlock => ({ type: 'text', text: value, code_answer_protocol: 1, code_answer_start: start, phase: start ? 'final_answer' : 'commentary' })
const blocks = [tool('before'), text('Arbejdsnotat.'), text('Det oprindelige svar.', true), tool('lateA'), text('Syntese A.'), tool('lateB'), text('Syntese B.')]
const props = { mode: 'living' as const, density: 'compact' as const, streaming: true, status: 'working' as const, finalAnswerStarted: true, blocks }

it('folds at the first paced answer word even when server completion arrives first', () => {
  shown = [blocks[0]!, blocks[1]!, { ...blocks[2], text: '' } as ContentBlock]
  const { container, rerender } = render(<ChatFlowPresentation {...props} />)
  const fold = container.querySelector('.chat-flow-gruppe-ydre')!
  expect(fold).toHaveAttribute('data-aaben', 'true')
  expect(container.querySelector('.rv-tur')).not.toBeVisible()
  expect(container.querySelectorAll('[data-plassering="efter"]')).toHaveLength(0)
  rerender(<ChatFlowPresentation {...props} streaming={false} status="done" paceFinalAnswer />)
  expect(fold).toHaveAttribute('data-aaben', 'true')
  expect(container.querySelector('.rv-tur')).not.toBeVisible()
  shown = [blocks[0]!, blocks[1]!, { ...blocks[2], text: 'D' } as ContentBlock]
  rerender(<ChatFlowPresentation {...props} streaming={false} status="done" paceFinalAnswer />)
  expect(fold).toHaveAttribute('data-aaben', 'false')
  expect(container.querySelector('.rv-tur')).toBeVisible()
  expect(container.querySelector('.chat-flow-answer')).toHaveTextContent('D')
})

it('keeps answer and both syntheses stable in order while only rounds collapse', () => {
  vi.useFakeTimers()
  const onPaced = vi.fn()
  const { container, rerender } = render(<ChatFlowPresentation {...props} paceFinalAnswer onAnswerPaced={onPaced} />)
  const answerNodes = [...container.querySelectorAll('.chat-flow-answer-text')]
  const ordered = container.querySelector('.chat-flow-answer')!
  expect([...ordered.children].map((e) => e.className)).toEqual([
    'chat-flow-answer-text', 'chat-flow-runde', 'chat-flow-answer-text', 'chat-flow-runde', 'chat-flow-answer-text',
  ])
  expect(container.querySelectorAll('[data-levetid="live"]')).toHaveLength(2)
  expect(onPaced).not.toHaveBeenCalled()
  rerender(<ChatFlowPresentation {...props} streaming={false} status="done" paceFinalAnswer onAnswerPaced={onPaced} />)
  const afterNodes = [...container.querySelectorAll('.chat-flow-answer-text')]
  answerNodes.forEach((node, index) => expect(afterNodes[index]).toBe(node))
  expect(ordered).toHaveTextContent('Det oprindelige svar.')
  expect(ordered).toHaveTextContent('Syntese A.')
  expect(ordered).toHaveTextContent('Syntese B.')
  expect(container.querySelectorAll('[data-levetid="kollapset"]')).toHaveLength(2)
  act(() => vi.advanceTimersByTime(CODE_FOLD_MS - 1))
  expect(onPaced).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(51))
  expect(onPaced).toHaveBeenCalledOnce()
  fireEvent.click(container.querySelector('.rv-tur')!)
  const details = container.querySelector('.chat-flow-work-details')!
  expect(details.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(2)
  expect(details).not.toHaveTextContent('Det oprindelige svar.')
})


it('retains revealed round details while the head closes', () => {
  const { container } = render(<ChatFlowPresentation {...props} />)
  fireEvent.click(container.querySelector('.rv-tur')!)
  const details = container.querySelector('.chat-flow-work-details')!
  expect(details.querySelector('.rv-arbejdsrunde')).not.toBeNull()
  fireEvent.click(container.querySelector('.rv-tur')!)
  expect(container.querySelector('.chat-flow-work-details')).toBe(details)
  expect(container.querySelector('.chat-flow-gruppe-ydre')).toHaveAttribute('inert')
})
