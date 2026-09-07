import { alleredeGivneTilladelser, bedOmTilladelse } from './permissionRequests'

jest.mock('@notifee/react-native', () => ({
  __esModule: true,
  default: { getNotificationSettings: jest.fn(), requestPermission: jest.fn() },
}))
jest.mock('expo-audio', () => ({
  getRecordingPermissionsAsync: jest.fn(),
  requestRecordingPermissionsAsync: jest.fn(),
}))
jest.mock('expo-camera', () => ({
  Camera: { getCameraPermissionsAsync: jest.fn(), requestCameraPermissionsAsync: jest.fn() },
}))
jest.mock('expo-location', () => ({
  getForegroundPermissionsAsync: jest.fn(),
  requestForegroundPermissionsAsync: jest.fn(),
}))

const notifee = require('@notifee/react-native').default
const Audio = require('expo-audio')
const { Camera } = require('expo-camera')
const Location = require('expo-location')

beforeEach(() => {
  jest.clearAllMocks()
  notifee.getNotificationSettings.mockResolvedValue({ authorizationStatus: 1 })
  Audio.getRecordingPermissionsAsync.mockResolvedValue({ granted: true })
  Camera.getCameraPermissionsAsync.mockResolvedValue({ granted: false })
  Location.getForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' })
})

it('rapporterer kun det der ER givet — kameraet mangler her', async () => {
  await expect(alleredeGivneTilladelser()).resolves.toEqual(['push', 'mikrofon', 'lokation'])
})

it('åbner INGEN dialog under aflæsning', async () => {
  await alleredeGivneTilladelser()
  expect(notifee.requestPermission).not.toHaveBeenCalled()
  expect(Audio.requestRecordingPermissionsAsync).not.toHaveBeenCalled()
  expect(Camera.requestCameraPermissionsAsync).not.toHaveBeenCalled()
  expect(Location.requestForegroundPermissionsAsync).not.toHaveBeenCalled()
})

it('et modul der kaster gør ikke resten ubrugelig — vi spørger hellere om det ukendte', async () => {
  Audio.getRecordingPermissionsAsync.mockRejectedValue(new Error('nej'))
  await expect(alleredeGivneTilladelser()).resolves.toEqual(['push', 'lokation'])
})

it('bedOmTilladelse melder falsk i stedet for at kaste', async () => {
  Camera.requestCameraPermissionsAsync.mockRejectedValue(new Error('nede'))
  await expect(bedOmTilladelse('kamera')).resolves.toBe(false)
})

it('lokation beder KUN om forgrund — baggrund hører til i indstillinger', async () => {
  Location.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' })
  await expect(bedOmTilladelse('lokation')).resolves.toBe(true)
  expect(Location.requestForegroundPermissionsAsync).toHaveBeenCalled()
})
