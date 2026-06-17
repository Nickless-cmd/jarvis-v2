import * as SecureStore from 'expo-secure-store'
import { clearAuthConfig, loadAuthConfig, saveAuthConfig } from './authStore'

jest.mock('expo-secure-store', () => {
  const data = new Map<string, string>()
  return {
    __reset: jest.fn(() => {
      data.clear()
    }),
    getItemAsync: jest.fn((key: string) => Promise.resolve(data.get(key) ?? null)),
    setItemAsync: jest.fn((key: string, value: string) => {
      data.set(key, value)
      return Promise.resolve()
    }),
    deleteItemAsync: jest.fn((key: string) => {
      data.delete(key)
      return Promise.resolve()
    })
  }
})

beforeEach(() => {
  ;(SecureStore as typeof SecureStore & { __reset: () => void }).__reset()
  jest.clearAllMocks()
})

it('stores and loads normalized token config', async () => {
  await saveAuthConfig({ apiBaseUrl: 'https://api.srvlab.dk', authToken: ' token ' })
  await expect(loadAuthConfig()).resolves.toEqual({
    apiBaseUrl: 'https://api.srvlab.dk/',
    authToken: 'token'
  })
})

it('clears token config', async () => {
  await saveAuthConfig({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' })
  await clearAuthConfig()
  await expect(loadAuthConfig()).resolves.toBeNull()
  expect(SecureStore.deleteItemAsync).toHaveBeenCalled()
})

it('returns null for malformed secure-store payloads', async () => {
  await SecureStore.setItemAsync('jarvis.mobile.auth', '{not-json')

  await expect(loadAuthConfig()).resolves.toBeNull()
})

it('returns null for structurally invalid secure-store payloads', async () => {
  await SecureStore.setItemAsync('jarvis.mobile.auth', JSON.stringify({ apiBaseUrl: 7, authToken: true }))

  await expect(loadAuthConfig()).resolves.toBeNull()
})

it('returns null for whitespace-only stored tokens', async () => {
  await SecureStore.setItemAsync(
    'jarvis.mobile.auth',
    JSON.stringify({ apiBaseUrl: '   ', authToken: '   ' })
  )

  await expect(loadAuthConfig()).resolves.toBeNull()
})
