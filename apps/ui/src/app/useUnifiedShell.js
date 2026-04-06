import { useEffect, useMemo, useRef, useState } from 'react'
import { backend } from '../lib/adapters'
import { appendMessagesToSession, updateSessionMessage, upsertSessionMessage } from '../lib/sessionState'

const ACTIVE_SESSION_KEY = 'jarvis-ui-active-session'

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function rememberActiveSession(sessionId) {
  if (!sessionId || typeof window === 'undefined') return
  window.localStorage.setItem(ACTIVE_SESSION_KEY, sessionId)
}

function preferredSessionId() {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(ACTIVE_SESSION_KEY) || ''
}

export function useUnifiedShell() {
  const [activeView, setActiveView] = useState('chat')
  const [shell, setShell] = useState(null)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [error, setError] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeRunId, setActiveRunId] = useState(null)
  const [workingSteps, setWorkingSteps] = useState([])
  const [capabilityActivity, setCapabilityActivity] = useState([])
  const [lastRunTokens, setLastRunTokens] = useState(null)
  const [streamingTokenEstimate, setStreamingTokenEstimate] = useState(0)
  const [systemHealth, setSystemHealth] = useState({ cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 })
  const [jarvisSurface, setJarvisSurface] = useState(null)
  const liveSubscriptionStartedAtRef = useRef(Date.now())
  const jarvisSurfaceRefreshTimerRef = useRef(null)
  const jarvisSurfaceRefreshInFlightRef = useRef(false)

  async function refreshShell() {
    const next = await backend.getShell()
    setShell(next)
    return next
  }

  async function fetchJarvisSurface() {
    if (jarvisSurfaceRefreshInFlightRef.current) return
    jarvisSurfaceRefreshInFlightRef.current = true
    try {
      const data = await backend.getJarvisSurface()
      setJarvisSurface(data)
    } catch {
      /* silent */
    } finally {
      jarvisSurfaceRefreshInFlightRef.current = false
    }
  }

  function scheduleJarvisSurfaceRefresh(delay = 180) {
    if (typeof window === 'undefined') {
      void fetchJarvisSurface()
      return
    }
    if (jarvisSurfaceRefreshTimerRef.current) {
      window.clearTimeout(jarvisSurfaceRefreshTimerRef.current)
    }
    jarvisSurfaceRefreshTimerRef.current = window.setTimeout(() => {
      jarvisSurfaceRefreshTimerRef.current = null
      void fetchJarvisSurface()
    }, delay)
  }

  async function loadSessionList({ preferredId = '' } = {}) {
    const items = await backend.listSessions()
    setSessions(items)
    const nextId =
      preferredId ||
      activeSessionId ||
      preferredSessionId() ||
      items[0]?.id ||
      ''
    if (nextId) {
      await loadSession(nextId, { sessionList: items })
      return
    }
    const created = await backend.createSession('New chat')
    setSessions([{
      id: created.id,
      title: created.title,
      updated_at: created.updated_at,
      created_at: created.created_at,
      last_message: created.last_message || 'Ready',
      message_count: created.message_count || 0,
    }])
    await loadSession(created.id)
  }

  async function loadSession(sessionId, { sessionList } = {}) {
    const session = await backend.getSession(sessionId)
    setActiveSession(session)
    setActiveSessionId(session.id)
    rememberActiveSession(session.id)
    if (sessionList) {
      setSessions(sessionList)
    } else {
      const items = await backend.listSessions()
      setSessions(items)
    }
  }

  async function initialize() {
    try {
      setIsRefreshing(true)
      await refreshShell()
      await loadSessionList({ preferredId: preferredSessionId() })
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load unified shell')
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    initialize()
    async function pollHealth() {
      try {
        const health = await backend.getSystemHealth()
        setSystemHealth(health)
      } catch { /* ignore health poll failures */ }
    }
    pollHealth()
    const healthInterval = setInterval(pollHealth, 10000)
    void fetchJarvisSurface()
    const jarvisInterval = setInterval(fetchJarvisSurface, 30000)
    return () => {
      clearInterval(healthInterval)
      clearInterval(jarvisInterval)
      if (jarvisSurfaceRefreshTimerRef.current && typeof window !== 'undefined') {
        window.clearTimeout(jarvisSurfaceRefreshTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    liveSubscriptionStartedAtRef.current = Date.now()
    const stop = backend.subscribeMissionControlEvents((event) => {
      const createdAt = Date.parse(String(event.createdAt || ''))
      if (!Number.isNaN(createdAt) && createdAt < liveSubscriptionStartedAtRef.current) return

      scheduleJarvisSurfaceRefresh(event.kind === 'channel.chat_message_appended' ? 250 : 120)

      if (event.kind !== 'channel.chat_message_appended') return

      const payload = event.payload || {}
      if (payload.source !== 'proactive-execution-pilot') return
      if (String(payload.session_id || '') !== String(activeSessionId || '')) return

      const message = payload.message || {}
      setActiveSession((current) => (current ? upsertSessionMessage(current, message) : current))
      setSessions((current) =>
        current.map((session) =>
          session.id === String(payload.session_id || '')
            ? {
                ...session,
                last_message: String(message.content || session.last_message || 'Ready'),
                message_count: Math.max(Number(session.message_count || 0), 0) + 1,
                updated_at: String(message.created_at || session.updated_at || ''),
              }
            : session
        )
      )
    })
    return stop
  }, [activeSessionId])

  const activeSessionSummary = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || null,
    [sessions, activeSessionId]
  )

  async function handleSelectionChange(payload) {
    try {
      const selection = await backend.updateMainAgentSelection(payload)
      setShell((current) => (current ? { ...current, selection } : current))
      setError('')
      await refreshShell()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update main agent selection')
    }
  }

  async function handleSend(content) {
    if (!activeSession || isStreaming) return

    const sessionId = activeSession.id
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      ts: nowLabel(),
    }
    const assistantMessageId = `assistant-stream-${Date.now()}`
    const pendingAssistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      ts: nowLabel(),
      pending: true,
    }

    setIsStreaming(true)
    setActiveRunId(null)
    setError('')
    setLastRunTokens(null)
    setStreamingTokenEstimate(0)
    setCapabilityActivity([])
    setActiveSession((current) =>
      current ? appendMessagesToSession(current, userMessage, pendingAssistantMessage) : current
    )

    try {
      const assistantMessage = await backend.streamMessage({
        sessionId,
        content,
        onRun: (payload) => {
          if (payload?.run_id) setActiveRunId(payload.run_id)
        },
        onCapability: (payload) => {
          setCapabilityActivity((prev) => [...prev.slice(-7), {
            ...payload,
            ts: Date.now(),
          }])
        },
        onWorkingStep: (step) => {
          setWorkingSteps((prev) => {
            if (step.status === 'done') {
              return prev.map((s) =>
                s.step === step.step ? { ...s, status: 'done' } : s
              )
            }
            return [...prev.filter((s) => s.step !== step.step), step]
          })
        },
        onDelta: (_delta, fullText) => {
          setStreamingTokenEstimate(Math.round(fullText.length / 4))
          setActiveSession((current) =>
            current
              ? updateSessionMessage(current, assistantMessageId, () => ({
                  content: fullText,
                  pending: true,
                }))
              : current
          )
        },
        onDone: (payload) => {
          if (payload?.total_tokens) {
            setLastRunTokens({
              input: payload.input_tokens || 0,
              output: payload.output_tokens || 0,
              total: payload.total_tokens || 0,
            })
          }
        },
      })

      setActiveSession((current) =>
        current
          ? updateSessionMessage(current, assistantMessageId, () => ({
              id: assistantMessage.id,
              content: assistantMessage.content,
              ts: assistantMessage.ts,
              pending: false,
            }))
          : current
      )
      await loadSession(sessionId)
      await refreshShell()
    } catch (err) {
      const failure = err instanceof Error ? err.message : 'Chat failed'
      setActiveSession((current) =>
        current
          ? updateSessionMessage(current, assistantMessageId, () => ({
              content: failure,
              ts: nowLabel(),
              pending: false,
            }))
          : current
      )
      setError(failure)
    } finally {
      setIsStreaming(false)
      setActiveRunId(null)
      setWorkingSteps([])
      setStreamingTokenEstimate(0)
    }
  }

  async function handleCancel() {
    if (!activeRunId) return
    try {
      await backend.cancelRun(activeRunId)
    } catch {
      // Best-effort cancel
    }
  }

  async function handleRenameSession(title) {
    if (!activeSessionId || !title?.trim()) return
    try {
      await backend.renameSession(activeSessionId, title.trim())
      await loadSession(activeSessionId)
      await refreshShell()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename session')
    }
  }

  async function handleDeleteSession() {
    if (!activeSessionId) return
    try {
      await backend.deleteSession(activeSessionId)
      setActiveSession(null)
      setActiveSessionId(null)
      await refreshShell()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session')
    }
  }

  async function handleCreateSession() {
    try {
      const session = await backend.createSession('New chat')
      await loadSession(session.id)
      await refreshShell()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create chat session')
    }
  }

  async function handleSessionSelect(sessionId) {
    try {
      await loadSession(sessionId)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat session')
    }
  }

  async function handleRefresh() {
    try {
      setIsRefreshing(true)
      await refreshShell()
      if (activeSessionId) {
        await loadSession(activeSessionId)
      } else {
        await loadSessionList({ preferredId: preferredSessionId() })
      }
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh unified shell')
    } finally {
      setIsRefreshing(false)
    }
  }

  return {
    activeView,
    setActiveView,
    shell,
    sessions,
    activeSession: activeSession || activeSessionSummary,
    activeSessionId,
    handleSessionSelect,
    handleSelectionChange,
    handleSend,
    handleCancel,
    handleRenameSession,
    handleDeleteSession,
    handleCreateSession,
    refreshShell: handleRefresh,
    error,
    isRefreshing,
    isStreaming,
    workingSteps,
    capabilityActivity,
    systemHealth,
    jarvisSurface,
    lastRunTokens,
    streamingTokenEstimate,
  }
}
