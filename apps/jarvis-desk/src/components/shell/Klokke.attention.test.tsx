import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

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
})
