import { Platform } from 'react-native'
import * as Application from 'expo-application'
import * as SecureStore from 'expo-secure-store'

const DEVICE_ID_KEY = 'jarvis.mobile.deviceId'

export interface DeviceIdentity {
  deviceId: string
  deviceName: string
}

function makeDeviceId(): string {
  const rand = Math.random().toString(36).slice(2, 10)
  return `mobile-${Date.now().toString(36)}-${rand}`
}

function defaultDeviceName(): string {
  const app = Application.applicationName || 'Jarvis'
  const os = Platform.OS === 'ios' ? 'iPhone' : Platform.OS === 'android' ? 'Android' : 'Mobile'
  return `${app} på ${os}`
}

export async function getOrCreateDeviceIdentity(): Promise<DeviceIdentity> {
  let existing = ''
  try {
    existing = (await SecureStore.getItemAsync(DEVICE_ID_KEY)) || ''
  } catch {
    existing = ''
  }
  const deviceId = existing || makeDeviceId()
  if (!existing) {
    try {
      await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId)
    } catch {
      /* best-effort */
    }
  }
  return { deviceId, deviceName: defaultDeviceName() }
}
