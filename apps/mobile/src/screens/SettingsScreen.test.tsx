import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { Linking } from 'react-native'
import { googleLinkStart, googleLoginResult } from '../lib/apiClient'
import { SettingsScreen } from './SettingsScreen'

const config = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'token'
}

const mockSignOut = jest.fn()

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({
    config,
    signOut: mockSignOut
  })
}))

jest.mock('../lib/apiClient', () => ({
  googleLinkStart: jest.fn(),
  googleLoginResult: jest.fn(),
  health: jest.fn().mockResolvedValue(true),
  getAccountMe: jest.fn().mockResolvedValue({ user_id: 'u', email: 'b@x.dk', role: 'owner', tier: 'owner', google_linked: false }),
  listConnectors: jest.fn().mockResolvedValue([]),
  setConnectorEnabled: jest.fn().mockResolvedValue(undefined),
  apiFetch: jest.fn().mockResolvedValue({ preferences: {
    global: 'auto', briefing: null, reminder: null, reach_out: null,
    team_invite: null, wakeup: null, quiet_start: '23:00', quiet_end: '07:00',
  } }),
}))

jest.mock('react-native-safe-area-context', () => ({
  useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 })
}))

jest.mock('../lib/useConnectivity', () => ({ useConnectivity: () => 'connected' }))

jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined)

beforeEach(() => {
  jest.clearAllMocks()
})

it('links Google account from settings', async () => {
  ;(googleLinkStart as jest.Mock).mockResolvedValue({
    authorize_url: 'https://accounts.google.com/link',
    nonce: 'link-nonce'
  })
  ;(googleLoginResult as jest.Mock).mockResolvedValue({ status: 'ok' })

  const screen = await render(<SettingsScreen />)

  await fireEvent.press(screen.getByText('Forbind Google-konto'))

  expect(googleLinkStart).toHaveBeenCalledWith(config)
  expect(Linking.openURL).toHaveBeenCalledWith('https://accounts.google.com/link')
  await waitFor(() => expect(screen.getByText('Google-konto forbundet')).toBeTruthy())
})
