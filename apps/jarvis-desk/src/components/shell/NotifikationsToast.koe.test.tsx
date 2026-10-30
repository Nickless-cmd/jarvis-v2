/** Køen i toast-stakken (28/10-2026).
 *
 *  BAGGRUND, maalt i kilden foer aendringen: `MAKS_SAMTIDIGE = 3` og
 *  `[...nye].slice(-3)` betoed at post 4, 5 og 6 blev KASTET VÆK ved
 *  indsættelsen — ikke udskudt. Toasten havde altsaa sagt «du fik et varsel»
 *  om noget brugeren aldrig saa. Samtidig mapprede render-delen over HELE
 *  køen, saa havde posterne ligget der, var de blevet vist samtidig i stedet
 *  for efter hinanden.
 *
 *  Testene her maaler de fire ting opgaven kraever, og de er
 *  adfaerdstests: de taeler hvad der staar paa skaermen, ikke hvad der staar
 *  i filen. En grep efter `slice(-3)` ville bestaa selv om betingelsen blev
 *  genindfoert under et andet navn.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const hent = vi.fn()
const afgoer = vi.fn()
const afslut = vi.fn()

vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => afslut(...a),
}))

const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))

vi.mock('../../lib/toastLyd', () => ({ spilToastKlang: vi.fn() }))
vi.mock('../../lib/updatesBridge', () => ({ updatesBridge: () => ({}) }))

const kontraktFeed = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>(
    '../../lib/agentContractApi',
  )
  return { ...rigtig, getKontraktFeed: (...a: unknown[]) => kontraktFeed(...a) }
})

import { NotifikationsToast, MAKS_SYNLIGE, LEVETID_MS } from './NotifikationsToast'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const TOMT_KONTRAKT_FEED = {
  status: 'ok' as const, cards: [], counts: { venter: 0, svar: 0, aktiv: 0, unread: 0 },
  contract_version: '1',
}

function post(id: string, titel: string) {
  return {
    id, slags: 'approval', titel, tekst: 'Noget', kan_afgoere: true,
    foraeldet: false, oprettet: '', session_id: 's1',
  }
}

/** Baseline (tom), saa seks nye poster paa én hentning. */
async function medSeksPoster() {
  hent.mockResolvedValueOnce({ poster: [], antal: 0 })
    .mockResolvedValue({
      poster: Array.from({ length: 6 }, (_, i) => post(`p${i}`, `Post ${i}`)),
      antal: 6,
    })
  render(<NotifikationsToast config={cfg} />)
  await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
  sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
  await waitFor(() => expect(screen.getByText('Post 0')).toBeTruthy())
}

describe('toast-køen', () => {
  beforeEach(() => {
    hent.mockReset()
    hent.mockResolvedValue({ poster: [], antal: 0 })
    afgoer.mockReset(); afgoer.mockResolvedValue({ ok: true, fejl: '' })
    afslut.mockReset(); afslut.mockResolvedValue(undefined)
    kontraktFeed.mockReset(); kontraktFeed.mockResolvedValue(TOMT_KONTRAKT_FEED)
    sockets.length = 0
  })

  // (a) Seks poster: ingen tabes, kun MAKS_SYNLIGE er synlige.
  it('viser kun de foerste felter og beholder resten i koe', async () => {
    await medSeksPoster()

    // De synlige er der …
    expect(screen.getByText('Post 0')).toBeTruthy()
    expect(screen.getByText('Post 1')).toBeTruthy()
    // … og post 2-5 er IKKE smidt væk, de venter. Det er hele forskellen fra
    // `slice(-3)`: dér var de ikke i komponenten overhovedet.
    expect(screen.queryByText('Post 2')).toBeNull()
    expect(document.querySelectorAll('.notif-toast').length).toBe(MAKS_SYNLIGE)
  })

  // (b) Et felt der udloeber slipper den naeste ind — uden en JS-timer der
  //     rykker køen; det sker fordi feltet fjernes fra køen.
  it('slipper den naeste ind naar et felt lukkes', async () => {
    await medSeksPoster()

    const foerste = screen.getByText('Post 0').closest('.notif-toast') as HTMLElement
    const luk = foerste.querySelector('.notif-toast-luk') as HTMLButtonElement
    luk.click()

    await waitFor(() => expect(screen.getByText('Post 2')).toBeTruthy())
    expect(screen.queryByText('Post 0')).toBeNull()
    // Stadig kun MAKS_SYNLIGE felter — køen rykker ind, den vaelter ikke ud.
    expect(document.querySelectorAll('.notif-toast').length).toBe(MAKS_SYNLIGE)
  })

  // (c) PWA-visningen er stadig slaaet fra: gaten ligger i App.tsx, ikke i
  //     komponenten, saa den maa maales dér.
  it('monteres ikke i PWA-bygget (gate i App.tsx)', () => {
    const app = readFileSync(resolve(__dirname, '../../App.tsx'), 'utf8')
    const i = app.indexOf('<NotifikationsToast')
    expect(i).toBeGreaterThan(-1)
    // Gaten skal staa i samme JSX-omraade, lige foer monteringen.
    const foer = app.slice(Math.max(0, i - 1500), i)
    expect(foer).toContain('__WEB_BUILD__')
  })

  // (d) Modproeve: en tom kø crasher ikke og renderer intet.
  it('renderer intet naar koeen er tom', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    const { container } = render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(container.querySelector('.notif-toast-lag')).toBeNull()
    expect(container.querySelectorAll('.notif-toast').length).toBe(0)
  })

  it('lever laenge nok til at blive laest', () => {
    // Nedtaellingen er en CSS-animation paa LEVETID_MS; et nul her ville
    // goere hvert felt usynligt i praksis.
    expect(LEVETID_MS).toBeGreaterThan(3000)
  })
})
