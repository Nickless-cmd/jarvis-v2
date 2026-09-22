import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// V3: Klokkens WS-effekt afhaenger af `[config, hentNu]`, og `hentNu` er
// `useCallback([config])`. Et NYT config-objekt ved hver Sidebar-render (selv
// med samme apiBaseUrl/authToken) faar effekten til at koere igen og aabne
// en ny socket. Probe malt live: 6 renders → 6 sockets.
//
// `useSettings` mockes her til at returnere et FRISKT objekt-literal ved
// hvert kald — netop for at bevise at fixet ikke laener sig op ad at
// `useSettings()` selv er stabil, men memoiserer paa de to STRENGE i
// Sidebar.
const openEventSocket = vi.fn(() => ({ close: vi.fn(), onmessage: null, onerror: null }))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
  openEventSocket: (...a: unknown[]) => openEventSocket(...a),
}))
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: vi.fn().mockResolvedValue({ poster: [], antal: 0 }),
}))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [], activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({
  // Nyt objekt hver gang — samme vaerdier, ny reference.
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' } }),
}))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))

import { Sidebar } from './Sidebar'

const vis = () => render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)

describe('Sidebar — klokkens socket', () => {
  it('et nyt config-objekt pr. render aabner IKKE en ny socket hver gang', () => {
    const { rerender } = vis()
    for (let i = 0; i < 5; i += 1) {
      rerender(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />)
    }
    // 6 renders i alt (1 mount + 5 rerender) — men ÉN socket, ikke seks.
    expect(openEventSocket).toHaveBeenCalledTimes(1)
  })
})
