import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { PanelProvider } from '../../contexts/PanelContext'

describe('MessageRow', () => {
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('forbi tænkning skjules helt; live tænkning viser "tænker…" + content', () => {
    // 2026-06-13: den hardcodede "tænkte…"-chip var legacy fra før vi havde
    // ægte thinking-content og rodede mellem tool-kald + i færdige beskeder.
    // Forbi-tænkning skjules nu HELT (intet label, intet content); kun LIVE
    // tænkning vises ("tænker…" + den strømmende content).
    const { rerender } = render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming={false} />)
    expect(screen.queryByText(/tænkte/i)).not.toBeInTheDocument()  // forbi → skjult
    expect(screen.queryByText('intern')).not.toBeInTheDocument()
    rerender(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming />)
    expect(screen.getByText(/tænker/i)).toBeInTheDocument()
    expect(screen.getByText('intern')).toBeInTheDocument()
  })
  it('renders user message as plain bubble text', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'hej Jarvis' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej Jarvis')).toBeInTheDocument()
  })
  it('viser gensend-knap på bruger-besked og kalder onResend med teksten', () => {
    const onResend = vi.fn()
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'kør igen' }]} density="compact" streaming={false} onResend={onResend} />)
    fireEvent.click(screen.getByTitle('Send igen'))
    expect(onResend).toHaveBeenCalledWith('kør igen')
  })
  it('ingen gensend-knap uden onResend', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'x' }]} density="compact" streaming={false} />)
    expect(screen.queryByTitle('Send igen')).not.toBeInTheDocument()
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
