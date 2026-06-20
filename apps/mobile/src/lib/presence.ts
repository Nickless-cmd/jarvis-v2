import { AppState } from 'react-native'
import NetInfo from '@react-native-community/netinfo'
import messaging from '@react-native-firebase/messaging'
import type { ApiConfig } from './types'
import { getDeviceLocation, loadPrecision, type LocationPayload } from './location'

export function networkToHint(type: string): 'home' | 'away' | 'unknown' {
  if (type === 'wifi') return 'home'
  if (type === 'cellular') return 'away'
  return 'unknown'
}

export interface MobilePingInput {
  token: string
  foreground: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
  // undefined = udelad (ingen ændring server-side); {} = ryd (toggle OFF);
  // LocationPayload = ny lokation.
  location?: LocationPayload | Record<string, never>
}

export interface MobilePingBody {
  device_key: string
  platform: 'mobile'
  foreground: boolean
  awake: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
  location?: LocationPayload | Record<string, never>
}

/** Pure: byg presence-ping-payload. device_key = FCM-token. */
export function buildMobilePing(i: MobilePingInput): MobilePingBody {
  const body: MobilePingBody = {
    device_key: i.token,
    platform: 'mobile',
    foreground: i.foreground,
    awake: true,
    network: i.network,
    interaction: i.interaction,
  }
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
export function startPresenceReporting(config: ApiConfig): () => void {
  let token = ''
  let network: 'home' | 'away' | 'unknown' = 'unknown'
  let interaction = true // app-åbning tæller som interaktion
  let stopped = false
  // Lokation: cache sidste fix i 60s så vi ikke poller GPS hvert ping. clearedOff
  // sikrer at vi sender {} ÉN gang når brugeren slår fra (rydder server-state).
  let cachedLoc: LocationPayload | null = null
  let cachedAt = 0
  let clearedOff = false

  const resolveLocation = async (): Promise<LocationPayload | Record<string, never> | undefined> => {
    const precision = await loadPrecision()
    if (precision === 'off') {
      cachedLoc = null
      if (clearedOff) return undefined // allerede ryddet → udelad (intet arbejde)
      clearedOff = true
      return {} // ryd server-state én gang
    }
    clearedOff = false
    const now = Date.now()
    if (cachedLoc && now - cachedAt < 60000) return cachedLoc
    const loc = await getDeviceLocation(precision)
    if (loc) { cachedLoc = loc; cachedAt = now; return loc }
    return cachedLoc ?? undefined // intet fix → behold sidst kendte / udelad
  }

  const send = async (): Promise<void> => {
    if (stopped) return
    if (!token) {
      try { token = await messaging().getToken() } catch { return }
    }
    const foreground = AppState.currentState === 'active'
    const location = await resolveLocation()
    if (stopped) return
    await post(config, '/presence/ping', buildMobilePing({ token, foreground, network, interaction, location }))
    interaction = false
  }

  const appSub = AppState.addEventListener('change', (s) => {
    if (s === 'active') interaction = true
    void send()
  })
  const netSub = NetInfo.addEventListener((state: { type?: string }) => {
    network = networkToHint(state.type ?? 'unknown')
    void send()
  })
  void send()
  const interval = setInterval(() => {
    if (AppState.currentState === 'active') void send()
  }, 30000)

  return () => {
    stopped = true
    clearInterval(interval)
    try { appSub.remove() } catch { /* noop */ }
    try { netSub() } catch { /* noop */ }
  }
}
