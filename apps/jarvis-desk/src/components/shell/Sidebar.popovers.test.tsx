import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: null, select: vi.fn(), newChat: vi.fn() }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  // Udsnits-abonnementet gaar gennem SAMME tilstand (4/10-2026):
  // Sidebar laeser nu ÉT felt, saa den ikke rendrer hele listen om
  // ved hver stream-chunk.
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('./Klokke', () => ({ Klokke: ({ onAaben }: { onAaben: () => void }) => <button onClick={onAaben}>Klokke</button> }))
vi.mock('./NotifikationsFeed', () => ({ NotifikationsFeed: ({ onAabnSession }: { onAabnSession: (id: string) => void }) => <div role="dialog" aria-label="Notifikationer"><button onClick={() => onAabnSession('other')}>Anden session</button></div> }))
vi.mock('./NotifikationSessionPanel', () => ({ NotifikationSessionPanel: ({ sessionId, isOwner }: { sessionId: string; isOwner: boolean }) => <div role="dialog" aria-label="Samtale fra notifikation" data-session={sessionId} data-owner={String(isOwner)} /> }))

import { Sidebar } from './Sidebar'

describe('Sidebar popovers', () => {
  it('åbner den notificerede session i højre panel', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    fireEvent.click(screen.getByRole('button', { name: 'Anden session' }))
    const panel = screen.getByRole('dialog', { name: 'Samtale fra notifikation' })
    expect(panel).toHaveAttribute('data-session', 'other')
    expect(panel).toHaveAttribute('data-owner', 'true')
    expect(screen.queryByRole('dialog', { name: 'Notifikationer' })).toBeNull()
  })
  it('klokken åbner og lukker feedet ved gentaget klik', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    expect(screen.getByRole('dialog', { name: 'Notifikationer' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    expect(screen.queryByRole('dialog', { name: 'Notifikationer' })).toBeNull()
  })

  it('klikket udenfor og Escape lukker feedet', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('dialog', { name: 'Notifikationer' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog', { name: 'Notifikationer' })).toBeNull()
  })
})
