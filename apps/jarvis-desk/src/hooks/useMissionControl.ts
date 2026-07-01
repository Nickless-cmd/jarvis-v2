import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import {
  getMcRuns, getMcAgents, getMcScheduledTasks, getMcOverviewSafe,
  type McRun, type McAgent, type McScheduledTask, type McOverview,
} from '../lib/missionControlApi'

const POLL_MS = 6000

/** Mission Control-datalag: poller runs/agenter/planlagt/overblik hver 6s + live-nudge
 *  via /ws (polling-fallback hvis nede). Samme robusthed som useCoworkData. Godkendelser
 *  hentes separat via useCoworkData (actionable queue) i MC-containeren. */
export function useMissionControl(config: ApiConfig | undefined, isOwner: boolean) {
  const [runs, setRuns] = useState<McRun[]>([])
  const [activeRun, setActiveRun] = useState<{ run_id?: string; status?: string } | null>(null)
  const [failedCount, setFailedCount] = useState(0)
  const [agents, setAgents] = useState<McAgent[]>([])
  const [scheduled, setScheduled] = useState<McScheduledTask[]>([])
  const [overview, setOverview] = useState<McOverview | null>(null)

  const cfgRef = useRef(config)
  cfgRef.current = config
  const aliveRef = useRef(true)
  useEffect(() => {
    aliveRef.current = true
    return () => { aliveRef.current = false }
  }, [])
  const ifAlive = <T,>(fn: (v: T) => void) => (v: T) => { if (aliveRef.current) fn(v) }

  const refresh = useCallback(async () => {
    const cfg = cfgRef.current
    if (!cfg) return
    await Promise.allSettled([
      getMcRuns(cfg, 30).then(ifAlive((r) => {
        setRuns(r.recent_runs ?? [])
        setActiveRun(r.active_run ?? null)
        setFailedCount(r.summary?.failed_count ?? 0)
      })),
      isOwner ? getMcAgents(cfg).then(ifAlive((r) => setAgents(r.agents ?? []))) : Promise.resolve(),
      getMcScheduledTasks(cfg).then(ifAlive(setScheduled)),
      getMcOverviewSafe(cfg).then(ifAlive(setOverview)).catch(() => { /* overblik er blødt */ }),
    ])
  }, [isOwner])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(id)
  }, [refresh, config?.apiBaseUrl, config?.authToken])

  useEffect(() => {
    const cfg = cfgRef.current
    if (!cfg) return
    const wsUrl = cfg.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws'
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = () => { void refresh() }
      ws.onerror = () => { /* polling-fallback dækker */ }
    } catch { /* polling-fallback dækker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [refresh, config?.apiBaseUrl])

  return { runs, activeRun, failedCount, agents, scheduled, overview, refresh }
}
