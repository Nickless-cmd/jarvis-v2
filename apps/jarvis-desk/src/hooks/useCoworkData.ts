import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { openEventSocket } from '../lib/api'
import { lavTrailingThrottle, WS_GENHENT_MS } from '../lib/trailingThrottle'
import {
  getCoworkQueue, getCoworkPlans, getCoworkTodos, getCoworkChannels, resolveQueueItem,
  getShareGuard, resolveShareGuard, getCoworkAgents,
  type QueueItem, type CoworkPlan, type CoworkTodo, type CoworkChannel, type ShareDecision,
  type ActiveAgent,
} from '../lib/coworkApi'

const POLL_MS = 6000

/** Henter de fire datasæt + poller hver 6s + abonnerer på Mission Control-WS.
 *  channels hentes kun for owner. */
export function useCoworkData(config: ApiConfig | undefined, isOwner: boolean) {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [plans, setPlans] = useState<CoworkPlan[]>([])
  const [todos, setTodos] = useState<CoworkTodo[]>([])
  const [channels, setChannels] = useState<CoworkChannel[]>([])
  const [shareGuard, setShareGuard] = useState<ShareDecision[]>([])
  const [agents, setAgents] = useState<ActiveAgent[]>([])
  const cfgRef = useRef(config)
  cfgRef.current = config

  // Undgå setState efter unmount (async fetch/WS der lander efter teardown).
  const aliveRef = useRef(true)
  useEffect(() => {
    aliveRef.current = true
    return () => { aliveRef.current = false }
  }, [])
  const ifAlive = <T,>(fn: (v: T) => void) => (v: T) => { if (aliveRef.current) fn(v) }

  // Ét ad gangen (12/11-2026): pollen og WS-genhentningen må ikke køre oven i hinanden.
  const laeserRef = useRef(false)
  const refresh = useCallback(async () => {
    const cfg = cfgRef.current
    if (!cfg || laeserRef.current) return
    laeserRef.current = true
    try { await Promise.allSettled([
      getCoworkQueue(cfg).then(ifAlive(setQueue)),
      getCoworkPlans(cfg).then(ifAlive(setPlans)),
      getCoworkTodos(cfg).then(ifAlive(setTodos)),
      isOwner ? getCoworkChannels(cfg).then(ifAlive(setChannels)) : Promise.resolve(),
      isOwner ? getShareGuard(cfg).then(ifAlive(setShareGuard)) : Promise.resolve(),
      isOwner ? getCoworkAgents(cfg).then(ifAlive(setAgents)) : Promise.resolve(),
    ]) } finally { laeserRef.current = false }
  }, [isOwner])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(id)
  }, [refresh, config?.apiBaseUrl, config?.authToken])

  // Live-updates via Mission Control-websocket (polling-fallback dækker hvis nede).
  useEffect(() => {
    const cfg = cfgRef.current
    if (!cfg) return
    let ws: WebSocket | null = null
    // Throttlet (12/11-2026): HVER besked fra strømmen udløste før seks GET'er, og strømmen
    // sender hændelser hele tiden → ~490 × 429 pr. endpoint på 5 minutter.
    const genhent = lavTrailingThrottle(() => void refresh(), WS_GENHENT_MS)
    try {
      ws = openEventSocket(cfg)
      ws.onmessage = () => genhent.kald()
      ws.onerror = () => { /* polling-fallback dækker; sluger fejl-event så det ikke bobler */ }
    } catch { /* polling-fallback dækker */ }
    return () => { genhent.annuller(); try { ws?.close() } catch { /* noop */ } }
  }, [refresh, config?.apiBaseUrl])

  const resolve = useCallback(async (id: string, decision: 'approve' | 'reject') => {
    const cfg = cfgRef.current
    if (!cfg) return
    setQueue((q) => q.filter((i) => i.id !== id))
    try { await resolveQueueItem(cfg, id, decision) } finally { void refresh() }
  }, [refresh])

  // Cross-user share-guard (§4.4): "okay at dele" (shared=true) / "hold privat" (false).
  const resolveShare = useCallback(async (id: string, shared: boolean) => {
    const cfg = cfgRef.current
    if (!cfg) return
    setShareGuard((s) => s.filter((d) => d.id !== id))
    try { await resolveShareGuard(cfg, id, shared) } finally { void refresh() }
  }, [refresh])

  return { queue, plans, todos, channels, shareGuard, agents, refresh, resolve, resolveShare }
}
