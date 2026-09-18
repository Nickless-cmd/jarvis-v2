/**
 * Artefakt-rækken i venstre panel (Bjørn 18/9-2026: «venstre panel mangler en
 * artifakts menu i code mode»).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [], activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar, modeFor } from './Sidebar'

describe('artefakt-rækken', () => {
  it('findes i code mode', () => {
    render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)
    expect(screen.getByRole('button', { name: /Artefakter/ })).toBeTruthy()
  })

  it('findes IKKE i chat — artefakterne er arbejdet i en mappe', () => {
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    expect(screen.queryByRole('button', { name: /Artefakter/ })).toBeNull()
  })

  it('åbner artefakt-fladen', () => {
    const skift = vi.fn()
    render(<Sidebar surface="code" onSurface={skift} userName="Bjørn" />)
    fireEvent.click(screen.getByRole('button', { name: /Artefakter/ }))
    expect(skift).toHaveBeenCalledWith('artifacts')
  })

  // Uden reglen faldt mode-vælgerne tilbage til «chat» for en ukendt flade, og
  // man forlod code i det øjeblik man åbnede artefakterne.
  it('man bliver i code mens artefakterne er åbne', () => {
    expect(modeFor('artifacts')).toBe('code')
    render(<Sidebar surface="artifacts" onSurface={() => {}} userName="Bjørn" />)
    // Rækken står der stadig, og den er markeret som den aktive.
    expect(screen.getByRole('button', { name: /Artefakter/ }).className).toContain('active')
  })

  it('ukendte flader falder stadig tilbage til chat', () => {
    expect(modeFor('gallery')).toBe('chat')
    expect(modeFor('code')).toBe('code')
  })
})
