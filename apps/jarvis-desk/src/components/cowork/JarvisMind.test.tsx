import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../lib/api', () => ({
  getMindIndex: vi.fn().mockResolvedValue({
    index: [
      { section: 'overview', label: 'Oversigt', ready: true },
      { section: 'mind', label: 'Sind', ready: true },
      { section: 'council', label: 'Council', ready: false },
    ],
  }),
  getMindSection: vi.fn().mockImplementation((_c, section: string) =>
    section === 'mind'
      ? Promise.resolve({ summary: '2/3 systemer aktive', systems: [
          { system: 'inner_voice', active: true, summary: 'taler' },
          { system: 'dreams', active: false },
        ] })
      : Promise.resolve({ status: 'green', coverage: { nerves: 116, clusters: 20 } }),
  ),
  pingServer: vi.fn().mockResolvedValue(20),  // ConnectionPill › useConnection
}))
vi.mock('../../lib/centralStream', () => ({
  subscribeCentralStream: vi.fn(() => () => {}),
}))

import { JarvisMind } from './JarvisMind'
import { getMindIndex, getMindSection } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

describe('JarvisMind', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('bygger sub-navbar fra hub-index (ét ground truth)', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindIndex).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Sind' })).toBeTruthy())
    expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy()
  })

  it('åbner den DELTE Central-stream for den levende puls', () => {
    render(<JarvisMind config={CFG} />)
    expect(subscribeCentralStream).toHaveBeenCalled()
  })

  it('default-fanen Sind henter sektion fra hub og viser surfaces', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindSection).toHaveBeenCalledWith(CFG, 'mind'))
    await waitFor(() => expect(screen.getByText(/inner voice/i)).toBeTruthy())
  })

  it('placeholder for pending-faner', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Council' }))
    expect(screen.getByText(/ikke endnu flyttet|endnu ikke flyttet/i)).toBeTruthy()
  })
})
