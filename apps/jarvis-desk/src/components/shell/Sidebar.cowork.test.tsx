import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Sidebar-hooks kræver providers + netværk; mock dem til ren render-test.
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: null, select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn() }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: null }),
}))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
}))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

describe('Sidebar mode-bevidst', () => {
  it('viser cowork-menu i cowork-surface', () => {
    render(<Sidebar surface="cowork" onSurface={() => {}} userName="Bjørn" />)
    expect(screen.getByText('Marketplace')).toBeInTheDocument()
    expect(screen.getByText('Mission Control')).toBeInTheDocument()
    expect(screen.queryByText('Ny samtale')).not.toBeInTheDocument()
  })

  it('viser session-liste i chat-surface', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    expect(screen.getByText('Ny samtale')).toBeInTheDocument()
    expect(screen.queryByText('Marketplace')).not.toBeInTheDocument()
  })
})
