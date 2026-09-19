import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ToolCard } from './ToolCard'
import type { ContentBlock } from '../../lib/sseProtocol'

function block(over: Partial<Extract<ContentBlock, { type: 'tool_use' }>>): Extract<ContentBlock, { type: 'tool_use' }> {
  return { type: 'tool_use', id: 't1', name: 'web_search', input: {}, status: 'done', ...over }
}

const bashBlock = block({ name: 'bash', input: { command: 'ls' }, result: 'fil.txt' })

describe('ToolCard', () => {
  it('compact shows pretty label + summary, hides result by default', () => {
    render(<ToolCard block={bashBlock} density="compact" />)
    expect(screen.getByText('Terminal')).toBeInTheDocument() // 'bash' → pæn label
    expect(screen.getByText('ls')).toBeInTheDocument()
    expect(screen.queryByText(/fil\.txt/)).toBeNull()
  })
  it('full shows result', () => {
    render(<ToolCard block={bashBlock} density="full" />)
    expect(screen.getByText(/fil\.txt/)).toBeInTheDocument()
  })
  it('shows pretty label + summary collapsed, not raw tool name', () => {
    render(<ToolCard block={block({ name: 'web_search', input: { query: 'vejr københavn' } })} density="compact" />)
    expect(screen.getByText('Websøgning')).toBeInTheDocument()
    expect(screen.getByText('vejr københavn')).toBeInTheDocument()
    expect(screen.queryByText('web_search')).toBeNull()
  })
  it('shows +N −M diff-stat for an edit collapsed', () => {
    // `old_text`/`new_text` — navnene vaerktoejet FAKTISK sender. Testen stod
    // med `old_string`, som intet kald bruger, og beviste derfor ingenting.
    render(<ToolCard block={block({ name: 'edit_file', input: { path: 'a.ts', old_text: 'a\nb', new_text: 'a\nc\nd' } })} density="compact" />)
    expect(screen.getByText(/\+\d+/)).toBeInTheDocument()
    expect(screen.getByText(/−\d+/)).toBeInTheDocument()
  })
  it('unknown tool gets Title-Case label', () => {
    render(<ToolCard block={block({ name: 'some_weird_tool', input: {} })} density="compact" />)
    expect(screen.getByText('Some Weird Tool')).toBeInTheDocument()
  })

  it('remember_this viser kun titlen og markerer fejl fra resultatet', () => {
    render(<ToolCard block={block({
      name: 'remember_this',
      input: { title: 'Korte svar', content: 'Privat fuld tekst, som ikke er en overskrift' },
      result: '{"status":"error","written":false}',
    })} density="compact" />)
    expect(screen.getByText('Minde')).toBeInTheDocument()
    expect(screen.getByText('Korte svar')).toBeInTheDocument()
    expect(screen.queryByText(/Privat fuld tekst/)).toBeNull()
    expect(document.querySelector('.toolcard-status.err')).toBeInTheDocument()
  })

  it('remember_this uden resultat viser ukendt udfald', () => {
    const block = { type: 'tool_use' as const, id: 'm2', name: 'remember_this',
      input: { title: 'Korte svar', content: 'Privat fuld tekst' }, status: 'done' as const }
    const { container } = render(<ToolCard block={block} density="compact" />)
    expect(container.querySelector('.toolcard-status.ukendt')).toHaveAttribute('title', 'Ukendt udfald')
  })
})
