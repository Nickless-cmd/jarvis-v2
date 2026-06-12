import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { PanelProvider } from '../../contexts/PanelContext'

describe('MessageRow', () => {
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('forbi tænkning skjules; live tænkning vises', () => {
    const { rerender } = render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming={false} />)
    expect(screen.queryByText(/tænk/i)).toBeNull()
    rerender(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming />)
    expect(screen.getByText(/tænker/i)).toBeInTheDocument()
    expect(screen.getByText('intern')).toBeInTheDocument()
  })
  it('renders user message as plain bubble text', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'hej Jarvis' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej Jarvis')).toBeInTheDocument()
  })
  it('viser "Åbn"-affordance for langt markdown-svar', () => {
    const long = '# Titel\n' + Array.from({ length: 45 }, (_, i) => `linje ${i}`).join('\n') + '\n## Sektion\nx'
    render(
      <PanelProvider defaultWidth={400}>
        <MessageRow role="assistant" blocks={[{ type: 'text', text: long }]} density="compact" streaming={false} />
      </PanelProvider>,
    )
    expect(screen.getByRole('button', { name: /åbn/i })).toBeTruthy()
  })
})
