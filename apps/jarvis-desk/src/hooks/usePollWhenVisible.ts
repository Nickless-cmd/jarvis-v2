import { useEffect, useState } from 'react'

/** Poll en async-fetcher KUN mens fanen faktisk er synlig (Bjørn 2026-06-23: Jarvis Mind
 *  må ikke hamre backenden konstant som det gamle MC). Polling pauser når:
 *   - komponenten er unmounted (anden zone/fane valgt), eller
 *   - browser-tab'en/vinduet er skjult (document.visibilityState === 'hidden').
 *  Henter straks ved (gen)synlighed, så data er friske når du kigger.
 *
 *  `enabled=false` slår polling helt fra (fx inaktiv fane i sub-navbaren). */
export function usePollWhenVisible<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled = true,
): { data: T | null; loading: boolean; error: string | null; refresh: () => void } {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!enabled) return
    let alive = true
    let timer: ReturnType<typeof setInterval> | null = null

    const poll = async () => {
      if (document.visibilityState === 'hidden') return  // skjult → spring over
      setLoading(true)
      try {
        const r = await fetcher()
        if (alive) { setData(r); setError(null) }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : 'fetch-fejl')
      } finally {
        if (alive) setLoading(false)
      }
    }

    void poll()                                  // straks ved mount/aktivering
    timer = setInterval(poll, intervalMs)
    const onVis = () => { if (document.visibilityState === 'visible') void poll() }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      alive = false
      if (timer) clearInterval(timer)
      document.removeEventListener('visibilitychange', onVis)
    }
    // tick tvinger en frisk poll ved refresh()
  }, [fetcher, intervalMs, enabled, tick])

  return { data, loading, error, refresh: () => setTick((t) => t + 1) }
}
