import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const afgoer = vi.fn()
const set = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => set(...a),
}))

import { NotifikationsFeed } from './NotifikationsFeed'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const post = (o: Partial<Record<string, unknown>> = {}) => ({
  id: '1', slags: 'approval', titel: 'Vil du tillade bash?',
  tekst: 'Jarvis vil køre en kommando.', session_id: 's-1',
  oprettet: new Date().toISOString(), kan_afgoere: true, foraeldet: false, ...o,
})

describe('NotifikationsFeed', () => {
  beforeEach(() => { hent.mockReset(); afgoer.mockReset(); set.mockReset() })

  it('en fejl ser IKKE ud som en tom feed', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
    expect(screen.queryByText(/Ingen notifikationer/)).toBeNull()
  })

  it('siger det pænt naar der faktisk ikke er noget', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText(/Ingen notifikationer/)).toBeInTheDocument()
  })

  it('godkender og fjerner posten fra listen', async () => {
    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [], antal: 0 })
    afgoer.mockResolvedValue({ ok: true, fejl: '' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, '1', true))
    await waitFor(() => expect(screen.queryByText('Vil du tillade bash?')).toBeNull())
  })

  it('siger det hoejt naar et svar ikke kunne sendes — og beholder posten', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    afgoer.mockResolvedValue({ ok: false, fejl: 'Kørslen er væk.' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Afvis' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Kørslen er væk.')
    expect(screen.getByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('en foraeldet post kan ikke afgoeres', async () => {
    hent.mockResolvedValue({ poster: [post({ foraeldet: true, kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText('Vil du tillade bash?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    expect(screen.getByText(/kunne ikke opdateres/i)).toBeInTheDocument()
  })

  it('baerer den fulde tekst som hover-information', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const raekke = await screen.findByTestId('notif-1')
    expect(raekke.getAttribute('title')).toBe('Jarvis vil køre en kommando.')
  })

  it('et spoergsmaal foerer hen til samtalen — det kan ikke svares her', async () => {
    hent.mockResolvedValue({
      poster: [post({ slags: 'question', kan_afgoere: false, titel: 'Hvilken fil?' })],
      antal: 1,
    })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    await screen.findByText('Hvilken fil?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    fireEvent.click(screen.getByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
  })

  it('aabner samtalen naar man trykker paa en post uden handling', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    fireEvent.click(await screen.findByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, '1'))
  })
})
