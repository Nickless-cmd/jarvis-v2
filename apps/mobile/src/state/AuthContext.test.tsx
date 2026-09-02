import { act, render, waitFor } from '@testing-library/react-native'
import { Text } from 'react-native'
import { AuthProvider, useAuth } from './AuthContext'

const mockLoadAuthConfig = jest.fn()
const mockSaveAuthConfig = jest.fn()
const mockClearAuthConfig = jest.fn()

jest.mock('../lib/authStore', () => ({
  loadAuthConfig: () => mockLoadAuthConfig(),
  saveAuthConfig: (config: unknown) => mockSaveAuthConfig(config),
  clearAuthConfig: () => mockClearAuthConfig(),
  normalizeApiBaseUrl: (value: string) => {
    const trimmed = value.trim() || 'https://api.srvlab.dk/'
    return trimmed.endsWith('/') ? trimmed : `${trimmed}/`
  }
}))

function Probe() {
  const { config, loading, signInWithToken, signOut } = useAuth()

  return (
    <>
      <Text>{loading ? 'loading' : 'ready'}</Text>
      <Text>{config ? `${config.apiBaseUrl}|${config.authToken}` : 'none'}</Text>
      <Text
        onPress={async () => {
          try {
            await signInWithToken('', 'token')
          } catch (error) {
            ;(globalThis as typeof globalThis & { __lastSignInError?: string }).__lastSignInError =
              error instanceof Error ? error.message : String(error)
          }
        }}
      >
        sign-in
      </Text>
      <Text onPress={() => void signOut()}>sign-out</Text>
    </>
  )
}

beforeEach(() => {
  mockLoadAuthConfig.mockReset()
  mockSaveAuthConfig.mockReset()
  mockClearAuthConfig.mockReset()
  delete (globalThis as typeof globalThis & { __lastSignInError?: string }).__lastSignInError
  global.fetch = jest.fn()
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
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true
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

it('boots unauthenticated when stored auth config is malformed', async () => {
  mockLoadAuthConfig.mockResolvedValueOnce(null)

  const screen = await render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  )

  await waitFor(() => expect(screen.getByText('ready')).toBeTruthy())
  expect(screen.getByText('none')).toBeTruthy()
})

it('rejects invalid tokens without persisting config', async () => {
  mockLoadAuthConfig.mockResolvedValueOnce(null)
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: false,
    status: 401
  })

  const screen = await render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  )

  await waitFor(() => expect(screen.getByText('ready')).toBeTruthy())

  await act(async () => {
    await screen.getByText('sign-in').props.onPress()
  })

  await waitFor(() =>
    expect(
      (globalThis as typeof globalThis & { __lastSignInError?: string }).__lastSignInError
    ).toBeTruthy()
  )
  expect(global.fetch).toHaveBeenCalledWith('https://api.srvlab.dk/api/whoami', {
    method: 'GET',
    headers: {
      Authorization: 'Bearer token'
    }
  })
  expect(mockSaveAuthConfig).not.toHaveBeenCalled()
  expect(
    (globalThis as typeof globalThis & { __lastSignInError?: string }).__lastSignInError
  ).toBe('Token blev afvist af Jarvis API')
  expect(screen.getByText('none')).toBeTruthy()
})
