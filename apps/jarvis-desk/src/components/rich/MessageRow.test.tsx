import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageRow } from './MessageRow'

describe('MessageRow', () => {
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('thinking block is collapsed by default', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming={false} />)
    expect(screen.queryByText('intern')).toBeNull()
    expect(screen.getByText(/tænkte/i)).toBeInTheDocument()
  })
  it('renders user message as plain bubble text', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'hej Jarvis' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej Jarvis')).toBeInTheDocument()
  })
})
