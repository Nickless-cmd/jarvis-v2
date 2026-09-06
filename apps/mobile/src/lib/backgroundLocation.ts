import * as Location from 'expo-location'
import * as TaskManager from 'expo-task-manager'
import messaging from '@react-native-firebase/messaging'
import type { ApiConfig } from './types'
import { loadAuthConfig } from './authStore'
import { getOrCreateDeviceIdentity } from './deviceIdentity'
import { reverseLabel, type LocationPayload } from './location'

const TASK = 'jarvis-background-location'

async function postBackgroundPing(config: ApiConfig, location: LocationPayload): Promise<void> {
  const identity = await getOrCreateDeviceIdentity()
  let token = ''
  try { token = await messaging().getToken() } catch { token = '' }
  await fetch(new URL('/presence/ping', config.apiBaseUrl).toString(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {})
    },
    body: JSON.stringify({
      device_key: identity.deviceId,
      push_token: token,
      device_name: identity.deviceName,
      platform: 'mobile',
      foreground: false,
      awake: true,
      network: 'unknown',
      interaction: false,
      location
    })
  })
}

TaskManager.defineTask(TASK, async ({ data, error }) => {
  if (error) return
  const locations = (data as { locations?: Location.LocationObject[] } | undefined)?.locations ?? []
  const latest = locations[locations.length - 1]
  if (!latest) return
  try {
    const config = await loadAuthConfig()
    if (!config) return
    const { latitude, longitude, accuracy } = latest.coords
    const label = await reverseLabel(latitude, longitude, true)
    await postBackgroundPing(config, {
      lat: latitude,
      lon: longitude,
      label,
      source: 'gps',
      precision: 'background',
      accuracy_m: typeof accuracy === 'number' ? accuracy : undefined,
      captured_at: new Date().toISOString()
    })
  } catch {
    /* background pings er best-effort */
  }
})

export async function syncBackgroundLocation(enabled: boolean): Promise<void> {
  try {
    const running = await Location.hasStartedLocationUpdatesAsync(TASK)
    if (!enabled) {
      if (running) await Location.stopLocationUpdatesAsync(TASK)
      return
    }
    const fg = await Location.getForegroundPermissionsAsync()
    if (fg.status !== 'granted') return
    const bg = await Location.requestBackgroundPermissionsAsync()
    if (bg.status !== 'granted') return
    if (running) return
    await Location.startLocationUpdatesAsync(TASK, {
      accuracy: Location.Accuracy.Balanced,
      timeInterval: 300000,
      distanceInterval: 250,
      pausesUpdatesAutomatically: true,
      foregroundService: {
        notificationTitle: 'Jarvis lokation',
        notificationBody: 'Jarvis deler din lokation, fordi du har slået baggrundslokation til.',
        notificationColor: '#6ee7a8'
      }
    })
  } catch {
    /* background location er best-effort */
  }
}
