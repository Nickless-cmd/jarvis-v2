import * as SecureStore from 'expo-secure-store'

const BATTERY_SAVER_KEY = 'jarvis.mobile.batterySaver'

export async function loadBatterySaver(): Promise<boolean> {
  try {
    return (await SecureStore.getItemAsync(BATTERY_SAVER_KEY)) === '1'
  } catch {
    return false
  }
}

export async function saveBatterySaver(on: boolean): Promise<void> {
  try {
    await SecureStore.setItemAsync(BATTERY_SAVER_KEY, on ? '1' : '0')
  } catch {
    /* best-effort */
  }
}
