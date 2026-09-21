import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const saet = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationsValg: (...a: unknown[]) => hent(...a),
  saetNotifikationsValg: (...a: unknown[]) => saet(...a),
}))

import { NotifikationsValg } from './NotifikationsValg'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('NotifikationsValg', () => {
  beforeEach(() => { hent.mockReset(); saet.mockReset() })

  it('en fejl ser ikke ud som tomme valg', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<NotifikationsValg config={cfg} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
  })

  it('gemmer et valg', async () => {
    hent.mockResolvedValue({ valg: { approval: 'auto', release: 'ingen' } })
    saet.mockResolvedValue({ ok: true, fejl: '' })
    render(<NotifikationsValg config={cfg} />)
    const felt = await screen.findByLabelText('Ny app-version')
    fireEvent.change(felt, { target: { value: 'push' } })
    await waitFor(() => expect(saet).toHaveBeenCalledWith(cfg, 'release', 'push'))
  })

  it('ruller valget tilbage og siger det naar det ikke kunne gemmes', async () => {
    hent.mockResolvedValue({ valg: { release: 'ingen' } })
    saet.mockResolvedValue({ ok: false, fejl: 'Kunne ikke gemmes.' })
    render(<NotifikationsValg config={cfg} />)
    const felt = await screen.findByLabelText('Ny app-version') as HTMLSelectElement
    fireEvent.change(felt, { target: { value: 'push' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Kunne ikke gemmes.')
    await waitFor(() => expect(felt.value).toBe('ingen'))
  })
})
