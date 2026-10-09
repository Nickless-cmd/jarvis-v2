/**
 * Web-push-abonnement (side-67aea8c5b6).
 *
 * PWA'en kunne ikke vækkes i baggrunden: service workeren havde ingen
 * `push`-handler, og der fandtes intet abonnement at sende til. Denne fil
 * lukker kredsen — hent den offentlige VAPID-nøgle fra serveren, abonnér i
 * browseren, og gem abonnementet server-side.
 *
 * To ting der ikke kan omgås:
 *  - `__WEB_BUILD__` — Electron-skallen har ingen push-tjeneste.
 *  - På iPhone virker web-push KUN når PWA'en er føjet til hjemmeskærmen.
 */
import type { ApiConfig } from '../lib/api'
import { apiFetch } from '../lib/api'

/** VAPID-nøglen er base64url; PushManager vil have bytes. */
function b64ToBytes(base64: string): Uint8Array<ArrayBuffer> {
  const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4))
  const raw = atob((base64 + pad).replace(/-/g, '+').replace(/_/g, '/'))
  // Bunden til en rigtig ArrayBuffer: TS 5.7 skelner mellem ArrayBuffer og
  // SharedArrayBuffer, og `PushManager.subscribe` tager kun den første.
  const out = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i)
  return out
}

/** Kan denne klient overhovedet modtage web-push? */
export function webPushMulig(): boolean {
  return (
    typeof __WEB_BUILD__ !== 'undefined' && __WEB_BUILD__ &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

/**
 * Abonnér (eller genbrug et eksisterende abonnement) og gem det server-side.
 *
 * Spørger KUN om notifikations-tilladelse hvis den ikke er afgjort endnu.
 * Returnerer false i stedet for at kaste — et manglende abonnement må ikke
 * vælte app-opstarten.
 */
export async function subscribeWebPush(config: ApiConfig): Promise<boolean> {
  if (!webPushMulig()) return false
  try {
    if (Notification.permission === 'default') {
      const svar = await Notification.requestPermission()
      if (svar !== 'granted') return false
    }
    if (Notification.permission !== 'granted') return false
    const { key } = await apiFetch<{ key: string }>(config, '/push/web/vapid')
    if (!key) return false
    const reg = await navigator.serviceWorker.ready
    const eksisterende = await reg.pushManager.getSubscription()
    const sub =
      eksisterende ??
      (await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: b64ToBytes(key),
      }))
    const json = sub.toJSON() as { endpoint?: string; keys?: { p256dh?: string; auth?: string } }
    const endpoint = String(json.endpoint ?? '')
    if (!endpoint) return false
    await apiFetch(config, '/push/web/subscribe', {
      method: 'POST',
      body: {
        endpoint,
        p256dh: String(json.keys?.p256dh ?? ''),
        auth: String(json.keys?.auth ?? ''),
      },
    })
    return true
  } catch {
    return false
  }
}

/**
 * Gen-etablér abonnementet ved opstart, men KUN hvis tilladelsen allerede er
 * givet. Spørger aldrig af sig selv: browseren kræver en brugerhandling, og et
 * prompt ved hver opstart ville være støj.
 */
export async function genopretWebPush(config: ApiConfig): Promise<void> {
  if (!webPushMulig() || Notification.permission !== 'granted') return
  await subscribeWebPush(config)
}

/** Afmeld: fjern abonnementet server-side og lokalt. */
export async function unsubscribeWebPush(config: ApiConfig): Promise<boolean> {
  if (!webPushMulig()) return false
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    if (!sub) return true
    await apiFetch(config, '/push/web/unsubscribe', {
      method: 'POST',
      body: { token: sub.endpoint },
    })
    await sub.unsubscribe()
    return true
  } catch {
    return false
  }
}
