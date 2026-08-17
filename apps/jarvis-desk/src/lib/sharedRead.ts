/** Delt læse-lag: kollapser dublerede GET-polls på tværs af komponenter.
 *
 *  Rod (Bjørn 17. aug 2026): desk'en pollede backenden 536 req/min fra ÉN klient, fordi
 *  flere komponenter uafhængigt spurgte om det SAMME — /chat/active-runs fra 4 komponenter
 *  (Sidebar/TakeoverHost/ChatView/CodeView), /central/realtime fra 3, /central/costs-daily
 *  ad 2 veje. Stormen sultede desk'ens egen SSE-læser → forbindelsen døde → Starlette
 *  cancellerede server-tasken → `CancelledError` → HELE Jarvis' run blev kasseret midt-flugt
 *  (vis_len=0). Se reference_cutoff_rootcause_pollstorm.
 *
 *  To mekanismer:
 *   1. **In-flight dedup + mikro-cache** — N komponenter der spørger om samme nøgle indenfor
 *      TTL deler ÉT svar. Ingen komponent skal ændre sit interval.
 *   2. **Streaming-backoff** — mens et run streamer forlænges TTL kraftigt, så baggrundsstøj
 *      ikke konkurrerer med SSE-læseren netop når det gør mest skade.
 *
 *  Fejl caches ALDRIG (en enkelt netværksfejl må ikke fastfryse en død værdi i TTL-vinduet).
 */

interface CacheEntry {
  value: unknown
  at: number
}

const _cache = new Map<string, CacheEntry>()
const _inflight = new Map<string, Promise<unknown>>()
let _streamActive = false

export interface SharedReadOptions {
  /** Hvor længe et svar må genbruges under normal drift. */
  ttlMs: number
  /** Hvor længe det må genbruges mens et run streamer (typisk meget længere). */
  streamingTtlMs?: number
}

/** Marker om et visible-run streamer lige nu (sættes fra StreamContext). */
export function setStreamActive(active: boolean): void {
  _streamActive = active
}

export function isStreamActive(): boolean {
  return _streamActive
}

function effectiveTtl(opts: SharedReadOptions): number {
  if (_streamActive && typeof opts.streamingTtlMs === 'number') {
    return Math.max(opts.ttlMs, opts.streamingTtlMs)
  }
  return opts.ttlMs
}

/** Læs via delt cache + in-flight dedup. Samme `key` = samme svar indenfor TTL. */
export async function sharedRead<T>(
  key: string,
  fetcher: () => Promise<T>,
  opts: SharedReadOptions,
): Promise<T> {
  const hit = _cache.get(key)
  if (hit && Date.now() - hit.at < effectiveTtl(opts)) {
    return hit.value as T
  }

  const pending = _inflight.get(key)
  if (pending) return pending as Promise<T>

  const p = (async () => {
    try {
      const value = await fetcher()
      _cache.set(key, { value, at: Date.now() })
      return value
    } finally {
      _inflight.delete(key)          // fejl → intet cachet, næste kald prøver igen
    }
  })()

  _inflight.set(key, p)
  return p
}

/** Ryd al delt state (kun til tests). */
export function __resetSharedRead(): void {
  _cache.clear()
  _inflight.clear()
  _streamActive = false
}
