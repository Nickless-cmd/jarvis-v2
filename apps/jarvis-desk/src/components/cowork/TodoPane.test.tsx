import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const createCoworkTodo = vi.fn().mockResolvedValue(undefined)
const setCoworkTodoStatus = vi.fn().mockResolvedValue(undefined)
const deleteCoworkTodo = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  createCoworkTodo: (...a: unknown[]) => createCoworkTodo(...a),
  setCoworkTodoStatus: (...a: unknown[]) => setCoworkTodoStatus(...a),
  deleteCoworkTodo: (...a: unknown[]) => deleteCoworkTodo(...a),
}))

import { TodoPane } from './TodoPane'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('TodoPane interaktiv', () => {
  beforeEach(() => { createCoworkTodo.mockClear(); setCoworkTodoStatus.mockClear(); deleteCoworkTodo.mockClear() })

  it('opretter en todo via input + Enter', async () => {
    const onChanged = vi.fn()
    render(<TodoPane todos={[]} config={cfg} onChanged={onChanged} />)
    const input = screen.getByPlaceholderText(/ny opgave/i)
    fireEvent.change(input, { target: { value: 'køb mælk' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(createCoworkTodo).toHaveBeenCalledWith(cfg, 'køb mælk'))
    expect(onChanged).toHaveBeenCalled()
  })

  it('cykler status ved klik på status-knap', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /skift status/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'in_progress'))
  })

  it('sletter en todo', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /slet/i }))
    await waitFor(() => expect(deleteCoworkTodo).toHaveBeenCalledWith(cfg, 'td-1'))
  })

  it('uden config: read-only (ingen input)', () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} />)
    expect(screen.queryByPlaceholderText(/ny opgave/i)).toBeNull()
  })
})
