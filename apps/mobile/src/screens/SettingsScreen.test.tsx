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
  health: jest.fn().mockResolvedValue(true)
}))

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
