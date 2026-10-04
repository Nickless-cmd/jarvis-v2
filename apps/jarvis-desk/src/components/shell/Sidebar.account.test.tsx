import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const update = vi.fn().mockResolvedValue(undefined)
const setFigure = vi.fn()
vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../lib/coworkApi', () => ({ getAccountQuota: vi.fn().mockResolvedValue({ tier: 'owner', items: [] }) }))
vi.mock('../../lib/figurVist', () => ({ useFigurVist: () => [true, setFigure] }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: null, select: vi.fn(), newChat: vi.fn() }),
}))
// Rollen kan skiftes pr. test — Michelle er `partner` i users.json, og det er
// netop den rolle klienten ikke kendte (Bjørn 29/9-2026).
const konto = vi.hoisted(() => ({ role: 'owner' }))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({
    settings: { apiBaseUrl: 'http://x', authToken: 't' },
    auth: { role: konto.role, display_name: 'Bjørn' }, update,
  }),
}))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  // Udsnits-abonnementet gaar gennem SAMME tilstand (4/10-2026):
  // Sidebar laeser nu ÉT felt, saa den ikke rendrer hele listen om
  // ved hver stream-chunk.
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('./Klokke', () => ({ Klokke: () => <button>Klokke</button> }))

import { Sidebar } from './Sidebar'

describe('konto-menu i Sidebar', () => {
  it('viser navn og tier samt figur og indstillinger i én menu', async () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Åbn konto-menu' }))
    expect(screen.getByRole('menu', { name: 'Konto' })).toBeTruthy()
    expect(screen.getByText('Owner')).toBeTruthy()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Skjul figur' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Skjul figur' }))
    expect(setFigure).toHaveBeenCalledWith(false)
    expect(screen.getByRole('button', { name: 'Indstillinger' })).toBeTruthy()
  })

  it('åbner indstillinger og kan logge ud', () => {
    const onSurface = vi.fn()
    render(<Sidebar surface="chat" onSurface={onSurface} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Åbn konto-menu' }))
    fireEvent.click(screen.getByRole('button', { name: 'Indstillinger' }))
    expect(onSurface).toHaveBeenCalledWith('settings')
    fireEvent.click(screen.getByRole('button', { name: 'Åbn konto-menu' }))
    fireEvent.click(screen.getByRole('button', { name: 'Log ud' }))
    expect(update).toHaveBeenCalledWith({ authToken: null })
  })
})

describe('rollen og bug-ikonet i fodens bund', () => {
  beforeEach(() => { konto.role = 'owner' })

  const who = () => screen.getByRole('button', { name: 'Åbn konto-menu' })

  it('skriver rollen efter navnet med en streg imellem', () => {
    // Bjørn 29/9-2026: «badge og navn efter navn bør der være en - og så
    // member/tier». ÉN rolle — ikke både role og tier.
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    expect(who().textContent).toContain('Bjørn')
    expect(who().textContent).toContain('- owner')
  })

  it('viser partner for Michelle — rollen findes i users.json', () => {
    // Klientens type kendte kun owner|member|guest, så et partner-token blev
    // vist som noget andet end det var.
    konto.role = 'partner'
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Michelle" />)
    expect(who().textContent).toContain('- partner')
  })

  it('viser member for Mikkel', () => {
    konto.role = 'member'
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Mikkel" />)
    expect(who().textContent).toContain('- member')
  })

  it('har et bug-ikon i fodens højre side', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    expect(screen.getByRole('button', { name: 'Rapportér en fejl' })).toBeTruthy()
  })

  it('bug-feltet lægger rapporten i skrivefeltet via jarvis-bug', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Rapportér en fejl' }))
    fireEvent.change(screen.getByLabelText('Hvad gik galt?'), { target: { value: 'Streamen stopper' } })
    const fanget: string[] = []
    const lyt = (e: Event) => fanget.push(String((e as CustomEvent<string>).detail))
    window.addEventListener('jarvis-bug', lyt)
    fireEvent.click(screen.getByRole('button', { name: 'Send til Jarvis' }))
    window.removeEventListener('jarvis-bug', lyt)
    expect(fanget).toEqual(['Streamen stopper'])
    // Feltet lukker og tømmes, så rapporten ikke kan sendes to gange.
    expect(screen.queryByLabelText('Hvad gik galt?')).toBeNull()
  })

  it('kan ikke sende en tom rapport', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Rapportér en fejl' }))
    expect(screen.getByRole('button', { name: 'Send til Jarvis' })).toBeDisabled()
  })
})
