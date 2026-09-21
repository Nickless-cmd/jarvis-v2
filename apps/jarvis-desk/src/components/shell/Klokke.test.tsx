import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const hent = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
}))

import { Klokke } from './Klokke'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('Klokke', () => {
  // Et "bart" mockReset() (uden en efterfoelgende default-implementering)
  // fik vitest 2.1.9 til fejlagtigt at maerke NAESTE tests egen, korrekt
  // fangede rejection som "unhandled" — reproducerbart ogsaa i en helt
  // generisk komponent uden forbindelse til Klokke/ro/notifikationerApi.
  // Samme moenster som CentralBadge.test.tsx bruger allerede: reset og saet
  // straks en harmloes default, saa mock'en aldrig staar "tom" mellem tests.
  beforeEach(() => {
    hent.mockReset()
    hent.mockResolvedValue({ poster: [], antal: 0 })
  })

  it('viser ingen taeller naar der intet er', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(screen.queryByTestId('klokke-taeller')).toBeNull()
  })

  it('taeller ALLE aabne, ikke kun dem der kraever et svar', async () => {
    hent.mockResolvedValue({
      poster: [
        { id: '1', slags: 'approval', titel: 'A', tekst: '', kan_afgoere: true, foraeldet: false, oprettet: '', session_id: null },
        { id: '2', slags: 'run_failed', titel: 'B', tekst: '', kan_afgoere: false, foraeldet: false, oprettet: '', session_id: null },
      ],
      antal: 2,
    })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('2')
  })

  it('siger fra naar listen ikke kunne hentes — og skjuler IKKE bare taelleren', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<Klokke config={cfg} onAaben={() => {}} />)
    const knap = await screen.findByRole('button', { name: /Notifikationer/ })
    await waitFor(() => expect(knap.getAttribute('title')).toMatch(/kunne ikke hentes/i))
  })

  it('viser 9+ i stedet for et tal der sprænger prikken', async () => {
    hent.mockResolvedValue({ poster: [], antal: 14 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('9+')
  })
})
