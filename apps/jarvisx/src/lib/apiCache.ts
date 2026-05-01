/**
 * Stale-while-revalidate fetcher for JarvisX.
 *
 * The threat: backend down (laptop sleep, vpn flap, server restart) →
 * every poll dies → views go blank → user thinks JarvisX broke.
 *
 * The fix: every successful response gets mirrored to localStorage,
 * keyed by URL. On the next call, we resolve the cached value
 * immediately AND fire the network request. If the network succeeds,
 * we update both the cache and the consumer. If it fails, the
 * consumer keeps what it had — gracefully degrading to "last-known
 * good" instead of empty state.
 *
 * Why localStorage and not IndexedDB: simpler, synchronous, and the
 * payloads we cache (whoami, sessions list, mind snapshot, staged
 * edits) are kilobytes not megabytes. localStorage's ~5MB budget is
 * fine. If we ever need binary or huge payloads, swap to IDB.
 *
 * Why not just pass cache: 'force-cache' to fetch: that's HTTP-cache
 * scoped, doesn't survive across cache busts, and doesn't give us
 * the "last known good" semantics we want when the network errors
 * (vs a 304 / 404).
 *
 * Adoption pattern:
 *
 *   import { cachedFetch } from '../lib/apiCache'
 *   const res = await cachedFetch(url)        // gives Response w/ stale flag
 *   const j = await res.json()
 *   if (res.fromCache) showStaleBadge()
 */

const PREFIX = 'jarvisx:cache:'
const VERSION = 1
// Cap individual cached entries at 256 KB so a runaway response
// doesn't blow the localStorage budget.
const MAX_BYTES = 256 * 1024

interface CachedEntry {
  v: number       // schema version
  url: string
  status: number
  body: string    // stringified body (we only cache JSON-shaped responses)
  fetchedAt: number
}

function key(url: string): string {
  return PREFIX + url
}

function readCache(url: string): CachedEntry | null {
  try {
    const raw = localStorage.getItem(key(url))
    if (!raw) return null
    const parsed = JSON.parse(raw) as CachedEntry
    if (parsed?.v !== VERSION) return null
    return parsed
  } catch {
    return null
  }
}

function writeCache(url: string, status: number, body: string): void {
  if (body.length > MAX_BYTES) return  // skip oversized
  const entry: CachedEntry = {
    v: VERSION,
    url,
    status,
    body,
    fetchedAt: Date.now(),
  }
  try {
    localStorage.setItem(key(url), JSON.stringify(entry))
  } catch {
    // Quota exceeded — quietly drop. Caller still gets the live response
    // since we write *after* returning success, so this is best-effort.
  }
}

export interface CachedResponse {
  ok: boolean
  status: number
  fromCache: boolean
  fetchedAt: number  // ms since epoch — UI can show "stale 3 min"
  json: () => Promise<unknown>
  text: () => Promise<string>
}

function cachedToResponse(entry: CachedEntry): CachedResponse {
  return {
    ok: entry.status >= 200 && entry.status < 300,
    status: entry.status,
    fromCache: true,
    fetchedAt: entry.fetchedAt,
    json: async () => JSON.parse(entry.body),
    text: async () => entry.body,
  }
}

function liveToResponse(status: number, body: string): CachedResponse {
  return {
    ok: status >= 200 && status < 300,
    status,
    fromCache: false,
    fetchedAt: Date.now(),
    json: async () => JSON.parse(body),
    text: async () => body,
  }
}

/**
 * Broadcast cache-state events so UI surfaces (ConnectionPill etc.)
 * can show a "stale" indicator when responses are being served from
 * cache because the network failed. Jarvis flagged this as the
 * worst-class failure mode of an offline cache: "it almost works"
 * is worse than honest backend-down. Listening components can show
 * the user the truth.
 *
 * Two events:
 *   jarvisx:cache-served-stale  — network failed, cached value used
 *   jarvisx:cache-revalidated   — cached then network refreshed
 *
 * detail.url is the full URL so listeners can scope to specific
 * endpoints if they care.
 */
function emitCacheEvent(name: 'cache-served-stale' | 'cache-revalidated', url: string) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(`jarvisx:${name}`, { detail: { url } }))
}

/**
 * Fetch with stale-while-revalidate semantics. Always tries the
 * network first; on failure, returns cached entry if any, else
 * re-throws. On success, updates the cache and returns the live
 * response.
 *
 * This is not the classic "return cache, revalidate in background"
 * SWR — that pattern needs the consumer to either re-render on
 * revalidation or polling. Our use is simpler: components poll on
 * intervals already; we just want their *current* fetch to not die
 * when offline. So: try network, fall back to cache.
 *
 * Use `prefer: 'cache-first'` for cold-start cases where you want
 * cached data immediately without waiting for the network — useful
 * for /api/whoami at app-mount where the user shouldn't see "Loading…"
 * if there's a known last-good answer sitting right there.
 */
export async function cachedFetch(
  url: string,
  init?: RequestInit & { prefer?: 'network-first' | 'cache-first' },
): Promise<CachedResponse> {
  const prefer = init?.prefer ?? 'network-first'

  if (prefer === 'cache-first') {
    const cached = readCache(url)
    if (cached) {
      // Fire network in background to refresh, but don't await it
      void (async () => {
        try {
          const res = await fetch(url, init)
          const body = await res.text()
          if (res.ok) {
            writeCache(url, res.status, body)
            emitCacheEvent('cache-revalidated', url)
          }
        } catch {
          // ignore — cached value is what user is seeing
        }
      })()
      return cachedToResponse(cached)
    }
  }

  // Network-first
  try {
    const res = await fetch(url, init)
    const body = await res.text()
    if (res.ok) writeCache(url, res.status, body)
    return liveToResponse(res.status, body)
  } catch (e) {
    const cached = readCache(url)
    if (cached) {
      emitCacheEvent('cache-served-stale', url)
      return cachedToResponse(cached)
    }
    throw e
  }
}

/**
 * Drop cache entries matching a URL prefix. Use after mutations
 * that invalidate cached state (e.g. after creating a session,
 * clear `/api/chat/sessions` cache).
 */
export function invalidateCache(urlPrefix: string): void {
  const target = key(urlPrefix)
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i)
    if (k && k.startsWith(target)) keysToRemove.push(k)
  }
  for (const k of keysToRemove) {
    try {
      localStorage.removeItem(k)
    } catch {
      /* ignore */
    }
  }
}

/** Clear every JarvisX API cache entry (debug / testing helper). */
export function clearAllApiCache(): void {
  invalidateCache('')
}
