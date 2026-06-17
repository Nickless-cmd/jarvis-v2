import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { AuthProvider, useAuth } from './AuthContext'

const mockLoadAuthConfig = jest.fn()
const mockSaveAuthConfig = jest.fn()
const mockClearAuthConfig = jest.fn()

jest.mock('../lib/authStore', () => ({
  loadAuthConfig: () => mockLoadAuthConfig(),
  saveAuthConfig: (config: unknown) => mockSaveAuthConfig(config),
  clearAuthConfig: () => mockClearAuthConfig()
}))

function Probe() {
  const { config, loading, signInWithToken, signOut } = useAuth()

  return (
    <>
      <Text>{loading ? 'loading' : 'ready'}</Text>
      <Text>{config ? `${config.apiBaseUrl}|${config.authToken}` : 'none'}</Text>
      <Text onPress={() => void signInWithToken('', 'token')}>sign-in</Text>
      <Text onPress={() => void signOut()}>sign-out</Text>
    </>
  )
}

beforeEach(() => {
  mockLoadAuthConfig.mockReset()
  mockSaveAuthConfig.mockReset()
  mockClearAuthConfig.mockReset()
})

it('loads stored config on mount', async () => {
  mockLoadAuthConfig.mockResolvedValueOnce({
    apiBaseUrl: 'https://api.srvlab.dk/',
    authToken: 'token'
  })

  const screen = await render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  )

  await waitFor(() => expect(screen.getByText('ready')).toBeTruthy())
  expect(screen.getByText('https://api.srvlab.dk/|token')).toBeTruthy()
})

it('signs in and signs out through the auth store', async () => {
  mockLoadAuthConfig
    .mockResolvedValueOnce(null)
    .mockResolvedValueOnce({
      apiBaseUrl: 'https://api.srvlab.dk/',
      authToken: 'token'
    })
  mockSaveAuthConfig.mockResolvedValue(undefined)
  mockClearAuthConfig.mockResolvedValue(undefined)

  const screen = await render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  )

  await waitFor(() => expect(screen.getByText('ready')).toBeTruthy())

  await act(async () => {
    await screen.getByText('sign-in').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('https://api.srvlab.dk/|token')).toBeTruthy())
  expect(mockSaveAuthConfig).toHaveBeenCalledWith({
    apiBaseUrl: 'https://api.srvlab.dk/',
    authToken: 'token'
  })

  await act(async () => {
    await screen.getByText('sign-out').props.onPress()
  })

  await waitFor(() => expect(screen.getByText('none')).toBeTruthy())
  expect(mockClearAuthConfig).toHaveBeenCalled()
})
