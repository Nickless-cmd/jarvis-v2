import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { PanelProvider } from '../../contexts/PanelContext'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'
import { paaAendringsFokus } from '../../lib/aendringsFokus'

const REDIGERING: ContentBlock[] = [
  { type: 'tool_use', id: 'e1', name: 'edit_file', input: { path: 'src/app.ts', old_text: 'før', new_text: 'efter' },
    status: 'done', result: '{"linjer_tilfoejet":9,"linjer_fjernet":4}' },
  { type: 'text', text: 'Filen er rettet.' },
]

describe('MessageRow', () => {
  it('viser ændringskortet under svaret i rækkevisning med målte +/− tal', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    try {
      const { container } = render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
      const kort = container.querySelector('.edited-files')!
      expect(kort).toBeInTheDocument()
      expect(kort).toHaveTextContent('Redigerede 1 fil')
      expect(kort).toHaveTextContent('+9')
      expect(kort).toHaveTextContent('−4')
      expect(container.querySelectorAll('.edited-files')).toHaveLength(1)
      expect(container.querySelector('.rv-svar')!.compareDocumentPosition(kort) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    } finally { localStorage.removeItem(RAEKKE_KEY) }
  })

  it('viser ændringskortet kun én gang i almindelig visning', () => {
    localStorage.setItem(RAEKKE_KEY, '0')
    const { container } = render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
    expect(container.querySelectorAll('.edited-files')).toHaveLength(1)
  })

  it('kortets fil åbner ændringsvisningen på den valgte sti', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    const fokus = vi.fn()
    const stop = paaAendringsFokus(fokus)
    try {
      render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
      fireEvent.click(screen.getByRole('button', { name: /app\.ts/ }))
      expect(fokus).toHaveBeenCalledWith('src/app.ts')
    } finally { stop(); localStorage.removeItem(RAEKKE_KEY) }
  })
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('tænkning er én linje: live med tid, bagefter foldbar — monologen står aldrig åben i tråden', () => {
    // 16/9-2026: live strømmede hele monologen ind i tråden, og bagefter var
    // den væk. Nu en linje begge steder, som mobilen.
    const { rerender } = render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming />)
    expect(screen.getByText(/Tænker/)).toBeInTheDocument()
    expect(screen.queryByText('intern')).not.toBeInTheDocument()
    rerender(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern', seconds: 8 }]} density="compact" streaming={false} />)
    fireEvent.click(screen.getByRole('button', { name: /Tænkte i 8s/ }))
    expect(screen.getByText('intern')).toBeInTheDocument()
  })
  it('en tanke FØR et værktøjskald er færdig, selv mens turen streamer', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'plan' }, { type: 'text', text: 'svar' }]} density="compact" streaming />)
    expect(screen.queryByText(/Tænker/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tænkte' })).toBeInTheDocument()
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
