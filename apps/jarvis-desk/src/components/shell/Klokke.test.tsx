import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const hent = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
}))

// Stub-sockets til WS-lytte-testerne nedenfor. Hver kaldt openEventSocket()
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
    sockets.length = 0
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

  // Selve hullet: fire tests ovenfor laaser TITEL/aria-label fast naar
  // hentningen fejler, men ingen af dem ser efter den visuelle proek selv.
  // En seende bruger ser `.klokke-fejl`; title/aria-label er kun der for
  // skaermlaesere. Fjernes proekken fra markup'et uden at title-teksten
  // aendres, bestod de fire eksisterende tests stadig — det er praecis det
  // scenarie disse to tests skal fange.
  //
  // data-testid frem for className: se kommentaren i Klokke.tsx. Kort sagt
  // er det samme valg komponenten allerede har traffet for klokke-taeller —
  // className er en stil-krog, data-testid er testens kontrakt.
  it('proek-markoeren ER i DOM naar hentningen FEJLER', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-fejl')).toBeInTheDocument()
  })

  it('proek-markoeren er IKKE i DOM naar hentningen LYKKES', async () => {
    hent.mockResolvedValue({ poster: [], antal: 3 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    await screen.findByTestId('klokke-taeller')
    expect(screen.queryByTestId('klokke-fejl')).toBeNull()
  })

  it('proek og taeller kan staa SAMTIDIG — listen fejler nu, men sidste kendte tal huskes', async () => {
    // Maalt i Klokke.tsx: fejl-branchen kalder kun setFejl(true), den
    // nulstiller ALDRIG antal. Saa et tal der blev hentet foer et senere
    // kald fejlede, bliver staaende. Vi genskaber det ved at aendre
    // `config`-objektet: `hent` er en useCallback der afhaenger af
    // `config`, saa en ny reference faar useEffect til at koere igen —
    // samme kodesti som naar intervallet selv trigger et nyt kald.
    hent.mockResolvedValue({ poster: [{ id: '1', slags: 'approval', titel: 'A', tekst: '', kan_afgoere: true, foraeldet: false, oprettet: '', session_id: null }], antal: 1 })
    const { rerender } = render(<Klokke config={cfg} onAaben={() => {}} />)
    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('1')

    hent.mockRejectedValue(new Error('offline'))
    rerender(<Klokke config={{ ...cfg, authToken: 't2' }} onAaben={() => {}} />)

    expect(await screen.findByTestId('klokke-fejl')).toBeInTheDocument()
    expect(screen.getByTestId('klokke-taeller')).toHaveTextContent('1')
  })

  // Selve pointen med opgave 10: klokken skal opdatere sig UDEN at man gaar
  // ud og ind af appen. `hentNu` (udloest af WS'en) gaar uden om ro-loftet —
  // ellers ville en haendelse kunne blive slugt af `maaPolle`.
  it('opdaterer taelleren paa en haendelse — uden at man gaar ud og ind', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 })
       .mockResolvedValue({ poster: [], antal: 3 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('klokke-taeller')).toBeNull()

    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })

    expect(await screen.findByTestId('klokke-taeller')).toHaveTextContent('3')
  })

  // Bussen paa /ws baerer ALT — indre stemme, raesonnement, hvad som helst.
  // En fremmed haendelse maa ALDRIG udloese en hentning; ellers lytter vi
  // reelt til hele bussen i stedet for kun `notifikation.*`.
  it('ignorerer haendelser der ikke er vores', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<Klokke config={cfg} onAaben={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'runtime.tick' }) })
    await new Promise((r) => setTimeout(r, 30))
    expect(hent).toHaveBeenCalledTimes(1)
  })
})
