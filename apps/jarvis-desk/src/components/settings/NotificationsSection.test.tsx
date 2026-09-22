import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { NotificationsSection } from './NotificationsSection'

const apiFetch = vi.fn()
vi.mock('../../lib/api', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

const DEFAULTS = {
  global: 'auto', briefing: null, reminder: null, reach_out: null,
  wakeup: null, quiet_start: '23:00', quiet_end: '07:00',
}

describe('NotificationsSection', () => {
  beforeEach(() => {
    apiFetch.mockReset().mockResolvedValue({ preferences: { ...DEFAULTS } })
  })

  it('henter præferencer + gemmer ændring via POST', async () => {
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    render(<NotificationsSection config={cfg} />)
    // global-dropdown vises med 'auto'
    await waitFor(() => expect(screen.getByText('Standard (alle)')).toBeInTheDocument())
    apiFetch.mockResolvedValueOnce({ preferences: { ...DEFAULTS, global: 'desktop' } })
    const selects = screen.getAllByRole('combobox')
    await userEvent.selectOptions(selects[0]!, 'desktop')
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(
      cfg, '/notifications/preferences',
      expect.objectContaining({ method: 'POST', body: { global: 'desktop' } }),
    ))
  })

  // V7: «no dual truth» — Morgenbriefing/Påmindelser/«Jarvis tager kontakt»
  // fandtes FOER som per-type-vælgere BAADE her (kolonner i
  // notification_preferences) OG i NotifikationsValg (raekker i
  // notifikations_valg), som rent faktisk vinder (notification_router laeser
  // raekkerne). Et valg i den gamle sektion saa ud til at gaelde, men gjorde
  // intet. De tre overlappende vælgere er derfor væk herfra — kun
  // Standard (alle) og Stille-timer hører til den gamle sektion nu.
  it('de overlappende per-type-vælgere er væk — kun Standard og Stille-timer', async () => {
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    render(<NotificationsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('Standard (alle)')).toBeInTheDocument())
    expect(screen.queryByText('Morgenbriefing')).toBeNull()
    expect(screen.queryByText('Påmindelser')).toBeNull()
    expect(screen.queryByText('Jarvis tager kontakt')).toBeNull()
  })

  // «Planlagte opfølgninger» (wakeup) har INGEN modpart i NotifikationsValg
  // (dens NAVN-liste mangler `wakeup`) — den bliver derfor staaende her,
  // fremfor at forsvinde sporløst fra begge sektioner.
  it('«Planlagte opfølgninger» bliver staaende — NotifikationsValg har ingen modpart', async () => {
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    render(<NotificationsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('Planlagte opfølgninger')).toBeInTheDocument())
  })
})
