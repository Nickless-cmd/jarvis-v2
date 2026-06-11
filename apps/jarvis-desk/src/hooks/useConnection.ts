import { useEffect, useState } from 'react'
import { pingServer } from '../lib/api'

export interface ConnectionState {
  online: boolean
  latencyMs: number | null
  host: string
}

/** Periodisk ping mod serveren (hver 10s) → forbindelses-status + latency. */
export function useConnection(config: { apiBaseUrl: string; authToken: string | null }): ConnectionState {
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [online, setOnline] = useState(false)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      const ms = await pingServer(config)
      if (!alive) return
      setLatencyMs(ms)
      setOnline(ms !== null)
    }
    void tick()
    const id = setInterval(tick, 10_000)
    return () => { alive = false; clearInterval(id) }
  }, [config.apiBaseUrl, config.authToken])

  let host = config.apiBaseUrl
  try { host = new URL(config.apiBaseUrl).host } catch { /* behold rå */ }
  return { online, latencyMs, host }
}
