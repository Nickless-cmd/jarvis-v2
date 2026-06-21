import { render, fireEvent, waitFor } from '@testing-library/react-native'
import { NotificationsSection } from './NotificationsSection'
import * as apiClient from '../lib/apiClient'

jest.mock('../lib/apiClient')

const DEFAULTS = {
  global: 'auto', briefing: null, reminder: null, reach_out: null,
  team_invite: null, wakeup: null, quiet_start: '23:00', quiet_end: '07:00',
}

describe('NotificationsSection', () => {
  beforeEach(() => {
    ;(apiClient.apiFetch as jest.Mock).mockReset()
      .mockResolvedValue({ preferences: { ...DEFAULTS } })
  })

  it('null config -> render intet', async () => {
    const screen = await render(<NotificationsSection config={null} />)
    expect(screen.queryByText('NOTIFIKATIONER')).toBeNull()
  })

  it('henter prefs + gemmer chip-valg via POST', async () => {
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const screen = await render(<NotificationsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('Morgenbriefing')).toBeTruthy())
    ;(apiClient.apiFetch as jest.Mock).mockResolvedValueOnce(
      { preferences: { ...DEFAULTS, briefing: 'mobile' } })
    // tryk 'mobile'-chip (der er flere; tag den første under briefing-rækken):
    const mobileChips = screen.getAllByText('mobile')
    fireEvent.press(mobileChips[0]!)
    await waitFor(() => expect(apiClient.apiFetch as jest.Mock).toHaveBeenCalledWith(
      cfg, '/notifications/preferences',
      expect.objectContaining({ method: 'POST' })))
  })
})
