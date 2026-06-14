import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import {
  getCoworkQueue, getCoworkPlans, getCoworkTodos, getCoworkChannels, resolveQueueItem,
  getShareGuard, resolveShareGuard,
  type QueueItem, type CoworkPlan, type CoworkTodo, type CoworkChannel, type ShareDecision,
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
  const cfgRef = useRef(config)
  cfgRef.current = config

  const refresh = useCallback(async () => {
    const cfg = cfgRef.current
    if (!cfg) return
    await Promise.allSettled([
      getCoworkQueue(cfg).then(setQueue),
      getCoworkPlans(cfg).then(setPlans),
      getCoworkTodos(cfg).then(setTodos),
      isOwner ? getCoworkChannels(cfg).then(setChannels) : Promise.resolve(),
      isOwner ? getShareGuard(cfg).then(setShareGuard) : Promise.resolve(),
    ])
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
    const wsUrl = cfg.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws'
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = () => { void refresh() }
    } catch { /* polling-fallback dækker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
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

  return { queue, plans, todos, channels, shareGuard, refresh, resolve, resolveShare }
}
