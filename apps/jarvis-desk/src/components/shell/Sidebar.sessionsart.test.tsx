import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

/**
 * Raekkens MAERKE skal sige det samme som gruppen.
 *
 * Grupperingen blev rettet 29/9-2026 (`cbb207f41`): arten kommer fra `kind`,
 * ikke fra `workspace_kind`. Men ikonet inde i raekken blev glemt og laeste
 * stadig `workspace_kind`. Konsekvensen var en samtale der stod i KODE-listen
 * med et CHAT-ikon — gruppen sagde ét, maerket sagde noget andet.
 *
 * Det er ikke kosmetik i denne sag: det forkerte felt er praecis dét der fik
 * Bjoern til at tro at samtalen var en chat-samtale.
 *
 * Jarvis fandt resten 29/9 ved at laese commit'en efter og se hvad den IKKE
 * roerte.
 */

const SESSIONER = [
  // Hans egen sag: kode-samtale UDEN bundet arbejdstrae. 10 af 26 saa saadan ud.
  { id: 'chat-uden-traeet', title: 'kode uden arbejdstrae', updated_at: 'x',
    kind: 'code', workspace_kind: null },
  // Den modsatte fejl: chat-samtale MED arbejdstrae. 19 saa saadan ud.
  { id: 'chat-med-traeet', title: 'chat med arbejdstrae', updated_at: 'x',
    kind: 'chat', workspace_kind: 'workstation' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  // Udsnits-abonnementet gaar gennem SAMME tilstand (4/10-2026):
  // Sidebar laeser nu ÉT felt, saa den ikke rendrer hele listen om
  // ved hver stream-chunk.
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

const vis = (surface: 'chat' | 'code') =>
  render(<Sidebar surface={surface} onSurface={() => {}} userName="Bjørn" />)

/** Lucide saetter klassen paa sin svg; vi laeser den fra raekkens knap. */
const ikonKlasser = (titel: string): string => {
  const knap = screen.getByText(titel).closest('button')
  const svg = knap?.querySelector('.session-mode-icon')
  return svg?.getAttribute('class') ?? ''
}

describe('raekkens maerke foelger samtalens art', () => {
  it('en kode-samtale UDEN arbejdstrae faar KODE-maerket', () => {
    vis('code')
    expect(ikonKlasser('kode uden arbejdstrae')).toMatch(/lucide-code/i)
  })

  it('en chat-samtale MED arbejdstrae faar CHAT-maerket', () => {
    vis('chat')
    expect(ikonKlasser('chat med arbejdstrae')).toMatch(/message-square/i)
  })

  it('maerket og gruppen er ALDRIG uenige', () => {
    // Det var hele fejlen: gruppen sagde kode, maerket sagde chat.
    vis('code')
    expect(screen.queryByText('chat med arbejdstrae')).toBeNull()
    expect(ikonKlasser('kode uden arbejdstrae')).toMatch(/lucide-code/i)
  })
})
