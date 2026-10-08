import { describe, expect, it } from 'vitest'
import { shouldCache } from './cachePolicy'

describe('PWA cache boundary', () => {
  const origin = location.origin
  it('allows only the app shell and static build files on the same origin', () => {
    for (const path of ['/', '/index.html', '/assets/app-abc123.js', '/favicon.svg', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png']) {
      expect(shouldCache(new URL(path, origin))).toBe(true)
    }
  })
  it('excludes authenticated data, event streams, mutations and foreign origins', () => {
    for (const path of ['/chat/stream/v2', '/ws', '/mc/runtime', '/api/auth/login', '/attachments/file', '/files/a', '/sw.js', '/assets/../chat/sessions']) {
      expect(shouldCache(new URL(path, origin))).toBe(false)
    }
    expect(shouldCache(new URL('https://elsewhere.example/assets/app.js'))).toBe(false)
  })
})
