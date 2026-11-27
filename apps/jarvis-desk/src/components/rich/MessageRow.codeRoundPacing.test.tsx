import { act, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MessageRow } from './MessageRow'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'
let shown: ContentBlock[] = []
vi.mock('../../lib/usePacedBlocks', () => ({ usePacedBlocks: () => shown }))
vi.mock('../../lib/useChatPacedBlocks', () => ({ useChatPacedBlocks: () => shown }))
afterEach(() => vi.useRealTimers())
const tool: ContentBlock = { type: 'tool_use', id: 'round', name: 'read_file', input: { path: 'a' }, status: 'running' }
it.each([false, true])('the active round fades with synthesis pacing (after answer=%s)', (afterAnswer) => {
  vi.useFakeTimers()
  localStorage.setItem(RAEKKE_KEY, '1')
  const answer: ContentBlock = { type: 'text', text: 'Resultatet.', code_answer_protocol: 1, code_answer_start: true }
  const synthesis: ContentBlock = { type: 'text', text: 'Den lange syntese er stadig ved at blive vist.', code_answer_protocol: 1, phase: 'commentary' }
  const blocks = [...(afterAnswer ? [answer] : []), tool, synthesis]
  shown = [...(afterAnswer ? [answer] : []), tool, { ...synthesis, text: 'Den' }]
  const { container, rerender } = render(<MessageRow presentation="code" role="assistant" density="compact" streaming
    blocks={blocks} runId={`run-${afterAnswer}`} turId={`turn-${afterAnswer}`} />)
  act(() => vi.advanceTimersByTime(421))
  const round = container.querySelector('.rv-arbejdsrunde[data-aktiv-runde]')!
  expect(round).not.toBeNull()
  expect(round).toHaveAttribute('data-pacing-skjult')
  expect(Boolean(round.closest('.rv-sen-runde'))).toBe(afterAnswer)
  shown = blocks
  rerender(<MessageRow presentation="code" role="assistant" density="compact" streaming
    blocks={[...blocks]} runId={`run-${afterAnswer}`} turId={`turn-${afterAnswer}`} />)
  expect(round).not.toHaveAttribute('data-pacing-skjult')
})
