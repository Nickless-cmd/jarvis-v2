import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: null, select: vi.fn(), newChat: vi.fn() }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))
vi.mock('./Klokke', () => ({ Klokke: ({ onAaben }: { onAaben: () => void }) => <button onClick={onAaben}>Klokke</button> }))
vi.mock('./NotifikationsFeed', () => ({ NotifikationsFeed: () => <div role="dialog" aria-label="Notifikationer">Feed</div> }))

import { Sidebar } from './Sidebar'

describe('Sidebar popovers', () => {
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
