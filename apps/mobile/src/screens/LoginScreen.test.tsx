import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { Linking } from 'react-native'
import { DEFAULT_API_BASE_URL } from '../lib/types'
import { LoginScreen } from './LoginScreen'

const mockSignInWithToken = jest.fn()
const mockGoogleLoginStart = jest.fn()
const mockGoogleLoginResult = jest.fn()

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({
    signInWithToken: mockSignInWithToken
  })
}))

jest.mock('../lib/apiClient', () => ({
  googleLoginStart: (...args: unknown[]) => mockGoogleLoginStart(...args),
  googleLoginResult: (...args: unknown[]) => mockGoogleLoginResult(...args),
  redeemPairingCode: jest.fn()
}))

jest.mock('expo-camera', () => ({
  CameraView: () => null,
  useCameraPermissions: () => [{ granted: false }, jest.fn()]
}))

jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined)

beforeEach(() => {
  jest.clearAllMocks()
  delete process.env.EXPO_PUBLIC_ENABLE_QR_PAIRING
})

it('defaults to the public Jarvis API and submits token login', async () => {
  mockSignInWithToken.mockResolvedValue(undefined)
  const screen = await render(<LoginScreen />)

  expect(screen.getByDisplayValue(DEFAULT_API_BASE_URL)).toBeTruthy()

  await fireEvent.changeText(screen.getByDisplayValue(DEFAULT_API_BASE_URL), DEFAULT_API_BASE_URL)
  await fireEvent.changeText(screen.getByDisplayValue(''), 'token-123')
  await fireEvent.press(screen.getByText('Forbind'))

  expect(mockSignInWithToken).toHaveBeenCalledWith(DEFAULT_API_BASE_URL, 'token-123')
})

it('opens the QR scanner from the pairing button', async () => {
  const screen = await render(<LoginScreen />)

  await fireEvent.press(screen.getByText('Scan QR fra Jarvis-desk'))

  // Uden kamera-tilladelse viser scanneren tilladelses-promptet.
  await waitFor(() => expect(screen.getByText('Tillad kamera')).toBeTruthy())
})

it('opens Google login and stores the returned Jarvis token', async () => {
  mockGoogleLoginStart.mockResolvedValue({
    authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth',
    nonce: 'nonce-1'
  })
  mockGoogleLoginResult.mockResolvedValue({
    status: 'ok',
    token: 'jarvis-token'
  })
  mockSignInWithToken.mockResolvedValue(undefined)

  const screen = await render(<LoginScreen />)

  await fireEvent.press(screen.getByText('Log ind med Google'))

  expect(mockGoogleLoginStart).toHaveBeenCalledWith(DEFAULT_API_BASE_URL, 'jarvis-mobile')
  expect(Linking.openURL).toHaveBeenCalledWith('https://accounts.google.com/o/oauth2/v2/auth')
  await waitFor(() =>
    expect(mockSignInWithToken).toHaveBeenCalledWith(DEFAULT_API_BASE_URL, 'jarvis-token')
  )
})

it('shows a useful message when Google login returns no linked account', async () => {
  mockGoogleLoginStart.mockResolvedValue({
    authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth',
    nonce: 'nonce-1'
  })
  mockGoogleLoginResult.mockResolvedValue({
    status: 'error',
    error: 'no_account'
  })

  const screen = await render(<LoginScreen />)

  await fireEvent.press(screen.getByText('Log ind med Google'))

  await waitFor(() =>
    expect(screen.getByText('Ingen Jarvis-konto er knyttet til denne Google-konto.')).toBeTruthy()
  )
})
