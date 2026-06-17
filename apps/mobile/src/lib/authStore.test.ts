import * as SecureStore from 'expo-secure-store'
import { clearAuthConfig, loadAuthConfig, saveAuthConfig } from './authStore'

jest.mock('expo-secure-store', () => {
  const data = new Map<string, string>()
  return {
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
