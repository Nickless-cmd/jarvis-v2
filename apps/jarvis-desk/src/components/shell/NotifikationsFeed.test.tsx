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

// V5: samme stub-moenster som Klokke.test.tsx — hvert openEventSocket()-kald
// laegger sin stub i `sockets`, saa en test kan finde den senest oprettede
// og udloese `onmessage` selv.
const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))

import { NotifikationsFeed } from './NotifikationsFeed'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const post = (o: Partial<Record<string, unknown>> = {}) => ({
  id: '1', slags: 'approval', titel: 'Vil du tillade bash?',
  tekst: 'Jarvis vil køre en kommando.', session_id: 's-1',
  oprettet: new Date().toISOString(), kan_afgoere: true, foraeldet: false, ...o,
})

describe('NotifikationsFeed', () => {
  beforeEach(() => { hent.mockReset(); afgoer.mockReset(); set.mockReset(); sockets.length = 0 })

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

  it('viser indholdet i feedet og kan afslutte en post uden samtale', async () => {
    hent.mockResolvedValueOnce({ poster: [post({ slags: 'run_done', kan_afgoere: false, session_id: null })], antal: 1 })
      .mockResolvedValue({ poster: [], antal: 0 })
    set.mockResolvedValue(undefined)
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText('Jarvis vil køre en kommando.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Færdig' }))
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, '1'))
    await waitFor(() => expect(screen.queryByText('Vil du tillade bash?')).toBeNull())
  })

  it('kan opdatere listen manuelt, mens feedet er åbent', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 }).mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText(/Ingen notifikationer/)
    fireEvent.click(screen.getByRole('button', { name: 'Opdater notifikationer' }))
    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
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
    expect(screen.queryByRole('button', { name: 'Færdig' })).toBeNull()
    fireEvent.click(screen.getByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
    expect(set).not.toHaveBeenCalled()
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

  // V1: en `foraeldet` post har `kan_afgoere: false` (ejeren kunne ikke
  // hydreres), saa raekkens onClick gaar samme vej som "run_done" ovenfor —
  // MEN et klik her maa ALDRIG lukke posten paa serveren. Den venter stadig;
  // en utilgaengelig ejer maa ikke faa den til at ligne en klaret opgave.
  it('en foraeldet post sender IKKE /set naar man klikker den — den er ikke klaret', async () => {
    hent.mockResolvedValue({
      poster: [post({ slags: 'run_done', kan_afgoere: false, foraeldet: true })],
      antal: 1,
    })
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    fireEvent.click(await screen.findByTestId('notif-1'))
    // Navigation maa gerne ske...
    expect(aabn).toHaveBeenCalledWith('s-1')
    // ...men /set maa ALDRIG sendes for en foraeldet raekke.
    await new Promise((r) => setTimeout(r, 10))
    expect(set).not.toHaveBeenCalled()
  })

  // V5: ruden staar IKKE stille mens den er aaben — den deler klokkens
  // live-signal (samme WS-bus, samme `notifikation.*`-filter).
  it('opdaterer listen paa en haendelse — uden at man lukker og aabner ruden igen', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 })
       .mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText(/Ingen notifikationer/)

    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })

    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('ignorerer haendelser der ikke er vores', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'runtime.tick' }) })
    await new Promise((r) => setTimeout(r, 30))
    expect(hent).toHaveBeenCalledTimes(1)
  })
})
