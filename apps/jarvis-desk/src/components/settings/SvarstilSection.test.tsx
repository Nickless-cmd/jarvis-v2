import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiFetch = vi.fn()
vi.mock('../../lib/api', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { SvarstilSection } from './SvarstilSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('SvarstilSection', () => {
  beforeEach(() => apiFetch.mockReset())

  it('viser den gemte stil og sender et skift til /api/preferences', async () => {
    apiFetch.mockResolvedValueOnce({ output_style: 'technical', tool_permissions: {} })
    apiFetch.mockResolvedValueOnce({ status: 'ok' })
    render(<SvarstilSection config={cfg} />)
    const sel = await screen.findByLabelText(/hvordan jarvis svarer/i)
    await waitFor(() => expect((sel as HTMLSelectElement).value).toBe('technical'))
    fireEvent.change(sel, { target: { value: 'concise' } })
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith(cfg, '/api/preferences', { method: 'POST', body: { output_style: 'concise' } }))
    expect(await screen.findByText('Gemt')).toBeInTheDocument()
  })

  it('ruller tilbage og viser fejlen hvis serveren afviser', async () => {
    apiFetch.mockResolvedValueOnce({ output_style: 'balanced' })
    apiFetch.mockRejectedValueOnce(new Error('HTTP 400: ukendt stil'))
    render(<SvarstilSection config={cfg} />)
    const sel = await screen.findByLabelText(/hvordan jarvis svarer/i)
    await waitFor(() => expect((sel as HTMLSelectElement).disabled).toBe(false))
    fireEvent.change(sel, { target: { value: 'detailed' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Svarstilen kunne ikke gemmes')
    expect((sel as HTMLSelectElement).value).toBe('balanced')
  })
})
