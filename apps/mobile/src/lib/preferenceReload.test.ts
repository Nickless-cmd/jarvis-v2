import * as SecureStore from 'expo-secure-store'
import { loadBatterySaver, saveBatterySaver } from './batteryPrefs'
import { loadBubblePersist, saveBubblePersist } from './bubbleSetting'
import { loadCameraPrefs, saveCameraPrefs } from './cameraPrefs'
import { loadPrecision, savePrecision } from './location'
import { loadThemePrefs, saveThemeAccent, saveThemeMode } from './themePrefs'

jest.mock('expo-secure-store', () => {
  const values: Record<string, string> = {}
  return {
    __esModule: true,
    __values: values,
    getItemAsync: jest.fn(async (key: string) => values[key] ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => { values[key] = value }),
    deleteItemAsync: jest.fn(async (key: string) => { delete values[key] }),
  }
})

beforeEach(() => {
  const values = (SecureStore as unknown as { __values: Record<string, string> }).__values
  Object.keys(values).forEach((key) => delete values[key])
})

it('gendanner lokale Settings-valg efter en kold load', async () => {
  await saveBatterySaver(true)
  await saveBubblePersist(true)
  await savePrecision('background')
  await saveCameraPrefs({ facing: 'front', flash: 'auto', shutterSound: false })
  await saveThemeMode('auto')
  await saveThemeAccent('bla')

  await expect(loadBatterySaver()).resolves.toBe(true)
  await expect(loadBubblePersist()).resolves.toBe(true)
  await expect(loadPrecision()).resolves.toBe('background')
  await expect(loadCameraPrefs()).resolves.toEqual({ facing: 'front', flash: 'auto', shutterSound: false })
  await expect(loadThemePrefs()).resolves.toEqual({ mode: 'auto', accent: 'bla' })
})
