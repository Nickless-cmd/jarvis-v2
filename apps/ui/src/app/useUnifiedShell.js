import { useEffect, useMemo, useState } from 'react'
import { backend } from '../lib/adapters'
import { appendMessagesToSession, createChatSession } from '../lib/sessionState'

export function useUnifiedShell() {
  const [activeView, setActiveView] = useState('chat')
  const [shell, setShell] = useState(null)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [error, setError] = useState('')

  async function refreshShell() {
    try {
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
    const selection = await backend.updateMainAgentSelection(payload)
    setShell((current) => (current ? { ...current, selection } : current))
    await refreshShell()
  }

  async function handleSend(content) {
    if (!activeSession) return

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setSessions((current) =>
      current.map((session) =>
        session.id === activeSession.id ? appendMessagesToSession(session, userMessage) : session
      )
    )

    try {
      const assistantMessage = await backend.sendMessage({ content })
      setSessions((current) =>
        current.map((session) =>
          session.id === activeSession.id
            ? appendMessagesToSession(session, assistantMessage)
            : session
        )
      )
      await refreshShell()
    } catch (err) {
      const failureMessage = {
        id: `assistant-failure-${Date.now()}`,
        role: 'assistant',
        content: err instanceof Error ? err.message : 'Chat failed',
        ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setSessions((current) =>
        current.map((session) =>
          session.id === activeSession.id
            ? appendMessagesToSession(session, failureMessage)
            : session
        )
      )
      setError(err instanceof Error ? err.message : 'Chat failed')
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
    error,
  }
}
