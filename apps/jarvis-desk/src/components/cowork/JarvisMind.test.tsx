import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../lib/api', () => ({
  getCognitiveArchitecture: vi.fn().mockResolvedValue({
    summary: '2/3 systemer aktive', active_count: 2, total_count: 3,
    systems: [
      { system: 'inner_voice', active: true, summary: 'taler' },
      { system: 'dreams', active: false },
      { system: 'compass', active: true },
    ],
  }),
  getMcOverview: vi.fn().mockResolvedValue({ ok: true }),
}))

import { JarvisMind } from './JarvisMind'
import { getCognitiveArchitecture } from '../../lib/api'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

describe('JarvisMind', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('viser sub-navbar med fanerne (ingen ekstra menu)', () => {
    render(<JarvisMind config={CFG} />)
    const tablist = screen.getByRole('tablist', { name: 'Jarvis Mind' })
    expect(tablist).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Sind' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Oversigt' })).toBeTruthy()
  })

  it('default-fanen Sind henter+viser cognitive surfaces', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getCognitiveArchitecture).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText(/inner voice/i)).toBeTruthy())
    expect(screen.getByText(/2\/3 systemer aktive/)).toBeTruthy()
  })

  it('placeholder for sektioner der ikke er flyttet endnu', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await userEvent.click(screen.getByRole('tab', { name: 'Council' }))
    expect(screen.getByText(/ikke endnu .*flyttet|ikke endnu flyttet|endnu ikke flyttet/i)).toBeTruthy()
  })
})
