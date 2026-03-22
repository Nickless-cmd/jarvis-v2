import { useEffect, useMemo, useState } from 'react'
import { backend } from '../lib/adapters'
import { appendMessagesToSession, createChatSession, updateSessionMessage } from '../lib/sessionState'

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function useUnifiedShell() {
  const [activeView, setActiveView] = useState('chat')
  const [shell, setShell] = useState(null)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [error, setError] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  async function refreshShell() {
    try {
      setIsRefreshing(true)
      const next = await backend.getShell()
      setShell(next)
      setSessions((current) => {
        if (current.length > 0) return current
        const initial = createChatSession({
          title: 'New chat',
          subtitle: next.chat.subtitle,
          bootstrapMessages: next.chat.bootstrapMessages,
        })
        setActiveSessionId(initial.id)
        return [initial]
      })
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load unified shell')
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    refreshShell()
  }, [])

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || sessions[0] || null,
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
    setSessions((current) =>
      current.map((session) =>
        session.id === sessionId
          ? appendMessagesToSession(session, userMessage, pendingAssistantMessage)
          : session
      )
    )

    try {
      const assistantMessage = await backend.streamMessage({
        content,
        onDelta: (_delta, fullText) => {
          setSessions((current) =>
            current.map((session) =>
              session.id === sessionId
                ? updateSessionMessage(session, assistantMessageId, () => ({
                    content: fullText,
                    pending: true,
                  }))
                : session
            )
          )
        },
      })

      setSessions((current) =>
        current.map((session) =>
          session.id === sessionId
            ? updateSessionMessage(session, assistantMessageId, () => ({
                id: assistantMessage.id,
                content: assistantMessage.content,
                ts: assistantMessage.ts,
                pending: false,
              }))
            : session
        )
      )
      await refreshShell()
    } catch (err) {
      const failure = err instanceof Error ? err.message : 'Chat failed'
      setSessions((current) =>
        current.map((session) =>
          session.id === sessionId
            ? updateSessionMessage(session, assistantMessageId, () => ({
                content: failure,
                ts: nowLabel(),
                pending: false,
              }))
            : session
        )
      )
      setError(failure)
    } finally {
      setIsStreaming(false)
    }
  }

  function handleCreateSession() {
    if (!shell) return
    const session = createChatSession({
      title: 'New chat',
      subtitle: shell.chat.subtitle,
      bootstrapMessages: shell.chat.bootstrapMessages,
    })
    setSessions((current) => [session, ...current])
    setActiveSessionId(session.id)
  }

  return {
    activeView,
    setActiveView,
    shell,
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    handleSelectionChange,
    handleSend,
    handleCreateSession,
    refreshShell,
    error,
    isRefreshing,
    isStreaming,
  }
}
