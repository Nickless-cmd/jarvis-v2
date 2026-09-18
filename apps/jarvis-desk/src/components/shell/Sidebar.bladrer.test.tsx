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

import { Sidebar } from './Sidebar'

describe('bladre-pilene i sidepanelets top', () => {
  it('står LIGE FØR søgeikonet — det var kravet', () => {
    // Bjørn 18/9-2026: «i toppen lige før søge ikonet skal der være to ikoner
    // … 2 pile der køre vær sin retning». Placeringen er selve kravet, så den
    // pinnes på DOM-rækkefølgen og ikke kun på at knapperne findes.
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)

    const top = document.querySelector('.sidebar-top-actions')
    expect(top).toBeTruthy()

    const knapper = Array.from(top!.querySelectorAll('button'))
      .map((b) => b.getAttribute('aria-label') || '')

    const forrige = knapper.findIndex((n) => /Forrige tilstand/.test(n))
    const naeste = knapper.findIndex((n) => /Næste tilstand/.test(n))
    const soeg = knapper.findIndex((n) => /Søg/.test(n))

    expect(forrige).toBeGreaterThanOrEqual(0)
    expect(naeste).toBe(forrige + 1)
    expect(soeg).toBeGreaterThan(naeste)
  })

  it('bladrer faktisk til nabo-tilstanden', () => {
    const skift = vi.fn()
    render(<Sidebar surface="chat" onSurface={skift} userName="Bjørn" />)

    fireEvent.click(screen.getByLabelText('Næste tilstand: Arbejde'))
    expect(skift).toHaveBeenLastCalledWith('cowork')

    fireEvent.click(screen.getByLabelText('Forrige tilstand: Code'))
    expect(skift).toHaveBeenLastCalledWith('code')
  })
})
