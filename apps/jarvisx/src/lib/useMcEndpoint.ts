import { useEffect, useRef, useState } from 'react'

/**
 * Polls an /mc/* endpoint on a timer. Tiny, dependency-free wrapper —
 * all the heavy data work lives on the backend; the UI just renders.
 *
 * Why not SWR/TanStack Query? Two endpoints, one polling cadence,
 * dropping a 12 kB lib for that would be silly. If we end up with 10+
 * endpoints we'll switch.
 */
export function useMcEndpoint<T = unknown>(
  apiBaseUrl: string,
  path: string,
  intervalMs: number = 5000,
): {
  data: T | null
  loading: boolean
  error: string | null
  refresh: () => void
} {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const tickRef = useRef<number | null>(null)
  const aliveRef = useRef<boolean>(true)

  const fetchOnce = async () => {
    try {
      const url = apiBaseUrl.replace(/\/$/, '') + path
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = (await res.json()) as T
      if (!aliveRef.current) return
      setData(json)
      setError(null)
    } catch (e: unknown) {
      if (!aliveRef.current) return
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (aliveRef.current) setLoading(false)
    }
  }

  useEffect(() => {
    aliveRef.current = true
    void fetchOnce()
    if (intervalMs > 0) {
      tickRef.current = window.setInterval(fetchOnce, intervalMs)
    }
    return () => {
      aliveRef.current = false
      if (tickRef.current) {
        window.clearInterval(tickRef.current)
        tickRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBaseUrl, path, intervalMs])

  return { data, loading, error, refresh: fetchOnce }
}
