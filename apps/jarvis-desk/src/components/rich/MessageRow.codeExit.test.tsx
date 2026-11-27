import { act, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MessageRow } from './MessageRow'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import { CODE_FOLD_MS } from '../../lib/codeTurnPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'
vi.mock('../../lib/usePacedBlocks', () => ({ usePacedBlocks: (blocks: ContentBlock[]) => blocks }))
vi.mock('../../lib/useChatPacedBlocks', () => ({ useChatPacedBlocks: (blocks: ContentBlock[]) => blocks }))
afterEach(() => vi.useRealTimers())
it('retains the live row through the late-round animation before signalling handover', () => {
  vi.useFakeTimers()
  localStorage.setItem(RAEKKE_KEY, '1')
  const done = vi.fn()
  const blocks: ContentBlock[] = [
    { type: 'text', text: 'The answer', phase: 'final_answer' },
    { type: 'tool_use', id: 'late', name: 'bash', input: {}, status: 'done' },
    { type: 'text', text: 'The synthesis', phase: 'commentary' },
  ]
  const props = { role: 'assistant' as const, presentation: 'code' as const, density: 'compact' as const, blocks, onAnswerPaced: done }
  const view = render(<MessageRow {...props} streaming finalAnswerStarted />)
  view.rerender(<MessageRow {...props} streaming={false} finalAnswerStarted />)
  act(() => vi.advanceTimersByTime(CODE_FOLD_MS - 1))
  expect(done).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(51))
  expect(done).toHaveBeenCalledTimes(1)
  expect(view.container.querySelector('.rv-svar')).toHaveTextContent('The answer')
  expect(view.container.querySelector('.rv-svar')).toHaveTextContent('The synthesis')
})
