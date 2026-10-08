import type { ApiConfig } from './api'

const KEY = 'jarvis:web-auth'

function currentBase(): string {
  return new URL('/', window.location.origin).toString()
}

export function readBrowserConfig(): ApiConfig {
  const apiBaseUrl = currentBase()
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { apiBaseUrl, authToken: null }
    const stored: unknown = JSON.parse(raw)
    if (stored && typeof stored === 'object' && 'origin' in stored && 'authToken' in stored &&
        stored.origin === window.location.origin && typeof stored.authToken === 'string' && stored.authToken.trim()) {
      return { apiBaseUrl, authToken: stored.authToken }
    }
  } catch { /* Corrupt or unavailable browser storage means logged out. */ }
  return { apiBaseUrl, authToken: null }
}

export function writeBrowserConfig(config: ApiConfig): void {
  if (config.apiBaseUrl !== currentBase()) return
  if (!config.authToken) { clearBrowserConfig(); return }
  try {
    localStorage.setItem(KEY, JSON.stringify({ origin: window.location.origin, authToken: config.authToken }))
  } catch { /* Private browsing can deny persistence; current login still works. */ }
}

export function clearBrowserConfig(): void {
  try { localStorage.removeItem(KEY) } catch { /* Storage may be unavailable. */ }
}
