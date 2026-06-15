import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const setCoworkTodoStatus = vi.fn().mockResolvedValue(undefined)
const setCoworkTodoExpiry = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  createCoworkTodo: vi.fn().mockResolvedValue(undefined),
  setCoworkTodoStatus: (...a: unknown[]) => setCoworkTodoStatus(...a),
  deleteCoworkTodo: vi.fn().mockResolvedValue(undefined),
  setCoworkTodoExpiry: (...a: unknown[]) => setCoworkTodoExpiry(...a),
}))

import { TodoPane } from './TodoPane'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('TodoPane TTL + pause', () => {
  beforeEach(() => { setCoworkTodoStatus.mockClear(); setCoworkTodoExpiry.mockClear() })

  it('pause-knap sætter status=paused', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /pause/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'paused'))
  })

  it('genoptag-knap på pauset todo sætter status=pending', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'paused' }]} config={cfg} />)
    fireEvent.click(screen.getByRole('button', { name: /genoptag/i }))
    await waitFor(() => expect(setCoworkTodoStatus).toHaveBeenCalledWith(cfg, 'td-1', 'pending'))
  })

  it('TTL-vælger "1 dag" sætter et expires_at', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending' }]} config={cfg} />)
    fireEvent.change(screen.getByLabelText(/udløb/i), { target: { value: 'day' } })
    await waitFor(() => expect(setCoworkTodoExpiry).toHaveBeenCalled())
    const call = setCoworkTodoExpiry.mock.calls[0]!
    expect(call[1]).toBe('td-1')
    expect(typeof call[2]).toBe('string')
  })

  it('TTL-vælger "Ingen" rydder expires_at', async () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'pending', expires_at: '2099-01-01T00:00:00+00:00' }]} config={cfg} />)
    fireEvent.change(screen.getByLabelText(/udløb/i), { target: { value: 'none' } })
    await waitFor(() => expect(setCoworkTodoExpiry).toHaveBeenCalledWith(cfg, 'td-1', null))
  })

  it('udløbet todo vises mutet med "udløbet"', () => {
    render(<TodoPane todos={[{ id: 'td-1', content: 'x', status: 'expired' }]} config={cfg} />)
    expect(screen.getByText(/udløbet/i)).toBeTruthy()
  })
})
