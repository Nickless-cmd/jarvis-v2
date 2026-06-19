import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance } from '@notifee/react-native'
import type { ApiConfig } from './types'
import { ackNotification } from './presence'

export type PushData = { kind: string; session_id?: string; run_id?: string; preview?: string; notif_id?: string }

/** Pure: byg notifikations-felter ud fra data + (evt.) hentet beskedtekst. Testbar. */
export function buildNotification(data: PushData, fetchedBody: string | null) {
  if (data.kind === 'reminder') {
    return { title: 'Påmindelse', body: data.preview ?? '', data }
  }
  if (data.kind === 'initiative') {
    return { title: 'Jarvis', body: data.preview ?? 'Jarvis vil sige noget', data }
  }
  // answer_ready
  return { title: 'Jarvis svarede', body: fetchedBody ?? 'Nyt svar', data }
}

async function fetchLatest(config: ApiConfig, sessionId: string): Promise<string | null> {
  try {
    const url = new URL(`/chat/sessions/${encodeURIComponent(sessionId)}`, config.apiBaseUrl).toString()
    const r = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
    })
    if (!r.ok) return null
    const j = await r.json()
    const msgs = j.messages ?? []
    const last = [...msgs].reverse().find((m: { role?: string }) => m.role === 'assistant')
    if (!last) return null
    const c = last.content
    const text =
      typeof c === 'string'
        ? c
        : Array.isArray(c)
          ? c.map((b: { text?: string }) => b.text ?? '').join('')
          : ''
    return text.slice(0, 140)
  } catch {
    return null
  }
}

export async function display(config: ApiConfig, data: PushData) {
  const body = data.session_id ? await fetchLatest(config, data.session_id) : null
  const n = buildNotification(data, body)
  const channelId = await notifee.createChannel({
    id: 'jarvis',
    name: 'Jarvis',
    importance: AndroidImportance.HIGH,
  })
  await notifee.displayNotification({
    title: n.title,
    body: n.body,
    data: n.data as Record<string, string>,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' },
  })
  // Device-awareness: kvittér så serveren ved beskeden nåede mobilen (annullerer
  // eskalering til en anden enhed). Best-effort.
  if (data.notif_id) void ackNotification(config, data.notif_id)
}

async function postToken(config: ApiConfig, token: string) {
  const url = new URL('/push/register', config.apiBaseUrl).toString()
  await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
    },
    body: JSON.stringify({ token, platform: 'android' }),
  })
}

/** Registrér token efter login + lyt på rotation. */
export async function registerForPush(config: ApiConfig): Promise<void> {
  try {
    // notifee.requestPermission() udløser Android 13+'s POST_NOTIFICATIONS-dialog
    // (messaging().requestPermission() gør det IKKE pålideligt på Android).
    await notifee.requestPermission()
    await messaging().requestPermission()
    const token = await messaging().getToken()
    await postToken(config, token)
    messaging().onTokenRefresh((t: string) => {
      void postToken(config, t)
    })
  } catch {
    /* graceful: ingen push, in-app virker stadig */
  }
}

/** Kald i forgrunden (app åben). Returnerer unsubscribe. */
export function attachForegroundHandler(config: ApiConfig) {
  return messaging().onMessage(async (msg) => {
    await display(config, (msg.data ?? {}) as unknown as PushData)
  })
}
