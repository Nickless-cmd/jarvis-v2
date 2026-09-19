import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { MessageRow } from './MessageRow'

afterEach(() => { vi.useRealTimers() })

describe('SkillLine i tråden', () => {
  it('skill_gate kører: egen linje med løbende tid', () => {
    vi.useFakeTimers()
    render(<MessageRow role="assistant" density="compact" streaming blocks={[
      { type: 'tool_use', id: 't1', name: 'skill_gate', input: { query: 'regneark' }, status: 'running' },
    ]} />)
    expect(screen.getByText(/Tjekker skills for «regneark»/)).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(3100) })
    expect(screen.getByText(/· 3s/)).toBeInTheDocument()
  })

  it('færdig: metadata i linjen, matches og rå kald bag chevronen', () => {
    render(<MessageRow role="assistant" density="compact" streaming={false} blocks={[
      { type: 'tool_use', id: 't1', name: 'skill_gate', input: {}, status: 'done', result: JSON.stringify({
        gate_result: 'invoked', skill_name: 'xlsx', score: 0.82, mode: 'auto_use', instructions_full_length: 4213,
        all_matches: [{ name: 'xlsx', score: 0.82 }, { name: 'csv', score: 0.4 }],
      }) },
    ]} />)
    expect(screen.getByText(/· 0,82 · indlæst · 4,2k tegn/)).toBeInTheDocument()
    expect(screen.queryByText('csv')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Skill-gate: xlsx/ }))
    expect(screen.getByText('csv')).toBeInTheDocument()
  })
})
