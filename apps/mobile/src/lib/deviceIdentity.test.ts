import * as SecureStore from 'expo-secure-store'
import { getOrCreateDeviceIdentity } from './deviceIdentity'

jest.mock('expo-secure-store', () => ({
  __esModule: true,
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(async () => undefined)
}))

const mockedStore = SecureStore as jest.Mocked<typeof SecureStore>

beforeEach(() => {
  jest.clearAllMocks()
})

it('creates and persists a stable install device id when missing', async () => {
  mockedStore.getItemAsync.mockResolvedValueOnce(null)

  const id = await getOrCreateDeviceIdentity()

  expect(id.deviceId).toMatch(/^mobile-/)
  expect(id.deviceName).toBeTruthy()
  expect(mockedStore.setItemAsync).toHaveBeenCalledWith('jarvis.mobile.deviceId', id.deviceId)
})

it('reuses the stored device id instead of using a push token as identity', async () => {
  mockedStore.getItemAsync.mockResolvedValueOnce('mobile-existing')

  await expect(getOrCreateDeviceIdentity()).resolves.toMatchObject({
    deviceId: 'mobile-existing'
  })
  expect(mockedStore.setItemAsync).not.toHaveBeenCalled()
})
