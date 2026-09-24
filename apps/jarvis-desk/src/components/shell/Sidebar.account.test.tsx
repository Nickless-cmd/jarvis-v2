import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const update = vi.fn().mockResolvedValue(undefined)
const setFigure = vi.fn()
vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../lib/coworkApi', () => ({ getAccountQuota: vi.fn().mockResolvedValue({ tier: 'owner', items: [] }) }))
vi.mock('../../lib/figurVist', () => ({ useFigurVist: () => [true, setFigure] }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: null, select: vi.fn(), newChat: vi.fn() }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({
    settings: { apiBaseUrl: 'http://x', authToken: 't' },
    auth: { role: 'owner', display_name: 'Bjørn' }, update,
  }),
}))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))
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
