import { AppState } from 'react-native'
import NetInfo from '@react-native-community/netinfo'
import messaging from '@react-native-firebase/messaging'
import type { ApiConfig } from './types'
import { getDeviceLocation, loadPrecision, type LocationPayload } from './location'
import { shouldUseGps } from './location'
import { getOrCreateDeviceIdentity } from './deviceIdentity'
import { syncBackgroundLocation } from './backgroundLocation'

export function networkToHint(type: string): 'home' | 'away' | 'unknown' {
  if (type === 'wifi') return 'home'
  if (type === 'cellular') return 'away'
  return 'unknown'
}

export interface MobilePingInput {
  token: string
  deviceId: string
  deviceName: string
  foreground: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
  activeSessionId?: string
  batterySaver?: boolean
  // undefined = udelad (ingen ændring server-side); {} = ryd (toggle OFF);
  // LocationPayload = ny lokation.
  location?: LocationPayload | Record<string, never>
}

export interface MobilePingBody {
  device_key: string
  push_token: string
  device_name: string
  platform: 'mobile'
  foreground: boolean
  awake: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
  active_session_id?: string
  battery_saver?: boolean
  location?: LocationPayload | Record<string, never>
}

/** Pure: byg presence-ping-payload. device_key = FCM-token. */
export function buildMobilePing(i: MobilePingInput): MobilePingBody {
  const body: MobilePingBody = {
    device_key: i.deviceId,
    push_token: i.token,
    device_name: i.deviceName,
    platform: 'mobile',
    foreground: i.foreground,
    awake: true,
    network: i.network,
    interaction: i.interaction,
  }
  if (i.activeSessionId) body.active_session_id = i.activeSessionId
  if (typeof i.batterySaver === 'boolean') body.battery_saver = i.batterySaver
  if (i.location !== undefined) body.location = i.location
  return body
}

async function post(config: ApiConfig, path: string, body: object): Promise<void> {
  try {
    await fetch(new URL(path, config.apiBaseUrl).toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch {
    /* presence/ack er best-effort */
  }
}

/** Kvittér en notifikation (vist/åbnet) → annullerer eskalering server-side. */
export async function ackNotification(config: ApiConfig, notifId: string): Promise<void> {
  if (!notifId) return
  await post(config, '/notifications/ack', { notif_id: notifId })
}

/**
 * Start device-presence-rapportering: ved AppState-skift (active/background),
 * NetInfo-skift (wifi/cellular) og hvert 30s mens foreground. Returnerer
 * en unsubscribe-funktion. Best-effort; fejler aldrig hårdt.
 */
export function startPresenceReporting(
  config: ApiConfig,
  opts: { getActiveSessionId?: () => string | null; getBatterySaver?: () => boolean } = {}
): () => void {
  let token = ''
  let deviceId = ''
  let deviceName = ''
  let network: 'home' | 'away' | 'unknown' = 'unknown'
  let interaction = true // app-åbning tæller som interaktion
  let stopped = false

  // Lokation hentes på SIN EGEN cadence (ikke i ping-stien) — getCurrentPositionAsync
  // kan hænge, og må ALDRIG blokere presence-pinget (det gav stale presence +
  // ingen ping, Bjørn 2026-06-20). send() læser blot den seneste cachede værdi.
  // `currentLocation`: undefined = udelad fra ping; {} = ryd; payload = lokation.
  let currentLocation: LocationPayload | Record<string, never> | undefined
  let clearedOff = false
  const refreshLocation = async (): Promise<void> => {
    try {
      const precision = await loadPrecision()
      if (precision === 'off') {
        void syncBackgroundLocation(false)
        if (clearedOff) { currentLocation = undefined; return }
        clearedOff = true
        currentLocation = {} // ryd server-state én gang
        return
      }
      void syncBackgroundLocation(precision === 'background' && !opts.getBatterySaver?.())
      clearedOff = false
      const effectivePrecision = opts.getBatterySaver?.() && shouldUseGps(precision) ? 'city' : precision
      const loc = await getDeviceLocation(effectivePrecision) // har egen 12s overordnet timeout
      if (loc) currentLocation = loc
      // intet fix → behold sidst kendte (rør ikke currentLocation)
    } catch {
      /* aldrig hård fejl — behold sidst kendte */
    }
  }

  const send = async (): Promise<void> => {
    if (stopped) return
    if (!deviceId) {
      try {
        const id = await getOrCreateDeviceIdentity()
        deviceId = id.deviceId
        deviceName = id.deviceName
      } catch {
        return
      }
    }
    if (!token) {
      try { token = await messaging().getToken() } catch { return }
    }
    const foreground = AppState.currentState === 'active'
    await post(config, '/presence/ping',
      buildMobilePing({
        token,
        deviceId,
        deviceName,
        foreground,
        network,
        interaction,
        location: currentLocation,
        activeSessionId: opts.getActiveSessionId?.() ?? undefined,
        batterySaver: opts.getBatterySaver?.()
      }))
    interaction = false
  }

  const appSub = AppState.addEventListener('change', (s) => {
    if (s === 'active') { interaction = true; void refreshLocation() }
    void send()
  })
  const netSub = NetInfo.addEventListener((state: { type?: string }) => {
    network = networkToHint(state.type ?? 'unknown')
    void send()
  })
  void refreshLocation()
  void send()
  const interval = setInterval(() => {
    if (AppState.currentState === 'active') void send()
  }, 30000)
  // Egen lokations-cadence: hvert 60s mens aktiv (adskilt fra pinget).
  const locInterval = setInterval(() => {
    if (AppState.currentState === 'active') void refreshLocation()
  }, 60000)

  return () => {
    stopped = true
    clearInterval(interval)
    clearInterval(locInterval)
    try { appSub.remove() } catch { /* noop */ }
    try { netSub() } catch { /* noop */ }
  }
}
