import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'

const hent = vi.fn()
const sockets: Array<{ onmessage: ((e: { data: string }) => void) | null }> = []
vi.mock('../../lib/notifikationerApi', () => ({ hentNotifikationer: (...args: unknown[]) => hent(...args) }))
vi.mock('../../lib/api', () => ({ openEventSocket: () => {
  const socket = { onmessage: null, onerror: null, close: vi.fn() }
  sockets.push(socket as never)
  return socket
} }))

import { Klokke } from './Klokke'
import { markNotificationsRead } from '../../lib/notificationAttention'

const config = { apiBaseUrl: 'http://example', authToken: 'token' }
const notification = (id: string) => ({ id, slags: 'question', titel: id, tekst: id,
  session_id: 'session', oprettet: '2026-10-04T00:00:00Z', kan_afgoere: false, foraeldet: false })

describe('Klokke attention', () => {
  beforeEach(() => { localStorage.clear(); hent.mockReset(); sockets.length = 0 })

  it('shows a small unread dot and rings until opened, then rings for the next notification', async () => {
    hent.mockResolvedValue({ poster: [notification('first')], antal: 1, venter: 1 })
    const open = vi.fn()
    render(<Klokke config={config} onAaben={open} />)
    const bell = screen.getByRole('button', { name: /Notifikationer/ })
    await waitFor(() => expect(bell).toHaveClass('klokke-attention'))
    expect(screen.getByTestId('klokke-ulast')).toBeInTheDocument()
    expect(screen.queryByTestId('klokke-taeller')).toBeNull()

    fireEvent.click(bell)
    expect(open).toHaveBeenCalledOnce()
    expect(bell).not.toHaveClass('klokke-attention')
    expect(screen.getByTestId('klokke-ulast')).toBeInTheDocument()
    markNotificationsRead(['first'])
    await waitFor(() => expect(screen.queryByTestId('klokke-ulast')).toBeNull())

    hent.mockResolvedValue({ poster: [notification('first'), notification('next')], antal: 2, venter: 2 })
    sockets.at(-1)?.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
    await waitFor(() => expect(bell).toHaveClass('klokke-attention'))
    expect(screen.getByTestId('klokke-ulast')).toBeInTheDocument()
  })

  it('keeps read notification ids across remounts', async () => {
    hent.mockResolvedValue({ poster: [notification('first')], antal: 1, venter: 1 })
    const view = render(<Klokke config={config} onAaben={() => {}} />)
    await screen.findByTestId('klokke-ulast')
    fireEvent.click(screen.getByRole('button', { name: /Notifikationer/ }))
    markNotificationsRead(['first'])
    view.unmount()
    render(<Klokke config={config} onAaben={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(2))
    expect(screen.queryByTestId('klokke-ulast')).toBeNull()
  })

  it('ignores a stale response after a newer empty feed', async () => {
    let resolveOld!: (value: unknown) => void
    hent.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValue({ poster: [], antal: 0, venter: 0 })
    render(<Klokke config={config} onAaben={() => {}} />)
    act(() => { sockets.at(-1)?.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.lukket' }) }) })
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(2))
    await act(async () => { resolveOld({ poster: [notification('already-closed')], antal: 1, venter: 1 }) })
    expect(screen.getByRole('button', { name: 'Notifikationer' })).not.toHaveClass('klokke-attention')
    expect(screen.queryByTestId('klokke-ulast')).toBeNull()
  })

  // Maalt 4/10-2026: der laa 1152 aabne `run_done` («Svar klar i «X»»), og der
  // kommer en ny hver gang et run slutter. Tog klokken dem med, ringede og
  // prikkede den permanent — hvert klik kvitterer kun dem der er der NU.
  const runDone = (id: string) => ({ ...notification(id), slags: 'run_done' })

  it('ringer ikke for run_done — baggrundsstof er ikke «noget nyt»', async () => {
    hent.mockResolvedValue({ poster: [runDone('a'), runDone('b')], antal: 2, venter: 0 })
    render(<Klokke config={config} onAaben={() => {}} />)
    // Det EKSAKTE navn er beviset: baade puls og prik ville have gjort
    // aria-label til «Notifikationer — ulaeste poster».
    await waitFor(() => expect(
      screen.getByRole('button', { name: 'Notifikationer' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Notifikationer' })).not.toHaveClass('klokke-attention')
    expect(screen.queryByTestId('klokke-ulast')).toBeNull()
  })

  it('ringer stadig naar en post der kraever svar ligger ved siden af run_done', async () => {
    hent.mockResolvedValue({ poster: [runDone('a'), notification('spoerg')], antal: 2, venter: 1 })
    render(<Klokke config={config} onAaben={() => {}} />)
    await waitFor(() => expect(
      screen.getByRole('button', { name: /ulæste poster/ })).toHaveClass('klokke-attention'))
    expect(screen.getByTestId('klokke-ulast')).toBeInTheDocument()
  })
})
