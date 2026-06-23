import { useEffect, useRef, useState } from 'react'

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

  // KRITISK (Bjørn 2026-06-23): hold fetcheren i en ref, så effekten IKKE afhænger af dens
  // identitet. Ellers river hver forælder-re-render (fx den konstante live-puls) poll'en ned
  // før fetch'en fuldfører → data sættes aldrig → evig "Henter…". Nu kører poll-cyklussen
  // stabilt; fetcherRef bruges altid med den nyeste closure.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    if (!enabled) return
    let alive = true
    let timer: ReturnType<typeof setInterval> | null = null

    const poll = async () => {
      if (document.visibilityState === 'hidden') return  // skjult → spring over
      setLoading(true)
      try {
        const r = await fetcherRef.current()
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
    // IKKE fetcher i deps — kun det der faktisk skal genstarte poll-cyklussen.
  }, [intervalMs, enabled, tick])

  return { data, loading, error, refresh: () => setTick((t) => t + 1) }
}
