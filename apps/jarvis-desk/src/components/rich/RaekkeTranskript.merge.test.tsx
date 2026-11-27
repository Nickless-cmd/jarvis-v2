import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { RaekkeTranskript } from './RaekkeTranskript'
import type { ContentBlock } from '../../lib/sseProtocol'

const blocks: ContentBlock[] = [
  { type: 'tool_use', id: 'first', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Original answer', phase: 'final_answer' },
  { type: 'tool_use', id: 'late-a', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Synthesis A', phase: 'commentary' },
  { type: 'tool_use', id: 'late-b', name: 'bash', input: {}, status: 'done' },
  { type: 'text', text: 'Synthesis B', phase: 'commentary' },
]
describe('late round exit preserves the answer', () => {
  it('waits for pacing, then collapses only work and keeps each text container', () => {
    const view = render(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted svarRuller />)
    const texts = [...view.container.querySelectorAll('.rv-svar-tekst')]
    expect(texts.map(x => x.textContent)).toEqual(['Original answer', 'Synthesis A', 'Synthesis B'])
    view.rerender(<RaekkeTranskript blocks={blocks} streaming={false} finalAnswerStarted svarRuller />)
    expect([...view.container.querySelectorAll('.rv-sen-runde')].every(x => x.getAttribute('data-samles') === 'false')).toBe(true)
    view.rerender(<RaekkeTranskript blocks={blocks} streaming={false} finalAnswerStarted svarRuller={false} />)
    expect([...view.container.querySelectorAll('.rv-sen-runde')].every(x => x.getAttribute('data-samles') === 'true')).toBe(true)
    expect([...view.container.querySelectorAll('.rv-svar-tekst')]).toEqual(texts)
    expect(texts.map(x => x.textContent)).toEqual(['Original answer', 'Synthesis A', 'Synthesis B'])
    expect(texts[0]!.closest('.rv-sen-runde')).toBeNull()
  })
})

it('does not let an early delivery close the explicit-protocol work phase', () => {
  const view = render(<SettingsProvider><RaekkeTranskript streaming blocks={[
    { type: 'tool_use', id: 'early', name: 'bash', input: {} },
    { type: 'text', text: 'Still working', phase: 'final_answer', code_answer_protocol: 1 },
    { type: 'file', filename: 'report.txt', url: '/report.txt' },
  ]} /></SettingsProvider>)
  expect(view.container.querySelector('.rv-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
})
