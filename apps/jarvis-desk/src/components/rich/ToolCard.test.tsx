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
    render(<ToolCard block={block({ name: 'edit_file', input: { path: 'a.ts', old_string: 'a\nb', new_string: 'a\nc\nd' } })} density="compact" />)
    expect(screen.getByText(/\+\d+/)).toBeInTheDocument()
    expect(screen.getByText(/−\d+/)).toBeInTheDocument()
  })
  it('unknown tool gets Title-Case label', () => {
    render(<ToolCard block={block({ name: 'some_weird_tool', input: {} })} density="compact" />)
    expect(screen.getByText('Some Weird Tool')).toBeInTheDocument()
  })
})
