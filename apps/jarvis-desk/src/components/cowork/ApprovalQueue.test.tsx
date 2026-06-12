import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApprovalQueue } from './ApprovalQueue'

const items = [
  { id: 'a', kind: 'file_edit' as const, title: 'skriv core/x.py', detail: 'core/x.py', source: 'capability', diff: '-gammel\n+ny' },
  { id: 'b', kind: 'tool_intent' as const, title: 'kør git push', detail: 'git push', source: 'capability' },
]

describe('ApprovalQueue', () => {
  it('viser items + kalder onResolve ved Godkend', () => {
    const onResolve = vi.fn()
    render(<ApprovalQueue items={items} onResolve={onResolve} />)
    expect(screen.getByText('skriv core/x.py')).toBeInTheDocument()
    fireEvent.click(screen.getAllByText('Godkend')[0]!)
    expect(onResolve).toHaveBeenCalledWith('a', 'approve')
  })
  it('viser diff når man folder ud', () => {
    render(<ApprovalQueue items={items} onResolve={vi.fn()} />)
    fireEvent.click(screen.getByText('Diff'))
    expect(screen.getByText(/\+ny/)).toBeInTheDocument()
  })
  it('tom tilstand', () => {
    render(<ApprovalQueue items={[]} onResolve={vi.fn()} />)
    expect(screen.getByText(/ingen afventende/i)).toBeInTheDocument()
  })
})
