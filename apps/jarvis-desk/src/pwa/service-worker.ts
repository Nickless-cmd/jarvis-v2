/// <reference lib="webworker" />
import { shouldCache } from './cachePolicy'

declare const self: ServiceWorkerGlobalScope
declare const __PWA_CACHE__: string
declare const __PWA_ENTRY_ASSETS__: string[]

const CACHE = `jarvis-desk-web-${__PWA_CACHE__}`
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png', ...__PWA_ENTRY_ASSETS__]

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(Promise.all([
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('jarvis-desk-web-') && key !== CACHE).map((key) => caches.delete(key)))),
    self.clients.claim(),
  ]))
})

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') void self.skipWaiting()
})

// ── Web-push (side-67aea8c5b6) ─────────────────────────────────────────────
// Workeren havde kun install/activate/message/fetch. Uden en `push`-handler
// kan PWA'en ikke vækkes i baggrunden; uden `notificationclick` åbner et tryk
// ingenting — beskeden forsvinder uden at føre nogen steder hen.

self.addEventListener('push', (event) => {
  let data: Record<string, unknown> = {}
  try {
    data = event.data ? (event.data.json() as Record<string, unknown>) : {}
  } catch {
    data = {}
  }
  const title = String(data.title ?? 'Jarvis')
  const body = String(data.preview ?? data.body ?? 'Nyt svar fra Jarvis')
  const session = String(data.session_id ?? '')
  const url = session ? `/?session=${encodeURIComponent(session)}` : '/'
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      // run_id som tag: to notifikationer fra samme kørsel erstatter hinanden
      // i stedet for at hobe sig op i systembakken.
      tag: String(data.run_id ?? data.kind ?? 'jarvis'),
      data: { url },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = String((event.notification.data as { url?: string } | null)?.url ?? '/')
  event.waitUntil(
    (async () => {
      const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of all) {
        if ('focus' in client) {
          await client.focus()
          if ('navigate' in client) void client.navigate(target)
          return
        }
      }
      await self.clients.openWindow(target)
    })(),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)
  if (req.method !== 'GET' || req.headers.has('Authorization') || !shouldCache(url)) return

  if (url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(fetch(req).then((response) => {
      if (response.ok) event.waitUntil(caches.open(CACHE).then((cache) => cache.put(req, response.clone())))
      return response
    }).catch(async () => {
      const cached = await caches.match(req) ?? await caches.match('/index.html')
      if (cached) return cached
      throw new Error('App shell unavailable offline')
    }))
    return
  }

  event.respondWith(caches.match(req).then((cached) => cached ?? fetch(req).then((response) => {
    if (response.ok && response.type === 'basic') event.waitUntil(caches.open(CACHE).then((cache) => cache.put(req, response.clone())))
    return response
  })))
})
