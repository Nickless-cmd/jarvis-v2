import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { DEFAULT_API_BASE_URL } from '../lib/types'
import { LoginScreen } from './LoginScreen'

const mockSignInWithToken = jest.fn()

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({
    signInWithToken: mockSignInWithToken
  })
}))

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

it('keeps QR pairing disabled by default with a visible message', async () => {
  const screen = await render(<LoginScreen />)

  await fireEvent.press(screen.getByText('Scan QR fra Jarvis-desk'))

  await waitFor(() =>
    expect(screen.getByText('QR pairing er ikke aktiv endnu. Brug bearer token for nu.')).toBeTruthy()
  )
})
