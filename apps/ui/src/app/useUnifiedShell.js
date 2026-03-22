import { useEffect, useMemo, useState } from 'react'
import { backend } from '../lib/adapters'
import { appendMessagesToSession, updateSessionMessage } from '../lib/sessionState'

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

  async function refreshShell() {
    const next = await backend.getShell()
    setShell(next)
    return next
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
  }, [])

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
    setError('')
    setActiveSession((current) =>
      current ? appendMessagesToSession(current, userMessage, pendingAssistantMessage) : current
    )

    try {
      const assistantMessage = await backend.streamMessage({
        sessionId,
        content,
        onDelta: (_delta, fullText) => {
          setActiveSession((current) =>
            current
              ? updateSessionMessage(current, assistantMessageId, () => ({
                  content: fullText,
                  pending: true,
                }))
              : current
          )
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
    handleCreateSession,
    refreshShell: handleRefresh,
    error,
    isRefreshing,
    isStreaming,
  }
}
