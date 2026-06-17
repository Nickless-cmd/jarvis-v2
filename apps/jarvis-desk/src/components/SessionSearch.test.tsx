import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const searchSessions = vi.fn()
vi.mock('../lib/sessionSearchApi', () => ({ searchSessions: (...a: unknown[]) => searchSessions(...a) }))

import { SessionSearch } from './SessionSearch'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('SessionSearch', () => {
  beforeEach(() => searchSessions.mockReset())

  it('viser intet når lukket', () => {
    const { container } = render(<SessionSearch open={false} config={cfg} onSelect={vi.fn()} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('søger og viser hits + valg kalder onSelect+onClose', async () => {
    searchSessions.mockResolvedValue([{ session_id: 's1', title: 'Budget', snippet: 'om penge' }])
    const onSelect = vi.fn(); const onClose = vi.fn()
    render(<SessionSearch open config={cfg} onSelect={onSelect} onClose={onClose} />)
    fireEvent.change(screen.getByPlaceholderText('Søg i samtaler…'), { target: { value: 'budget' } })
    await waitFor(() => expect(screen.getByText('Budget')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Budget'))
    expect(onSelect).toHaveBeenCalledWith('s1')
    expect(onClose).toHaveBeenCalled()
  })

  it('Esc lukker', () => {
    const onClose = vi.fn()
    render(<SessionSearch open config={cfg} onSelect={vi.fn()} onClose={onClose} />)
    fireEvent.keyDown(screen.getByPlaceholderText('Søg i samtaler…'), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})
