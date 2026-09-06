import * as SecureStore from 'expo-secure-store'
import { loadCameraPrefs, saveCameraPrefs } from './cameraPrefs'

jest.mock('expo-secure-store', () => ({
  __esModule: true,
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(async () => undefined)
}))

const mockedStore = SecureStore as jest.Mocked<typeof SecureStore>

beforeEach(() => {
  jest.clearAllMocks()
})

it('defaults to back camera with shutter enabled', async () => {
  mockedStore.getItemAsync.mockResolvedValueOnce(null)

  await expect(loadCameraPrefs()).resolves.toEqual({
    facing: 'back',
    flash: 'off',
    shutterSound: true
  })
})

it('persists valid camera preferences including disabled shutter sound', async () => {
  await saveCameraPrefs({ facing: 'front', flash: 'on', shutterSound: false })

  expect(mockedStore.setItemAsync).toHaveBeenCalledWith(
    'jarvis.mobile.cameraPrefs',
    JSON.stringify({ facing: 'front', flash: 'on', shutterSound: false })
  )
})
