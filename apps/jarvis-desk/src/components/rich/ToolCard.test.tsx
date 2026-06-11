import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ToolCard } from './ToolCard'

const block = { type: 'tool_use' as const, id: 't1', name: 'bash', input: { command: 'ls' }, status: 'done' as const, result: 'fil.txt' }

describe('ToolCard', () => {
  it('compact shows name + status, hides result by default', () => {
    render(<ToolCard block={block} density="compact" />)
    expect(screen.getByText(/bash/)).toBeInTheDocument()
    expect(screen.queryByText(/fil\.txt/)).toBeNull()
  })
  it('full shows result', () => {
    render(<ToolCard block={block} density="full" />)
    expect(screen.getByText(/fil\.txt/)).toBeInTheDocument()
  })
})
