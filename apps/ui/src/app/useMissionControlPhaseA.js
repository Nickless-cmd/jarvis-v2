import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { backend } from '../lib/adapters'

const TAB_REFRESH_MS = {
  overview: 120000,
  operations: 120000,
  observability: 180000,
  jarvis: 300000,
}

const EVENT_REFRESH_MIN_MS = {
  overview: 30000,
  operations: 45000,
  observability: 60000,
  jarvis: 120000,
}

const RUN_RELATED_FAMILIES = new Set(['runtime'])
const APPROVAL_RELATED_FAMILIES = new Set(['approvals', 'tool', 'runtime'])
const OBS_RELATED_FAMILIES = new Set([
  'runtime',
  'cost',
  'approvals',
  'incident',
  'channel',
  'tool',
  'heartbeat',
  'open_loop_signal',
  'private_inner_note_signal',
  'private_initiative_tension_signal',
  'private_state_snapshot',
  'relation_continuity_signal',
  'regulation_homeostasis_signal',
  'witness_signal',
  'chronicle_consolidation_brief',
  'metabolism_state_signal',
  'release_marker_signal',
  'autonomy_pressure_signal',
  'proactive_loop_lifecycle',
  'proactive_question_gate',
  'execution_pilot',
])
const JARVIS_RELATED_FAMILIES = new Set([
  'heartbeat',
  'memory',
  'inner-voice',
  'self-model',
  'open_loop_signal',
  'private_inner_note_signal',
  'private_initiative_tension_signal',
  'private_state_snapshot',
  'relation_continuity_signal',
  'regulation_homeostasis_signal',
  'witness_signal',
  'chronicle_consolidation_brief',
  'metabolism_state_signal',
  'release_marker_signal',
  'autonomy_pressure_signal',
  'proactive_loop_lifecycle',
  'proactive_question_gate',
  'execution_pilot',
])

const MC_TAB_KEY = 'jarvis-mc-active-tab'

function preferredMcTab() {
  if (typeof window === 'undefined') return 'overview'
  return window.localStorage.getItem(MC_TAB_KEY) || 'overview'
}

export function useMissionControlPhaseA({ active, selection }) {
  const [activeTab, setActiveTab] = useState(preferredMcTab)

  function setActiveTabPersisted(tab) {
    window.localStorage.setItem(MC_TAB_KEY, tab)
    setActiveTab(tab)
  }
  const [focusSection, setFocusSection] = useState('')
  const [data, setData] = useState({
    overview: null,
    operations: null,
    observability: null,
    jarvis: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRealtimeEventAt, setLastRealtimeEventAt] = useState('')
  const [drawer, setDrawer] = useState(null)
  const [toolIntentActionState, setToolIntentActionState] = useState({ busy: false, error: '' })
  const refreshQueue = useRef(new Set())
  const refreshTimer = useRef(null)
  const inflightRefreshes = useRef(new Map())
  const lastEventRefreshAt = useRef(new Map())

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

  const runRefresh = useCallback((key, loader) => {
    const current = inflightRefreshes.current.get(key)
    if (current) return current
    const pending = Promise.resolve()
      .then(loader)
      .finally(() => {
        if (inflightRefreshes.current.get(key) === pending) {
          inflightRefreshes.current.delete(key)
        }
      })
    inflightRefreshes.current.set(key, pending)
    return pending
  }, [])

  const refreshOverview = useCallback(async () => {
    await runRefresh('overview', async () => {
      const overview = await backend.getMissionControlOverview({ selection })
      setData((current) => ({ ...current, overview: applySelectionToOverview(overview) }))
    })
  }, [selection, applySelectionToOverview, runRefresh])

  const refreshOperations = useCallback(async () => {
    await runRefresh('operations', async () => {
      const operations = await backend.getMissionControlOperations()
      setData((current) => ({ ...current, operations }))
    })
  }, [runRefresh])

  const refreshObservability = useCallback(async () => {
    await runRefresh('observability', async () => {
      const observability = await backend.getMissionControlObservability()
      setData((current) => ({ ...current, observability }))
    })
  }, [runRefresh])

  const refreshJarvis = useCallback(async () => {
    await runRefresh('jarvis', async () => {
      const jarvis = await backend.getMissionControlJarvis()
      setData((current) => ({ ...current, jarvis }))
    })
  }, [runRefresh])

  const isJarvisTab = useCallback(
    (tabId) => ['mind', 'reflection'].includes(tabId),
    []
  )

  const refreshAll = useCallback(async ({ background = false } = {}) => {
    if (background) {
      setIsRefreshing(true)
    } else {
      setIsLoading(true)
    }
    try {
      if (background && isJarvisTab(activeTab)) {
        const next = await backend.getMissionControlPhaseB({ selection })
        setData({
          overview: applySelectionToOverview(next.overview),
          operations: next.operations,
          observability: next.observability,
          jarvis: next.jarvis,
        })
        return
      }

      const overview = await backend.getMissionControlOverview({ selection })
      setData((current) => ({
        overview: applySelectionToOverview(overview),
        operations: current.operations,
        observability: current.observability,
        jarvis: current.jarvis,
      }))

      void (async () => {
        await refreshOperations()
        await refreshObservability()
      })()
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [selection, applySelectionToOverview, activeTab, isJarvisTab, refreshJarvis])

  const refreshTab = useCallback(async (tabId, { background = true } = {}) => {
    if (background) setIsRefreshing(true)
    try {
      if (tabId === 'overview') await refreshOverview()
      if (tabId === 'operations') await refreshOperations()
      if (tabId === 'observability') await refreshObservability()
      if (tabId === 'jarvis') await refreshJarvis()
    } finally {
      setIsRefreshing(false)
    }
  }, [refreshJarvis, refreshObservability, refreshOperations, refreshOverview])

  const scheduleRefresh = useCallback((tabs) => {
    if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return
    tabs.forEach((tab) => refreshQueue.current.add(tab))
    if (refreshTimer.current) return
    refreshTimer.current = window.setTimeout(async () => {
      const now = Date.now()
      const pending = Array.from(refreshQueue.current).filter((tab) => {
        const minInterval = EVENT_REFRESH_MIN_MS[tab] || 0
        const lastRun = lastEventRefreshAt.current.get(tab) || 0
        return now - lastRun >= minInterval
      })
      refreshQueue.current.clear()
      refreshTimer.current = null
      if (pending.length === 0) return
      setIsRefreshing(true)
      try {
        for (const tab of pending) {
          if (tab === 'overview') await refreshOverview()
          if (tab === 'operations') await refreshOperations()
          if (tab === 'observability') await refreshObservability()
          if (tab === 'jarvis') await refreshJarvis()
        }
        const completedAt = Date.now()
        pending.forEach((tab) => {
          lastEventRefreshAt.current.set(tab, completedAt)
        })
      } finally {
        setIsRefreshing(false)
      }
    }, 1500)
  }, [refreshJarvis, refreshObservability, refreshOperations, refreshOverview])

  useEffect(() => {
    if (!active) return
    refreshAll()
  }, [active, refreshAll])

  useEffect(() => {
    if (!active) return
    if (activeTab === 'operations' && !data.operations) {
      refreshOperations()
      return
    }
    if (activeTab === 'observability' && !data.observability) {
      refreshObservability()
      return
    }
    if (isJarvisTab(activeTab) && !data.jarvis) {
      refreshJarvis()
    }
  }, [active, activeTab, data.jarvis, data.observability, data.operations, isJarvisTab, refreshJarvis, refreshObservability, refreshOperations])

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
      if (JARVIS_RELATED_FAMILIES.has(family) && (data.jarvis || isJarvisTab(activeTab))) tabs.push('jarvis')
      if (tabs.length > 0) scheduleRefresh(tabs)
    })
    return () => {
      stop?.()
    }
  }, [active, activeTab, data.jarvis, isJarvisTab, scheduleRefresh])

  useEffect(() => {
    if (!active) return
    const every = TAB_REFRESH_MS[activeTab]
    if (!every) return
    const timer = window.setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return
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
    setActiveTabPersisted(tabId)
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

  const openJarvisDetail = useCallback((title, item) => {
    let kind = 'jarvis'
    if (item?.candidateId) kind = 'contract-candidate'
    else if (item?.kind === 'approval-gated-tool-intent-light') kind = 'tool-intent'
    else if (item?.focusId) kind = 'development-focus'
    setDrawer({
      kind,
      title,
      item,
      busy: false,
    })
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

  const actOnToolIntent = useCallback(async (action) => {
    setToolIntentActionState({ busy: true, error: '' })
    try {
      let response = null
      if (action === 'approve') response = await backend.approveToolIntent()
      if (action === 'deny') response = await backend.denyToolIntent()
      const [operations, jarvis] = await Promise.all([
        backend.getMissionControlOperations(),
        data.jarvis ? backend.getMissionControlJarvis() : Promise.resolve(null),
      ])
      setData((current) => ({
        ...current,
        operations,
        jarvis: jarvis || current.jarvis,
      }))
      setToolIntentActionState({ busy: false, error: '' })
      return response
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Action failed'
      setToolIntentActionState({ busy: false, error: message })
      throw error
    }
  }, [data.jarvis])

  const actOnContractCandidate = useCallback(async (candidateId, action) => {
    setDrawer((current) => (current ? { ...current, busy: true, error: '' } : current))
    try {
      let response = null
      if (action === 'approve') response = await backend.approveRuntimeContractCandidate(candidateId)
      if (action === 'reject') response = await backend.rejectRuntimeContractCandidate(candidateId)
      if (action === 'apply') response = await backend.applyRuntimeContractCandidate(candidateId)
      const jarvis = await backend.getMissionControlJarvis()
      setData((current) => ({ ...current, jarvis }))

      const pendingWrites = jarvis?.contract?.pendingWrites || []
      const responseCandidate = response?.candidate
        ? {
            candidateId: response.candidate.candidate_id || '',
            candidateType: response.candidate.candidate_type || '',
            targetFile: response.candidate.target_file || '',
            status: response.candidate.status || 'unknown',
            sourceKind: response.candidate.source_kind || '',
            sourceMode: response.candidate.source_mode || '',
            actor: response.candidate.actor || '',
            sessionId: response.candidate.session_id || '',
            runId: response.candidate.run_id || '',
            canonicalKey: response.candidate.canonical_key || '',
            summary: response.candidate.summary || 'Candidate detail',
            reason: response.candidate.reason || '',
            evidenceSummary: response.candidate.evidence_summary || '',
            supportSummary: response.candidate.support_summary || '',
            statusReason: response.candidate.status_reason || '',
            proposedValue: response.candidate.proposed_value || '',
            writeSection: response.candidate.write_section || '',
            confidence: response.candidate.confidence || '',
            evidenceClass: response.candidate.evidence_class || '',
            supportCount: Number(response.candidate.support_count || 0),
            sessionCount: Number(response.candidate.session_count || 0),
            mergeCount: Number(response.candidate.merge_count || 0),
            source: '/mc/runtime-contract',
            createdAt: response.candidate.created_at || '',
            updatedAt: response.candidate.updated_at || '',
            write: response?.write || null,
          }
        : null
      const updatedCandidate = responseCandidate
        || pendingWrites.flatMap((workflow) => workflow.items || []).find((item) => item.candidateId === candidateId)

      if (updatedCandidate) {
        setDrawer({
          kind: updatedCandidate.candidateId ? 'contract-candidate' : 'jarvis',
          title: updatedCandidate.summary || 'Candidate detail',
          item: updatedCandidate,
          busy: false,
        })
      } else {
        setDrawer(null)
      }
    } catch (error) {
      setDrawer((current) => (
        current
          ? { ...current, busy: false, error: error instanceof Error ? error.message : 'Action failed' }
          : current
      ))
    }
  }, [refreshJarvis])

  const actOnDevelopmentFocus = useCallback(async (focusId, action) => {
    if (action !== 'complete') return
    setDrawer((current) => (current ? { ...current, busy: true, error: '' } : current))
    try {
      const response = await backend.completeDevelopmentFocus(focusId)
      const jarvis = await backend.getMissionControlJarvis()
      setData((current) => ({ ...current, jarvis }))
      if (response?.focus) {
        setDrawer({
          kind: 'development-focus',
          title: response.focus.title || 'Development Focus',
          item: { ...response.focus, source: '/mc/jarvis/development-focus' },
          busy: false,
        })
      } else {
        setDrawer(null)
      }
    } catch (error) {
      setDrawer((current) => (
        current
          ? { ...current, busy: false, error: error instanceof Error ? error.message : 'Action failed' }
          : current
      ))
    }
  }, [refreshJarvis])

  const actOnHeartbeatTick = useCallback(async () => {
    setIsRefreshing(true)
    try {
      const response = await backend.runHeartbeatTick()
      const jarvis = await backend.getMissionControlJarvis()
      setData((current) => ({ ...current, jarvis }))
      if (response?.tick) {
        setDrawer({
          kind: 'jarvis',
          title: 'Heartbeat Tick',
          item: {
            ...response.tick,
            source: '/mc/heartbeat/tick',
            summary: response.tick.decision_summary || response.tick.action_summary || 'Heartbeat tick detail',
            createdAt: response.tick.finished_at || response.tick.started_at || '',
          },
          busy: false,
        })
      }
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  const sections = useMemo(() => data, [data])

  return {
    activeTab,
    setActiveTab: setActiveTabPersisted,
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
    openJarvisDetail,
    actOnApproval,
    actOnToolIntent,
    actOnContractCandidate,
    actOnHeartbeatTick,
    actOnDevelopmentFocus,
    toolIntentActionBusy: toolIntentActionState.busy,
    toolIntentActionError: toolIntentActionState.error,
  }
}
