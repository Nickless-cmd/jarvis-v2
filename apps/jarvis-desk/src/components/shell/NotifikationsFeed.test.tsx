import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const afgoer = vi.fn()
const set = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  hentTidligere: async () => ({ poster: [], antal: 0 }),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => set(...a),
}))

const kontraktFeed = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>('../../lib/agentContractApi')
  return { ...rigtig, getKontraktFeed: (...a: unknown[]) => kontraktFeed(...a) }
})

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

const forMinutterSiden = (min: number) => new Date(Date.now() - min * 60_000).toISOString()

function vis(props: Partial<Parameters<typeof NotifikationsFeed>[0]> = {}) {
  return render(
    <NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} {...props} />,
  )
}

/**
 * Feedet er fra 25/10-2026 ÉN liste: nyeste øverst, højst `FEED_MAKS` (12)
 * poster, ingen faner. Historikken er flyttet ud til sin egen flade i Arbejde.
 *
 * Testene her værner netop det skift, fordi det er der filen kan drive:
 * en fane der kommer tilbage, et loft der falder væk, eller en fodende der
 * påstår at der ikke er mere når der er.
 */
describe('NotifikationsFeed', () => {
  beforeEach(() => {
    hent.mockReset(); afgoer.mockReset(); set.mockReset()
    kontraktFeed.mockReset().mockResolvedValue({
      status: 'ok', cards: [], counts: { venter: 0, svar: 0, aktiv: 0, unread: 0 }, contract_version: 'agent-contract-v1' })
    localStorage.clear()
    sockets.length = 0
  })

  it('viser en post fra feedet', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1, venter: 1 })
    vis()
    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('har ingen faner — der er ingen tab-rolle i ruden', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1, venter: 1 })
    vis()
    await screen.findByText('Vil du tillade bash?')
    expect(screen.queryAllByRole('tab')).toHaveLength(0)
  })

  it('sorterer nyeste øverst, uanset slags', async () => {
    // `run_done` laa foer i «Svar»-fanen og var derfor ALDRIG oeverst. Nu er
    // tiden den eneste akse, saa den nyeste svar-post skal staa foerst.
    hent.mockResolvedValue({
      poster: [
        post({ id: 'gammel', titel: 'Gammel godkendelse', oprettet: forMinutterSiden(30) }),
        post({ id: 'ny', titel: 'Nyt svar', slags: 'run_done', kan_afgoere: false, oprettet: forMinutterSiden(1) }),
      ],
      antal: 2, venter: 1,
    })
    vis()
    await screen.findByText('Nyt svar')
    const titler = screen.getAllByTestId(/^notif-/).map((el) => el.textContent ?? '')
    expect(titler[0]).toContain('Nyt svar')
    expect(titler[1]).toContain('Gammel godkendelse')
  })

  it('viser højst 12 poster og siger hvor mange der er skjult', async () => {
    const mange = Array.from({ length: 15 }, (_, i) =>
      post({ id: `p${i}`, titel: `Post ${i}`, oprettet: forMinutterSiden(i + 1) }))
    hent.mockResolvedValue({ poster: mange, antal: 15, venter: 15 })
    vis({ onSeAlle: () => {} })
    await screen.findByText('Post 0')
    expect(screen.getAllByTestId(/^notif-/)).toHaveLength(12)
    expect(screen.getByRole('button', { name: /Se alle notifikationer \(3 ældre\)/ })).toBeInTheDocument()
  })

  it('fodenden kalder onSeAlle — historikken skal kunne nås', async () => {
    const seAlle = vi.fn()
    hent.mockResolvedValue({ poster: [post()], antal: 1, venter: 1 })
    vis({ onSeAlle: seAlle })
    await screen.findByText('Vil du tillade bash?')
    fireEvent.click(screen.getByRole('button', { name: /Se alle notifikationer/ }))
    expect(seAlle).toHaveBeenCalledTimes(1)
  })

  it('viser ingen fodende naar der ikke er nogen historik-flade at gaa til', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1, venter: 1 })
    vis()
    await screen.findByText('Vil du tillade bash?')
    expect(screen.queryByRole('button', { name: /Se alle notifikationer/ })).toBeNull()
  })

  it('godkender gennem API-laget og henter igen', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1, venter: 1 })
    afgoer.mockResolvedValue({ ok: true, fejl: '' })
    vis()
    fireEvent.click(await screen.findByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, '1', true))
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(2))
  })

  it('en fejlet hentning er ikke en tom liste', async () => {
    hent.mockRejectedValue(new Error('nede'))
    vis()
    expect(await screen.findByRole('alert')).toHaveTextContent('Notifikationerne kunne ikke hentes.')
    expect(screen.queryByText('Ingen notifikationer — alt er klaret.')).toBeNull()
  })

  it('tom liste har sin egen tekst', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0, venter: 0 })
    vis()
    expect(await screen.findByText('Ingen notifikationer — alt er klaret.')).toBeInTheDocument()
  })
})
