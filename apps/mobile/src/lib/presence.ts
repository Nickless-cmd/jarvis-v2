import { AppState } from 'react-native'
import NetInfo from '@react-native-community/netinfo'
import messaging from '@react-native-firebase/messaging'
import type { ApiConfig } from './types'

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
}

export interface MobilePingBody {
  device_key: string
  platform: 'mobile'
  foreground: boolean
  awake: boolean
  network: 'home' | 'away' | 'unknown'
  interaction: boolean
}

/** Pure: byg presence-ping-payload. device_key = FCM-token. */
export function buildMobilePing(i: MobilePingInput): MobilePingBody {
  return {
    device_key: i.token,
    platform: 'mobile',
    foreground: i.foreground,
    awake: true,
    network: i.network,
    interaction: i.interaction,
  }
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

  const send = async (): Promise<void> => {
    if (stopped) return
    if (!token) {
      try { token = await messaging().getToken() } catch { return }
    }
    const foreground = AppState.currentState === 'active'
    await post(config, '/presence/ping', buildMobilePing({ token, foreground, network, interaction }))
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
