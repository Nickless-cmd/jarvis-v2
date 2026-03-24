import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { backend } from '../lib/adapters'

const TAB_REFRESH_MS = {
  overview: 30000,
  operations: 20000,
  observability: 60000,
}

const RUN_RELATED_FAMILIES = new Set(['runtime'])
const APPROVAL_RELATED_FAMILIES = new Set(['approvals', 'tool', 'runtime'])
const OBS_RELATED_FAMILIES = new Set(['runtime', 'cost', 'approvals', 'incident', 'channel', 'tool'])

export function useMissionControlPhaseA({ active, selection }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [focusSection, setFocusSection] = useState('')
  const [data, setData] = useState({
    overview: null,
    operations: null,
    observability: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRealtimeEventAt, setLastRealtimeEventAt] = useState('')
  const [drawer, setDrawer] = useState(null)
  const refreshQueue = useRef(new Set())
  const refreshTimer = useRef(null)

  const applySelectionToOverview = useCallback((overview) => {
    if (!overview) return overview
    return {
      ...overview,
      cards: (overview.cards || []).map((card) =>
        card.id === 'lane-health'
          ? {
              ...card,
              value: `${selection?.currentProvider || 'unknown'} / ${selection?.currentModel || 'unknown'}`,
            }
          : card
      ),
    }
  }, [selection])

  const refreshOverview = useCallback(async () => {
    const overview = await backend.getMissionControlOverview({ selection })
    setData((current) => ({ ...current, overview: applySelectionToOverview(overview) }))
  }, [selection, applySelectionToOverview])

  const refreshOperations = useCallback(async () => {
    const operations = await backend.getMissionControlOperations()
    setData((current) => ({ ...current, operations }))
  }, [])

  const refreshObservability = useCallback(async () => {
    const observability = await backend.getMissionControlObservability()
    setData((current) => ({ ...current, observability }))
  }, [])

  const refreshAll = useCallback(async ({ background = false } = {}) => {
    if (background) {
      setIsRefreshing(true)
    } else {
      setIsLoading(true)
    }
    try {
      const next = await backend.getMissionControlPhaseA({ selection })
      setData({
        overview: applySelectionToOverview(next.overview),
        operations: next.operations,
        observability: next.observability,
      })
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [selection, applySelectionToOverview])

  const refreshTab = useCallback(async (tabId, { background = true } = {}) => {
    if (background) setIsRefreshing(true)
    try {
      if (tabId === 'overview') await refreshOverview()
      if (tabId === 'operations') await refreshOperations()
      if (tabId === 'observability') await refreshObservability()
    } finally {
      setIsRefreshing(false)
    }
  }, [refreshObservability, refreshOperations, refreshOverview])

  const scheduleRefresh = useCallback((tabs) => {
    tabs.forEach((tab) => refreshQueue.current.add(tab))
    if (refreshTimer.current) return
    refreshTimer.current = window.setTimeout(async () => {
      const pending = Array.from(refreshQueue.current)
      refreshQueue.current.clear()
      refreshTimer.current = null
      if (pending.length === 0) return
      setIsRefreshing(true)
      try {
        await Promise.all(
          pending.map((tab) => {
            if (tab === 'overview') return refreshOverview()
            if (tab === 'operations') return refreshOperations()
            if (tab === 'observability') return refreshObservability()
            return Promise.resolve()
          })
        )
      } finally {
        setIsRefreshing(false)
      }
    }, 600)
  }, [refreshObservability, refreshOperations, refreshOverview])

  useEffect(() => {
    if (!active) return
    refreshAll()
  }, [active, refreshAll])

  useEffect(() => {
    if (!active) return
    const stop = backend.subscribeMissionControlEvents((event) => {
      setLastRealtimeEventAt(event.createdAt || new Date().toISOString())
      setData((current) => ({
        ...current,
        overview: current.overview
          ? { ...current.overview, importantEvents: [event, ...(current.overview.importantEvents || [])].slice(0, 6) }
          : current.overview,
        observability: current.observability
          ? { ...current.observability, events: [event, ...(current.observability.events || [])].slice(0, 80) }
          : current.observability,
      }))

      const family = String(event.family || '')
      const tabs = []
      if (RUN_RELATED_FAMILIES.has(family)) tabs.push('overview', 'operations')
      if (APPROVAL_RELATED_FAMILIES.has(family)) tabs.push('overview', 'operations')
      if (OBS_RELATED_FAMILIES.has(family)) tabs.push('observability')
      if (tabs.length > 0) scheduleRefresh(tabs)
    })
    return () => {
      stop?.()
    }
  }, [active, scheduleRefresh])

  useEffect(() => {
    if (!active) return
    const every = TAB_REFRESH_MS[activeTab]
    if (!every) return
    const timer = window.setInterval(() => {
      refreshTab(activeTab, { background: true })
    }, every)
    return () => window.clearInterval(timer)
  }, [active, activeTab, refreshTab])

  useEffect(() => {
    return () => {
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current)
    }
  }, [])

  useEffect(() => {
    setData((current) => ({
      ...current,
      overview: applySelectionToOverview(current.overview),
    }))
  }, [selection, applySelectionToOverview])

  useEffect(() => {
    if (!focusSection) return
    const timer = window.setTimeout(() => {
      const node = document.getElementById(focusSection)
      node?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 40)
    return () => window.clearTimeout(timer)
  }, [activeTab, focusSection])

  const navigateTo = useCallback((tabId, sectionId = '') => {
    setActiveTab(tabId)
    setFocusSection(sectionId)
  }, [])

  const openRunDetail = useCallback((run) => {
    setDrawer({ kind: 'run', title: `Run ${run.runId || ''}`, item: run })
  }, [])

  const openEventDetail = useCallback((event) => {
    setDrawer({ kind: 'event', title: event.kind || 'Event detail', item: event })
  }, [])

  const openApprovalDetail = useCallback((approval) => {
    setDrawer({ kind: 'approval', title: approval.capabilityName || approval.requestId, item: approval, busy: false })
  }, [])

  const openSessionDetail = useCallback(async (session) => {
    setDrawer({ kind: 'session', title: session.title || 'Session', item: { ...session, loading: true } })
    try {
      const detail = await backend.getSession(session.id)
      setDrawer({ kind: 'session', title: detail.title || 'Session', item: detail })
    } catch (error) {
      setDrawer({
        kind: 'session',
        title: session.title || 'Session',
        item: {
          ...session,
          messages: [
            {
              id: 'session-load-error',
              role: 'assistant',
              content: error instanceof Error ? error.message : 'Failed to load session',
            },
          ],
        },
      })
    }
  }, [])

  const closeDrawer = useCallback(() => setDrawer(null), [])

  const actOnApproval = useCallback(async (requestId, action) => {
    setDrawer((current) => (current ? { ...current, busy: true } : current))
    try {
      if (action === 'approve') await backend.approveCapabilityRequest(requestId)
      if (action === 'execute') await backend.executeCapabilityRequest(requestId)
      await Promise.all([refreshOverview(), refreshOperations(), refreshObservability()])
      const updated = (await backend.getMissionControlOperations()).approvals.requests.find((item) => item.requestId === requestId)
      if (updated) {
        setDrawer({ kind: 'approval', title: updated.capabilityName || updated.requestId, item: updated, busy: false })
      } else {
        setDrawer(null)
      }
    } catch (error) {
      setDrawer((current) => (current ? { ...current, busy: false, error: error instanceof Error ? error.message : 'Action failed' } : current))
    }
  }, [refreshObservability, refreshOperations, refreshOverview])

  const sections = useMemo(() => data, [data])

  return {
    activeTab,
    setActiveTab,
    focusSection,
    sections,
    drawer,
    isLoading,
    isRefreshing,
    lastRealtimeEventAt,
    navigateTo,
    refreshAll,
    closeDrawer,
    openRunDetail,
    openEventDetail,
    openApprovalDetail,
    openSessionDetail,
    actOnApproval,
  }
}
