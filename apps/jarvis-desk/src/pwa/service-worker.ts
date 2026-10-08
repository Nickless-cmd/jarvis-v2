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
