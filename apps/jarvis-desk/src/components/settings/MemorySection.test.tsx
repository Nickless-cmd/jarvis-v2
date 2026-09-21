import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getAccountMemory = vi.fn()
const searchAccountMemory = vi.fn()
vi.mock('../../lib/coworkApi', () => ({
  getAccountMemory: (...a: unknown[]) => getAccountMemory(...a),
  searchAccountMemory: (...a: unknown[]) => searchAccountMemory(...a),
}))

import { MemorySection } from './MemorySection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('MemorySection', () => {
  beforeEach(() => { getAccountMemory.mockReset(); searchAccountMemory.mockReset() })

  it('viser MEMORY.md-indhold og brain-antal', async () => {
    getAccountMemory.mockResolvedValue({
      memory_md: '- husk mælk', user_md: 'Bjørn', recent_sensory: [], brain_count: 7,
    })
    render(<MemorySection config={cfg} />)
    await waitFor(() => expect(screen.getAllByText(/husk mælk/)[0]).toBeTruthy())
    expect(screen.getByText(/7/)).toBeTruthy()
  })

  it('søger og viser resultater', async () => {
    getAccountMemory.mockResolvedValue({ memory_md: '', user_md: '', recent_sensory: [], brain_count: 0 })
    searchAccountMemory.mockResolvedValue([{ id: 's1', content: 'regnvejr' }])
    render(<MemorySection config={cfg} />)
    const input = await screen.findByPlaceholderText(/søg/i)
    fireEvent.change(input, { target: { value: 'regn' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(searchAccountMemory).toHaveBeenCalledWith(cfg, 'regn'))
    await waitFor(() => expect(screen.getByText(/regnvejr/)).toBeTruthy())
  })
})

it('reports a failed search and keeps the entered query for retry', async () => {
  getAccountMemory.mockResolvedValue({ memory_md: '', user_md: '', recent_sensory: [], brain_count: 0 })
  searchAccountMemory.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([])
  render(<MemorySection config={cfg} />)
  const input = await screen.findByLabelText('Søg i seneste observationer')
  fireEvent.change(input, { target: { value: 'ferie' } })
  fireEvent.click(screen.getByRole('button', { name: 'Søg' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Søgningen kunne ikke gennemføres')
  expect(input).toHaveValue('ferie')
  fireEvent.click(screen.getByRole('button', { name: 'Søg' }))
  expect(await screen.findByText('Ingen observationer matcher din søgning.')).toBeInTheDocument()
})
